
import os
import numpy as np
import torch
import torch.nn as nn
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_DIR = os.path.join(BASE_DIR, "models")

MODEL_PATH = os.path.join(MODEL_DIR, "risk_model.pth")
SCALER_PATH = os.path.join(MODEL_DIR, "risk_scaler.pkl")

FEATURE_NAMES = [
    "temperature",
    "humidity",
    "smoke",
    "occupancy"
]

CLASSES = ["LOW", "MODERATE", "HIGH", "CRITICAL"]


def calculate_training_risk(temperature, smoke, occupancy):

    score = 0

    if temperature >= 50:
        score += 35
    elif temperature >= 45:
        score += 30
    elif temperature >= 40:
        score += 25
    elif temperature >= 35:
        score += 15
    elif temperature >= 32:
        score += 5

    if smoke >= 0.80:
        score += 40
    elif smoke >= 0.60:
        score += 35
    elif smoke >= 0.50:
        score += 30
    elif smoke >= 0.30:
        score += 15
    elif smoke >= 0.15:
        score += 5

    if occupancy >= 50:
        score += 25
    elif occupancy >= 40:
        score += 20
    elif occupancy >= 30:
        score += 15
    elif occupancy >= 15:
        score += 5

    score = min(score, 100)

    if score >= 70:
        return 3
    elif score >= 40:
        return 2
    elif score >= 20:
        return 1

    return 0


def create_training_data(samples=8000):

    rng = np.random.default_rng(42)

    temperature = rng.uniform(25, 55, samples)
    humidity = rng.uniform(25, 80, samples)
    smoke = rng.uniform(0, 1, samples)
    occupancy = rng.integers(0, 51, samples)

    X = np.column_stack((
        temperature,
        humidity,
        smoke,
        occupancy
    ))

    y = np.array([
        calculate_training_risk(t, s, o)
        for t, s, o in zip(temperature, smoke, occupancy)
    ])

    return X, y


class RiskMLP(nn.Module):

    def __init__(self):

        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(4, 64),
            nn.ReLU(),
            nn.Dropout(0.2),

            nn.Linear(64, 32),
            nn.ReLU(),

            nn.Linear(32, 4)
        )

    def forward(self, x):

        return self.network(x)


def train_model():

    print("\nEVAC-TWIN DEEP LEARNING RISK MODEL")

    X, y = create_training_data()

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y
    )

    scaler = StandardScaler()

    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    X_train = torch.tensor(X_train, dtype=torch.float32)
    X_test = torch.tensor(X_test, dtype=torch.float32)

    y_train = torch.tensor(y_train, dtype=torch.long)
    y_test = torch.tensor(y_test, dtype=torch.long)

    model = RiskMLP()

    criterion = nn.CrossEntropyLoss()

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=0.001
    )

    epochs = 100

    for epoch in range(epochs):

        model.train()

        optimizer.zero_grad()

        outputs = model(X_train)

        loss = criterion(outputs, y_train)

        loss.backward()

        optimizer.step()

        if (epoch + 1) % 10 == 0:
            print(
                f"Epoch [{epoch + 1}/{epochs}] "
                f"Loss: {loss.item():.4f}"
            )

    model.eval()

    with torch.no_grad():

        outputs = model(X_test)

        predictions = torch.argmax(
            outputs,
            dim=1
        )

    accuracy = accuracy_score(
        y_test.numpy(),
        predictions.numpy()
    )

    print("\nTest Accuracy:", round(accuracy * 100, 2), "%")

    print("\nClassification Report:")

    print(classification_report(
        y_test.numpy(),
        predictions.numpy(),
        labels=[0, 1, 2, 3],
        target_names=CLASSES,
        zero_division=0
    ))

    os.makedirs(MODEL_DIR, exist_ok=True)

    torch.save(
        model.state_dict(),
        MODEL_PATH
    )

    joblib.dump(
        scaler,
        SCALER_PATH
    )
import json
import copy
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from torch.utils.data import DataLoader, TensorDataset


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "datasets" / "risk_training_data.csv"
MODEL_DIR = BASE_DIR / "models"
MODEL_DIR.mkdir(exist_ok=True)

FEATURES = ["temperature", "humidity", "smoke", "occupancy"]
CLASSES = ["LOW", "MODERATE", "HIGH", "CRITICAL"]

torch.manual_seed(42)
np.random.seed(42)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def calculate_risk(row):
    score = 0

    if row["temperature"] >= 50:
        score += 35
    elif row["temperature"] >= 45:
        score += 30
    elif row["temperature"] >= 40:
        score += 25
    elif row["temperature"] >= 35:
        score += 15
    elif row["temperature"] >= 32:
        score += 5

    if row["smoke"] >= 0.80:
        score += 40
    elif row["smoke"] >= 0.60:
        score += 35
    elif row["smoke"] >= 0.50:
        score += 30
    elif row["smoke"] >= 0.30:
        score += 15
    elif row["smoke"] >= 0.15:
        score += 5

    if row["occupancy"] >= 50:
        score += 25
    elif row["occupancy"] >= 40:
        score += 20
    elif row["occupancy"] >= 30:
        score += 15
    elif row["occupancy"] >= 15:
        score += 5

    if score >= 70:
        return 3
    elif score >= 40:
        return 2
    elif score >= 20:
        return 1
    return 0


class RiskMLP(nn.Module):
    def __init__(self):
        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(4, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, 4)
        )

    def forward(self, x):
        return self.network(x)


def make_loader(X, y, shuffle=False):
    dataset = TensorDataset(
        torch.tensor(X, dtype=torch.float32),
        torch.tensor(y, dtype=torch.long)
    )
    return DataLoader(dataset, batch_size=256, shuffle=shuffle)


def main():
    print("\nEVAC-TWIN DEEP LEARNING RISK MODEL")
    print("Device:", device)

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Create the prepared dataset first: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)

    missing = [c for c in FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df = df[FEATURES].replace([np.inf, -np.inf], np.nan)
    df = df.dropna()

    if len(df) < 100:
        raise ValueError("Collect more real sensor records before training.")

    if (df["occupancy"] < 0).any():
        raise ValueError("Occupancy cannot be negative.")

    if (df["smoke"] < 0).any():
        raise ValueError("Smoke values cannot be negative.")

    # Derived risk labels: these are rule-based labels, not original labels.
    y = df.apply(calculate_risk, axis=1).to_numpy(dtype=np.int64)
    X = df[FEATURES].to_numpy(dtype=np.float32)

    print("Total records:", len(df))
    print("\nRisk label distribution:")
    print(pd.Series(y).value_counts().sort_index())

    # 70% training, 10% validation, 10% calibration, 10% testing
    X_train, X_rem, y_train, y_rem = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=y
    )

    X_temp, X_test, y_temp, y_test = train_test_split(
        X_rem, y_rem, test_size=1/3, random_state=42, stratify=y_rem
    )

    X_val, X_cal, y_val, y_cal = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
    )

    print("\nDataset split:")
    print("Training:", len(X_train))
    print("Validation:", len(X_val))
    print("Calibration:", len(X_cal))
    print("Testing:", len(X_test))

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train).astype(np.float32)
    X_val = scaler.transform(X_val).astype(np.float32)
    X_cal = scaler.transform(X_cal).astype(np.float32)
    X_test = scaler.transform(X_test).astype(np.float32)

    train_loader = make_loader(X_train, y_train, True)
    val_loader = make_loader(X_val, y_val)
    cal_loader = make_loader(X_cal, y_cal)
    test_loader = make_loader(X_test, y_test)

    model = RiskMLP().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=0.001, weight_decay=0.0001
    )

    best_loss = float("inf")
    best_weights = None
    patience = 12
    wait = 0

    for epoch in range(100):
        model.train()
        total_loss = 0

        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(xb)

        train_loss = total_loss / len(train_loader.dataset)

        model.eval()
        val_loss = 0

        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                loss = criterion(model(xb), yb)
                val_loss += loss.item() * len(xb)

        val_loss /= len(val_loader.dataset)

        if (epoch + 1) % 10 == 0:
            print(
                f"Epoch [{epoch + 1}/100] "
                f"Train Loss: {train_loss:.4f} "
                f"Validation Loss: {val_loss:.4f}"
            )

        if val_loss < best_loss:
            best_loss = val_loss
            best_weights = copy.deepcopy(model.state_dict())
            wait = 0
        else:
            wait += 1

        if wait >= patience:
            print("Early stopping.")
            break

    model.load_state_dict(best_weights)

    # Calibration records are kept separate from training.
    model.eval()
    calibration_count = 0
    with torch.no_grad():
        for xb, yb in cal_loader:
            xb = xb.to(device)
            calibration_count += len(xb)

    # Test evaluation
    predictions = []
    actual = []

    with torch.no_grad():
        for xb, yb in test_loader:
            logits = model(xb.to(device))
            predictions.extend(torch.argmax(logits, dim=1).cpu().numpy())
            actual.extend(yb.numpy())

    print("\nTest Accuracy:",
          round(accuracy_score(actual, predictions) * 100, 2), "%")

    print("\nClassification Report:")
    print(classification_report(
        actual,
        predictions,
        labels=[0, 1, 2, 3],
        target_names=CLASSES,
        zero_division=0
    ))

    print("Confusion Matrix:")
    print(confusion_matrix(actual, predictions, labels=[0, 1, 2, 3]))

    torch.save(model.state_dict(), MODEL_DIR / "risk_model.pth")
    joblib.dump(scaler, MODEL_DIR / "risk_scaler.pkl")

    with open(MODEL_DIR / "risk_config.json", "w") as f:
        json.dump({
            "features": FEATURES,
            "classes": CLASSES,
            "label_method": "domain_based_derived_labels",
            "calibration_records": calibration_count
        }, f, indent=4)

    print("\nRisk DL model saved successfully.")


if __name__ == "__main__":
    main()


    print("\nDeep Learning model saved:", MODEL_PATH)
    print("Scaler saved:", SCALER_PATH)


if __name__ == "__main__":
    train_model()
