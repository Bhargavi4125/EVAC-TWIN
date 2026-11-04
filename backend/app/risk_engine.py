
# ============================================================
# EVAC-TWIN - DETERMINISTIC RISK ENGINE
# ============================================================

def _safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def calculate_risk(sensor):
    if not sensor:
        return {
            "score": 0,
            "level": "NO DATA",
            "recommendation": "Waiting for sensor data.",
            "factors": {
                "temperature": 0,
                "smoke": 0,
                "occupancy": 0,
            },
        }

    temperature = max(
        _safe_float(sensor.get("temperature")),
        0.0
    )

    smoke = max(
        _safe_float(sensor.get("smoke")),
        0.0
    )

    occupancy = max(
        _safe_int(sensor.get("occupancy")),
        0
    )

    # Temperature risk - Maximum 35
    if temperature >= 50:
        temperature_risk = 35
    elif temperature >= 45:
        temperature_risk = 30
    elif temperature >= 40:
        temperature_risk = 25
    elif temperature >= 35:
        temperature_risk = 15
    elif temperature >= 32:
        temperature_risk = 5
    else:
        temperature_risk = 0

    # Smoke risk - Maximum 40
    if smoke >= 0.8:
        smoke_risk = 40
    elif smoke >= 0.6:
        smoke_risk = 35
    elif smoke >= 0.5:
        smoke_risk = 30
    elif smoke >= 0.3:
        smoke_risk = 15
    elif smoke >= 0.15:
        smoke_risk = 5
    else:
        smoke_risk = 0

    # Occupancy risk - Maximum 25
    if occupancy >= 50:
        occupancy_risk = 25
    elif occupancy >= 40:
        occupancy_risk = 20
    elif occupancy >= 30:
        occupancy_risk = 15
    elif occupancy >= 15:
        occupancy_risk = 5
    else:
        occupancy_risk = 0

    # Total risk score
    score = min(
        temperature_risk + smoke_risk + occupancy_risk,
        100
    )

    # Risk classification
    if score >= 70:
        level = "CRITICAL"
        recommendation = (
            "Immediate evacuation recommended. "
            "Activate emergency procedures."
        )
    elif score >= 40:
        level = "HIGH"
        recommendation = (
            "High-risk conditions detected. "
            "Prepare evacuation routes and alert occupants."
        )
    elif score >= 20:
        level = "MODERATE"
        recommendation = (
            "Elevated conditions detected. "
            "Continue close monitoring and prepare for escalation."
        )
    else:
        level = "LOW"
        recommendation = (
            "Environmental conditions are stable. "
            "Continue normal monitoring."
        )

    return {
        "score": score,
        "level": level,
        "recommendation": recommendation,
        "factors": {
            "temperature": temperature_risk,
            "smoke": smoke_risk,
            "occupancy": occupancy_risk,
        },
    }
