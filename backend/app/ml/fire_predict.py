
import os
import json
import joblib
import numpy as np
import torch
import torch.nn as nn


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")

MODEL_PATH = os.path.join(MODEL_DIR, "fire_alarm_model.pth")
SCALER_PATH = os.path.join(MODEL_DIR, "fire_alarm_scaler.pkl")
CONFIG_PATH = os.path.join(MODEL_DIR, "fire_alarm_config.json")

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


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


FEATURES = [
    "Temperature[C]",
    "Humidity[%]",
    "TVOC[ppb]",
    "eCO2[ppm]",
    "PM1.0",
    "PM2.5"
]

model = None
scaler = None
temperature = 1.0
threshold = 0.5


try:
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    FEATURES = config["features"]
    temperature = float(config["temperature"])
    threshold = float(config["threshold"])

    scaler = joblib.load(SCALER_PATH)

    model = FireModel().to(DEVICE)

    state_dict = torch.load(
        MODEL_PATH,
        map_location=DEVICE
    )

    model.load_state_dict(state_dict)
    model.eval()

    print("[DL] Fire Detection model loaded successfully")
    print("[DL] Device:", DEVICE)
    print("[DL] Threshold:", threshold)
    print("[DL] Calibration temperature:", temperature)

except Exception as error:
    print("[DL ERROR] Fire model loading failed:", error)
    model = None
    scaler = None


def predict_fire(sensor_data):

    if model is None or scaler is None:
        return {
            "fire_alarm": None,
            "probability": None,
            "message": "Fire DL model is not available."
        }

    try:

        values = []

        for feature in FEATURES:

            value = sensor_data.get(feature)

            if value is None:
                raise ValueError(
                    f"Missing feature: {feature}"
                )

            value = float(value)

            if not np.isfinite(value):
                raise ValueError(
                    f"Invalid feature: {feature}"
                )

            values.append(value)

        input_data = np.array(
            [values],
            dtype=np.float32
        )

        scaled_data = scaler.transform(input_data)

        input_tensor = torch.tensor(
            scaled_data,
            dtype=torch.float32
        ).to(DEVICE)

        model.eval()

        with torch.no_grad():

            logits = model(input_tensor)

            probability = torch.sigmoid(
                logits / temperature
            ).item()

        prediction = int(probability >= threshold)

        return {
            "fire_alarm": prediction,
            "probability": round(probability * 100, 2),
            "message": (
                "Fire detected by Deep Learning model."
                if prediction == 1
                else "No fire detected by Deep Learning model."
            )
        }

    except Exception as error:

        print("[DL ERROR] Fire prediction failed:", error)

        return {
            "fire_alarm": None,
            "probability": None,
            "message": str(error)
        }
