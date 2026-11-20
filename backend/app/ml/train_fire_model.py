
import copy
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_curve,
    auc,
    precision_recall_curve,
    average_precision_score
)
from sklearn.calibration import calibration_curve

from torch.utils.data import DataLoader, TensorDataset


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "datasets" / "smoke_detection_iot.csv"
MODEL_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "results"

MODEL_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

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

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)


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

    temperature = nn.Parameter(
        torch.ones(1, device=device)
    )

    optimizer = torch.optim.LBFGS(
        [temperature],
        lr=0.01,
        max_iter=100
    )

    loss_function = nn.BCEWithLogitsLoss()

    def closure():

        optimizer.zero_grad()

        temp = torch.clamp(
            temperature,
            min=0.05,
            max=10
        )

        loss = loss_function(
            logits / temp,
            labels
        )

        loss.backward()

        return loss

    optimizer.step(closure)

    return float(
        torch.clamp(
            temperature,
            min=0.05,
            max=10
        ).item()
    )


print("\nEVAC-TWIN DEEP LEARNING FIRE MODEL")
print("Device:", device)


# DATASET LOADING

if not DATA_PATH.exists():

    raise FileNotFoundError(
        f"Dataset not found: {DATA_PATH}"
    )

df = pd.read_csv(DATA_PATH)

df = df[FEATURES + [TARGET]].copy()

df = df.replace(
    [np.inf, -np.inf],
    np.nan
)

df = df.dropna()

X = df[FEATURES].astype("float32")
y = df[TARGET].astype("int64")

print("\nTotal records:", len(df))

print("\nClass distribution:")
print(y.value_counts().sort_index())


# DATASET SUMMARY

dataset_summary = pd.DataFrame({
    "Details": [
        "Total Records",
        "Total Features",
        "Target Column",
        "No Fire Records",
        "Fire Records"
    ],
    "Values": [
        len(df),
        len(FEATURES),
        TARGET,
        int((df[TARGET] == 0).sum()),
        int((df[TARGET] == 1).sum())
    ]
})

print("\n===== DATASET SUMMARY =====")
print(dataset_summary.to_string(index=False))

dataset_summary.to_csv(
    RESULTS_DIR / "dataset_summary.csv",
    index=False
)


# DATASET DISTRIBUTION GRAPH

class_counts = y.value_counts().sort_index()

plt.figure(figsize=(7, 5))

plt.bar(
    ["No Fire", "Fire"],
    [
        class_counts.get(0, 0),
        class_counts.get(1, 0)
    ]
)

plt.title("Fire Detection Dataset Distribution")
plt.xlabel("Class")
plt.ylabel("Number of Records")

plt.tight_layout()

plt.savefig(
    RESULTS_DIR / "dataset_distribution.png",
    dpi=300
)

plt.close()


# DATASET SPLITTING

X_train, X_remaining, y_train, y_remaining = train_test_split(
    X,
    y,
    test_size=0.30,
    random_state=42,
    stratify=y
)

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


split_table = pd.DataFrame({
    "Dataset": [
        "Training",
        "Validation",
        "Calibration",
        "Testing"
    ],
    "Records": [
        len(X_train),
        len(X_val),
        len(X_cal),
        len(X_test)
    ]
})

print("\n===== DATASET SPLIT =====")
print(split_table.to_string(index=False))

split_table.to_csv(
    RESULTS_DIR / "dataset_split.csv",
    index=False
)


# FEATURE SCALING

scaler = StandardScaler()

X_train = scaler.fit_transform(X_train)
X_val = scaler.transform(X_val)
X_cal = scaler.transform(X_cal)
X_test = scaler.transform(X_test)


# DATA LOADER

def make_loader(X_data, y_data, shuffle=False):

    x_tensor = torch.tensor(
        X_data,
        dtype=torch.float32
    )

    y_tensor = torch.tensor(
        np.asarray(y_data).reshape(-1, 1),
        dtype=torch.float32
    )

    dataset = TensorDataset(
        x_tensor,
        y_tensor
    )

    return DataLoader(
        dataset,
        batch_size=256,
        shuffle=shuffle
    )


train_loader = make_loader(
    X_train, y_train, True
)

val_loader = make_loader(
    X_val, y_val
)

cal_loader = make_loader(
    X_cal, y_cal
)

test_loader = make_loader(
    X_test, y_test
)


# MODEL INITIALIZATION

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

train_losses = []
val_losses = []

train_accuracies = []
val_accuracies = []


# MODEL TRAINING

print("\nTraining started...\n")

for epoch in range(epochs):

    model.train()

    train_loss = 0
    train_correct = 0

    for xb, yb in train_loader:

        xb = xb.to(device)
        yb = yb.to(device)

        optimizer.zero_grad()

        output = model(xb)

        loss = criterion(output, yb)

        loss.backward()

        optimizer.step()

        train_loss += loss.item() * len(xb)

        train_correct += (
            (torch.sigmoid(output) >= 0.5) == (yb >= 0.5)
        ).sum().item()

    train_loss /= len(train_loader.dataset)

    train_accuracy = (
        train_correct / len(train_loader.dataset)
    )

    # VALIDATION

    model.eval()

    val_loss = 0
    val_correct = 0

    with torch.no_grad():

        for xb, yb in val_loader:

            xb = xb.to(device)
            yb = yb.to(device)

            output = model(xb)

            loss = criterion(output, yb)

            val_loss += loss.item() * len(xb)

            val_correct += (
                (torch.sigmoid(output) >= 0.5) == (yb >= 0.5)
            ).sum().item()

    val_loss /= len(val_loader.dataset)

    val_accuracy = (
        val_correct / len(val_loader.dataset)
    )

    train_losses.append(train_loss)
    val_losses.append(val_loss)

    train_accuracies.append(train_accuracy)
    val_accuracies.append(val_accuracy)

    if (epoch + 1) % 10 == 0:

        print(
            f"Epoch [{epoch + 1}/{epochs}] "
            f"Train Loss: {train_loss:.4f} "
            f"Validation Loss: {val_loss:.4f} "
            f"Train Accuracy: {train_accuracy:.4f} "
            f"Validation Accuracy: {val_accuracy:.4f}"
        )

    if val_loss < best_loss:

        best_loss = val_loss

        best_weights = copy.deepcopy(
            model.state_dict()
        )

        wait = 0

    else:

        wait += 1

    if wait >= patience:

        print("\nEarly stopping applied.")

        break


model.load_state_dict(best_weights)


# TRAINING CONFIGURATION

print("\n===== MODEL TRAINING CONFIGURATION =====")

print("Architecture: 6 -> 64 -> 32 -> 1")
print("Activation Function: ReLU")
print("Dropout:", model.network[2].p)
print("Batch Size:", train_loader.batch_size)
print("Maximum Epochs:", epochs)
print("Early Stopping Patience:", patience)

print("\nOptimizer: AdamW")
print("Learning Rate:", optimizer.param_groups[0]["lr"])
print("Weight Decay:", optimizer.param_groups[0]["weight_decay"])

print("\nBest Validation Loss:", round(best_loss, 4))
print("Epochs Completed:", epoch + 1)


# TRAINING HISTORY CSV

history = pd.DataFrame({
    "Epoch": range(1, len(train_losses) + 1),
    "Training Loss": train_losses,
    "Validation Loss": val_losses,
    "Training Accuracy": train_accuracies,
    "Validation Accuracy": val_accuracies
})

history.to_csv(
    RESULTS_DIR / "training_history.csv",
    index=False
)


# TEMPERATURE CALIBRATION

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

print(
    "\nCalibration temperature:",
    round(temperature, 4)
)


# FINAL TESTING

test_logits = []
test_labels = []

with torch.no_grad():

    for xb, yb in test_loader:

        xb = xb.to(device)

        logits = model(xb)

        test_logits.append(logits)
        test_labels.append(yb)


test_logits = torch.cat(test_logits)

test_labels = torch.cat(
    test_labels
).numpy().ravel()


probabilities = torch.sigmoid(
    test_logits / temperature
).cpu().numpy().ravel()

predictions = (
    probabilities >= 0.5
).astype(int)


# PERFORMANCE METRICS

accuracy = accuracy_score(
    test_labels,
    predictions
)

precision = precision_score(
    test_labels,
    predictions,
    zero_division=0
)

recall = recall_score(
    test_labels,
    predictions,
    zero_division=0
)

macro_f1 = f1_score(
    test_labels,
    predictions,
    average="macro"
)

fpr, tpr, roc_thresholds = roc_curve(
    test_labels,
    probabilities
)

roc_auc = auc(fpr, tpr)

pr_precision, pr_recall, pr_thresholds = precision_recall_curve(
    test_labels,
    probabilities
)

average_precision = average_precision_score(
    test_labels,
    probabilities
)

metrics_table = pd.DataFrame({
    "Metric": [
        "Accuracy (%)",
        "Precision",
        "Recall",
        "Macro F1 Score",
        "ROC AUC Score",
        "Average Precision",
        "Best Validation Loss",
        "Epochs Completed",
        "Calibration Temperature"
    ],
    "Value": [
        round(accuracy * 100, 2),
        round(precision, 4),
        round(recall, 4),
        round(macro_f1, 4),
        round(roc_auc, 4),
        round(average_precision, 4),
        round(best_loss, 4),
        epoch + 1,
        round(temperature, 4)
    ]
})

print("\n===== FINAL TEST RESULTS =====")
print(metrics_table.to_string(index=False))

metrics_table.to_csv(
    RESULTS_DIR / "performance_metrics.csv",
    index=False
)


# CLASSIFICATION REPORT

report = classification_report(
    test_labels,
    predictions,
    labels=[0, 1],
    target_names=["No Fire", "Fire"],
    zero_division=0
)

print("\n===== CLASSIFICATION REPORT =====")
print(report)

with open(
    RESULTS_DIR / "classification_report.txt",
    "w",
    encoding="utf-8"
) as f:

    f.write(report)


# CONFUSION MATRIX

cm = confusion_matrix(
    test_labels,
    predictions,
    labels=[0, 1]
)

print("\n===== CONFUSION MATRIX =====")
print(cm)

plt.figure(figsize=(6, 5))

plt.imshow(
    cm,
    interpolation="nearest",
    cmap="Blues"
)

plt.title("Fire Detection Confusion Matrix")
plt.colorbar()

plt.xticks(
    [0, 1],
    ["No Fire", "Fire"]
)

plt.yticks(
    [0, 1],
    ["No Fire", "Fire"]
)

plt.xlabel("Predicted Label")
plt.ylabel("Actual Label")

for i in range(2):

    for j in range(2):

        plt.text(
            j,
            i,
            str(cm[i, j]),
            ha="center",
            va="center",
            color="black",
            fontsize=13
        )

plt.tight_layout()

plt.savefig(
    RESULTS_DIR / "confusion_matrix.png",
    dpi=300
)

plt.close()


# ROC CURVE

plt.figure(figsize=(7, 5))

plt.plot(
    fpr,
    tpr,
    label=f"Fire Detection (AUC = {roc_auc:.4f})"
)

plt.plot(
    [0, 1],
    [0, 1],
    linestyle="--",
    label="Random Classifier"
)

plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")

plt.title("Fire Detection ROC Curve")

plt.legend()
plt.grid(True)

plt.tight_layout()

plt.savefig(
    RESULTS_DIR / "roc_curve.png",
    dpi=300
)

plt.close()


# PRECISION RECALL CURVE

plt.figure(figsize=(7, 5))

plt.plot(
    pr_recall,
    pr_precision,
    label=f"Average Precision = {average_precision:.4f}"
)

plt.xlabel("Recall")
plt.ylabel("Precision")

plt.title("Fire Detection Precision-Recall Curve")

plt.legend()
plt.grid(True)

plt.tight_layout()

plt.savefig(
    RESULTS_DIR / "precision_recall_curve.png",
    dpi=300
)

plt.close()


# TRAINING AND VALIDATION LOSS

plt.figure(figsize=(8, 5))

plt.plot(
    range(1, len(train_losses) + 1),
    train_losses,
    label="Training Loss"
)

plt.plot(
    range(1, len(val_losses) + 1),
    val_losses,
    label="Validation Loss"
)

plt.xlabel("Epoch")
plt.ylabel("Loss")

plt.title("Training and Validation Loss")

plt.legend()
plt.grid(True)

plt.tight_layout()

plt.savefig(
    RESULTS_DIR / "training_loss.png",
    dpi=300
)

plt.close()


# TRAINING AND VALIDATION ACCURACY

plt.figure(figsize=(8, 5))

plt.plot(
    range(1, len(train_accuracies) + 1),
    train_accuracies,
    label="Training Accuracy"
)

plt.plot(
    range(1, len(val_accuracies) + 1),
    val_accuracies,
    label="Validation Accuracy"
)

plt.xlabel("Epoch")
plt.ylabel("Accuracy")

plt.title("Training and Validation Accuracy")

plt.legend()
plt.grid(True)

plt.tight_layout()

plt.savefig(
    RESULTS_DIR / "training_validation_accuracy.png",
    dpi=300
)

plt.close()


# CALIBRATION CURVE

fraction_positive, mean_predicted = calibration_curve(
    test_labels,
    probabilities,
    n_bins=10,
    strategy="uniform"
)

plt.figure(figsize=(7, 5))

plt.plot(
    mean_predicted,
    fraction_positive,
    marker="o",
    label="Fire Detection"
)

plt.plot(
    [0, 1],
    [0, 1],
    linestyle="--",
    label="Perfect Calibration"
)

plt.xlabel("Mean Predicted Probability")
plt.ylabel("Fraction of Positives")

plt.title("Fire Detection Calibration Curve")

plt.legend()
plt.grid(True)

plt.tight_layout()

plt.savefig(
    RESULTS_DIR / "calibration_curve.png",
    dpi=300
)

plt.close()


# SAVE MODEL

torch.save(
    model.state_dict(),
    MODEL_DIR / "fire_alarm_model.pth"
)

joblib.dump(
    scaler,
    MODEL_DIR / "fire_alarm_scaler.pkl"
)

with open(
    MODEL_DIR / "fire_alarm_config.json",
    "w"
) as f:

    json.dump(
        {
            "features": FEATURES,
            "temperature": temperature,
            "threshold": 0.5
        },
        f,
        indent=4
    )


# SAVE COMPLETE RESULTS

with open(
    RESULTS_DIR / "training_results.txt",
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "EVAC-TWIN DEEP LEARNING FIRE DETECTION RESULTS\n"
    )

    f.write("=" * 55 + "\n\n")

    f.write(f"Total Records: {len(df)}\n")
    f.write(f"Device: {device}\n")
    f.write("Architecture: 6 -> 64 -> 32 -> 1\n")
    f.write("Activation: ReLU\n")
    f.write("Optimizer: AdamW\n")

    f.write(
        f"Learning Rate: {optimizer.param_groups[0]['lr']}\n"
    )

    f.write(
        f"Best Validation Loss: {best_loss:.4f}\n"
    )

    f.write(
        f"Epochs Completed: {epoch + 1}\n"
    )

    f.write(
        f"Calibration Temperature: {temperature:.4f}\n"
    )

    f.write(
        f"Accuracy: {accuracy * 100:.2f}%\n"
    )

    f.write(
        f"Precision: {precision:.4f}\n"
    )

    f.write(
        f"Recall: {recall:.4f}\n"
    )

    f.write(
        f"Macro F1 Score: {macro_f1:.4f}\n"
    )

    f.write(
        f"ROC AUC Score: {roc_auc:.4f}\n"
    )

    f.write(
        f"Average Precision: {average_precision:.4f}\n\n"
    )

    f.write("DATASET SUMMARY\n")
    f.write(dataset_summary.to_string(index=False))

    f.write("\n\nDATASET SPLIT\n")
    f.write(split_table.to_string(index=False))

    f.write("\n\nPERFORMANCE METRICS\n")
    f.write(metrics_table.to_string(index=False))

    f.write("\n\nCLASSIFICATION REPORT\n")
    f.write(report)

    f.write("\n\nCONFUSION MATRIX\n")
    f.write(str(cm))


# FINAL OUTPUT

print("\n===== SAVED MODEL FILES =====")

print("fire_alarm_model.pth")
print("fire_alarm_scaler.pkl")
print("fire_alarm_config.json")

print("\n===== SAVED RESULT FILES =====")

for file in sorted(RESULTS_DIR.iterdir()):

    if file.is_file():

        print(file.name)

print("\nResults folder:", RESULTS_DIR)

print("\nTraining completed successfully.")
