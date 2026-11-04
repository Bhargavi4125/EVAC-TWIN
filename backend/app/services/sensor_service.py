
from app.database import sensors_collection
from app.ml.zone_risk import calculate_zone_risk
from app.building_layout import BUILDING_ID, ROOMS


# ============================================================
# EVAC-TWIN — SENSOR INTELLIGENCE SERVICE
# ============================================================


def get_zone_id(sensor):
    if not sensor:
        return ""

    zone_id = sensor.get("zone_id")

    if zone_id is not None:
        return str(zone_id)

    device_id = str(sensor.get("device_id", ""))

    return device_id.removeprefix("sensor-")


# ============================================================
# LATEST SENSOR PER ZONE
# ============================================================

def latest_sensors():
    sensors = []

    for zone_id in ROOMS:
        sensor = sensors_collection.find_one(
            {"zone_id": str(zone_id)},
            {"_id": 0},
            sort=[("timestamp", -1)],
        )

        if sensor:
            sensors.append(sensor)

    sensors.sort(key=lambda sensor: int(get_zone_id(sensor)))

    return sensors


# ============================================================
# SINGLE LATEST SENSOR
# ============================================================

def latest_sensor(zone_id):
    zone_id = str(zone_id)

    return sensors_collection.find_one(
        {"zone_id": zone_id},
        {"_id": 0},
        sort=[("timestamp", -1)],
    )


# ============================================================
# SENSOR INTELLIGENCE
# ============================================================

def enrich_sensor(sensor):
    if not sensor:
        return None

    result = dict(sensor)

    zone_id = get_zone_id(result)

    result["zone_id"] = zone_id
    result.setdefault("device_id", f"sensor-{zone_id}")
    result.setdefault("building_id", BUILDING_ID)

    # --------------------------------------------------------
    # Existing DL result
    # --------------------------------------------------------

    has_dl_result = (
        result.get("risk_level") is not None
        and result.get("risk_score") is not None
    )

    if not has_dl_result:
        result.update(calculate_zone_risk(result))

    else:
        result["risk_level"] = str(
            result.get("risk_level", "LOW")
        ).upper()

        try:
            result["risk_score"] = float(
                result.get("risk_score", 0)
            )
        except (TypeError, ValueError):
            result["risk_score"] = 0.0

        try:
            result["confidence"] = float(
                result.get("confidence", 0)
            )
        except (TypeError, ValueError):
            result["confidence"] = 0.0

        result.setdefault("dl_prediction", result["risk_level"])
        result.setdefault("dl_confidence", result["confidence"])
        result.setdefault("dl_probabilities", {})

        result.setdefault(
            "recommendation",
            "Continue monitoring sensor conditions.",
        )

    # --------------------------------------------------------
    # Zone metadata
    # --------------------------------------------------------

    result["zone"] = f"Zone {zone_id}"

    try:
        result["floor"] = int(
            result.get(
                "floor",
                ROOMS.get(zone_id, {}).get("floor", 0),
            )
        )
    except (TypeError, ValueError):
        result["floor"] = ROOMS.get(
            zone_id, {}
        ).get("floor", 0)

    return result


# ============================================================
# LATEST ZONE INTELLIGENCE
# ============================================================

def latest_zone_intelligence():
    return [
        enrich_sensor(sensor)
        for sensor in latest_sensors()
    ]


# ============================================================
# SENSOR HISTORY
# ============================================================

def sensor_history(zone_id=None, limit=100):
    query = {}

    if zone_id:
        query["zone_id"] = str(zone_id)

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 100

    limit = max(1, min(limit, 1000))

    return list(
        sensors_collection.find(
            query,
            {"_id": 0},
        )
        .sort("timestamp", -1)
        .limit(limit)
    )
