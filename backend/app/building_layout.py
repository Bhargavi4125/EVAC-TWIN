
# ============================================================
# EVAC-TWIN — BUILDING ALPHA TOPOLOGY
# ============================================================

BUILDING_ID = "building-alpha"


# ============================================================
# ROOMS
# ============================================================

ROOMS = {
    "101": {"floor": 1, "name": "Room 101"},
    "102": {"floor": 1, "name": "Room 102"},
    "103": {"floor": 1, "name": "Room 103"},
    "104": {"floor": 1, "name": "Room 104"},

    "201": {"floor": 2, "name": "Room 201"},
    "202": {"floor": 2, "name": "Room 202"},
    "203": {"floor": 2, "name": "Room 203"},
    "204": {"floor": 2, "name": "Room 204"},

    "301": {"floor": 3, "name": "Room 301"},
    "302": {"floor": 3, "name": "Room 302"},
    "303": {"floor": 3, "name": "Room 303"},
    "304": {"floor": 3, "name": "Room 304"},
}


# ============================================================
# ONE STRAIGHT CORRIDOR PER FLOOR
# ============================================================

CORRIDORS = {
    "CORRIDOR_1": {
        "floor": 1,
        "adjacent_zones": ["101", "102", "103", "104"],
    },

    "CORRIDOR_2": {
        "floor": 2,
        "adjacent_zones": ["201", "202", "203", "204"],
    },

    "CORRIDOR_3": {
        "floor": 3,
        "adjacent_zones": ["301", "302", "303", "304"],
    },
}


# ============================================================
# ONE CONTINUOUS STAIRCASE — LEFT SIDE
# ============================================================

STAIRS = {
    "STAIR_MAIN": {
        "name": "Main Staircase",
        "floor_connections": {
            1: "STAIR_MAIN_1",
            2: "STAIR_MAIN_2",
            3: "STAIR_MAIN_3",
        },

        "connected_zones": {
            1: ["101", "102", "103", "104"],
            2: ["201", "202", "203", "204"],
            3: ["301", "302", "303", "304"],
        },
    },
}


# ============================================================
# THREE SEPARATE EMERGENCY EXITS — RIGHT SIDE
# One exit on each floor
# ============================================================

EXITS = {
    "EXIT 1": {
        "name": "Floor 1 Emergency Exit",
        "floor": 1,
        "node": "EXIT_1_NODE",
        "base_distance": 1.0,
    },

    "EXIT 2": {
        "name": "Floor 2 Emergency Exit",
        "floor": 2,
        "node": "EXIT_2_NODE",
        "base_distance": 1.0,
    },

    "EXIT 3": {
        "name": "Floor 3 Emergency Exit",
        "floor": 3,
        "node": "EXIT_3_NODE",
        "base_distance": 1.0,
    },
}


# ============================================================
# GRAPH EDGES
# ============================================================

EDGES = [

    # --------------------------------------------------------
    # FLOOR 1
    # --------------------------------------------------------

    ("101", "CORRIDOR_1"),
    ("102", "CORRIDOR_1"),
    ("103", "CORRIDOR_1"),
    ("104", "CORRIDOR_1"),

    ("CORRIDOR_1", "STAIR_MAIN_1"),
    ("CORRIDOR_1", "EXIT_1_NODE"),

    # --------------------------------------------------------
    # FLOOR 2
    # --------------------------------------------------------

    ("201", "CORRIDOR_2"),
    ("202", "CORRIDOR_2"),
    ("203", "CORRIDOR_2"),
    ("204", "CORRIDOR_2"),

    ("CORRIDOR_2", "STAIR_MAIN_2"),
    ("CORRIDOR_2", "EXIT_2_NODE"),

    # --------------------------------------------------------
    # FLOOR 3
    # --------------------------------------------------------

    ("301", "CORRIDOR_3"),
    ("302", "CORRIDOR_3"),
    ("303", "CORRIDOR_3"),
    ("304", "CORRIDOR_3"),

    ("CORRIDOR_3", "STAIR_MAIN_3"),
    ("CORRIDOR_3", "EXIT_3_NODE"),

    # --------------------------------------------------------
    # CONTINUOUS STAIRCASE CONNECTION
    # --------------------------------------------------------

    ("STAIR_MAIN_1", "STAIR_MAIN_2"),
    ("STAIR_MAIN_2", "STAIR_MAIN_3"),
]


# ============================================================
# EXIT NODES
# ============================================================

EXIT_NODES = {
    "EXIT 1": "EXIT_1_NODE",
    "EXIT 2": "EXIT_2_NODE",
    "EXIT 3": "EXIT_3_NODE",
}


# ============================================================
# HELPERS
# ============================================================

def get_floor(zone_id):

    zone_id = str(zone_id)

    if zone_id in ROOMS:
        return ROOMS[zone_id]["floor"]

    for corridor_name, corridor in CORRIDORS.items():
        if zone_id == corridor_name:
            return corridor["floor"]

    for stair in STAIRS.values():
        for floor, node in stair["floor_connections"].items():
            if zone_id == node:
                return floor

    for exit_data in EXITS.values():
        if zone_id == exit_data["node"]:
            return exit_data["floor"]

    return 0


def get_exit_stair(exit_name):
    """
    Emergency exits are directly connected to corridors.
    They are separate from the staircase.
    """
    return None


def get_stair_floor_node(stair_name, floor):

    stair = STAIRS.get(stair_name)

    if not stair:
        return None

    return stair["floor_connections"].get(floor)


def get_room_stairs(zone_id):

    zone_id = str(zone_id)

    floor = get_floor(zone_id)

    if floor == 0 or zone_id not in ROOMS:
        return []

    return ["STAIR_MAIN"]
