
import os
import json
import joblib
import numpy as np
import torch
import torch.nn as nn


# ============================================================
# EVAC-TWIN - DEEP LEARNING RISK PREDICTION
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_DIR = os.path.join(BASE_DIR, "models")

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "risk_model.pth"
)

SCALER_PATH = os.path.join(
    MODEL_DIR,
    "risk_scaler.pkl"
)

CONFIG_PATH = os.path.join(
    MODEL_DIR,
    "risk_config.json"
)

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)


# ============================================================
# LOAD MODEL CONFIGURATION
# ============================================================

try:

    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    CLASSES = config["classes"]
    FEATURES = config["features"]

except Exception as error:

    print(f"[DL ERROR] Config loading failed: {error}")

    CLASSES = ["CRITICAL", "HIGH", "LOW", "MODERATE"]
    FEATURES = ["temperature", "humidity", "smoke", "occupancy"]


# ============================================================
# DEEP LEARNING MODEL
# ============================================================

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
            nn.Linear(32, len(CLASSES))
        )

    def forward(self, x):

        return self.net(x)


# ============================================================
# LOAD TRAINED MODEL AND SCALER
# ============================================================

model = None
scaler = None

try:

    scaler = joblib.load(SCALER_PATH)

    model = RiskNet().to(DEVICE)

    state_dict = torch.load(
        MODEL_PATH,
        map_location=DEVICE
    )

    model.load_state_dict(state_dict)
    model.eval()

    print("[DL] Risk model loaded successfully")
    print("[DL] Device:", DEVICE)
    print("[DL] Classes:", CLASSES)

except Exception as error:

    print("[DL ERROR] Model loading failed:", error)

    model = None
    scaler = None


# ============================================================
# RISK SCORES
# ============================================================

RISK_SCORES = {
    "LOW": 10,
    "MODERATE": 40,
    "HIGH": 70,
    "CRITICAL": 100,
}


# ============================================================
# SAFE NUMERIC CONVERSION
# ============================================================

def safe_float(value, default=0.0):

    try:

        return float(value)

    except (TypeError, ValueError):

        return default


# ============================================================
# RECOMMENDATION
# ============================================================

def get_recommendation(level):

    level = str(level or "LOW").upper()

    if level == "CRITICAL":

        return (
            "Immediate evacuation recommended. "
            "Activate emergency procedures."
        )

    if level == "HIGH":

        return (
            "High-risk conditions detected. "
            "Prepare evacuation routes and alert occupants."
        )

    if level == "MODERATE":

        return (
            "Some elevated conditions are present. "
            "Continue monitoring sensor values."
        )

    return (
        "Environmental conditions are stable. "
        "Continue normal monitoring."
    )


# ============================================================
# FALLBACK RISK CALCULATION
# ============================================================

def fallback_risk(
    temperature,
    humidity,
    smoke,
    occupancy
):

    score = 0

    if temperature >= 40:
        score += 35

    elif temperature >= 38:
        score += 25

    elif temperature >= 35:
        score += 15

    if smoke >= 0.8:
        score += 40

    elif smoke >= 0.5:
        score += 25

    elif smoke >= 0.3:
        score += 10

    if occupancy >= 45:
        score += 25

    elif occupancy >= 30:
        score += 15

    elif occupancy >= 15:
        score += 5

    score = min(score, 100)

    if score >= 70:
        level = "CRITICAL"

    elif score >= 40:
        level = "HIGH"

    elif score >= 20:
        level = "MODERATE"

    else:
        level = "LOW"

    return {
        "level": level,
        "score": score,
        "confidence": 100.0,
        "probabilities": {
            name: 100.0 if name == level else 0.0
            for name in RISK_SCORES
        },
        "recommendation": get_recommendation(level),
    }


# ============================================================
# DEEP LEARNING RISK PREDICTION
# ============================================================

def predict_risk(sensor_data):

    temperature = safe_float(sensor_data.get("temperature"))
    humidity = safe_float(sensor_data.get("humidity"))
    smoke = safe_float(sensor_data.get("smoke"))
    occupancy = safe_float(sensor_data.get("occupancy"))

    if model is None or scaler is None:

        return fallback_risk(
            temperature,
            humidity,
            smoke,
            occupancy
        )

    try:

        features = np.array(
            [[temperature, humidity, smoke, occupancy]],
            dtype=np.float32
        )

        scaled_features = scaler.transform(features)

        input_tensor = torch.tensor(
            scaled_features,
            dtype=torch.float32
        ).to(DEVICE)

        model.eval()

        with torch.no_grad():

            logits = model(input_tensor)

            probabilities = torch.softmax(
                logits,
                dim=1
            )[0]

        probabilities = probabilities.cpu().numpy()

        prediction_index = int(np.argmax(probabilities))

        ml_level = CLASSES[prediction_index]

        probability_map = {
            name: 0.0 for name in RISK_SCORES
        }

        for label, probability in zip(CLASSES, probabilities):

            probability_map[label] = round(
                float(probability) * 100,
                2
            )

        confidence = round(
            float(np.max(probabilities)) * 100,
            2
        )

        risk_score = sum(
            probability_map[level] * weight / 100
            for level, weight in RISK_SCORES.items()
        )

        rule_result = fallback_risk(
            temperature,
            humidity,
            smoke,
            occupancy
        )

        risk_priority = {
            "LOW": 1,
            "MODERATE": 2,
            "HIGH": 3,
            "CRITICAL": 4,
        }

        rule_level = rule_result["level"]

        level = (
            rule_level
            if risk_priority[rule_level] > risk_priority[ml_level]
            else ml_level
        )

        score = round(
            min(max(max(risk_score, rule_result["score"]), 0), 100),
            2
        )

        return {
            "level": level,
            "score": score,
            "confidence": confidence,
            "probabilities": probability_map,
            "recommendation": get_recommendation(level),
        }

    except Exception as error:

        print("[DL ERROR] Prediction failed:", error)

        return fallback_risk(
            temperature,
            humidity,
            smoke,
            occupancy
        )
