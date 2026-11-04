
from app.ml.predict import predict_risk


# ============================================================
# EVAC-TWIN — ZONE RISK INTELLIGENCE
# ============================================================


# ============================================================
# FLOOR DETECTION
# ============================================================

def get_floor(device_id):

    try:

        device_number = int(
            str(device_id).replace(
                "sensor-",
                "",
                1
            )
        )

        return device_number // 100

    except (
        ValueError,
        TypeError
    ):

        return 0


# ============================================================
# ZONE ID
# ============================================================

def get_zone_id(sensor):

    if not sensor:
        return ""

    zone_id = sensor.get(
        "zone_id"
    )

    if zone_id is not None:

        return str(
            zone_id
        )

    device_id = str(
        sensor.get(
            "device_id",
            ""
        )
    )

    if device_id.startswith(
        "sensor-"
    ):

        return device_id.replace(
            "sensor-",
            "",
            1
        )

    return device_id


# ============================================================
# ZONE NAME
# ============================================================

def get_zone_name(device_id):

    zone_id = str(
        device_id
    ).replace(
        "sensor-",
        "",
        1
    )

    return f"Zone {zone_id}"


# ============================================================
# ZONE RISK
# ============================================================

def calculate_zone_risk(sensor):

    zone_id = get_zone_id(
        sensor
    )

    device_id = sensor.get(
        "device_id",
        f"sensor-{zone_id}"
    )

    # --------------------------------------------------------
    # RUN DEEP LEARNING MODEL
    # --------------------------------------------------------

    dl_result = predict_risk({

        "temperature":
            sensor.get(
                "temperature",
                0
            ),

        "humidity":
            sensor.get(
                "humidity",
                0
            ),

        "smoke":
            sensor.get(
                "smoke",
                0
            ),

        "occupancy":
            sensor.get(
                "occupancy",
                0
            ),

    })

    # --------------------------------------------------------
    # RETURN COMPLETE ZONE RESULT
    # --------------------------------------------------------

    return {

        "device_id":
            device_id,

        "zone_id":
            zone_id,

        "zone":
            get_zone_name(
                zone_id
            ),

        "floor":
            get_floor(
                zone_id
            ),

        "temperature":
            sensor.get(
                "temperature",
                0
            ),

        "humidity":
            sensor.get(
                "humidity",
                0
            ),

        "smoke":
            sensor.get(
                "smoke",
                0
            ),

        "occupancy":
            sensor.get(
                "occupancy",
                0
            ),

        # ----------------------------------------------------
        # DEEP LEARNING RESULTS
        # ----------------------------------------------------

        "risk_level":
            dl_result[
                "level"
            ],

        "risk_score":
            dl_result[
                "score"
            ],

        "confidence":
            dl_result[
                "confidence"
            ],

        "dl_confidence":
            dl_result[
                "confidence"
            ],

        "dl_prediction":
            dl_result[
                "level"
            ],

        "dl_probabilities":
            dl_result[
                "probabilities"
            ],

        "recommendation":
            dl_result[
                "recommendation"
            ],

        # ----------------------------------------------------
        # SENSOR METADATA
        # ----------------------------------------------------

        "simulation_mode":
            sensor.get(
                "simulation_mode"
            ),

        "timestamp":
            sensor.get(
                "timestamp"
            ),
    }


# ============================================================
# RANK ZONES
# ============================================================

def rank_zones(sensors):

    zone_results = []

    for sensor in sensors:

        try:

            result = calculate_zone_risk(
                sensor
            )

            zone_results.append(
                result
            )

        except Exception as error:

            print(
                "[ZONE DL ERROR] "
                f"{sensor.get('device_id')}: "
                f"{error}"
            )

    # --------------------------------------------------------
    # RISK ORDER
    # --------------------------------------------------------

    risk_order = {

        "CRITICAL": 4,

        "HIGH": 3,

        "MODERATE": 2,

        "LOW": 1,

        "SAFE": 0,

    }

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    zone_results.sort(

        key=lambda zone: (

            risk_order.get(

                str(
                    zone.get(
                        "risk_level",
                        "LOW"
                    )
                ).upper(),

                0

            ),

            float(
                zone.get(
                    "confidence",
                    0
                )
            ),

            float(
                zone.get(
                    "risk_score",
                    0
                )
            ),

        ),

        reverse=True

    )

    return zone_results


# ============================================================
# MOST DANGEROUS ZONE
# ============================================================

def get_most_dangerous_zone(
    sensors
):

    ranked_zones = rank_zones(
        sensors
    )

    if not ranked_zones:

        return None

    return ranked_zones[0]
