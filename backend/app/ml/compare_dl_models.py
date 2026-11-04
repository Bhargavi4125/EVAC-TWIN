
import os
import warnings
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, classification_report, confusion_matrix
)

from pytorch_tabnet.tab_model import TabNetClassifier

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(
    BASE_DIR, "datasets", "smoke_detection_iot.csv"
)

FEATURES = [
    "Temperature[C]", "Humidity[%]", "TVOC[ppb]",
    "eCO2[ppm]", "PM1.0", "PM2.5"
]

TARGET = "Fire Alarm"


def compare_dl_models():

    print("\nEVAC-TWIN - DEEP LEARNING MODEL COMPARISON")

    # Load and clean dataset
    data = pd.read_csv(DATA_PATH)
    data = data[FEATURES + [TARGET]].copy()
    data = data.replace([np.inf, -np.inf], np.nan)
    data = data.dropna()

    X = data[FEATURES].astype(np.float32)
    y = data[TARGET].astype(int)

    print("Total samples:", len(X))

    # 70% training, 10% validation,
    # 10% calibration, 10% testing
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.30,
        random_state=42, stratify=y
    )

    X_val, X_temp, y_val, y_temp = train_test_split(
        X_temp, y_temp, test_size=2/3,
        random_state=42, stratify=y_temp
    )

    X_cal, X_test, y_cal, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50,
        random_state=42, stratify=y_temp
    )

    print("\nDATA SPLIT")
    print("Training:", len(X_train))
    print("Validation:", len(X_val))
    print("Calibration:", len(X_cal))
    print("Testing:", len(X_test))

    # Convert data into NumPy arrays
    X_train_np = X_train.to_numpy()
    X_val_np = X_val.to_numpy()
    X_cal_np = X_cal.to_numpy()
    X_test_np = X_test.to_numpy()

    y_train_np = y_train.to_numpy()
    y_val_np = y_val.to_numpy()
    y_cal_np = y_cal.to_numpy()

    # TabNet model
    model = TabNetClassifier(
        n_d=16,
        n_a=16,
        n_steps=5,
        gamma=1.5,
        lambda_sparse=1e-4,
        optimizer_params=dict(lr=0.02),
        seed=42,
        verbose=10
    )

    print("\nTRAINING TABNET")

    model.fit(
        X_train=X_train_np,
        y_train=y_train_np,
        eval_set=[
            (X_train_np, y_train_np),
            (X_val_np, y_val_np)
        ],
        eval_name=["train", "validation"],
        eval_metric=["auc"],
        max_epochs=100,
        patience=15,
        batch_size=1024,
        virtual_batch_size=128,
        num_workers=0,
        drop_last=False,
        weights=1
    )

    # Calibration using separate calibration data
    raw_prob = model.predict_proba(X_cal_np)[:, 1]
    raw_prob = np.clip(raw_prob, 1e-6, 1 - 1e-6)

    logits = np.log(raw_prob / (1 - raw_prob)).reshape(-1, 1)

    calibrator = LogisticRegression()
    calibrator.fit(logits, y_cal_np)

    # Final testing
    test_prob = model.predict_proba(X_test_np)[:, 1]
    test_prob = np.clip(test_prob, 1e-6, 1 - 1e-6)

    test_logits = np.log(
        test_prob / (1 - test_prob)
    ).reshape(-1, 1)

    predictions = calibrator.predict(test_logits)

    # Evaluation
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

    print("\nTABNET CLASSIFICATION REPORT")
    print(classification_report(
        y_test, predictions, zero_division=0
    ))

    print("Confusion Matrix:")
    print(confusion_matrix(y_test, predictions))

    results = pd.DataFrame([{
        "Model": "TabNet",
        "Accuracy": round(accuracy * 100, 2),
        "Precision": round(precision * 100, 2),
        "Recall": round(recall * 100, 2),
        "F1 Score": round(f1 * 100, 2)
    }])

    print("\nTABNET RESULTS")
    print(results.to_string(index=False))


if __name__ == "__main__":
    compare_dl_models()
