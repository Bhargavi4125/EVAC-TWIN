
import json
import os
from datetime import datetime, timezone


import paho.mqtt.client as mqtt

from app.database import (
    sensors_collection,
    events_collection,
)
from app.ml.predict import predict_risk
from app.ml.fire_predict import predict_fire
from app.services.sms_service import send_sms
from app.services.routing_service import calculate_all_routes
from app.services.sensor_service import latest_zone_intelligence
from app.services.alert_state import (
    claim_sms_alert,
    release_sms_alert,
    clear_sms_alert,
)


# ============================================================
# EVAC-TWIN — MQTT SENSOR INGESTION
# ============================================================

MQTT_BROKER = os.getenv(
    "MQTT_BROKER",
    "localhost",
)

MQTT_PORT = int(
    os.getenv(
        "MQTT_PORT",
        "1883",
    )
)

MQTT_TOPIC = os.getenv(
    "MQTT_TOPIC",
    "evac-twin/sensors",
)


# ============================================================
# RISK ORDER
# ============================================================

RISK_ORDER = {
    "LOW": 1,
    "MODERATE": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}


# ============================================================
# PREVIOUS RISK STATE
# ============================================================
#
# Keeps the most recent risk level for every zone in memory.
#
# Example:
#
# {
#     "304": "CRITICAL",
#     "303": "HIGH"
# }
#
# This prevents a new event from being created every time
# the simulator publishes the same risk level.
# ============================================================

previous_risk_levels = {}
previous_fire_alarms = {}

# ============================================================
# SAFE NUMBER
# ============================================================

def safe_float(
    value,
    default=0.0,
):
    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


# ============================================================
# SAFE INTEGER
# ============================================================

def safe_int(
    value,
    default=0,
):
    try:
        return int(
            float(value)
        )

    except (
        TypeError,
        ValueError,
    ):
        return default


# ============================================================
# TIMESTAMP
# ============================================================

def utc_timestamp():
    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# CREATE RISK EVENT
# ============================================================

def create_risk_event(
    sensor,
    previous_level,
    current_level,
):
    """
    Create an event when a zone's risk level changes.

    Events are generated for:

        LOW → MODERATE
        MODERATE → HIGH
        HIGH → CRITICAL

    and also for recovery:

        CRITICAL → HIGH
        HIGH → MODERATE
        MODERATE → LOW
    """

    zone_id = str(
        sensor.get(
            "zone_id",
            "",
        )
    )

    building_id = sensor.get(
        "building_id",
        "building-alpha",
    )

    risk_score = safe_float(
        sensor.get(
            "risk_score",
            0,
        )
    )

    # --------------------------------------------------------
    # Determine event type
    # --------------------------------------------------------

    previous_rank = RISK_ORDER.get(
        previous_level,
        0,
    )

    current_rank = RISK_ORDER.get(
        current_level,
        0,
    )

    if current_rank > previous_rank:

        event_type = "RISK_ESCALATION"

        severity = current_level

        message = (
            f"Risk escalated in Zone {zone_id}: "
            f"{previous_level} → {current_level}."
        )

    elif current_rank < previous_rank:

        event_type = "RISK_REDUCTION"

        severity = current_level

        message = (
            f"Risk reduced in Zone {zone_id}: "
            f"{previous_level} → {current_level}."
        )

    else:

        return



    
    # Resolve previous active risk events when risk decreases
    if current_rank < previous_rank:
        events_collection.update_many(
            {
                "building_id": building_id,
                "zone_id": zone_id,
                "status": "ACTIVE",
                "event_type": "RISK_ESCALATION",
            },
            {
                "$set": {
                    "status": "RESOLVED",
                    "resolved_at": utc_timestamp(),
                }
            },
        )
    # Resolve older escalation events when risk decreases.
   
    # --------------------------------------------------------
    # Create event document
    # --------------------------------------------------------

    event = {
        "event_type": event_type,

        "building_id": building_id,

        "zone_id": zone_id,

        "device_id": sensor.get(
            "device_id",
            f"sensor-{zone_id}",
        ),

        "previous_risk_level": previous_level,

        "risk_level": current_level,

        "risk_score": risk_score,

        "severity": severity,

        "message": message,

        "recommendation": sensor.get(
            "recommendation",
            "Continue monitoring sensor conditions.",
        ),

        "simulation_mode": sensor.get(
            "simulation_mode",
            "LIVE",
        ),

        "timestamp": utc_timestamp(),

        "status": (
    "RESOLVED"
    if event_type == "RISK_REDUCTION"
    else "ACTIVE"
),
    }

    try:

        events_collection.insert_one(
            event
        )

        print(
            "[EVENT] "
            f"{event_type} | "
            f"Zone {zone_id} | "
            f"{previous_level} → {current_level}"
        )

    except Exception as error:

        print(
            "[EVENT ERROR] "
            f"Unable to save event: {error}"
        )




def create_fire_alarm_event(sensor):
    risk_level = str(
        sensor.get("risk_level", "LOW")
    ).upper()

    risk_score = safe_float(
        sensor.get("risk_score", 0)
    )

    fire_probability = safe_float(
        sensor.get("fire_alarm_probability", 0)
    )

    # Do not create a CRITICAL fire event from LOW-risk data
    # unless the fire model independently confirms a strong alarm.
    if (
        sensor.get("fire_alarm_prediction") != 1
        or fire_probability < 80
    ):
        return

    event = {
        "event_type": "FIRE_ALARM_PREDICTED",
        "building_id": sensor.get(
            "building_id", "building-alpha"
        ),
        "zone_id": sensor.get("zone_id", ""),
        "device_id": sensor.get("device_id", ""),
        "risk_level": risk_level,
        "risk_score": risk_score,
        "severity": "CRITICAL",
        "message": (
            f"FIRE ALERT: Fire alarm predicted in Zone "
            f"{sensor.get('zone_id', '')}, "
            f"Floor {sensor.get('floor', 'Unknown')}."
        ),
        "recommendation": (
            "Check the affected zone and follow the verified "
            "evacuation route."
        ),
        "simulation_mode": sensor.get(
            "simulation_mode", "LIVE"
        ),
        "timestamp": utc_timestamp(),
        "status": "ACTIVE",
    }

    try:
        events_collection.insert_one(event)
        print("\nFIRE ALERT")
        print(event["message"])
        print("Risk:", risk_level)
        print("Fire probability:", fire_probability)
        print(event["recommendation"])

    except Exception as error:
        print(f"[FIRE ALERT ERROR] {error}")

# ============================================================
# MQTT CONNECT
# ============================================================

def on_connect(
    client,
    userdata,
    flags,
    reason_code,
    properties,
):

    if reason_code == 0:

        print()
        print(
            "MQTT connected"
        )

        client.subscribe(
            MQTT_TOPIC
        )

        print(
            f"Subscribed to {MQTT_TOPIC}"
        )

    else:

        print(
            "MQTT connection failed: "
            f"{reason_code}"
        )


# ============================================================
# MQTT MESSAGE
# ============================================================

def on_message(
    client,
    userdata,
    msg,
):

    try:

        # ====================================================
        # READ PAYLOAD
        # ====================================================

        payload = msg.payload.decode(
            "utf-8"
        )

        sensor = json.loads(
            payload
        )

        if not isinstance(sensor, dict):

            print(
                "[MQTT] "
                "Ignoring invalid sensor payload."
            )

            return

        # ====================================================
        # NORMALIZE ZONE
        # ====================================================

        sensor["Temperature[C]"] = sensor.get("Temperature[C]", sensor.get("temperature"))
        sensor["Humidity[%]"] = sensor.get("Humidity[%]", sensor.get("humidity"))
        sensor["TVOC[ppb]"] = sensor.get("TVOC[ppb]")
        sensor["eCO2[ppm]"] = sensor.get("eCO2[ppm]")
        sensor["PM1.0"] = sensor.get("PM1.0")
        sensor["PM2.5"] = sensor.get("PM2.5")
        zone_id = sensor.get(
            "zone_id"
        )

        device_id = sensor.get(
            "device_id"
        )

        if zone_id is None and device_id:

            zone_id = str(
                device_id
            ).replace(
                "sensor-",
                "",
                1,
            )

        if zone_id is not None:

            zone_id = str(
                zone_id
            )

        else:

            zone_id = ""

        if not device_id:

            device_id = (
                f"sensor-{zone_id}"
            )

        sensor["zone_id"] = zone_id

        sensor["device_id"] = device_id

        # ====================================================
        # NORMALIZE SENSOR VALUES
        # ====================================================

        sensor["temperature"] = safe_float(
            sensor.get(
                "temperature",
                0,
            )
        )

        sensor["humidity"] = safe_float(
            sensor.get(
                "humidity",
                0,
            )
        )

        sensor["smoke"] = safe_float(
            sensor.get(
                "smoke",
                0,
            )
        )

        sensor["occupancy"] = safe_int(
            sensor.get(
                "occupancy",
                0,
            )
        )

        # ====================================================
        # TIMESTAMP
        # ====================================================

        if not sensor.get(
            "timestamp"
        ):

            sensor["timestamp"] = (
                utc_timestamp()
            )

                # ====================================================
        # DEEP LEARNING RISK PREDICTION
        # ====================================================

        dl_result = predict_risk(
            {
                "temperature": sensor["temperature"],
                "humidity": sensor["humidity"],
                "smoke": sensor["smoke"],
                "occupancy": sensor["occupancy"],
            }
        )

        current_level = str(
            dl_result.get("level", "LOW")
        ).upper()

        sensor["risk_score"] = float(
            dl_result.get("score", 0)
        )

        sensor["risk_level"] = current_level
        sensor["dl_prediction"] = current_level

        sensor["confidence"] = float(
            dl_result.get("confidence", 0)
        )

        sensor["dl_confidence"] = sensor["confidence"]

        sensor["dl_probabilities"] = dl_result.get(
            "probabilities", {}
        )

        sensor["recommendation"] = dl_result.get(
            "recommendation",
            "Continue monitoring sensor conditions."
        )
        
        
        # DATASET-BASED FIRE PREDICTION

        fire_features = [
            "Temperature[C]",
            "Humidity[%]",
            "TVOC[ppb]",
            "eCO2[ppm]",
            "PM1.0",
            "PM2.5",
        ]

        has_fire_features = all(
            feature in sensor and sensor[feature] is not None
            for feature in fire_features
        )

        print(
            "FIRE FEATURES:",
            {
                feature: sensor.get(feature)
                for feature in fire_features
            }
        )


        if has_fire_features:
            fire_result = predict_fire(
                {
                    feature: safe_float(sensor[feature])
                    for feature in fire_features
                }
            )

            print("FIRE MODEL RESULT:", fire_result)

            current_fire_alarm = fire_result["fire_alarm"]
            fire_probability = fire_result.get("probability") or 0

            sensor["fire_alarm_dl_prediction"] = current_fire_alarm
            sensor["fire_alarm_probability"] = fire_probability
            sensor["fire_alarm_prediction"] = (
               1
               if current_fire_alarm == 1 and fire_probability >= 80
               else 0
)
            sensor["fire_alarm_message"] = fire_result["message"]
            sensor["fire_alarm_source"] = "DL_MODEL"
            print(
    "[FIRE CHECK]",
    sensor["device_id"],
    "Probability =", sensor["fire_alarm_probability"],
    "Final =", sensor["fire_alarm_prediction"]
)

           
            # Create an event only when the final prediction
            # crosses the configured threshold.
            print(
                "[FIRE CHECK]",
                sensor["device_id"],
                "Probability =", sensor["fire_alarm_probability"],
                "Final =", sensor["fire_alarm_prediction"]
            )

            print(
                "[FIRE DEBUG]",
                "Device =", sensor.get("device_id"),
                "Prediction =", sensor.get("fire_alarm_prediction"),
                "Probability =", fire_probability,
                "Previous =", previous_fire_alarms.get(zone_id, 0)
            )

            if (
                sensor["fire_alarm_prediction"] == 1
                and fire_probability >= 80
            ):
                previous_fire_alarm = previous_fire_alarms.get(
                    zone_id, 0
                )

                if previous_fire_alarm != 1:
                    create_fire_alarm_event(sensor)

                previous_fire_alarms[zone_id] = 1

            else:
                previous_fire_alarms[zone_id] = 0

                # Resolve previous fire alerts when prediction clears.
                events_collection.update_many(
                    {
                        "building_id": sensor.get(
                            "building_id",
                            "building-alpha",
                        ),
                        "zone_id": zone_id,
                        "event_type": "FIRE_ALARM_PREDICTED",
                        "status": "ACTIVE",
                    },
                    {
                        "$set": {
                            "status": "RESOLVED",
                            "resolved_at": utc_timestamp(),
                        }
                    },
                )


        # ====================================================
        # SIMULATION MODE
        # ====================================================

        if "simulation_mode" not in sensor:

            sensor["simulation_mode"] = (
                "LIVE"
            )

        # ====================================================
        # SOURCE
        # ====================================================

        sensor["source"] = "MQTT"

        # ====================================================
        # RISK EVENT DETECTION
        # ====================================================

        previous_level = (
            previous_risk_levels.get(
                zone_id
            )
        )

        # Resolve stale active risk events
        if (
            current_level not in ("HIGH", "CRITICAL")
            and (
                previous_level is None
                or previous_level in ("HIGH", "CRITICAL")
            )
        ):
            events_collection.update_many(
                {
                    "building_id": sensor.get(
                        "building_id",
                        "building-alpha",
                    ),
                    "zone_id": zone_id,
                    "event_type": "RISK_ESCALATION",
                    "status": "ACTIVE",
                },
                {
                    "$set": {
                        "status": "RESOLVED",
                        "resolved_at": utc_timestamp(),
                    }
                },
            )

        # Existing escalation/recovery code continues here
        effective_previous = (
            previous_level
            if previous_level is not None
            else "LOW"
        )
        # --------------------------------------------------
        # ESCALATION: zone is now HIGH or CRITICAL.
        # Fire an event when entering this band for the
        # first time (previous_level is None → treat as LOW)
        # or when transitioning up from a lower band.
        # --------------------------------------------------
        effective_previous = previous_level if previous_level is not None else "LOW"

        if current_level in ("HIGH", "CRITICAL"):
            if effective_previous not in ("HIGH", "CRITICAL"):
                create_risk_event(
                    sensor,
                    effective_previous,
                    current_level,
                )

        # --------------------------------------------------
        # RECOVERY: zone was HIGH/CRITICAL and has now
        # dropped below that threshold.
        # --------------------------------------------------
        elif previous_level in ("HIGH", "CRITICAL") and current_level not in ("HIGH", "CRITICAL"):
            create_risk_event(
                sensor,
                previous_level,
                current_level,
            )

        # Save the latest state.
        previous_risk_levels[
            zone_id
        ] = current_level

    
           # ====================================================
        # ONE-TIME EMERGENCY SMS ALERT
        # ====================================================

        ml_fire_alarm = (
           sensor.get("fire_alarm_prediction", 0) == 1
)

        risk_emergency = current_level in (
    "HIGH",
    "CRITICAL"
)

        emergency_active = ml_fire_alarm or risk_emergency

        if emergency_active:

            if claim_sms_alert(zone_id):

                try:
                    sensors = latest_zone_intelligence() or []

                    sensors = [
                        s for s in sensors
                        if str(s.get("zone_id")) != zone_id
                    ]

                    sensors.append(sensor)

                    route_result = calculate_all_routes(
                        sensors,
                        selected_zone=zone_id
                    )

                    recommended = route_result.get(
                        "selected_zone_recommendation"
                    )

                    route_name = (
                        f"{recommended.get('exit')} - "
                        f"{recommended.get('name')}"
                        if recommended
                        else "No safe exit available"
                    )

                    message = (
                        f"EVAC-TWIN EMERGENCY ALERT! "
                        f"Zone: {zone_id}. "
                        f"Risk: {current_level}. "
                        f"Risk Score: {sensor['risk_score']}. "
                        f"Recommended Exit: {route_name}. "
                        f"Please evacuate immediately."
                    )

                    result = send_sms(message)

                    if result:
                        print(f"[SMS] Alert sent for Zone {zone_id}")
                    else:
                        release_sms_alert(zone_id)
                        print(f"[SMS] Failed for Zone {zone_id}")

                except Exception as e:
                    release_sms_alert(zone_id)
                    print("[SMS] Emergency alert error:", e)

        else:
            clear_sms_alert(zone_id)

        

        # ====================================================
        # SAVE SENSOR DATA
        # ====================================================

        sensors_collection.insert_one(
            sensor
        )

        # ====================================================
        # CONSOLE LOG
        # ====================================================

        print(
            "[SAVED] "
            f"Zone {zone_id} | "
            f"{sensor['temperature']:.2f}°C | "
            f"Humidity "
            f"{sensor['humidity']:.2f}% | "
            f"Smoke "
            f"{sensor['smoke']:.3f} | "
            f"People "
            f"{sensor['occupancy']} | "
            f"DL "
            f"{sensor['dl_prediction']} | "
            f"Score "
            f"{sensor['risk_score']:.2f} | "
            f"Confidence "
            f"{sensor['dl_confidence']:.2f}%"
        )

    except json.JSONDecodeError as error:

        print(
            f"[MQTT JSON ERROR] {error}"
        )

    except Exception as error:

        print(
            f"[MQTT ERROR] {error}"
        )


# ============================================================
# START MQTT SUBSCRIBER
# ============================================================

def start_mqtt_subscriber():

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2
    )

    client.on_connect = on_connect

    client.on_message = on_message

    client.connect(
        MQTT_BROKER,
        MQTT_PORT,
        60,
    )

    client.loop_start()

    print()
    print(
        "MQTT subscriber started"
    )

    print(
        f"Broker : "
        f"{MQTT_BROKER}:{MQTT_PORT}"
    )

    print(
        f"Topic  : "
        f"{MQTT_TOPIC}"
    )

    return client
