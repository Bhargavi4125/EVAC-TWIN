
import os
import json
import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder, label_binarize
from sklearn.utils.class_weight import compute_class_weight

from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_curve,
    auc,
    precision_recall_curve,
    average_precision_score,
    roc_auc_score
)

from torch.utils.data import TensorDataset, DataLoader

# =====================================================
# 1. PATH CONFIGURATION
# =====================================================

BASE = os.path.dirname(os.path.abspath(__file__))

DATA = os.path.join(BASE, "datasets", "risk_training_data.csv")
MODEL_DIR = os.path.join(BASE, "models")
RESULTS_DIR = os.path.join(BASE, "results")

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

torch.manual_seed(42)
np.random.seed(42)

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("\nEVAC-TWIN DEEP LEARNING RISK MODEL")
print("Device:", device)

# =====================================================
# 2. LOAD DATASET
# =====================================================

if not os.path.exists(DATA):
    raise FileNotFoundError(f"Dataset not found: {DATA}")

df = pd.read_csv(DATA)

features = [
    "temperature",
    "humidity",
    "smoke",
    "occupancy"
]

target = "risk_level"

df = df[features + [target]].copy()

df = df.replace(
    [np.inf, -np.inf],
    np.nan
)

df = df.dropna()
df = df.drop_duplicates()

X = df[features].values.astype(np.float32)

y_text = df[target].astype(str).str.upper()

encoder = LabelEncoder()
y = encoder.fit_transform(y_text)

num_classes = len(encoder.classes_)

print("\nDATASET SUMMARY")
print("-----------------------------")
print("Total Records:", len(df))
print("Total Features:", len(features))
print("Target Column:", target)
print("Risk Classes:", list(encoder.classes_))

print("\nClass Distribution:")
print(df[target].value_counts())

# =====================================================
# 3. SAVE DATASET SUMMARY
# =====================================================

dataset_summary = pd.DataFrame({
    "Details": [
        "Total Records",
        "Total Features",
        "Target Column",
        "Number of Risk Classes"
    ],
    "Values": [
        len(df),
        len(features),
        target,
        num_classes
    ]
})

dataset_summary.to_csv(
    os.path.join(RESULTS_DIR, "risk_dataset_summary.csv"),
    index=False
)

class_distribution = (
    pd.Series(y_text)
    .value_counts()
    .reindex(encoder.classes_, fill_value=0)
    .reset_index()
)

class_distribution.columns = [
    "Risk Level",
    "Records"
]

class_distribution.to_csv(
    os.path.join(RESULTS_DIR, "risk_class_distribution.csv"),
    index=False
)

# =====================================================
# 4. DATASET DISTRIBUTION GRAPH
# =====================================================

plt.figure(figsize=(8, 5))

plt.bar(
    class_distribution["Risk Level"],
    class_distribution["Records"]
)

plt.xlabel("Risk Level")
plt.ylabel("Number of Records")

plt.title("Risk Dataset Class Distribution")

plt.grid(axis="y")

plt.tight_layout()

plt.savefig(
    os.path.join(RESULTS_DIR, "risk_dataset_distribution.png"),
    dpi=300
)

plt.close()

# =====================================================
# 5. DATASET SPLITTING
# =====================================================

X_train, X_temp, y_train, y_temp = train_test_split(
    X,
    y,
    test_size=0.30,
    random_state=42,
    stratify=y
)

X_val, X_test, y_val, y_test = train_test_split(
    X_temp,
    y_temp,
    test_size=0.50,
    random_state=42,
    stratify=y_temp
)

split_summary = pd.DataFrame({
    "Dataset": [
        "Training",
        "Validation",
        "Testing"
    ],
    "Records": [
        len(X_train),
        len(X_val),
        len(X_test)
    ],
    "Percentage": [
        len(X_train) / len(X) * 100,
        len(X_val) / len(X) * 100,
        len(X_test) / len(X) * 100
    ]
})

split_summary.to_csv(
    os.path.join(RESULTS_DIR, "risk_dataset_split.csv"),
    index=False
)

print("\nDATASET SPLIT")
print(split_summary.to_string(index=False))

# =====================================================
# 6. FEATURE SCALING
# =====================================================

scaler = StandardScaler()

X_train = scaler.fit_transform(X_train).astype(np.float32)
X_val = scaler.transform(X_val).astype(np.float32)
X_test = scaler.transform(X_test).astype(np.float32)

# =====================================================
# 7. DEEP LEARNING MODEL
# =====================================================

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

            nn.Linear(32, num_classes)
        )

    def forward(self, x):
        return self.net(x)

# =====================================================
# 8. CLASS WEIGHTS
# =====================================================

weights = compute_class_weight(
    class_weight="balanced",
    classes=np.unique(y_train),
    y=y_train
)

weights = torch.tensor(
    weights,
    dtype=torch.float32
).to(device)

model = RiskNet().to(device)

criterion = nn.CrossEntropyLoss(
    weight=weights
)

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=0.001
)

# =====================================================
# 9. DATA LOADERS
# =====================================================

def make_loader(x, y, shuffle=False):

    dataset = TensorDataset(
        torch.tensor(x, dtype=torch.float32),
        torch.tensor(y, dtype=torch.long)
    )

    return DataLoader(
        dataset,
        batch_size=128,
        shuffle=shuffle
    )

train_loader = make_loader(
    X_train,
    y_train,
    True
)

val_loader = make_loader(
    X_val,
    y_val
)

test_loader = make_loader(
    X_test,
    y_test
)

# =====================================================
# 10. MODEL TRAINING
# =====================================================

best_loss = float("inf")

patience = 12
wait = 0

train_losses = []
val_losses = []

train_accuracies = []
val_accuracies = []

best_epoch = 0

epochs = 100

print("\nTRAINING STARTED")
print("-----------------------------")

for epoch in range(epochs):

    model.train()

    total_train_loss = 0
    train_correct = 0
    train_total = 0

    for xb, yb in train_loader:

        xb = xb.to(device)
        yb = yb.to(device)

        optimizer.zero_grad()

        outputs = model(xb)

        loss = criterion(outputs, yb)

        loss.backward()

        optimizer.step()

        total_train_loss += loss.item() * len(xb)

        predicted = outputs.argmax(dim=1)

        train_correct += (
            predicted == yb
        ).sum().item()

        train_total += len(yb)

    avg_train_loss = (
        total_train_loss / train_total
    )

    train_accuracy = (
        train_correct / train_total
    )

    # VALIDATION

    model.eval()

    total_val_loss = 0
    val_correct = 0
    val_total = 0

    with torch.no_grad():

        for xb, yb in val_loader:

            xb = xb.to(device)
            yb = yb.to(device)

            outputs = model(xb)

            loss = criterion(outputs, yb)

            total_val_loss += loss.item() * len(xb)

            predicted = outputs.argmax(dim=1)

            val_correct += (
                predicted == yb
            ).sum().item()

            val_total += len(yb)

    val_loss = (
        total_val_loss / val_total
    )

    val_accuracy = (
        val_correct / val_total
    )

    train_losses.append(avg_train_loss)
    val_losses.append(val_loss)

    train_accuracies.append(train_accuracy)
    val_accuracies.append(val_accuracy)

    print(
        f"Epoch {epoch + 1}: "
        f"Training Loss = {avg_train_loss:.4f}, "
        f"Validation Loss = {val_loss:.4f}, "
        f"Training Accuracy = {train_accuracy:.4f}, "
        f"Validation Accuracy = {val_accuracy:.4f}"
    )

    if val_loss < best_loss:

        best_loss = val_loss
        best_epoch = epoch + 1

        wait = 0

        torch.save(
            model.state_dict(),
            os.path.join(MODEL_DIR, "risk_model.pth")
        )

    else:

        wait += 1

    if wait >= patience:

        print("\nEarly stopping.")
        break

# =====================================================
# 11. SAVE TRAINING HISTORY
# =====================================================

history = pd.DataFrame({
    "Epoch": range(1, len(train_losses) + 1),
    "Training Loss": train_losses,
    "Validation Loss": val_losses,
    "Training Accuracy": train_accuracies,
    "Validation Accuracy": val_accuracies
})

history.to_csv(
    os.path.join(RESULTS_DIR, "risk_training_history.csv"),
    index=False
)

print("\nBest Epoch:", best_epoch)
print("Best Validation Loss:", round(best_loss, 4))

# =====================================================
# 12. TRAINING AND VALIDATION LOSS GRAPH
# =====================================================

plt.figure(figsize=(9, 5))

plt.plot(
    history["Epoch"],
    history["Training Loss"],
    label="Training Loss"
)

plt.plot(
    history["Epoch"],
    history["Validation Loss"],
    label="Validation Loss"
)

plt.xlabel("Epoch")
plt.ylabel("Loss")

plt.title("Risk Model Training and Validation Loss")

plt.legend()
plt.grid(True)

plt.tight_layout()

plt.savefig(
    os.path.join(RESULTS_DIR, "risk_training_loss.png"),
    dpi=300
)

plt.close()

# =====================================================
# 13. TRAINING AND VALIDATION ACCURACY GRAPH
# =====================================================

plt.figure(figsize=(9, 5))

plt.plot(
    history["Epoch"],
    history["Training Accuracy"],
    label="Training Accuracy"
)

plt.plot(
    history["Epoch"],
    history["Validation Accuracy"],
    label="Validation Accuracy"
)

plt.xlabel("Epoch")
plt.ylabel("Accuracy")

plt.title("Risk Model Training and Validation Accuracy")

plt.legend()
plt.grid(True)

plt.tight_layout()

plt.savefig(
    os.path.join(RESULTS_DIR, "risk_training_validation_accuracy.png"),
    dpi=300
)

plt.close()

# =====================================================
# 14. LOAD BEST MODEL
# =====================================================

model.load_state_dict(
    torch.load(
        os.path.join(MODEL_DIR, "risk_model.pth"),
        map_location=device
    )
)

model.eval()

# =====================================================
# 15. MODEL TESTING
# =====================================================

predictions = []
actual_values = []
probability_values = []

with torch.no_grad():

    for xb, yb in test_loader:

        xb = xb.to(device)

        outputs = model(xb)

        probabilities = torch.softmax(
            outputs,
            dim=1
        )

        predicted = outputs.argmax(dim=1)

        predictions.extend(
            predicted.cpu().numpy()
        )

        actual_values.extend(
            yb.numpy()
        )

        probability_values.extend(
            probabilities.cpu().numpy()
        )

predictions = np.array(predictions)

actual_values = np.array(actual_values)

probability_values = np.array(
    probability_values
)

# =====================================================
# 16. PERFORMANCE METRICS
# =====================================================

accuracy = accuracy_score(
    actual_values,
    predictions
)

precision = precision_score(
    actual_values,
    predictions,
    average="weighted",
    zero_division=0
)

recall = recall_score(
    actual_values,
    predictions,
    average="weighted",
    zero_division=0
)

f1 = f1_score(
    actual_values,
    predictions,
    average="weighted",
    zero_division=0
)

macro_f1 = f1_score(
    actual_values,
    predictions,
    average="macro",
    zero_division=0
)

# =====================================================
# 17. MULTICLASS ROC CURVE
# =====================================================

y_test_binary = label_binarize(
    actual_values,
    classes=np.arange(num_classes)
)

roc_values = []

plt.figure(figsize=(9, 7))

for i, class_name in enumerate(encoder.classes_):

    if len(np.unique(y_test_binary[:, i])) < 2:

        print(
            f"ROC skipped for {class_name}: "
            "test data does not contain both classes."
        )

        continue

    fpr, tpr, thresholds = roc_curve(
        y_test_binary[:, i],
        probability_values[:, i]
    )

    class_auc = auc(fpr, tpr)

    roc_values.append(class_auc)

    plt.plot(
        fpr,
        tpr,
        label=f"{class_name} (AUC = {class_auc:.4f})"
    )

plt.plot(
    [0, 1],
    [0, 1],
    linestyle="--",
    label="Random Classifier"
)

plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")

plt.title("Risk Prediction Multiclass ROC Curve")

plt.legend()
plt.grid(True)

plt.tight_layout()

plt.savefig(
    os.path.join(RESULTS_DIR, "risk_roc_curve.png"),
    dpi=300
)

plt.close()

roc_auc = (
    float(np.mean(roc_values))
    if roc_values else float("nan")
)

print("\nMean One-vs-Rest ROC AUC:", roc_auc)


# =====================================================
# 18. MULTICLASS PRECISION-RECALL CURVE
# =====================================================

plt.figure(figsize=(9, 7))

pr_values = []

for i, class_name in enumerate(encoder.classes_):

    if len(np.unique(y_test_binary[:, i])) < 2:
        continue

    pr_precision, pr_recall, thresholds = precision_recall_curve(
        y_test_binary[:, i],
        probability_values[:, i]
    )

    class_ap = average_precision_score(
        y_test_binary[:, i],
        probability_values[:, i]
    )

    pr_values.append(class_ap)

    plt.plot(
        pr_recall,
        pr_precision,
        label=f"{class_name} (AP = {class_ap:.4f})"
    )

plt.xlabel("Recall")
plt.ylabel("Precision")

plt.title("Risk Prediction Precision-Recall Curve")

plt.legend()
plt.grid(True)

plt.tight_layout()

plt.savefig(
    os.path.join(RESULTS_DIR, "risk_precision_recall_curve.png"),
    dpi=300
)

plt.close()

average_precision = (
    float(np.mean(pr_values))
    if pr_values else float("nan")
)

# =====================================================
# 19. SAVE PERFORMANCE METRICS
# =====================================================

metrics = pd.DataFrame({
    "Metric": [
        "Accuracy",
        "Weighted Precision",
        "Weighted Recall",
        "Weighted F1 Score",
        "Macro F1 Score",
        "Mean One-vs-Rest ROC AUC",
        "Mean Average Precision",
        "Best Epoch",
        "Best Validation Loss"
    ],
    "Value": [
        accuracy,
        precision,
        recall,
        f1,
        macro_f1,
        roc_auc,
        average_precision,
        best_epoch,
        best_loss
    ]
})

metrics.to_csv(
    os.path.join(RESULTS_DIR, "risk_performance_metrics.csv"),
    index=False
)

print("\nPERFORMANCE METRICS")
print("-----------------------------")
print(metrics.to_string(index=False))

# =====================================================
# 20. CLASSIFICATION REPORT
# =====================================================

report = classification_report(
    actual_values,
    predictions,
    labels=np.arange(num_classes),
    target_names=encoder.classes_,
    zero_division=0
)

print("\nCLASSIFICATION REPORT")
print("-----------------------------")
print(report)

with open(
    os.path.join(RESULTS_DIR, "risk_classification_report.txt"),
    "w",
    encoding="utf-8"
) as f:

    f.write("RISK MODEL CLASSIFICATION REPORT\n\n")
    f.write(report)

# =====================================================
# 21. CONFUSION MATRIX
# =====================================================

cm = confusion_matrix(
    actual_values,
    predictions,
    labels=np.arange(num_classes)
)

print("\nCONFUSION MATRIX")
print("-----------------------------")
print(cm)

cm_df = pd.DataFrame(
    cm,
    index=encoder.classes_,
    columns=encoder.classes_
)

cm_df.to_csv(
    os.path.join(RESULTS_DIR, "risk_confusion_matrix.csv")
)

plt.figure(figsize=(8, 6))

sns.heatmap(
    cm,
    annot=True,
    fmt="d",
    cmap="Blues",
    xticklabels=encoder.classes_,
    yticklabels=encoder.classes_
)

plt.xlabel("Predicted Risk Level")
plt.ylabel("Actual Risk Level")

plt.title("Risk Model Confusion Matrix")

plt.tight_layout()

plt.savefig(
    os.path.join(RESULTS_DIR, "risk_confusion_matrix.png"),
    dpi=300
)

plt.close()

# =====================================================
# 22. SAVE MODEL FILES
# =====================================================

joblib.dump(
    scaler,
    os.path.join(MODEL_DIR, "risk_scaler.pkl")
)

joblib.dump(
    encoder,
    os.path.join(MODEL_DIR, "risk_encoder.pkl")
)

config = {
    "features": features,
    "classes": encoder.classes_.tolist(),
    "input_size": 4,
    "hidden_sizes": [64, 32],
    "num_classes": num_classes
}

with open(
    os.path.join(MODEL_DIR, "risk_config.json"),
    "w"
) as f:

    json.dump(
        config,
        f,
        indent=4
    )

# =====================================================
# 23. SAVE COMPLETE TRAINING SUMMARY
# =====================================================

with open(
    os.path.join(RESULTS_DIR, "risk_training_results.txt"),
    "w",
    encoding="utf-8"
) as f:

    f.write("RISK DEEP LEARNING MODEL TRAINING RESULTS\n")
    f.write("=" * 50 + "\n\n")

    f.write(f"Total Records: {len(df)}\n")
    f.write(f"Training Records: {len(X_train)}\n")
    f.write(f"Validation Records: {len(X_val)}\n")
    f.write(f"Testing Records: {len(X_test)}\n\n")

    f.write(f"Features: {features}\n")
    f.write(f"Classes: {encoder.classes_.tolist()}\n\n")

    f.write("Architecture: 4 -> 64 -> 32 -> Classes\n")
    f.write("Activation: ReLU\n")
    f.write("Optimizer: AdamW\n")
    f.write("Loss Function: Weighted Cross Entropy\n\n")

    f.write(f"Best Epoch: {best_epoch}\n")
    f.write(f"Best Validation Loss: {best_loss:.4f}\n\n")

    f.write(f"Accuracy: {accuracy:.4f}\n")
    f.write(f"Weighted Precision: {precision:.4f}\n")
    f.write(f"Weighted Recall: {recall:.4f}\n")
    f.write(f"Weighted F1 Score: {f1:.4f}\n")
    f.write(f"Macro F1 Score: {macro_f1:.4f}\n")
    f.write(f"Mean One-vs-Rest ROC AUC: {roc_auc:.4f}\n")
    f.write(f"Mean Average Precision: {average_precision:.4f}\n\n")

    f.write("DATASET SUMMARY\n")
    f.write(dataset_summary.to_string(index=False))

    f.write("\n\nDATASET SPLIT\n")
    f.write(split_summary.to_string(index=False))

    f.write("\n\nPERFORMANCE METRICS\n")
    f.write(metrics.to_string(index=False))

    f.write("\n\nCLASSIFICATION REPORT\n")
    f.write(report)

    f.write("\nCONFUSION MATRIX\n")
    f.write(str(cm))

# =====================================================
# 24. FINAL OUTPUT
# =====================================================

print("\nMODEL FILES SAVED:")
print("-----------------------------")

print("risk_model.pth")
print("risk_scaler.pkl")
print("risk_encoder.pkl")
print("risk_config.json")

print("\nRESULT FILES SAVED:")
print("-----------------------------")

for file in sorted(os.listdir(RESULTS_DIR)):

    if file.startswith("risk_"):

        print(file)

print("\nRisk DL Model Training Completed Successfully!")