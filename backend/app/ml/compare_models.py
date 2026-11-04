import os
import copy
import warnings
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from pytorch_tabnet.tab_model import TabNetClassifier

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(
    BASE_DIR, "datasets", "smoke_detection_iot.csv"
)

FEATURES = [
    "Temperature[C]",
    "Humidity[%]",
    "TVOC[ppb]",
    "eCO2[ppm]",
    "PM1.0",
    "PM2.5"
]

TARGET = "Fire Alarm"

RANDOM_STATE = 42
EPOCHS = 60
PATIENCE = 10
BATCH_SIZE = 512

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)


# --------------------------------------------------
# FT-TRANSFORMER MODEL
# --------------------------------------------------

class FTTransformer(nn.Module):

    def __init__(self, n_features, d_model=32, heads=4):

        super().__init__()

        self.weight = nn.Parameter(
            torch.randn(n_features, d_model) * 0.02
        )

        self.bias = nn.Parameter(
            torch.zeros(n_features, d_model)
        )

        self.cls_token = nn.Parameter(
            torch.zeros(1, 1, d_model)
        )

        self.encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=heads,
            dim_feedforward=64,
            dropout=0.1,
            batch_first=True,
            activation="gelu"
        )

        self.encoder = nn.TransformerEncoder(
            self.encoder_layer,
            num_layers=2
        )

        self.output = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, 1)
        )

    def forward(self, x):

        tokens = (
            x.unsqueeze(-1) * self.weight.unsqueeze(0)
            + self.bias.unsqueeze(0)
        )

        cls = self.cls_token.expand(
            x.size(0), -1, -1
        )

        tokens = torch.cat([cls, tokens], dim=1)
        encoded = self.encoder(tokens)

        return self.output(encoded[:, 0]).squeeze(1)


# --------------------------------------------------
# SAINT-STYLE TABULAR TRANSFORMER
# --------------------------------------------------

class SAINTStyle(nn.Module):

    def __init__(self, n_features, d_model=32, heads=4):

        super().__init__()

        self.weight = nn.Parameter(
            torch.randn(n_features, d_model) * 0.02
        )

        self.bias = nn.Parameter(
            torch.zeros(n_features, d_model)
        )

        self.attention = nn.MultiheadAttention(
            embed_dim=d_model,
            num_heads=heads,
            dropout=0.1,
            batch_first=True
        )

        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)

        self.feed_forward = nn.Sequential(
            nn.Linear(d_model, 64),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(64, d_model)
        )

        self.output = nn.Sequential(
            nn.Linear(d_model, 32),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(32, 1)
        )

    def forward(self, x):

        tokens = (
            x.unsqueeze(-1) * self.weight.unsqueeze(0)
            + self.bias.unsqueeze(0)
        )

        attended, _ = self.attention(
            tokens, tokens, tokens
        )

        tokens = self.norm1(tokens + attended)
        tokens = self.norm2(
            tokens + self.feed_forward(tokens)
        )

        pooled = tokens.mean(dim=1)

        return self.output(pooled).squeeze(1)


# --------------------------------------------------
# PYTORCH TRAINING FUNCTION
# --------------------------------------------------

def train_torch_model(model, X_train, y_train,
                      X_val, y_val):

    model = model.to(DEVICE)

    train_x = torch.tensor(
        X_train, dtype=torch.float32
    )

    train_y = torch.tensor(
        y_train, dtype=torch.float32
    )

    val_x = torch.tensor(
        X_val, dtype=torch.float32
    ).to(DEVICE)

    val_y = torch.tensor(
        y_val, dtype=torch.float32
    ).to(DEVICE)

    loader = DataLoader(
        TensorDataset(train_x, train_y),
        batch_size=BATCH_SIZE,
        shuffle=True
    )

    optimizer = torch.optim.Adam(
        model.parameters(), lr=0.001
    )

    loss_function = nn.BCEWithLogitsLoss()

    best_loss = float("inf")
    best_weights = None
    patience_count = 0
    best_epoch = 0

    for epoch in range(EPOCHS):

        model.train()
        total_loss = 0

        for batch_x, batch_y in loader:

            batch_x = batch_x.to(DEVICE)
            batch_y = batch_y.to(DEVICE)

            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = loss_function(outputs, batch_y)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        model.eval()

        with torch.no_grad():
            val_outputs = model(val_x)
            val_loss = loss_function(
                val_outputs, val_y
            ).item()

        if val_loss < best_loss:

            best_loss = val_loss
            best_weights = copy.deepcopy(
                model.state_dict()
            )
            best_epoch = epoch + 1
            patience_count = 0

        else:
            patience_count += 1

        if (epoch + 1) % 10 == 0:
            print(
                "Epoch:", epoch + 1,
                "Train Loss:", round(
                    total_loss / len(loader), 4
                ),
                "Validation Loss:", round(val_loss, 4)
            )

        if patience_count >= PATIENCE:
            print("Early stopping at epoch:", epoch + 1)
            break

    if best_weights is not None:
        model.load_state_dict(best_weights)

    return model, best_epoch


def torch_predict(model, X):

    model.eval()

    values = torch.tensor(
        X, dtype=torch.float32
    ).to(DEVICE)

    with torch.no_grad():
        logits = model(values)
        probabilities = torch.sigmoid(logits)

    return probabilities.cpu().numpy()


# --------------------------------------------------
# PROBABILITY CALIBRATION
# --------------------------------------------------

def calibrate_predictions(cal_prob, y_cal, test_prob):

    cal_prob = np.clip(cal_prob, 1e-6, 1 - 1e-6)
    test_prob = np.clip(test_prob, 1e-6, 1 - 1e-6)

    cal_logits = np.log(
        cal_prob / (1 - cal_prob)
    ).reshape(-1, 1)

    test_logits = np.log(
        test_prob / (1 - test_prob)
    ).reshape(-1, 1)

    calibrator = LogisticRegression(max_iter=1000)
    calibrator.fit(cal_logits, y_cal)

    return calibrator.predict(test_logits)


# --------------------------------------------------
# EVALUATION FUNCTION
# --------------------------------------------------

def evaluate_model(name, y_test, predictions):

    accuracy = accuracy_score(y_test, predictions)
    precision = precision_score(
        y_test, predictions, zero_division=0
    )
    recall = recall_score(
        y_test, predictions, zero_division=0
    )
    f1 = f1_score(
        y_test, predictions, zero_division=0
    )

    print("\n", name)
    print(
        classification_report(
            y_test, predictions, zero_division=0
        )
    )

    print("Confusion Matrix:")
    print(confusion_matrix(y_test, predictions))

    return {
        "Model": name,
        "Accuracy": round(accuracy * 100, 2),
        "Precision": round(precision * 100, 2),
        "Recall": round(recall * 100, 2),
        "F1 Score": round(f1 * 100, 2)
    }


# --------------------------------------------------
# MAIN COMPARISON
# --------------------------------------------------

def compare_models():

    print("\nEVAC-TWIN - ML AND DL MODEL COMPARISON")
    print("Device:", DEVICE)

    # Load and clean dataset

    data = pd.read_csv(DATA_PATH)
    data = data[FEATURES + [TARGET]].copy()
    data = data.replace([np.inf, -np.inf], np.nan)
    data = data.dropna()

    X = data[FEATURES]
    y = data[TARGET].astype(int)

    print("\nTotal samples:", len(X))

    # Same split is used for all eight models:
    # 70% training, 10% validation,
    # 10% calibration, 10% testing.

    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y,
        test_size=0.30,
        random_state=RANDOM_STATE,
        stratify=y
    )

    X_val, X_temp, y_val, y_temp = train_test_split(
        X_temp, y_temp,
        test_size=2/3,
        random_state=RANDOM_STATE,
        stratify=y_temp
    )

    X_cal, X_test, y_cal, y_test = train_test_split(
        X_temp, y_temp,
        test_size=0.50,
        random_state=RANDOM_STATE,
        stratify=y_temp
    )

    print("\nDATA SPLIT")
    print("Training:", len(X_train))
    print("Validation:", len(X_val))
    print("Calibration:", len(X_cal))
    print("Testing:", len(X_test))

    # Scaling is fitted only on training data.
    # The same scaled splits are used by DL models.

    scaler = StandardScaler()

    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)
    X_cal_s = scaler.transform(X_cal)
    X_test_s = scaler.transform(X_test)

    results = []

    # --------------------------------------------------
    # 1-4. TRADITIONAL ML MODELS
    # --------------------------------------------------

    models = {

        "Random Forest": RandomForestClassifier(
            n_estimators=150,
            max_depth=16,
            min_samples_leaf=2,
            random_state=RANDOM_STATE,
            class_weight="balanced",
            n_jobs=-1
        ),

        "Logistic Regression": make_pipeline(
            StandardScaler(),
            LogisticRegression(
                max_iter=1000,
                class_weight="balanced"
            )
        ),

        "KNN": make_pipeline(
            StandardScaler(),
            KNeighborsClassifier(n_neighbors=5)
        ),

        "SVM": make_pipeline(
            StandardScaler(),
            SVC(
                class_weight="balanced",
                probability=True,
                random_state=RANDOM_STATE
            )
        )
    }

    for name, model in models.items():

        print("\nTraining:", name)

        # All models learn from exactly X_train, y_train.
        model.fit(X_train, y_train)

        # All models use the same calibration and test sets.
        cal_prob = model.predict_proba(X_cal)[:, 1]
        test_prob = model.predict_proba(X_test)[:, 1]

        predictions = calibrate_predictions(
            cal_prob, y_cal, test_prob
        )

        results.append(
            evaluate_model(name, y_test, predictions)
        )

    # --------------------------------------------------
    # 5. MLP
    # --------------------------------------------------

    print("\nTraining: Deep Learning MLP")

    mlp = make_pipeline(
        StandardScaler(),
        MLPClassifier(
            hidden_layer_sizes=(128, 64),
            activation="relu",
            solver="adam",
            alpha=0.0001,
            learning_rate_init=0.001,
            batch_size=256,
            max_iter=100,
            early_stopping=True,
            random_state=RANDOM_STATE
        )
    )

    # MLP also learns from the same X_train, y_train.
    mlp.fit(X_train, y_train)

    cal_prob = mlp.predict_proba(X_cal)[:, 1]
    test_prob = mlp.predict_proba(X_test)[:, 1]

    predictions = calibrate_predictions(
        cal_prob, y_cal, test_prob
    )

    results.append(
        evaluate_model(
            "Deep Learning MLP", y_test, predictions
        )
    )

    # --------------------------------------------------
    # 6. TABNET
    # --------------------------------------------------

    print("\nTraining: TabNet")

    tabnet = TabNetClassifier(
        n_d=16,
        n_a=16,
        n_steps=5,
        gamma=1.5,
        lambda_sparse=1e-4,
        optimizer_params={"lr": 0.02},
        seed=RANDOM_STATE,
        verbose=10
    )

    tabnet.fit(
        X_train=X_train_s.astype(np.float32),
        y_train=y_train.to_numpy(),
        eval_set=[
            (
                X_train_s.astype(np.float32),
                y_train.to_numpy()
            ),
            (
                X_val_s.astype(np.float32),
                y_val.to_numpy()
            )
        ],
        eval_name=["train", "validation"],
        eval_metric=["auc"],
        max_epochs=100,
        patience=15,
        batch_size=1024,
        virtual_batch_size=128,
        num_workers=0,
        drop_last=False
    )

    cal_prob = tabnet.predict_proba(
        X_cal_s.astype(np.float32)
    )[:, 1]

    test_prob = tabnet.predict_proba(
        X_test_s.astype(np.float32)
    )[:, 1]

    predictions = calibrate_predictions(
        cal_prob, y_cal, test_prob
    )

    results.append(
        evaluate_model("TabNet", y_test, predictions)
    )

    # --------------------------------------------------
    # 7. FT-TRANSFORMER
    # --------------------------------------------------

    print("\nTraining: FT-Transformer")

    ft_model = FTTransformer(
        n_features=len(FEATURES)
    )

    ft_model, ft_epochs = train_torch_model(
        ft_model,
        X_train_s.astype(np.float32),
        y_train.to_numpy().astype(np.float32),
        X_val_s.astype(np.float32),
        y_val.to_numpy().astype(np.float32)
    )

    cal_prob = torch_predict(
        ft_model, X_cal_s.astype(np.float32)
    )

    test_prob = torch_predict(
        ft_model, X_test_s.astype(np.float32)
    )

    predictions = calibrate_predictions(
        cal_prob, y_cal, test_prob
    )

    results.append(
        evaluate_model(
            "FT-Transformer", y_test, predictions
        )
    )

    print("FT-Transformer best epoch:", ft_epochs)

    # --------------------------------------------------
    # 8. SAINT-STYLE TRANSFORMER
    # --------------------------------------------------

    print("\nTraining: SAINT-style Transformer")

    saint_model = SAINTStyle(
        n_features=len(FEATURES)
    )

    saint_model, saint_epochs = train_torch_model(
        saint_model,
        X_train_s.astype(np.float32),
        y_train.to_numpy().astype(np.float32),
        X_val_s.astype(np.float32),
        y_val.to_numpy().astype(np.float32)
    )

    cal_prob = torch_predict(
        saint_model, X_cal_s.astype(np.float32)
    )

    test_prob = torch_predict(
        saint_model, X_test_s.astype(np.float32)
    )

    predictions = calibrate_predictions(
        cal_prob, y_cal, test_prob
    )

    results.append(
        evaluate_model(
            "SAINT-style Transformer", y_test, predictions
        )
    )

    print("SAINT-style best epoch:", saint_epochs)

    # --------------------------------------------------
    # FINAL COMPARISON
    # --------------------------------------------------

    results_df = pd.DataFrame(results)

    results_df = results_df.sort_values(
        by="F1 Score",
        ascending=False
    )

    print("\nFINAL MODEL COMPARISON")
    print(results_df.to_string(index=False))

    print("\nBEST MODEL:")
    print(results_df.iloc[0]["Model"])

    output_path = os.path.join(
        BASE_DIR, "model_comparison_results.csv"
    )

    results_df.to_csv(output_path, index=False)

    print("\nResults saved to:", output_path)


if __name__ == "__main__":
    compare_models()
