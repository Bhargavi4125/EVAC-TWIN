import copy
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score
)
from torch.utils.data import DataLoader, TensorDataset


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "datasets" / "smoke_detection_iot.csv"
MODEL_DIR = BASE_DIR / "models"
MODEL_DIR.mkdir(exist_ok=True)

FEATURES = [
    "Temperature[C]",
    "Humidity[%]",
    "TVOC[ppb]",
    "eCO2[ppm]",
    "PM1.0",
    "PM2.5"
]

TARGET = "Fire Alarm"

torch.manual_seed(42)
np.random.seed(42)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class FireModel(nn.Module):
    def __init__(self):
        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(6, 64),
            nn.ReLU(),
            nn.Dropout(0.2),

            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.2),

            nn.Linear(32, 1)
        )

    def forward(self, x):
        return self.network(x)


def temperature_calibration(logits, labels):
    temperature = nn.Parameter(torch.ones(1, device=device))

    optimizer = torch.optim.LBFGS(
        [temperature],
        lr=0.01,
        max_iter=100
    )

    loss_function = nn.BCEWithLogitsLoss()

    def closure():
        optimizer.zero_grad()

        temp = torch.clamp(temperature, min=0.05, max=10)
        loss = loss_function(logits / temp, labels)

        loss.backward()
        return loss

    optimizer.step(closure)

    return float(torch.clamp(temperature, min=0.05, max=10).item())


print("\nEVAC-TWIN DEEP LEARNING FIRE MODEL")
print("Device:", device)

if not DATA_PATH.exists():
    raise FileNotFoundError(
        f"Dataset not found: {DATA_PATH}"
    )

df = pd.read_csv(DATA_PATH)

df = df[FEATURES + [TARGET]].copy()

df = df.replace([np.inf, -np.inf], np.nan)
df = df.dropna()

X = df[FEATURES].astype("float32")
y = df[TARGET].astype("int64")

print("\nTotal records:", len(df))
print("\nClass distribution:")
print(y.value_counts().sort_index())

# 70% training and 30% remaining data
X_train, X_remaining, y_train, y_remaining = train_test_split(
    X,
    y,
    test_size=0.30,
    random_state=42,
    stratify=y
)

# Divide remaining 30% equally into validation, calibration and testing
X_temp, X_test, y_temp, y_test = train_test_split(
    X_remaining,
    y_remaining,
    test_size=1/3,
    random_state=42,
    stratify=y_remaining
)

X_val, X_cal, y_val, y_cal = train_test_split(
    X_temp,
    y_temp,
    test_size=0.50,
    random_state=42,
    stratify=y_temp
)

print("\nDataset split:")
print("Training:", len(X_train))
print("Validation:", len(X_val))
print("Calibration:", len(X_cal))
print("Testing:", len(X_test))

# Fit scaler only on training data
scaler = StandardScaler()

X_train = scaler.fit_transform(X_train)
X_val = scaler.transform(X_val)
X_cal = scaler.transform(X_cal)
X_test = scaler.transform(X_test)

def make_loader(X_data, y_data, shuffle=False):
    x_tensor = torch.tensor(
        X_data,
        dtype=torch.float32
    )

    y_tensor = torch.tensor(
        np.asarray(y_data).reshape(-1, 1),
        dtype=torch.float32
    )

    dataset = TensorDataset(x_tensor, y_tensor)

    return DataLoader(
        dataset,
        batch_size=256,
        shuffle=shuffle
    )


train_loader = make_loader(X_train, y_train, True)
val_loader = make_loader(X_val, y_val)
cal_loader = make_loader(X_cal, y_cal)
test_loader = make_loader(X_test, y_test)

model = FireModel().to(device)

criterion = nn.BCEWithLogitsLoss()

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=0.001,
    weight_decay=0.0001
)

best_loss = float("inf")
best_weights = None
patience = 12
wait = 0
epochs = 100

print("\nTraining started...\n")

for epoch in range(epochs):

    model.train()
    train_loss = 0

    for xb, yb in train_loader:
        xb = xb.to(device)
        yb = yb.to(device)

        optimizer.zero_grad()

        output = model(xb)
        loss = criterion(output, yb)

        loss.backward()
        optimizer.step()

        train_loss += loss.item() * len(xb)

    train_loss /= len(train_loader.dataset)

    model.eval()
    val_loss = 0

    with torch.no_grad():
        for xb, yb in val_loader:
            xb = xb.to(device)
            yb = yb.to(device)

            output = model(xb)
            loss = criterion(output, yb)

            val_loss += loss.item() * len(xb)

    val_loss /= len(val_loader.dataset)

    if (epoch + 1) % 10 == 0:
        print(
            f"Epoch [{epoch + 1}/{epochs}] "
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
        print("\nEarly stopping applied.")
        break

model.load_state_dict(best_weights)

# Calibration: use only the separate calibration set
model.eval()

cal_logits = []
cal_labels = []

with torch.no_grad():
    for xb, yb in cal_loader:
        xb = xb.to(device)

        logits = model(xb)

        cal_logits.append(logits)
        cal_labels.append(yb.to(device))

cal_logits = torch.cat(cal_logits)
cal_labels = torch.cat(cal_labels)

temperature = temperature_calibration(
    cal_logits,
    cal_labels
)

print("\nCalibration temperature:", round(temperature, 4))

# Final evaluation on untouched test data
test_logits = []
test_labels = []

with torch.no_grad():
    for xb, yb in test_loader:
        xb = xb.to(device)

        logits = model(xb)

        test_logits.append(logits)
        test_labels.append(yb)

test_logits = torch.cat(test_logits)
test_labels = torch.cat(test_labels).numpy().ravel()

probabilities = torch.sigmoid(
    test_logits / temperature
).cpu().numpy().ravel()

predictions = (probabilities >= 0.5).astype(int)

accuracy = accuracy_score(test_labels, predictions)
macro_f1 = f1_score(
    test_labels,
    predictions,
    average="macro"
)

print("\nFINAL TEST RESULTS")
print("Test Accuracy:", round(accuracy * 100, 2), "%")
print("Macro F1 Score:", round(macro_f1, 4))

print("\nClassification Report:")
print(
    classification_report(
        test_labels,
        predictions,
        labels=[0, 1],
        target_names=["No Fire", "Fire"],
        zero_division=0
    )
)

print("Confusion Matrix:")
print(confusion_matrix(test_labels, predictions))

# Save model and preprocessing information
torch.save(
    model.state_dict(),
    MODEL_DIR / "fire_alarm_model.pth"
)

joblib.dump(
    scaler,
    MODEL_DIR / "fire_alarm_scaler.pkl"
)

with open(MODEL_DIR / "fire_alarm_config.json", "w") as f:
    json.dump(
        {
            "features": FEATURES,
            "temperature": temperature,
            "threshold": 0.5
        },
        f,
        indent=4
    )

print("\nSaved files:")
print("fire_alarm_model.pth")
print("fire_alarm_scaler.pkl")
print("fire_alarm_config.json")
print("\nTraining completed successfully.")