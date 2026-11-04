
import os
import json
import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import classification_report, confusion_matrix
from torch.utils.data import TensorDataset, DataLoader

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "datasets", "risk_training_data.csv")
MODEL_DIR = os.path.join(BASE, "models")

os.makedirs(MODEL_DIR, exist_ok=True)

df = pd.read_csv(DATA)

features = ["temperature", "humidity", "smoke", "occupancy"]
target = "risk_level"

df = df[features + [target]].drop_duplicates()
df = df.dropna()

X = df[features].values.astype(np.float32)
y_text = df[target].astype(str).str.upper()

encoder = LabelEncoder()
y = encoder.fit_transform(y_text)

X_train, X_temp, y_train, y_temp = train_test_split(
    X, y, test_size=0.30, random_state=42, stratify=y
)

X_val, X_test, y_val, y_test = train_test_split(
    X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
)

scaler = StandardScaler()
X_train = scaler.fit_transform(X_train).astype(np.float32)
X_val = scaler.transform(X_val).astype(np.float32)
X_test = scaler.transform(X_test).astype(np.float32)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class RiskNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(4, 64),
            nn.ReLU(),
            nn.Dropout(0.25),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.20),
            nn.Linear(32, len(encoder.classes_))
        )

    def forward(self, x):
        return self.net(x)

weights = compute_class_weight(
    class_weight="balanced",
    classes=np.unique(y_train),
    y=y_train
)

weights = torch.tensor(weights, dtype=torch.float32).to(device)

model = RiskNet().to(device)
criterion = nn.CrossEntropyLoss(weight=weights)
optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)

def make_loader(x, y, shuffle=False):
    dataset = TensorDataset(
        torch.tensor(x, dtype=torch.float32),
        torch.tensor(y, dtype=torch.long)
    )
    return DataLoader(dataset, batch_size=128, shuffle=shuffle)

train_loader = make_loader(X_train, y_train, True)
val_loader = make_loader(X_val, y_val)

best_loss = float("inf")
patience = 12
wait = 0

for epoch in range(100):
    model.train()
    for xb, yb in train_loader:
        xb, yb = xb.to(device), yb.to(device)
        optimizer.zero_grad()
        loss = criterion(model(xb), yb)
        loss.backward()
        optimizer.step()

    model.eval()
    val_loss = 0

    with torch.no_grad():
        for xb, yb in val_loader:
            xb, yb = xb.to(device), yb.to(device)
            val_loss += criterion(model(xb), yb).item()

    val_loss /= len(val_loader)
    print(f"Epoch {epoch+1}: Validation Loss = {val_loss:.4f}")

    if val_loss < best_loss:
        best_loss = val_loss
        wait = 0
        torch.save(model.state_dict(), os.path.join(MODEL_DIR, "risk_model.pth"))
    else:
        wait += 1

    if wait >= patience:
        print("Early stopping.")
        break

model.load_state_dict(
    torch.load(os.path.join(MODEL_DIR, "risk_model.pth"), map_location=device)
)

model.eval()
predictions = []

with torch.no_grad():
    for xb, yb in make_loader(X_test, y_test):
        xb = xb.to(device)
        predictions.extend(model(xb).argmax(dim=1).cpu().numpy())

print("\nClassification Report:")
print(classification_report(
    y_test,
    predictions,
    labels=np.arange(len(encoder.classes_)),
    target_names=encoder.classes_,
    zero_division=0
))

print("Confusion Matrix:")
print(confusion_matrix(y_test, predictions))

joblib.dump(scaler, os.path.join(MODEL_DIR, "risk_scaler.pkl"))

config = {
    "features": features,
    "classes": encoder.classes_.tolist(),
    "input_size": 4,
    "hidden_sizes": [64, 32],
    "num_classes": len(encoder.classes_)
}

with open(os.path.join(MODEL_DIR, "risk_config.json"), "w") as f:
    json.dump(config, f, indent=4)

print("\nRisk DL model training completed!")
print("Saved files in:", MODEL_DIR)
