from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.ml.predict import predict_risk
from pydantic import BaseModel

from app.database import (
    buildings_collection,
    events_collection,
    check_database_connection,
)
from app.building_layout import BUILDING_ID, ROOMS, CORRIDORS, STAIRS, EXITS
from app.mqtt_subscriber import start_mqtt_subscriber
from app.routing.evacuation_router import router as evacuation_router
from app.services.sensor_service import latest_zone_intelligence, sensor_history

app = FastAPI(
    title="EVAC-TWIN",
    description="Emergency Intelligence Digital Twin",
    version="2.0.0",
)
class RiskPredictionInput(BaseModel):
    temperature: float
    humidity: float
    smoke: float
    occupancy: int
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(evacuation_router)


@app.get("/")
def root():
    return {
        "project": "EVAC-TWIN",
        "service": "Emergency Intelligence Digital Twin",
        "motto": "Sense → Predict → Understand → Simulate → Route → Respond",
        "status": "online",
        "backend": "FastAPI",
        "routing": "dynamic",
        "deep_learning": "PyTorch MLP",
        "mqtt": "enabled",
    }


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "service": "EVAC-TWIN Backend",
        "database": "connected" if check_database_connection() else "disconnected",
        "mqtt": "enabled",
        "deep_learning": "enabled",
        "routing": "dynamic",
        "topology": "Building Alpha",
    }


@app.get("/api/sensors")
def get_sensors():
    return latest_zone_intelligence()


@app.get("/api/sensors/history")
def get_sensor_history(zone_id: str | None = None, limit: int = 100):
    return sensor_history(zone_id, limit)


@app.get("/api/sensors/{zone_id}")
def get_sensor(zone_id: str):
    sensors = latest_zone_intelligence()
    sensor = next((s for s in sensors if str(s["zone_id"]) == str(zone_id).removeprefix("sensor-")), None)
    if sensor is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Zone sensor not found")
    return sensor
@app.post("/api/ai/predict-risk")
def predict_risk_api(data: RiskPredictionInput):
    sensor_data = {
        "temperature": data.temperature,
        "humidity": data.humidity,
        "smoke": data.smoke,
        "occupancy": data.occupancy,
    }

    result = predict_risk(sensor_data)

    return {
        "model": "PyTorch Deep Learning",
        "prediction": result.get("level"),
        "risk_score": result.get("score"),
        "confidence": result.get("confidence"),
        "probabilities": result.get("probabilities"),
        "recommendation": result.get("recommendation"),
    }


@app.get("/api/events")
def get_events():
    active_events = list(
        events_collection.find(
            {"status": "ACTIVE"},
            {"_id": 0}
        ).sort("timestamp", -1).limit(100)
    )

    return active_events


@app.get("/api/buildings")
def get_buildings():
    buildings = list(buildings_collection.find({}, {"_id": 0}))
    if not buildings:
        return [{
            "building_id": BUILDING_ID,
            "name": "Building Alpha",
            "floors": 3,
            "zones": len(ROOMS),
            "staircases": len(STAIRS),
            "exits": len(EXITS),
        }]
    return buildings


@app.get("/api/buildings/summary")
def get_building_summary():
    sensors = latest_zone_intelligence()
    distribution = {"low": 0, "moderate": 0, "high": 0, "critical": 0}
    total_occupancy = 0
    for sensor in sensors:
        level = str(sensor.get("risk_level", "LOW")).lower()
        if level in distribution:
            distribution[level] += 1
        total_occupancy += int(sensor.get("occupancy", 0) or 0)

    if distribution["critical"]:
        overall = "CRITICAL"
    elif distribution["high"]:
        overall = "HIGH"
    elif distribution["moderate"]:
        overall = "MODERATE"
    else:
        overall = "LOW"

    return {
        "building_id": BUILDING_ID,
        "total_zones": len(sensors),
        "overall_risk": overall,
        "risk_distribution": distribution,
        "total_occupancy": total_occupancy,
    }


mqtt_client = None


@app.on_event("startup")
def startup_event():
    global mqtt_client
    print("=" * 60)
    print("EVAC-TWIN BACKEND — ONLINE")
    print("=" * 60)
    try:
        mqtt_client = start_mqtt_subscriber()
        print("MQTT Subscriber : STARTED")
    except Exception as error:
        print(f"MQTT Subscriber : FAILED - {error}")


@app.on_event("shutdown")
def shutdown_event():
    global mqtt_client
    if mqtt_client:
        try:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
        except Exception:
            pass
