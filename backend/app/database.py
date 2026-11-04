from pymongo import MongoClient, ASCENDING, DESCENDING
import os

from dotenv import load_dotenv


# ============================================================
# EVAC-TWIN — DATABASE CONFIGURATION
# ============================================================

load_dotenv()


MONGO_URL = os.getenv(
    "MONGO_URL",
    "mongodb://127.0.0.1:27017"
)

DATABASE_NAME = os.getenv(
    "MONGO_DATABASE",
    "evac_twin"
)


# ============================================================
# MONGODB CONNECTION
# ============================================================

client = MongoClient(
    MONGO_URL,
    serverSelectionTimeoutMS=5000
)

db = client[DATABASE_NAME]


# ============================================================
# COLLECTIONS
# ============================================================

sensors_collection = db["sensors"]
events_collection = db["events"]
buildings_collection = db["buildings"]


# ============================================================
# INDEXES
# ============================================================

def initialize_indexes():

    # --------------------------------------------------------
    # SENSOR HISTORY
    # --------------------------------------------------------

    sensors_collection.create_index(
        [
            ("device_id", ASCENDING),
            ("timestamp", DESCENDING)
        ],
        name="sensor_history"
    )

    sensors_collection.create_index(
        [
            ("building_id", ASCENDING),
            ("zone_id", ASCENDING),
            ("timestamp", DESCENDING)
        ],
        name="zone_sensor_history"
    )

    # --------------------------------------------------------
    # EVENTS
    # --------------------------------------------------------

    events_collection.create_index(
        [
            ("building_id", ASCENDING),
            ("zone_id", ASCENDING),
            ("timestamp", DESCENDING)
        ],
        name="event_history"
    )

    events_collection.create_index(
        [
            ("risk_level", ASCENDING),
            ("timestamp", DESCENDING)
        ],
        name="risk_event_history"
    )

    # --------------------------------------------------------
    # BUILDINGS
    # --------------------------------------------------------

    buildings_collection.create_index(
        [
            ("building_id", ASCENDING)
        ],
        unique=True,
        name="building_id_unique"
    )


# ============================================================
# DATABASE HEALTH CHECK
# ============================================================

def check_database_connection():

    try:

        client.admin.command(
            "ping"
        )

        return True

    except Exception as error:

        print(
            f"MongoDB connection failed: {error}"
        )

        return False


# ============================================================
# INITIALIZE DATABASE
# ============================================================

initialize_indexes()