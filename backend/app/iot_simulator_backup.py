import argparse
import json
import os
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt


# ============================================================
# EVAC-TWIN — VIRTUAL IoT SENSOR SIMULATOR
# ============================================================

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "evac-twin/sensors")
PUBLISH_INTERVAL = float(os.getenv("PUBLISH_INTERVAL", "3"))


# ============================================================
# BUILDING CONFIGURATION
# ============================================================

BUILDING_ID = "building-alpha"

ZONES = [
    # Floor 1
    {"zone_id": "101", "floor": 1, "base_occupancy": 6},
    {"zone_id": "102", "floor": 1, "base_occupancy": 7},
    {"zone_id": "103", "floor": 1, "base_occupancy": 5},
    {"zone_id": "104", "floor": 1, "base_occupancy": 4},

    # Floor 2
    {"zone_id": "201", "floor": 2, "base_occupancy": 8},
    {"zone_id": "202", "floor": 2, "base_occupancy": 7},
    {"zone_id": "203", "floor": 2, "base_occupancy": 6},
    {"zone_id": "204", "floor": 2, "base_occupancy": 5},

    # Floor 3
    {"zone_id": "301", "floor": 3, "base_occupancy": 7},
    {"zone_id": "302", "floor": 3, "base_occupancy": 6},
    {"zone_id": "303", "floor": 3, "base_occupancy": 5},
    {"zone_id": "304", "floor": 3, "base_occupancy": 4},
]


# ============================================================
# INITIAL SENSOR STATE
# ============================================================


sensor_state = {}

for zone in ZONES:
    sensor_state[zone["zone_id"]] = {
        "temperature": random.uniform(29.0, 31.0),
        "humidity": random.uniform(48.0, 58.0),
        "smoke": random.uniform(0.05, 0.15),
        "occupancy": zone["base_occupancy"],
        "tvoc": random.uniform(50, 300),
        "eco2": random.uniform(400, 600),
        "pm1": random.uniform(1.0, 3.0),
        "pm25": random.uniform(1.0, 4.0),
    }


# ============================================================
# SIMULATION MODE  — set via CLI args or defaults
# ============================================================
#
# Usage:
#   python -m app.iot_simulator                     # NORMAL mode, random zone
#   python -m app.iot_simulator --mode FIRE          # FIRE in random zone
#   python -m app.iot_simulator --mode FIRE --zone 304
#   python -m app.iot_simulator --mode SMOKE --zone 201
#

_parser = argparse.ArgumentParser(
    description="EVAC-TWIN Virtual IoT Sensor Simulator"
)
_parser.add_argument(
    "--mode",
    default=os.getenv("SIMULATION_MODE", "FIRE"),
    choices=["NORMAL", "FIRE", "SMOKE", "CROWD"],
    help="Simulation scenario mode",
)
_parser.add_argument(
    "--zone",
    default=os.getenv("EMERGENCY_ZONE", ""),
    help="Emergency zone ID (e.g. 304). Leave blank for random selection.",
)
_args, _unknown = _parser.parse_known_args()

SIMULATION_MODE: str = _args.mode.upper()

# Resolve emergency zone: use CLI arg, or pick a random zone.
_zone_arg = str(_args.zone).strip()
if _zone_arg and _zone_arg in [z["zone_id"] for z in ZONES]:
    EMERGENCY_ZONE: str = _zone_arg
elif SIMULATION_MODE != "NORMAL":
    EMERGENCY_ZONE = random.choice(
        [z["zone_id"] for z in ZONES]
    )
else:
    EMERGENCY_ZONE = ""


# ============================================================
# MQTT CONNECTION
# ============================================================

client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2
)


def on_connect(client, userdata, flags, reason_code, properties):

    if reason_code == 0:
        print()
        print("=" * 60)
        print("EVAC-TWIN IoT SIMULATOR")
        print("=" * 60)
        print("Connected to MQTT broker")
        print(f"Broker : {MQTT_BROKER}:{MQTT_PORT}")
        print(f"Topic  : {MQTT_TOPIC}")
        print(f"Mode   : {SIMULATION_MODE}")
        if EMERGENCY_ZONE:
            print(f"Zone   : {EMERGENCY_ZONE} (emergency origin)")
        print("=" * 60)
        print()

    else:
        print(
            f"MQTT connection failed: {reason_code}"
        )


client.on_connect = on_connect


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


def smooth_change(
    current,
    target,
    max_change
):
    difference = target - current

    change = clamp(
        difference,
        -max_change,
        max_change
    )

    return current + change


# ============================================================
# NORMAL ENVIRONMENT
# ============================================================

def update_normal(zone_id, zone):

    state = sensor_state[zone_id]

    # --------------------------------------------------------
    # Temperature
    # --------------------------------------------------------

    target_temperature = random.uniform(
        29.5,
        31.5
    )

    state["temperature"] = smooth_change(
        state["temperature"],
        target_temperature,
        0.35
    )

    # --------------------------------------------------------
    # Humidity
    # --------------------------------------------------------

    target_humidity = random.uniform(
        48,
        58
    )

    state["humidity"] = smooth_change(
        state["humidity"],
        target_humidity,
        1.0
    )

    # --------------------------------------------------------
    # Smoke
    # --------------------------------------------------------

    target_smoke = random.uniform(
        0.05,
        0.15
    )

    state["smoke"] = smooth_change(
        state["smoke"],
        target_smoke,
        0.03
    )

    # --------------------------------------------------------
    # Occupancy
    # --------------------------------------------------------

    occupancy_change = random.choice(
        [-1, 0, 0, 0, 1]
    )

    state["occupancy"] += occupancy_change

    state["occupancy"] = int(
        clamp(
            state["occupancy"],
            0,
            50
        )
    )


# ============================================================
# FIRE SIMULATION
# ============================================================

def update_fire(zone_id, zone):

    state = sensor_state[zone_id]

    # --------------------------------------------------------
    # Emergency zone
    # --------------------------------------------------------

    if zone_id == EMERGENCY_ZONE:

        state["temperature"] += random.uniform(
            0.4,
            1.2
        )

        state["smoke"] += random.uniform(
            0.04,
            0.10
        )

    else:

        # ----------------------------------------------------
        # Nearby zones gradually become affected.
        # ----------------------------------------------------

        emergency_floor = next(
            (
                item["floor"]
                for item in ZONES
                if item["zone_id"] == EMERGENCY_ZONE
            ),
            1
        )

        distance = abs(
            zone["floor"] - emergency_floor
        )

        if distance == 0:

            state["temperature"] += random.uniform(
                0.10,
                0.30
            )

            state["smoke"] += random.uniform(
                0.01,
                0.03
            )

        elif distance == 1:

            state["temperature"] += random.uniform(
                0.02,
                0.08
            )

            state["smoke"] += random.uniform(
                0.002,
                0.012
            )

        else:

            state["temperature"] = smooth_change(
                state["temperature"],
                30,
                0.10
            )

            state["smoke"] = smooth_change(
                state["smoke"],
                0.10,
                0.01
            )

    # --------------------------------------------------------
    # Humidity
    # --------------------------------------------------------

    state["humidity"] = smooth_change(
        state["humidity"],
        45,
        0.5
    )

    # --------------------------------------------------------
    # Occupancy
    # --------------------------------------------------------

    # People gradually leave affected areas.
    if (
        state["smoke"] >= 0.6
        or state["temperature"] >= 38
    ):

        state["occupancy"] -= random.randint(
            0,
            2
        )

    else:

        state["occupancy"] += random.choice(
            [-1, 0, 0, 1]
        )

    state["occupancy"] = int(
        clamp(
            state["occupancy"],
            0,
            50
        )
    )
 
    # Simulated air-quality sensor changes during fire
    
    if zone_id == EMERGENCY_ZONE:
        state["tvoc"] = 1103.0
        state["eco2"] = 404.0
        state["pm1"] = 1.87
        state["pm25"] = 1.94
    else:
        state["tvoc"] = clamp(state["tvoc"], 0, 60000)
        state["eco2"] = clamp(state["eco2"], 400, 60000)
        state["pm1"] = clamp(state["pm1"], 0, 14333.69)
        state["pm25"] = clamp(state["pm25"], 0, 45432.26)
    # --------------------------------------------------------
    # Safety limits
    # --------------------------------------------------------

    state["temperature"] = clamp(
        state["temperature"],
        25,
        55
    )

    state["smoke"] = clamp(
        state["smoke"],
        0,
        1
    )


# ============================================================
# SMOKE SIMULATION
# ============================================================

def update_smoke(zone_id, zone):

    state = sensor_state[zone_id]

    if zone_id == EMERGENCY_ZONE:

        state["smoke"] += random.uniform(
            0.03,
            0.07
        )

        state["temperature"] += random.uniform(
            0.05,
            0.20
        )

    else:

        state["smoke"] += random.uniform(
            0.005,
            0.025
        )

        state["temperature"] += random.uniform(
            0.01,
            0.05
        )

    state["smoke"] = clamp(
        state["smoke"],
        0,
        1
    )

    state["temperature"] = clamp(
        state["temperature"],
        25,
        50
    )

    state["humidity"] = smooth_change(
        state["humidity"],
        47,
        0.5
    )


# ============================================================
# CROWD SIMULATION
# ============================================================

def update_crowd(zone_id, zone):

    state = sensor_state[zone_id]

    state["occupancy"] += random.randint(
        0,
        2
    )

    state["occupancy"] = int(
        clamp(
            state["occupancy"],
            0,
            50
        )
    )

    state["temperature"] += random.uniform(
        0.01,
        0.08
    )

    state["humidity"] += random.uniform(
        0.02,
        0.10
    )

    state["temperature"] = clamp(
        state["temperature"],
        25,
        45
    )

    state["humidity"] = clamp(
        state["humidity"],
        30,
        80
    )


# ============================================================
# UPDATE SENSOR
# ============================================================

def update_sensor(zone):

    zone_id = zone["zone_id"]

    if SIMULATION_MODE == "FIRE":

        update_fire(
            zone_id,
            zone
        )

    elif SIMULATION_MODE == "SMOKE":

        update_smoke(
            zone_id,
            zone
        )

    elif SIMULATION_MODE == "CROWD":

        update_crowd(
            zone_id,
            zone
        )

    else:

        update_normal(
            zone_id,
            zone
        )


# ============================================================
# CREATE MQTT PAYLOAD
# ============================================================

def create_payload(zone):

    zone_id = zone["zone_id"]

    state = sensor_state[zone_id]

    return {

        "device_id": f"sensor-{zone_id}",

        "building_id": BUILDING_ID,

        "zone_id": zone_id,

        "floor": zone["floor"],

        "temperature": round(
            state["temperature"],
            2
        ),

        "humidity": round(
            state["humidity"],
            2
        ),

        "smoke": round(
            state["smoke"],
            3
        ),
        
        "TVOC[ppb]": round(state["tvoc"], 2),

        "eCO2[ppm]": round(state["eco2"], 2),

        "PM1.0": round(state["pm1"], 2),

        "PM2.5": round(state["pm25"], 2),

        "occupancy": int(
            state["occupancy"]
        ),

        "simulation_mode": SIMULATION_MODE,

        "timestamp": datetime.now(
            timezone.utc
        ).isoformat()
    }


# ============================================================
# PUBLISH SENSOR DATA
# ============================================================

def publish_sensor(zone):

    update_sensor(zone)

    payload = create_payload(zone)

    message = json.dumps(
        payload
    )

    client.publish(
        MQTT_TOPIC,
        message
    )

    print(
        f"[{payload['zone_id']}] "
        f"T={payload['temperature']}°C | "
        f"H={payload['humidity']}% | "
        f"Smoke={payload['smoke']} | "
        f"People={payload['occupancy']}"
    )


# ============================================================
# MAIN LOOP
# ============================================================

def main():

    try:

        print("Connecting to MQTT...")

        client.connect(
            MQTT_BROKER,
            MQTT_PORT,
            60
        )

        client.loop_start()

        time.sleep(1)

        while True:

            for zone in ZONES:

                publish_sensor(zone)

            print(
                "-" * 60
            )

            time.sleep(
                PUBLISH_INTERVAL
            )

    except KeyboardInterrupt:

        print()
        print(
            "Stopping IoT simulator..."
        )

    except Exception as error:

        print(
            f"Simulator error: {error}"
        )

    finally:

        client.loop_stop()
        client.disconnect()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
