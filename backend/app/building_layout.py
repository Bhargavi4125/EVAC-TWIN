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
# FLOOR CORRIDOR SECTIONS
#
# The corridor is divided into three sections so that
# different hazards can affect different parts of the route.
#
# LEFT  -> rooms 101/201/301
# CENTER -> rooms 102/202/302 and 103/203/303
# RIGHT -> rooms 104/204/304
# ============================================================

CORRIDORS = {

    "CORRIDOR_1_LEFT": {
        "floor": 1,
        "adjacent_zones": ["101", "102"],
    },

    "CORRIDOR_1_CENTER": {
        "floor": 1,
        "adjacent_zones": ["102", "103"],
    },

    "CORRIDOR_1_RIGHT": {
        "floor": 1,
        "adjacent_zones": ["103", "104"],
    },

    "CORRIDOR_2_LEFT": {
        "floor": 2,
        "adjacent_zones": ["201", "202"],
    },

    "CORRIDOR_2_CENTER": {
        "floor": 2,
        "adjacent_zones": ["202", "203"],
    },

    "CORRIDOR_2_RIGHT": {
        "floor": 2,
        "adjacent_zones": ["203", "204"],
    },

    "CORRIDOR_3_LEFT": {
        "floor": 3,
        "adjacent_zones": ["301", "302"],
    },

    "CORRIDOR_3_CENTER": {
        "floor": 3,
        "adjacent_zones": ["302", "303"],
    },

    "CORRIDOR_3_RIGHT": {
        "floor": 3,
        "adjacent_zones": ["303", "304"],
    },
}


# ============================================================
# STAIRS
# ============================================================

STAIRS = {

    "STAIR_A": {
        "name": "Stair A",
        "exit": "EXIT A",

        "floor_connections": {
            1: "STAIR_A_1",
            2: "STAIR_A_2",
            3: "STAIR_A_3",
        },

        "connected_zones": {
            1: ["101", "102"],
            2: ["201", "202"],
            3: ["301", "302"],
        },
    },

    "STAIR_B": {
        "name": "Stair B",
        "exit": "EXIT B",

        "floor_connections": {
            1: "STAIR_B_1",
            2: "STAIR_B_2",
            3: "STAIR_B_3",
        },

        "connected_zones": {
            1: ["102", "103"],
            2: ["202", "203"],
            3: ["302", "303"],
        },
    },

    "STAIR_C": {
        "name": "Stair C",
        "exit": "EXIT C",

        "floor_connections": {
            1: "STAIR_C_1",
            2: "STAIR_C_2",
            3: "STAIR_C_3",
        },

        "connected_zones": {
            1: ["103", "104"],
            2: ["203", "204"],
            3: ["303", "304"],
        },
    },
}


# ============================================================
# EXITS
# ============================================================

EXITS = {

    "EXIT A": {
        "name": "Primary Emergency Exit",
        "stair": "STAIR_A",
        "base_distance": 1.0,
    },

    "EXIT B": {
        "name": "Secondary Emergency Exit",
        "stair": "STAIR_B",
        "base_distance": 1.2,
    },

    "EXIT C": {
        "name": "Rear Emergency Exit",
        "stair": "STAIR_C",
        "base_distance": 1.5,
    },
}


# ============================================================
# GRAPH EDGES
#
# Each edge represents a physically possible movement.
# ============================================================

EDGES = [

    # --------------------------------------------------------
    # FLOOR 1
    # --------------------------------------------------------

    ("101", "CORRIDOR_1_LEFT"),
    ("102", "CORRIDOR_1_LEFT"),

    ("102", "CORRIDOR_1_CENTER"),
    ("103", "CORRIDOR_1_CENTER"),

    ("103", "CORRIDOR_1_RIGHT"),
    ("104", "CORRIDOR_1_RIGHT"),

    ("CORRIDOR_1_LEFT", "CORRIDOR_1_CENTER"),
    ("CORRIDOR_1_CENTER", "CORRIDOR_1_RIGHT"),

    # Stair access
    ("CORRIDOR_1_LEFT", "STAIR_A_1"),
    ("CORRIDOR_1_CENTER", "STAIR_B_1"),
    ("CORRIDOR_1_RIGHT", "STAIR_C_1"),

    # --------------------------------------------------------
    # FLOOR 2
    # --------------------------------------------------------

    ("201", "CORRIDOR_2_LEFT"),
    ("202", "CORRIDOR_2_LEFT"),

    ("202", "CORRIDOR_2_CENTER"),
    ("203", "CORRIDOR_2_CENTER"),

    ("203", "CORRIDOR_2_RIGHT"),
    ("204", "CORRIDOR_2_RIGHT"),

    ("CORRIDOR_2_LEFT", "CORRIDOR_2_CENTER"),
    ("CORRIDOR_2_CENTER", "CORRIDOR_2_RIGHT"),

    ("CORRIDOR_2_LEFT", "STAIR_A_2"),
    ("CORRIDOR_2_CENTER", "STAIR_B_2"),
    ("CORRIDOR_2_RIGHT", "STAIR_C_2"),

    # --------------------------------------------------------
    # FLOOR 3
    # --------------------------------------------------------

    ("301", "CORRIDOR_3_LEFT"),
    ("302", "CORRIDOR_3_LEFT"),

    ("302", "CORRIDOR_3_CENTER"),
    ("303", "CORRIDOR_3_CENTER"),

    ("303", "CORRIDOR_3_RIGHT"),
    ("304", "CORRIDOR_3_RIGHT"),

    ("CORRIDOR_3_LEFT", "CORRIDOR_3_CENTER"),
    ("CORRIDOR_3_CENTER", "CORRIDOR_3_RIGHT"),

    ("CORRIDOR_3_LEFT", "STAIR_A_3"),
    ("CORRIDOR_3_CENTER", "STAIR_B_3"),
    ("CORRIDOR_3_RIGHT", "STAIR_C_3"),

    # --------------------------------------------------------
    # VERTICAL STAIR CONNECTIONS
    # --------------------------------------------------------

    ("STAIR_A_1", "STAIR_A_2"),
    ("STAIR_A_2", "STAIR_A_3"),

    ("STAIR_B_1", "STAIR_B_2"),
    ("STAIR_B_2", "STAIR_B_3"),

    ("STAIR_C_1", "STAIR_C_2"),
    ("STAIR_C_2", "STAIR_C_3"),
]


# ============================================================
# EXIT NODES
# ============================================================

EXIT_NODES = {

    "EXIT A": "EXIT_A_NODE",
    "EXIT B": "EXIT_B_NODE",
    "EXIT C": "EXIT_C_NODE",
}


EDGES += [

    ("STAIR_A_1", "EXIT_A_NODE"),
    ("STAIR_B_1", "EXIT_B_NODE"),
    ("STAIR_C_1", "EXIT_C_NODE"),
]


# ============================================================
# HELPERS
# ============================================================

def get_floor(zone_id):

    zone_id = str(zone_id)

    if zone_id in ROOMS:
        return ROOMS[zone_id]["floor"]

    return 0


def get_exit_stair(exit_name):

    exit_data = EXITS.get(exit_name)

    if not exit_data:
        return None

    return exit_data["stair"]


def get_stair_floor_node(stair_name, floor):

    stair = STAIRS.get(stair_name)

    if not stair:
        return None

    return stair["floor_connections"].get(floor)


def get_room_stairs(zone_id):

    zone_id = str(zone_id)

    floor = get_floor(zone_id)

    if floor == 0:
        return []

    result = []

    for stair_name, stair in STAIRS.items():

        zones = stair["connected_zones"].get(
            floor,
            []
        )

        if zone_id in zones:
            result.append(stair_name)

    return result