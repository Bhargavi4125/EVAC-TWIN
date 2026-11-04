from fastapi import APIRouter, HTTPException, Body
from app.database import events_collection
from app.building_layout import BUILDING_ID, ROOMS, CORRIDORS, STAIRS, EXITS, EDGES, EXIT_NODES
from app.services.sensor_service import latest_zone_intelligence
from app.services.routing_service import calculate_all_routes, calculate_zone_routes, build_risk_map, BUILDING_GRAPH,compare_algorithms
from app.ml.predict import predict_risk
from app.services.sms_service import send_sms
from app.services.alert_state import (
    claim_sms_alert,
    release_sms_alert,
    clear_sms_alert,
)
router = APIRouter(prefix="/api/evacuation", tags=["Evacuation"])


def _zone_payload(sensor):
    zone_id = str(sensor["zone_id"])
    return {
        **sensor,
        "connections": BUILDING_GRAPH.get(zone_id, []),
    }


@router.get("/health")
def evacuation_health():
    return {
        "status": "healthy",
        "service": "Dynamic Topology-Based Evacuation Router",
        "routing": "active",
        "zone_intelligence": "enabled",
        "building_topology": "enabled",
        "pathfinding": "Dijkstra",
        "dynamic_risk_routing": "enabled",
        "critical_start_escape": "enabled",
        "zones": len(ROOMS),
        "exits": len(EXITS),
        "staircases": len(STAIRS),
        "deep_learning": "PyTorch MLP",
    }


@router.get("/topology")
def get_building_topology():
    return {
        "building_id": BUILDING_ID,
        "zones": ROOMS,
        "corridors": CORRIDORS,
        "stairs": STAIRS,
        "exits": EXITS,
        "exit_nodes": EXIT_NODES,
        "edges": EDGES,
        "graph": BUILDING_GRAPH,
    }

@router.get("/routes")
def get_evacuation_routes(zone_id: str = None):

    sensors = latest_zone_intelligence()

    if not sensors:
        raise HTTPException(status_code=404, detail="No zone sensor data available")


    return calculate_all_routes(sensors, selected_zone=zone_id)



def _build_zone_route(device_id: str, simulation_data=None):
    zone_id = str(device_id).removeprefix("sensor-")

    if zone_id not in ROOMS:
        raise HTTPException(status_code=404, detail="Zone not found")

    sensors = latest_zone_intelligence()

    if not sensors:
        raise HTTPException(status_code=404, detail="No zone sensor data available")

    if simulation_data:
        simulation_sensor = {
            "temperature": simulation_data.get("temperature"),
            "smoke": simulation_data.get("smoke"),
            "occupancy": simulation_data.get("occupancy"),
        }

        risk = predict_risk({
    "temperature": simulation_sensor["temperature"],
    "humidity": float(
        next(
            (s.get("humidity", 50) for s in sensors
             if str(s["zone_id"]) == zone_id),
            50
        )
    ),
    "smoke": simulation_sensor["smoke"],
    "occupancy": simulation_sensor["occupancy"],
})

        for sensor in sensors:
            if str(sensor["zone_id"]) == zone_id:
                sensor["temperature"] = simulation_sensor["temperature"]
                sensor["smoke"] = simulation_sensor["smoke"]
                sensor["occupancy"] = simulation_sensor["occupancy"]
                sensor["risk_score"] = risk["score"]
                sensor["risk_level"] = risk["level"]
                sensor["dl_prediction"] = risk["level"]
                sensor["dl_confidence"] = risk["confidence"]
                sensor["dl_probabilities"] = risk["probabilities"]
                sensor["recommendation"] = risk["recommendation"]
                break

    risk_map = build_risk_map(sensors)

    if zone_id not in risk_map:
        raise HTTPException(status_code=404, detail="No sensor data found for this zone")

    routes = calculate_zone_routes(zone_id, risk_map)
    available = [r for r in routes if r["status"] == "AVAILABLE"]
    caution = [r for r in routes if r["status"] == "CAUTION"]
    candidates = available or caution
    recommended = min(candidates, key=lambda r: r["risk_score"]) if candidates else None

    sensor = next(s for s in sensors if str(s["zone_id"]) == zone_id)

    return {
        "device_id": sensor.get("device_id", f"sensor-{zone_id}"),
        "zone_id": zone_id,
        "route_status": (
    "SAFE ROUTE"
    if recommended and recommended["status"] == "AVAILABLE"
    else "CAUTION ROUTE"
    if recommended and recommended["status"] == "CAUTION"
    else "NO SAFE EXIT"
),
        "recommended_exit": recommended,
        "alternative_exits": sorted(
            [r for r in routes if r["status"] != "BLOCKED" and (not recommended or r["exit"] != recommended["exit"])],
            key=lambda r: r["risk_score"],
        ),
        "all_routes": routes,
        "zone": _zone_payload(sensor),
    }


@router.post("/route/{device_id}")
def get_zone_evacuation_route(
    device_id: str,
    simulation_data: dict = Body(default=None),
):
    return _build_zone_route(device_id, simulation_data)

@router.post("/compare/{device_id}")
def compare_zone_algorithms(
    device_id: str,
    simulation_data: dict = Body(None),
):
    zone_id = str(device_id).removeprefix("sensor-")

    sensors = latest_zone_intelligence()

    if simulation_data:
        risk = predict_risk({
    "temperature": float(simulation_data.get("temperature", 0)),
    "humidity": float(
        next(
            (s.get("humidity", 50) for s in sensors
             if str(s["zone_id"]) == zone_id),
            50
        )
    ),
    "smoke": float(simulation_data.get("smoke", 0)),
    "occupancy": int(simulation_data.get("occupancy", 0)),
})

        for sensor in sensors:
            if str(sensor["zone_id"]) == zone_id:
                sensor["risk_score"] = risk["score"]
                sensor["risk_level"] = risk["level"]
                sensor["dl_prediction"] = risk["level"]
                sensor["dl_confidence"] = risk["confidence"]
                sensor["dl_probabilities"] = risk["probabilities"]
                sensor["recommendation"] = risk["recommendation"]
                break

    risk_map = build_risk_map(sensors)
    comparison = compare_algorithms(zone_id, risk_map)

    return {
        "device_id": device_id,
        "zone_id": zone_id,
        "comparison": comparison,
    }


@router.get("/zone/{device_id}")
def get_zone_route(device_id: str):
    return _build_zone_route(device_id)


@router.get("/summary")
def evacuation_summary():
    sensors = latest_zone_intelligence()
    if not sensors:
        return {
            "route_status": "NO DATA",
            "recommended_exit": None,
            "recommended_exit_name": None,
            "risk_score": 100,
            "critical_zones": 0,
            "high_risk_zones": 0,
            "total_zones": 0,
        }

    result = calculate_all_routes(sensors)
    recommended = result.get("recommended_exit")
    return {
        "route_status": result["route_status"],
        "recommended_exit": recommended["exit"] if recommended else None,
        "recommended_exit_name": recommended["name"] if recommended else None,
        "risk_score": recommended["risk_score"] if recommended else 100,
        "critical_zones": result["critical_zones"],
        "high_risk_zones": result["high_risk_zones"],
        "total_zones": result["total_zones"],
    }


@router.get("/exits")
def evacuation_exits():
    sensors = latest_zone_intelligence()
    if not sensors:
        raise HTTPException(status_code=404, detail="No sensor data available")
    result = calculate_all_routes(sensors)
    return {
        "exits": result["exits"],
        "recommended_exit": result["recommended_exit"],
        "alternative_exits": result["alternative_exits"],
        "route_status": result["route_status"],
    }
@router.post("/simulation/{device_id}")
def run_simulation_sms(
    device_id: str,
    simulation_data: dict = Body(...)
):
    zone_id = str(device_id).removeprefix("sensor-")

    if zone_id not in ROOMS:
        raise HTTPException(status_code=404, detail="Zone not found")

    sensors = latest_zone_intelligence() or []

    live_sensor = next(
        (
            s for s in sensors
            if str(s.get("zone_id")) == zone_id
        ),
        None
    )

    if not live_sensor:
        raise HTTPException(
            status_code=404,
            detail="No sensor data available for this zone"
        )

    temperature = float(simulation_data.get("temperature", 0))
    smoke = float(simulation_data.get("smoke", 0))
    occupancy = int(simulation_data.get("occupancy", 0))
    humidity = float(live_sensor.get("humidity", 50))

    scenario = simulation_data.get("scenario", "Fire Emergency")

    scenario_multipliers = {
        "Fire Emergency": {
            "temperature": 1.2,
            "smoke": 1.4,
            "occupancy": 0.8,
        },
        "High Temperature": {
            "temperature": 1.6,
            "smoke": 0.5,
            "occupancy": 0.6,
        },
        "Smoke Emergency": {
            "temperature": 0.7,
            "smoke": 1.7,
            "occupancy": 0.7,
        },
        "Overcrowding": {
            "temperature": 0.5,
            "smoke": 0.6,
            "occupancy": 1.8,
        },
        "Combined Emergency": {
            "temperature": 1.3,
            "smoke": 1.3,
            "occupancy": 1.3,
        },
    }

    multipliers = scenario_multipliers.get(
        scenario,
        scenario_multipliers["Fire Emergency"]
    )

    adjusted_temperature = temperature * multipliers["temperature"]
    adjusted_smoke = smoke * multipliers["smoke"]
    adjusted_occupancy = round(
        occupancy * multipliers["occupancy"]
    )

    dl_result = predict_risk({
        "temperature": adjusted_temperature,
        "humidity": humidity,
        "smoke": adjusted_smoke,
        "occupancy": adjusted_occupancy,
    })

    risk_score = dl_result["score"]
    risk_level = dl_result["level"]

    if risk_level not in ("HIGH", "CRITICAL"):
        return {
            "sms_sent": False,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "message": "No emergency SMS required."
        }

    if not claim_sms_alert(zone_id):
        return {
            "sms_sent": False,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "message": "SMS already sent for this active zone emergency."
        }

    try:
        simulation_sensor = {
            **live_sensor,
            "temperature": adjusted_temperature,
            "humidity": humidity,
            "smoke": adjusted_smoke,
            "occupancy": adjusted_occupancy,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "dl_prediction": risk_level,
            "dl_confidence": dl_result["confidence"],
            "dl_probabilities": dl_result["probabilities"],
            "recommendation": dl_result["recommendation"],
        }

        updated_sensors = [
            s for s in sensors
            if str(s.get("zone_id")) != zone_id
        ]

        updated_sensors.append(simulation_sensor)

        route_result = calculate_all_routes(
            updated_sensors,
            selected_zone=zone_id
        )

        recommended = route_result.get(
            "selected_zone_recommendation"
        )

        route_name = (
            f"{recommended.get('exit')} - {recommended.get('name')}"
            if recommended
            else "No safe exit available"
        )

        message = (
            f"EVAC-TWIN SIMULATION ALERT! "
            f"Zone: {zone_id}. "
            f"Risk: {risk_level}. "
            f"Risk Score: {risk_score}. "
            f"Recommended Exit: {route_name}. "
            f"Please evacuate immediately."
        )

        success = send_sms(message)

        if not success:
            release_sms_alert(zone_id)

        return {
            "sms_sent": success,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "recommended_exit": route_name,
            "message": (
                "Simulation emergency SMS sent."
                if success
                else "SMS sending failed."
            )
        }

    except Exception as error:
        release_sms_alert(zone_id)
        raise HTTPException(
            status_code=500,
            detail=f"Simulation alert failed: {error}"
        )