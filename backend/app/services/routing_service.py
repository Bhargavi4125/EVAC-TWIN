
from heapq import heappop, heappush
from math import inf
from time import perf_counter
from collections import deque

from app.building_layout import (
    BUILDING_ID,
    ROOMS,
    CORRIDORS,
    STAIRS,
    EXITS,
    EXIT_NODES,
    EDGES,
)


# =========================================================
# EVAC-TWIN - ROUTING CONFIGURATION
# =========================================================

NORMAL_EDGE_COST = 1.0
CORRIDOR_EDGE_COST = 1.0
STAIR_EDGE_COST = 2.0
EXIT_EDGE_COST = 1.0

RISK_PENALTY = {
    "LOW": 0.0,
    "MODERATE": 3.0,
    "HIGH": 12.0,
    "CRITICAL": inf,
    "UNKNOWN": 20.0,
}

CONTINUOUS_RISK_WEIGHT = 5.0
UNKNOWN_RISK_SCORE = 50.0

# Corridors and staircases currently have no individual
# sensor inputs in the building layout.
INFRASTRUCTURE_SENSORS_AVAILABLE = False

ROUTING_RISK_LEVELS = {
    "WARNING",
    "MODERATE",
    "HIGH",
    "CRITICAL",
    "UNKNOWN",
}


# =========================================================
# BUILDING GRAPH
# =========================================================

def build_graph():

    graph = {}

    for a, b in EDGES:
        graph.setdefault(a, set()).add(b)
        graph.setdefault(b, set()).add(a)

    return {
        node: sorted(neighbors)
        for node, neighbors in graph.items()
    }


BUILDING_GRAPH = build_graph()


# =========================================================
# NODE HELPERS
# =========================================================

def is_exit(node):
    return node in EXIT_NODES.values()


def is_room(node):
    return node in ROOMS


def is_corridor(node):
    return node in CORRIDORS


def is_stair(node):
    return str(node).startswith("STAIR_")


def get_node_floor(node):

    if node in ROOMS:
        return ROOMS[node].get("floor")

    if node in CORRIDORS:
        return CORRIDORS[node].get("floor")

    if is_stair(node):

        for stair in STAIRS.values():
            for floor, landing in stair.get(
                "floor_connections", {}
            ).items():

                if landing == node:
                    return floor

    for exit_name, exit_node in EXIT_NODES.items():

        if exit_node == node:
            return EXITS[exit_name].get("floor")

    return None


def node_risk(node, risk_map):

    if node in risk_map:

        risk = risk_map[node]

        return {
            "risk_score": float(
                risk.get("risk_score", UNKNOWN_RISK_SCORE)
            ),
            "risk_level": str(
                risk.get("risk_level", "UNKNOWN")
            ).upper(),
            "occupancy": int(
                risk.get("occupancy", 0) or 0
            ),
            "sensor_available": bool(
                risk.get("sensor_available", True)
            ),
        }

    if node in CORRIDORS or is_stair(node) or is_exit(node):

        return {
            "risk_score": UNKNOWN_RISK_SCORE,
            "risk_level": "UNKNOWN",
            "occupancy": 0,
            "sensor_available": False,
        }

    return {
        "risk_score": UNKNOWN_RISK_SCORE,
        "risk_level": "UNKNOWN",
        "occupancy": 0,
        "sensor_available": False,
    }


# =========================================================
# EDGE COST
# =========================================================

def edge_cost(current, neighbor, risk_map, start):

    if is_exit(current):
        return inf

    if is_exit(neighbor):
        return EXIT_EDGE_COST

    # Avoid entering another critical-risk room.
    if is_room(neighbor):

        risk = node_risk(neighbor, risk_map)

        level = risk["risk_level"]

        if level == "CRITICAL" and neighbor != start:
            return inf

        score = risk["risk_score"]

        level_penalty = RISK_PENALTY.get(
            level,
            RISK_PENALTY["UNKNOWN"]
        )

        continuous_penalty = (
            score / 100.0
        ) * CONTINUOUS_RISK_WEIGHT

        return (
            NORMAL_EDGE_COST
            + level_penalty
            + continuous_penalty
        )

    if is_stair(neighbor) or is_stair(current):
        return STAIR_EDGE_COST

    if is_corridor(neighbor) or is_corridor(current):
        return CORRIDOR_EDGE_COST

    return NORMAL_EDGE_COST


# =========================================================
# PATH RECONSTRUCTION
# =========================================================

def reconstruct_path(previous, start, target):

    if start == target:
        return [start]

    if target not in previous:
        return None

    path = [target]
    current = target

    while current != start:

        current = previous.get(current)

        if current is None:
            return None

        path.append(current)

    path.reverse()

    return path


# =========================================================
# BREADTH-FIRST SEARCH
# =========================================================

def bfs_path(start, target):

    if start not in BUILDING_GRAPH:
        return None

    if target not in BUILDING_GRAPH:
        return None

    queue = deque([start])
    visited = {start}
    previous = {}

    nodes_explored = 0

    while queue:

        current = queue.popleft()
        nodes_explored += 1

        if current == target:
            break

        for neighbor in BUILDING_GRAPH.get(current, []):

            if neighbor not in visited:

                visited.add(neighbor)
                previous[neighbor] = current
                queue.append(neighbor)

    if target not in visited:
        return None

    path = reconstruct_path(
        previous,
        start,
        target
    )

    return {
        "path": path,
        "edges": len(path) - 1,
        "nodes_explored": nodes_explored
    }


def test_bfs():

    result = bfs_path(
        "101",
        EXIT_NODES["EXIT 1"]
    )

    print("BFS TEST PATH:", result)


# =========================================================
# DEPTH-FIRST SEARCH
# =========================================================

def dfs_path(start, target):

    if start not in BUILDING_GRAPH:
        return None

    if target not in BUILDING_GRAPH:
        return None

    stack = [start]
    visited = {start}
    previous = {}

    nodes_explored = 0

    while stack:

        current = stack.pop()
        nodes_explored += 1

        if current == target:
            break

        for neighbor in BUILDING_GRAPH.get(current, []):

            if neighbor not in visited:

                visited.add(neighbor)
                previous[neighbor] = current
                stack.append(neighbor)

    if target not in visited:
        return None

    path = reconstruct_path(
        previous,
        start,
        target
    )

    return {
        "path": path,
        "edges": len(path) - 1,
        "nodes_explored": nodes_explored
    }


# =========================================================
# A-STAR SEARCH
# =========================================================

def a_star_path(start, target, risk_map):

    if start not in BUILDING_GRAPH:
        return None

    if target not in BUILDING_GRAPH:
        return None

    # Zero heuristic keeps the search optimal.
    # This makes it equivalent to Dijkstra here.
    def heuristic(node):
        return 0.0

    open_set = [
        (heuristic(start), 0.0, start)
    ]

    previous = {}
    g_score = {
        start: 0.0
    }

    visited = set()
    nodes_explored = 0

    while open_set:

        _, current_cost, current = heappop(open_set)

        if current in visited:
            continue

        if current_cost > g_score.get(current, inf):
            continue

        visited.add(current)
        nodes_explored += 1

        if current == target:
            break

        if is_exit(current):
            continue

        for neighbor in BUILDING_GRAPH.get(current, []):

            if neighbor in visited:
                continue

            cost = edge_cost(
                current,
                neighbor,
                risk_map,
                start
            )

            if cost == inf:
                continue

            new_score = current_cost + cost

            if new_score < g_score.get(neighbor, inf):

                g_score[neighbor] = new_score
                previous[neighbor] = current

                f_score = (
                    new_score + heuristic(neighbor)
                )

                heappush(
                    open_set,
                    (f_score, new_score, neighbor)
                )

    if target not in g_score:
        return None

    path = reconstruct_path(
        previous,
        start,
        target
    )

    if path is None:
        return None

    return {
        "path": path,
        "cost": round(g_score[target], 2),
        "edges": len(path) - 1,
        "nodes_explored": nodes_explored
    }


# =========================================================
# DIJKSTRA SHORTEST PATH
# =========================================================

def shortest_path(start, target, risk_map):

    if start not in BUILDING_GRAPH:
        return None

    if target not in BUILDING_GRAPH:
        return None

    distances = {
        node: inf
        for node in BUILDING_GRAPH
    }

    previous = {}

    distances[start] = 0.0

    queue = [(0.0, start)]

    visited = set()
    nodes_explored = 0

    while queue:

        distance, current = heappop(queue)

        if current in visited:
            continue

        if distance > distances[current]:
            continue

        visited.add(current)
        nodes_explored += 1

        if current == target:
            break

        if is_exit(current):
            continue

        for neighbor in BUILDING_GRAPH.get(current, []):

            if neighbor in visited:
                continue

            cost = edge_cost(
                current,
                neighbor,
                risk_map,
                start
            )

            if cost == inf:
                continue

            candidate = distance + cost

            if candidate < distances[neighbor]:

                distances[neighbor] = candidate
                previous[neighbor] = current

                heappush(
                    queue,
                    (candidate, neighbor)
                )

    if distances[target] == inf:
        return None

    path = reconstruct_path(
        previous,
        start,
        target
    )

    if path is None:
        return None

    return {
        "path": path,
        "cost": round(distances[target], 2),
        "edges": len(path) - 1,
        "nodes_explored": nodes_explored
    }


# =========================================================
# PATH RISK ANALYSIS
# =========================================================

def analyze_path(path, risk_map):

    critical = []
    high = []
    moderate = []
    unknown = []
    scores = []

    unmonitored_corridors = []
    unmonitored_stairs = []

    for node in path:

        if is_room(node):

            risk = node_risk(node, risk_map)

            level = risk["risk_level"]
            score = risk["risk_score"]

            scores.append(score)

            if level == "CRITICAL":
                critical.append(node)

            elif level == "HIGH":
                high.append(node)

            elif level in ("MODERATE", "WARNING"):
                moderate.append(node)

            elif level == "UNKNOWN":
                unknown.append(node)

        elif is_corridor(node):

            unmonitored_corridors.append(node)

        elif is_stair(node):

            unmonitored_stairs.append(node)

    average = (
        sum(scores) / len(scores)
        if scores else 0.0
    )

    maximum = (
        max(scores)
        if scores else 0.0
    )

    # A critical room cannot be used as an intermediate
    # node. The starting room is allowed for evacuation.
    blocking_critical = [
        node
        for index, node in enumerate(path)
        if index > 0
        and is_room(node)
        and node_risk(node, risk_map)["risk_level"] == "CRITICAL"
    ]

    if blocking_critical:

        status = "BLOCKED"
        reason = "A critical-risk room blocks this route."

    elif unknown:

        status = "CAUTION"
        reason = (
            "One or more rooms have unavailable "
            "sensor intelligence."
        )

    elif not INFRASTRUCTURE_SENSORS_AVAILABLE and (
        unmonitored_corridors or unmonitored_stairs
    ):

        status = "CAUTION"
        reason = (
            "Corridor or staircase sensor data is unavailable. "
            "This route requires on-site verification."
        )

    elif maximum >= 35:

        status = "CAUTION"
        reason = "The route contains elevated-risk conditions."

    else:

        status = "AVAILABLE"
        reason = "No significant monitored hazard was detected."

    return {
        "status": status,
        "reason": reason,
        "average_risk": round(average, 2),
        "maximum_risk": round(maximum, 2),
        "critical_zones": critical,
        "high_zones": high,
        "moderate_zones": moderate,
        "unknown_zones": unknown,
        "unmonitored_corridors": unmonitored_corridors,
        "unmonitored_stairs": unmonitored_stairs,
        "infrastructure_sensor_coverage": (
            INFRASTRUCTURE_SENSORS_AVAILABLE
        )
    }


# =========================================================
# ROUTE SCORE
# =========================================================

def calculate_route_score(analysis, physical_cost):

    average_risk = float(
        analysis.get("average_risk", 0.0)
    )

    maximum_risk = float(
        analysis.get("maximum_risk", 0.0)
    )

    physical_component = min(
        100.0,
        float(physical_cost) * 5.0
    )

    score = (
        average_risk * 0.60
        + maximum_risk * 0.25
        + physical_component * 0.15
    )

    # Unmonitored infrastructure increases uncertainty.
    if (
        analysis.get("unmonitored_corridors")
        or analysis.get("unmonitored_stairs")
    ):
        score += 10.0

    if analysis.get("unknown_zones"):
        score += 10.0

    return round(
        min(100.0, score),
        2
    )


# =========================================================
# ROUTE SELECTION
# =========================================================

def select_recommended_route(routes, zone_id):

    zone_floor = ROOMS[str(zone_id)]["floor"]

    available = [
        route for route in routes
        if route and route["status"] == "AVAILABLE"
    ]

    caution = [
        route for route in routes
        if route and route["status"] == "CAUTION"
    ]

    # Safety status takes priority.
    candidates = available or caution

    if not candidates:
        return None

    # Prefer a same-floor exit among routes with the
    # best available safety status.
    same_floor = [
        route for route in candidates
        if route.get("exit_floor") == zone_floor
    ]

    if same_floor:
        candidates = same_floor

    return min(
        candidates,
        key=lambda route: (
            route["risk_score"],
            route["distance"] if route["distance"] is not None else inf
        )
    )


# =========================================================
# CALCULATE ONE ZONE TO EXIT ROUTE
# =========================================================

def calculate_route(zone_id, exit_name, risk_map):

    zone_id = str(zone_id)

    exit_config = EXITS.get(exit_name)

    if zone_id not in ROOMS or not exit_config:
        return None

    target = EXIT_NODES.get(exit_name)

    if not target:
        return None

    zone_floor = ROOMS[zone_id]["floor"]
    exit_floor = exit_config["floor"]

    base = {
        "exit": exit_name,
        "name": exit_config["name"],
        "exit_floor": exit_floor,
        "same_floor": zone_floor == exit_floor,
        "status": "BLOCKED",
        "risk_score": 100.0,
        "reason": "No route is available.",
        "path": [],
        "distance": None,
        "cost": None,
        "edges": None,
        "average_risk": 100.0,
        "maximum_risk": 100.0,
        "critical_zones": [],
        "high_zones": [],
        "moderate_zones": [],
        "unknown_zones": [],
        "unmonitored_corridors": [],
        "unmonitored_stairs": [],
        "infrastructure_sensor_coverage": (
            INFRASTRUCTURE_SENSORS_AVAILABLE
        )
    }

    # CHANGE 1:
    # Do not recommend evacuation to a higher floor.
    if exit_floor > zone_floor:
        base["reason"] = (
            "Upward evacuation is not permitted. "
            "Use a same-floor or lower-floor emergency exit."
        )
        return base

    result = shortest_path(
        zone_id,
        target,
        risk_map
    )

    if result is None:
        return base

    analysis = analyze_path(
        result["path"],
        risk_map
    )

    final_score = calculate_route_score(
        analysis,
        result["cost"]
    )

    return {
        **base,
        **analysis,
        "status": analysis["status"],
        "risk_score": final_score,
        "path": result["path"],
        "distance": result["edges"],
        "cost": result["cost"],
        "edges": result["edges"]
    }


# =========================================================
# BUILD RISK MAP FROM SENSOR DATA
# =========================================================

def build_risk_map(sensors):

    risk_map = {}

    for sensor in sensors:

        zone_id = str(
            sensor.get("zone_id", "")
        )

        if zone_id not in ROOMS:
            continue

        raw_level = sensor.get("risk_level")

        risk_level = (
            str(raw_level).upper()
            if raw_level is not None
            else "UNKNOWN"
        )

        if risk_level == "WARNING":
            risk_level = "MODERATE"

        if risk_level not in RISK_PENALTY:
            risk_level = "UNKNOWN"

        raw_score = sensor.get("risk_score")

        try:

            risk_score = float(raw_score)

        except (TypeError, ValueError):

            risk_score = (
                UNKNOWN_RISK_SCORE
                if risk_level == "UNKNOWN"
                else 0.0
            )

        try:

            occupancy = int(
                sensor.get("occupancy", 0) or 0
            )

        except (TypeError, ValueError):

            occupancy = 0

        # Latest sensor record for a zone overwrites
        # the earlier record.
        risk_map[zone_id] = {
            "risk_score": max(
                0.0,
                min(100.0, risk_score)
            ),
            "risk_level": risk_level,
            "occupancy": max(0, occupancy),
            "sensor_available": True
        }

    return risk_map


# =========================================================
# CALCULATE ALL EXIT OPTIONS FOR ONE ZONE
# =========================================================

def calculate_zone_routes(zone_id, risk_map):

    return [
        calculate_route(
            zone_id,
            exit_name,
            risk_map
        )
        for exit_name in EXITS
    ]


# =========================================================
# PATH RISK SUMMARY
# =========================================================

def calculate_path_risk(path, risk_map):

    if not path:
        return None

    total_risk = 0
    high_risk_rooms = 0
    critical_rooms = 0
    unknown_rooms = 0

    for node in path:

        if not is_room(node):
            continue

        risk = node_risk(node, risk_map)

        total_risk += risk["risk_score"]

        level = risk["risk_level"]

        if level == "HIGH":
            high_risk_rooms += 1

        elif level == "CRITICAL":
            critical_rooms += 1

        elif level == "UNKNOWN":
            unknown_rooms += 1

    return {
        "total_risk": round(total_risk, 2),
        "high_risk_rooms": high_risk_rooms,
        "critical_rooms": critical_rooms,
        "unknown_rooms": unknown_rooms
    }


# =========================================================
# COMPARE ROUTING ALGORITHMS
# =========================================================

def compare_algorithms(zone_id, risk_map):

    results = []

    for exit_name, target in EXIT_NODES.items():

        start_time = perf_counter()
        bfs = bfs_path(zone_id, target)
        bfs_time = (perf_counter() - start_time) * 1000

        start_time = perf_counter()
        dfs = dfs_path(zone_id, target)
        dfs_time = (perf_counter() - start_time) * 1000

        start_time = perf_counter()
        dijkstra = shortest_path(
            zone_id,
            target,
            risk_map
        )
        dijkstra_time = (perf_counter() - start_time) * 1000

        start_time = perf_counter()
        astar = a_star_path(
            zone_id,
            target,
            risk_map
        )
        astar_time = (perf_counter() - start_time) * 1000

        results.append({

            "exit": target,

            "bfs": {
                "path": bfs["path"] if bfs else None,
                "edges": bfs["edges"] if bfs else None,
                "nodes_explored": (
                    bfs["nodes_explored"] if bfs else None
                ),
                "execution_time_ms": round(bfs_time, 4),
                "risk_exposure": calculate_path_risk(
                    bfs["path"] if bfs else None,
                    risk_map
                )
            },

            "dfs": {
                "path": dfs["path"] if dfs else None,
                "edges": dfs["edges"] if dfs else None,
                "nodes_explored": (
                    dfs["nodes_explored"] if dfs else None
                ),
                "execution_time_ms": round(dfs_time, 4),
                "risk_exposure": calculate_path_risk(
                    dfs["path"] if dfs else None,
                    risk_map
                )
            },

            "dijkstra": {
                "path": dijkstra["path"] if dijkstra else None,
                "cost": dijkstra["cost"] if dijkstra else None,
                "edges": dijkstra["edges"] if dijkstra else None,
                "nodes_explored": (
                    dijkstra["nodes_explored"]
                    if dijkstra else None
                ),
                "execution_time_ms": round(dijkstra_time, 4),
                "risk_exposure": calculate_path_risk(
                    dijkstra["path"] if dijkstra else None,
                    risk_map
                )
            },

            "a_star": {
                "path": astar["path"] if astar else None,
                "cost": astar["cost"] if astar else None,
                "edges": astar["edges"] if astar else None,
                "nodes_explored": (
                    astar["nodes_explored"]
                    if astar else None
                ),
                "execution_time_ms": round(astar_time, 4),
                "risk_exposure": calculate_path_risk(
                    astar["path"] if astar else None,
                    risk_map
                )
            }
        })

    return results


# =========================================================
# ROUTE WEIGHT
# =========================================================

def _route_weight(route, risk_map, zone_id):

    occupancy = max(
        0,
        int(
            risk_map.get(zone_id, {}).get(
                "occupancy", 0
            )
        )
    )

    return (
        route["risk_score"],
        -occupancy
    )


# =========================================================
# CALCULATE COMPLETE BUILDING EVACUATION
# =========================================================

def calculate_all_routes(sensors, selected_zone=None):

    risk_map = build_risk_map(sensors)

    zones = []

    # =====================================================
    # DYNAMIC ROUTES FOR EVERY MONITORED ROOM
    # =====================================================

    for zone_id, zone_risk in risk_map.items():

        routes = calculate_zone_routes(
            zone_id,
            risk_map
        )

        recommended = select_recommended_route(
            routes,
            zone_id
        )

        # CHANGE 2:
        # Include only physically reachable routes that
        # are AVAILABLE or CAUTION.
        alternatives = sorted(
            [
                route
                for route in routes
                if route
                and route["status"] in ("AVAILABLE", "CAUTION")
                and (
                    recommended is None
                    or route["exit"] != recommended["exit"]
                )
            ],
            key=lambda route: (
                route["risk_score"],
                route["distance"]
                if route["distance"] is not None
                else inf
            )
        )

        zones.append({

            "zone_id": zone_id,

            "floor": ROOMS[zone_id]["floor"],

            "risk_level": zone_risk["risk_level"],

            "risk_score": zone_risk["risk_score"],

            "occupancy": zone_risk["occupancy"],

            "recommended_exit": recommended,

            "alternative_exits": alternatives,

            "all_routes": routes,

            "route_status": (
                recommended["status"]
                if recommended
                else "NO SAFE ROUTE AVAILABLE"
            )
        })

    selected_zone_data = next(
        (
            zone for zone in zones
            if zone["zone_id"] == str(selected_zone)
        ),
        None
    )

    # =====================================================
    # BUILDING-LEVEL EXIT ANALYSIS
    # =====================================================

    exits = []

    for exit_name, exit_config in EXITS.items():

        route_records = []

        for zone_id in risk_map:

            route = calculate_route(
                zone_id,
                exit_name,
                risk_map
            )

            if route is not None:
                route_records.append((zone_id, route))

        usable = [
            (zone_id, route)
            for zone_id, route in route_records
            if route["status"] in ("AVAILABLE", "CAUTION")
        ]

        connected = sorted(
            [zone_id for zone_id, _ in usable],
            key=int
        )

        if usable:

            total_people = sum(
                risk_map[zone_id]["occupancy"]
                for zone_id, _ in usable
            )

            if total_people > 0:

                weighted_score = (
                    sum(
                        route["risk_score"]
                        * risk_map[zone_id]["occupancy"]
                        for zone_id, route in usable
                    )
                    / total_people
                )

            else:

                weighted_score = (
                    sum(
                        route["risk_score"]
                        for _, route in usable
                    )
                    / len(usable)
                )

            best_zone, best_route = min(
                usable,
                key=lambda item: item[1]["risk_score"]
            )

            status = (
                "AVAILABLE"
                if any(
                    route["status"] == "AVAILABLE"
                    for _, route in usable
                )
                else "CAUTION"
            )

            reason = (
                "At least one monitored room has a route "
                "to this exit. Check route-specific warnings."
            )

            exits.append({

                "exit": exit_name,

                "name": exit_config["name"],

                "floor": exit_config["floor"],

                "risk_score": round(
                    min(100.0, weighted_score),
                    2
                ),

                "status": status,

                "reason": reason,

                "connected_zones": connected,

                "total_people": total_people,

                "best_path": best_route["path"],

                "best_zone": best_zone,

                "distance": best_route["distance"]
            })

        else:

            exits.append({

                "exit": exit_name,

                "name": exit_config["name"],

                "floor": exit_config["floor"],

                "risk_score": 100.0,

                "status": "BLOCKED",

                "reason": "No reachable route was found.",

                "connected_zones": [],

                "total_people": 0,

                "best_path": [],

                "best_zone": None,

                "distance": None
            })

    # =====================================================
    # BUILDING-LEVEL RECOMMENDED EXIT
    # =====================================================

    available_exits = [
        exit_data for exit_data in exits
        if exit_data["status"] == "AVAILABLE"
    ]

    caution_exits = [
        exit_data for exit_data in exits
        if exit_data["status"] == "CAUTION"
    ]

    candidates = available_exits or caution_exits

    recommended = (
        min(
            candidates,
            key=lambda exit_data: (
                exit_data["risk_score"],
                -len(exit_data["connected_zones"])
            )
        )
        if candidates
        else None
    )

    # =====================================================
    # BUILDING-LEVEL ALTERNATIVE EXITS
    # =====================================================

    # CHANGE 3:
    # Keep only usable building-level exits.
    alternatives = sorted(
        [
            exit_data
            for exit_data in exits
            if (
                exit_data["status"] in ("AVAILABLE", "CAUTION")
                and (
                    recommended is None
                    or exit_data["exit"] != recommended["exit"]
                )
            )
        ],
        key=lambda exit_data: exit_data["risk_score"]
    )

    # =====================================================
    # BUILDING ROUTE STATUS
    # =====================================================

    if available_exits:
        route_status = "AVAILABLE ROUTE"

    elif caution_exits:
        route_status = "CAUTION - VERIFY ROUTE"

    else:
        route_status = "NO SAFE ROUTE AVAILABLE"

    # =====================================================
    # BUILDING CONDITION
    # =====================================================

    if any(
        risk["risk_level"] == "CRITICAL"
        for risk in risk_map.values()
    ):
        building_condition = "CRITICAL"

    elif any(
        risk["risk_level"] == "HIGH"
        for risk in risk_map.values()
    ):
        building_condition = "HIGH RISK"

    elif any(
        risk["risk_level"] in ("MODERATE", "WARNING")
        for risk in risk_map.values()
    ):
        building_condition = "MODERATE RISK"

    else:
        building_condition = "NORMAL"

    # =====================================================
    # ZONE STATISTICS
    # =====================================================

    monitored_zones = len(risk_map)

    critical_zones = sum(
        1 for risk in risk_map.values()
        if risk["risk_level"] == "CRITICAL"
    )

    high_risk_zones = sum(
        1 for risk in risk_map.values()
        if risk["risk_level"] == "HIGH"
    )

    moderate_risk_zones = sum(
        1 for risk in risk_map.values()
        if risk["risk_level"] in ("MODERATE", "WARNING")
    )

    unknown_zones = sum(
        1 for risk in risk_map.values()
        if risk["risk_level"] == "UNKNOWN"
    )

    # =====================================================
    # TOTAL OCCUPANCY
    # =====================================================

    total_occupancy = sum(
        risk["occupancy"]
        for risk in risk_map.values()
    )

    # =====================================================
    # FINAL RESPONSE
    # =====================================================

    return {

        "building_id": BUILDING_ID,

        "zones": zones,

        "exits": exits,

        "recommended_exit": recommended,

        "selected_zone": selected_zone,

        "selected_zone_recommendation": (
            selected_zone_data["recommended_exit"]
            if selected_zone_data
            else None
        ),

        "selected_zone_routes": (
            selected_zone_data["all_routes"]
            if selected_zone_data
            else []
        ),

        "alternative_exits": alternatives,

        "route_status": route_status,

        "building_condition": building_condition,

        "total_zones": monitored_zones,

        "building_zones": len(ROOMS),

        "monitored_zones": monitored_zones,

        "unknown_zones": unknown_zones,

        "critical_zones": critical_zones,

        "high_risk_zones": high_risk_zones,

        "moderate_risk_zones": moderate_risk_zones,

        "total_occupancy": total_occupancy,

        "infrastructure_sensor_coverage": (
            INFRASTRUCTURE_SENSORS_AVAILABLE
        ),

        "building_graph": BUILDING_GRAPH
    }
