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
# EVAC-TWIN — ROUTING CONFIGURATION
# =========================================================

NORMAL_EDGE_COST = 1.0
CORRIDOR_EDGE_COST = 1.0
STAIR_EDGE_COST = 2.0
EXIT_EDGE_COST = 1.0


# Risk penalties applied when ENTERING a room.
#
# CRITICAL is handled separately because another critical
# room must never be entered during evacuation.
RISK_PENALTY = {
    "LOW": 0.0,
    "MODERATE": 3.0,
    "HIGH": 12.0,
    "CRITICAL": inf,
    "UNKNOWN": 20.0,
}


# Additional continuous risk contribution.
# This allows two HIGH zones with different risk scores
# to have different routing costs.
CONTINUOUS_RISK_WEIGHT = 5.0


# Missing sensor data is not considered safe.
# It remains traversable so one missing sensor does not
# completely destroy the evacuation network, but the route
# receives a caution penalty.
UNKNOWN_RISK_SCORE = 50.0


# =========================================================
# BUILDING GRAPH
# =========================================================

def build_graph():
    """
    Build an undirected graph from the physical building edges.

    The graph contains:
        - rooms
        - corridor sections
        - stair nodes
        - exit nodes
    """

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


def node_risk(node, risk_map):
    """
    Return normalized risk information for a node.

    Room nodes use live sensor intelligence.

    Non-room topology nodes such as corridors and stairs do
    not currently have individual sensors, so they are treated
    as LOW physical-topology nodes.

    Missing room sensor data is explicitly represented as
    UNKNOWN rather than silently becoming LOW.
    """

    if node in risk_map:
        risk = risk_map[node]

        return {
            "risk_score": float(
                risk.get("risk_score", 0.0)
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

    # Topology nodes without individual sensors.
    if node in CORRIDORS or is_stair(node) or is_exit(node):
        return {
            "risk_score": 0.0,
            "risk_level": "LOW",
            "occupancy": 0,
            "sensor_available": False,
        }

    # A room without current sensor information.
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
    """
    Calculate movement cost from current -> neighbor.

    Priority:

        EXIT
        ↓
        STAIR
        ↓
        CORRIDOR
        ↓
        ROOM
        ↓
        NORMAL

    Risk is applied to room entry.

    Rules:
        - The starting critical room is allowed.
        - Another critical room cannot be entered.
        - HIGH/MODERATE rooms remain traversable.
        - UNKNOWN rooms remain traversable with a caution penalty.
        - Corridors have normal movement cost.
        - Stairs have higher physical movement cost.
        - Exit nodes are terminal.
    """

    # =====================================================
    # EXIT
    # =====================================================

    if is_exit(neighbor):
        return EXIT_EDGE_COST

    # Once an exit has been reached, it is terminal.
    if is_exit(current):
        return inf

    # =====================================================
    # STAIR
    # =====================================================

    if is_stair(neighbor) or is_stair(current):
        return STAIR_EDGE_COST

    # =====================================================
    # CORRIDOR
    # =====================================================

    if is_corridor(neighbor) or is_corridor(current):
        return CORRIDOR_EDGE_COST

    # =====================================================
    # ROOM RISK
    # =====================================================

    if is_room(neighbor):

        risk = node_risk(
            neighbor,
            risk_map,
        )

        level = str(
            risk.get("risk_level", "UNKNOWN")
        ).upper()

        # Critical zones cannot be entered.
        # The starting critical zone is allowed because
        # occupants are already inside it.
        if level == "CRITICAL" and neighbor != start:
            return inf

        score = float(
            risk.get(
                "risk_score",
                UNKNOWN_RISK_SCORE,
            )
        )

        level_penalty = RISK_PENALTY.get(
            level,
            RISK_PENALTY["UNKNOWN"],
        )

        continuous_penalty = (
            score / 100.0
        ) * CONTINUOUS_RISK_WEIGHT

        return (
            NORMAL_EDGE_COST
            + level_penalty
            + continuous_penalty
        )

    return NORMAL_EDGE_COST



# =========================================================
# SHORTEST SAFE PHYSICAL PATH
# =========================================================


def bfs_path(start, target):
    queue = deque([start])
    visited = {start}
    nodes_explored = 0
    previous = {}

    while queue:
        current = queue.popleft()
        nodes_explored += 1

        if current == target:
            break

        for neighbor in BUILDING_GRAPH[current]:
            if neighbor not in visited:
                visited.add(neighbor)
                previous[neighbor] = current
                queue.append(neighbor)

    if target not in visited:
        return None

    path = [target]
    current = target

    while current != start:
        current = previous[current]
        path.append(current)

    path.reverse()

    return {
    "path": path,
    "edges": len(path) - 1,
    "nodes_explored": nodes_explored
}
def test_bfs():
    result = bfs_path("101", "EXIT_A")
    print("BFS TEST PATH:", result)

def dfs_path(start, target):
    stack = [start]
    visited = {start}
    nodes_explored = 0
    previous = {}

    while stack:
        current = stack.pop()
        nodes_explored += 1

        if current == target:
            break

        for neighbor in BUILDING_GRAPH[current]:
            if neighbor not in visited:
                visited.add(neighbor)
                previous[neighbor] = current
                stack.append(neighbor)

    if target not in visited:
        return None

    path = [target]
    current = target

    while current != start:
        current = previous[current]
        path.append(current)

    path.reverse()

    return {
    "path": path,
    "edges": len(path) - 1,
    "nodes_explored": nodes_explored
}

def a_star_path(start, target, risk_map):
    distances = {target: 0}
    queue = [target]

    while queue:
        current = queue.pop(0)

        for neighbor in BUILDING_GRAPH.get(current, []):
            if neighbor not in distances:
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)

    def heuristic(node):
        return distances.get(node, 0)

    open_set = [(heuristic(start), 0, start)]
    previous = {}
    g_score = {start: 0}
    visited = set()
    nodes_explored = 0

    while open_set:
        _, current_cost, current = heappop(open_set)

        if current in visited:
            continue

        visited.add(current)
        nodes_explored += 1

        if current == target:
            break

        if is_exit(current):
            continue

        for neighbor in BUILDING_GRAPH[current]:
            if neighbor in visited:
                continue

            cost = edge_cost(current, neighbor, risk_map, start)

            if cost == inf:
                continue

            new_score = current_cost + cost

            if new_score < g_score.get(neighbor, inf):
                g_score[neighbor] = new_score
                previous[neighbor] = current

                f_score = new_score + heuristic(neighbor)

                heappush(
                    open_set,
                    (f_score, new_score, neighbor)
                )

    if target not in previous and start != target:
        return None

    path = [target]
    current = target

    while current != start:
        current = previous[current]
        path.append(current)

    path.reverse()

    return {
        "path": path,
        "cost": round(g_score[target], 2),
        "edges": len(path) - 1,
        "nodes_explored": nodes_explored
    }
def shortest_path(start, target, risk_map):
    """
    Dijkstra shortest-path search using the physical
    Building Alpha topology and dynamic room risk.

    A critical starting room is allowed because people
    are already inside that room and must escape.

    Other critical rooms are blocked from entry.
    """

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

    queue = [
        (0.0, start)
    ]

    visited = set()
    nodes_explored = 0

    while queue:

        distance, current = heappop(queue)

        if current in visited or distance > distances[current]:
           continue


        visited.add(current)
        nodes_explored += 1

        if current == target:
            break

        if is_exit(current):
            continue

        for neighbor in BUILDING_GRAPH[current]:

            if neighbor in visited:
                continue

            cost = edge_cost(
                current,
                neighbor,
                risk_map,
                start,
            )

            if cost == inf:
                continue

            candidate = distance + cost

            if candidate < distances[neighbor]:

                distances[neighbor] = candidate

                previous[neighbor] = current

                heappush(
                    queue,
                    (
                        candidate,
                        neighbor,
                    ),
                )

    if distances[target] == inf:
        return None

    # =====================================================
    # RECONSTRUCT PATH
    # =====================================================

    path = [target]
    current = target

    while current != start:

        if current not in previous:
            return None

        current = previous[current]
        path.append(current)

    path.reverse()

    return {
    "path": path,
    "cost": round(distances[target], 2),
    "edges": len(path) - 1,
    "nodes_explored": nodes_explored,
}

# =========================================================
# PATH RISK ANALYSIS
# =========================================================

def analyze_path(path, risk_map):
    """
    Analyze every room appearing in an evacuation path.

    The starting room is included in the risk statistics.

    A critical starting room does NOT block the route.

    A critical room encountered after the starting room
    makes the route BLOCKED.

    UNKNOWN room sensor data produces CAUTION rather than
    being treated as safe.
    """

    critical = []
    high = []
    moderate = []
    unknown = []
    scores = []

    # =====================================================
    # ANALYZE ROOMS
    # =====================================================

    for node in path:

        if node not in ROOMS:
            continue

        risk = node_risk(
            node,
            risk_map,
        )

        level = str(
            risk.get(
                "risk_level",
                "UNKNOWN",
            )
        ).upper()

        score = float(
            risk.get(
                "risk_score",
                UNKNOWN_RISK_SCORE,
            )
        )

        scores.append(score)

        if level == "CRITICAL":
            critical.append(node)

        elif level == "HIGH":
            high.append(node)

        elif level == "MODERATE":
            moderate.append(node)

        elif level == "UNKNOWN":
            unknown.append(node)

    # =====================================================
    # RISK STATISTICS
    # =====================================================

    average = (
        sum(scores) / len(scores)
        if scores
        else 0.0
    )

    maximum = (
        max(scores)
        if scores
        else 0.0
    )

    # =====================================================
    # CRITICAL ZONES AFTER START
    # =====================================================

    blocking_critical = []

    for index, node in enumerate(path):

        # The first node is always the evacuation origin.
        if index == 0:
            continue

        if node not in ROOMS:
            continue

        risk = node_risk(
            node,
            risk_map,
        )

        level = str(
            risk.get(
                "risk_level",
                "UNKNOWN",
            )
        ).upper()

        if level == "CRITICAL":
            blocking_critical.append(node)

    # =====================================================
    # ROUTE STATUS
    # =====================================================

    if blocking_critical:

        status = "BLOCKED"

        reason = (
            "A critical-risk zone blocks this path."
        )

    elif unknown:

        status = "CAUTION"

        reason = (
            "The path contains a zone with unavailable "
            "sensor intelligence."
        )

    elif maximum >= 60:

        status = "CAUTION"

        reason = (
            "The evacuation starts in or passes through "
            "a critical-risk condition."
        )

    elif maximum >= 35:

        status = "CAUTION"

        reason = (
            "The path contains elevated-risk conditions."
        )

    else:

        status = "AVAILABLE"

        reason = (
            "Path is clear of significant hazards."
        )

    return {
        "status": status,
        "reason": reason,
        "average_risk": round(
            average,
            2,
        ),
        "maximum_risk": round(
            maximum,
            2,
        ),
        "critical_zones": critical,
        "high_zones": high,
        "moderate_zones": moderate,
        "unknown_zones": unknown,
    }


# =========================================================
# ROUTE SCORE
# =========================================================

def calculate_route_score(
    analysis,
    physical_cost,
):
    """
    Convert route characteristics into one comparable
    0-100 evacuation risk score.

    Components:

        Average room risk  -> 60%
        Maximum room risk  -> 25%
        Physical cost      -> 15%

    The score is used for comparing available exits.
    """

    average_risk = float(
        analysis.get(
            "average_risk",
            0.0,
        )
    )

    maximum_risk = float(
        analysis.get(
            "maximum_risk",
            0.0,
        )
    )

    # Keep the physical component bounded so a long but
    # otherwise safe route does not dominate the risk.
    physical_component = min(
        100.0,
        float(physical_cost) * 5.0,
    )

    score = (
        average_risk * 0.60
        + maximum_risk * 0.25
        + physical_component * 0.15
    )

    return round(
        min(
            100.0,
            score,
        ),
        2,
    )


# =========================================================
# CALCULATE ONE ZONE -> EXIT ROUTE
# =========================================================

def calculate_route(
    zone_id,
    exit_name,
    risk_map,
):
    """
    Calculate one complete evacuation option:

        zone → physical topology → exit
    """

    zone_id = str(zone_id)

    exit_config = EXITS.get(
        exit_name
    )

    if zone_id not in ROOMS:
        return None

    if not exit_config:
        return None

    target = EXIT_NODES.get(
        exit_name
    )

    if not target:
        return None

    # =====================================================
    # DEFAULT BLOCKED RESPONSE
    # =====================================================

    base = {
        "exit": exit_name,
        "name": exit_config["name"],
        "status": "BLOCKED",
        "risk_score": 100.0,
        "reason": (
            "No safe physical path exists."
        ),
        "path": [],
        "distance": None,
        "critical_zones": [],
        "high_zones": [],
        "moderate_zones": [],
        "unknown_zones": [],
        "average_risk": 100.0,
        "maximum_risk": 100.0,
    }

    # =====================================================
    # FIND PHYSICAL PATH
    # =====================================================

    result = shortest_path(
        zone_id,
        target,
        risk_map,
    )

    if result is None:
        return base

    # =====================================================
    # ANALYZE PATH
    # =====================================================

    analysis = analyze_path(
        result["path"],
        risk_map,
    )

    # =====================================================
    # FINAL ROUTE SCORE
    # =====================================================

    final_score = calculate_route_score(
        analysis,
        result["cost"],
    )

    # Use the status determined by analyze_path(), which correctly
    # uses `blocking_critical` (excludes the starting room) for the
    # BLOCKED decision. Do NOT re-derive from critical_zones here
    # because that list includes the starting room and would
    # incorrectly mark every route as BLOCKED when the origin zone
    # is CRITICAL.
    status = analysis["status"]

    return {
    **base,
    **analysis,
    "status": status,
    "risk_score": final_score,
    "path": result["path"],
    "distance": result["edges"],
    "cost": result["cost"],
    "edges": result["edges"],
}


# =========================================================
# BUILD RISK MAP FROM SENSOR DATA
# =========================================================

def build_risk_map(sensors):
    """
    Convert sensor intelligence into a zone-indexed map.

    Only actual Building Alpha rooms are included.

    Missing zones are NOT fabricated here. They remain
    absent and are interpreted as UNKNOWN by node_risk().
    """

    risk_map = {}

    for sensor in sensors:

        zone_id = str(
            sensor.get(
                "zone_id",
                "",
            )
        )

        if zone_id not in ROOMS:
            continue

        raw_level = sensor.get(
            "risk_level"
        )

        if raw_level is None:
            risk_level = "UNKNOWN"
        else:
            risk_level = str(
                raw_level
            ).upper()

        raw_score = sensor.get(
            "risk_score"
        )

        if raw_score is None:
            risk_score = (
                UNKNOWN_RISK_SCORE
                if risk_level == "UNKNOWN"
                else 0.0
            )
        else:
            try:
                risk_score = float(
                    raw_score
                )
            except (
                TypeError,
                ValueError,
            ):
                risk_score = (
                    UNKNOWN_RISK_SCORE
                    if risk_level == "UNKNOWN"
                    else 0.0
                )

        try:
            occupancy = int(
                sensor.get(
                    "occupancy",
                    0,
                )
                or 0
            )
        except (
            TypeError,
            ValueError,
        ):
            occupancy = 0

        risk_map[zone_id] = {
            "risk_score": max(
                0.0,
                min(
                    100.0,
                    risk_score,
                ),
            ),
            "risk_level": risk_level,
            "occupancy": max(
                0,
                occupancy,
            ),
            "sensor_available": True,
        }

    return risk_map


# =========================================================
# CALCULATE ALL EXIT OPTIONS FOR ONE ZONE
# =========================================================

def calculate_zone_routes(
    zone_id,
    risk_map,
):
    """
    Return all three exit options for one zone.
    """

    return [
        calculate_route(
            zone_id,
            exit_name,
            risk_map,
        )
        for exit_name in EXITS
    ]
def calculate_path_risk(path, risk_map):
    if not path:
        return None

    total_risk = 0
    high_risk_rooms = 0
    critical_rooms = 0
    unknown_rooms = 0

    for node in path:
        if is_room(node):
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

def compare_algorithms(zone_id, risk_map):
    exits = EXIT_NODES.values()
    results = []

    for target in exits:

        start_time = perf_counter()
        bfs = bfs_path(zone_id, target)
        bfs_time = (perf_counter() - start_time) * 1000

        start_time = perf_counter()
        dfs = dfs_path(zone_id, target)
        dfs_time = (perf_counter() - start_time) * 1000

        start_time = perf_counter()
        dijkstra = shortest_path(zone_id, target, risk_map)
        dijkstra_time = (perf_counter() - start_time) * 1000

        start_time = perf_counter()
        astar = a_star_path(zone_id, target, risk_map)
        astar_time = (perf_counter() - start_time) * 1000

        results.append({
            "exit": target,
           "bfs": {
    "path": bfs["path"] if bfs else None,
    "edges": bfs["edges"] if bfs else None,
    "nodes_explored": bfs["nodes_explored"] if bfs else None,
    "execution_time_ms": round(bfs_time, 4),
    "risk_exposure": calculate_path_risk(bfs["path"] if bfs else None, risk_map),
},
          "dfs": {
    "path": dfs["path"] if dfs else None,
    "edges": dfs["edges"] if dfs else None,
    "nodes_explored": dfs["nodes_explored"] if dfs else None,
    "execution_time_ms": round(dfs_time, 4),
    "risk_exposure": calculate_path_risk(dfs["path"] if dfs else None, risk_map),
},
          "dijkstra": {
    "path": dijkstra["path"] if dijkstra else None,
    "cost": dijkstra["cost"] if dijkstra else None,
    "edges": dijkstra["edges"] if dijkstra else None,
    "nodes_explored": dijkstra["nodes_explored"] if dijkstra else None,
    "execution_time_ms": round(dijkstra_time, 4),
    "risk_exposure": calculate_path_risk(dijkstra["path"] if dijkstra else None, risk_map),
},
          "a_star": {
    "path": astar["path"] if astar else None,
    "cost": astar["cost"] if astar else None,
    "edges": astar["edges"] if astar else None,
    "nodes_explored": astar["nodes_explored"] if astar else None,
    "execution_time_ms": round(astar_time, 4),
    "risk_exposure": calculate_path_risk(astar["path"] if astar else None, risk_map),
},
        })

    return results
# =========================================================
# ROUTE WEIGHT
# =========================================================

def _route_weight(
    route,
    risk_map,
    zone_id,
):
    """
    Weight helper retained for compatibility.

    Routes are primarily ordered by safety score.
    Occupancy is used for building-level aggregation,
    not to make one person's route inherently less safe.
    """

    occupancy = max(
        0,
        int(
            risk_map
            .get(
                zone_id,
                {},
            )
            .get(
                "occupancy",
                0,
            )
        ),
    )

    return (
        route["risk_score"],
        -occupancy,
    )


# =========================================================
# CALCULATE COMPLETE BUILDING EVACUATION
# =========================================================

def calculate_all_routes(sensors, selected_zone=None):
    """
    Calculate evacuation intelligence for the entire building.

    Returns:

        - zone-by-zone routes
        - exit-level analysis
        - building-level recommendation
        - alternative exits
        - risk statistics
        - building graph
    """

    risk_map = build_risk_map(
        sensors
    )

    zones = []

    # =====================================================
    # ZONE-BY-ZONE ROUTES
    # =====================================================

    for sensor in sensors:

        zone_id = str(
            sensor.get(
                "zone_id",
                "",
            )
        )

        if zone_id not in ROOMS:
            continue

        routes = calculate_zone_routes(
            zone_id,
            risk_map,
        )

        # -------------------------------------------------
        # AVAILABLE
        # -------------------------------------------------

        available = [
            route
            for route in routes
            if route
            and route["status"]
            == "AVAILABLE"
        ]

        # -------------------------------------------------
        # CAUTION
        # -------------------------------------------------

        caution = [
            route
            for route in routes
            if route
            and route["status"]
            == "CAUTION"
        ]

        # Safe routes are always preferred over caution
        # routes.
        candidates = (
            available
            or caution
        )

        recommended = (
            min(
                candidates,
                key=lambda route:
                route["risk_score"],
            )
            if candidates
            else None
        )

        alternatives = sorted(
            [
                route
                for route in routes
                if (
                    route
                    and route["status"]
                    != "BLOCKED"
                    and (
                        not recommended
                        or route["exit"]
                        != recommended["exit"]
                    )
                )
            ],
            key=lambda route:
            route["risk_score"],
        )

        zones.append({
            "zone_id": zone_id,

            "floor": ROOMS[
                zone_id
            ]["floor"],

            "recommended_exit": recommended,

            "alternative_exits": alternatives,

            "all_routes": routes,
        })
    selected_zone_data = next(
        (
            zone
            for zone in zones
            if zone["zone_id"] == str(selected_zone)
        ),
        None,
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
                risk_map,
            )

            if route is not None:
                route_records.append(
                    (
                        zone_id,
                        route,
                    )
                )

        # -------------------------------------------------
        # USABLE ROUTES
        # -------------------------------------------------

        usable = [
            (
                zone_id,
                route,
            )
            for zone_id, route
            in route_records
            if route["status"]
            != "BLOCKED"
        ]

        connected = sorted(
            [
                zone_id
                for zone_id, _
                in usable
            ],
            key=int,
        )

        # -------------------------------------------------
        # EXIT HAS USABLE ROUTES
        # -------------------------------------------------

        if usable:

            # Actual occupancy only.
            total_people = sum(
                max(
                    0,
                    int(
                        risk_map[
                            zone_id
                        ].get(
                            "occupancy",
                            0,
                        )
                    ),
                )
                for zone_id, _
                in usable
            )

            # -------------------------------------------------
            # WEIGHTED EXIT RISK
            # -------------------------------------------------
            #
            # If occupancy exists, people are used as the
            # weighting factor.
            #
            # If every zone currently reports zero occupancy,
            # use an ordinary mean so the exit still receives
            # a meaningful risk score.

            if total_people > 0:

                weighted_score = (
                    sum(
                        route["risk_score"]
                        * max(
                            0,
                            int(
                                risk_map[
                                    zone_id
                                ].get(
                                    "occupancy",
                                    0,
                                )
                            ),
                        )
                        for zone_id, route
                        in usable
                    )
                    / total_people
                )

            else:

                weighted_score = (
                    sum(
                        route["risk_score"]
                        for _, route
                        in usable
                    )
                    / len(usable)
                )

            # -------------------------------------------------
            # BEST ROUTE TO THIS EXIT
            # -------------------------------------------------

            best_zone, best_route = min(
                usable,
                key=lambda item:
                item[1]["risk_score"],
            )

            # -------------------------------------------------
            # EXIT STATUS
            # -------------------------------------------------

            status = (
                "AVAILABLE"
                if any(
                    route["status"]
                    == "AVAILABLE"
                    for _, route
                    in usable
                )
                else "CAUTION"
            )

            if status == "AVAILABLE":

                reason = (
                    "Exit has at least one currently "
                    "available evacuation route."
                )

            else:

                reason = (
                    "Exit is reachable, but one or more "
                    "routes contain elevated or unknown risk."
                )

            exits.append({

                "exit": exit_name,

                "name": exit_config["name"],

                "risk_score": round(
                    min(
                        100.0,
                        weighted_score,
                    ),
                    2,
                ),

                "status": status,

                "reason": reason,

                "connected_zones": connected,

                "total_people": total_people,

                "best_path": best_route["path"],

                "best_zone": best_zone,

                "distance": best_route["distance"],
            })

        # -------------------------------------------------
        # EXIT COMPLETELY BLOCKED
        # -------------------------------------------------

        else:

            exits.append({

                "exit": exit_name,

                "name": exit_config["name"],

                "risk_score": 100.0,

                "status": "BLOCKED",

                "reason": (
                    "No safe physical route is currently "
                    "available from the monitored zones."
                ),

                "connected_zones": [],

                "total_people": 0,

                "best_path": [],

                "best_zone": None,

                "distance": None,
            })

    # =====================================================
    # BUILDING-LEVEL RECOMMENDED EXIT
    # =====================================================

    available_exits = [
        exit_data
        for exit_data in exits
        if exit_data["status"]
        == "AVAILABLE"
    ]

    caution_exits = [
        exit_data
        for exit_data in exits
        if exit_data["status"]
        == "CAUTION"
    ]

    # Always prefer a genuinely available exit.
    candidates = (
        available_exits
        or caution_exits
    )

    recommended = (
        min(
            candidates,
            key=lambda exit_data:
            (
                exit_data["risk_score"],
                -len(
                    exit_data[
                        "connected_zones"
                    ]
                ),
            ),
        )
        if candidates
        else None
    )

    # =====================================================
    # ALTERNATIVE EXITS
    # =====================================================

    alternatives = sorted(
        [
            exit_data
            for exit_data in exits
            if (
                exit_data["status"]
                != "BLOCKED"
                and (
                    not recommended
                    or exit_data["exit"]
                    != recommended["exit"]
                )
            )
        ],
        key=lambda exit_data:
        exit_data["risk_score"],
    )


    # =====================================================
    # FINAL BUILDING STATUS
    # =====================================================

    if available_exits:
        route_status = "SAFE ROUTE"
    elif caution_exits:
        route_status = "CAUTION ROUTE"
    else:
        route_status = "NO SAFE EXIT"

    building_condition = (
        "CRITICAL"
        if any(
            risk.get("risk_level") == "CRITICAL"
            for risk in risk_map.values()
        )
        else "HIGH RISK"
        if any(
            risk.get("risk_level") == "HIGH"
            for risk in risk_map.values()
        )
        else "NORMAL"
    )


    # =====================================================
    # ZONE STATISTICS
    # =====================================================

    monitored_zones = [
        sensor
        for sensor in sensors
        if str(
            sensor.get(
                "zone_id",
                "",
            )
        ) in ROOMS
    ]

    critical_zones = sum(
        1
        for sensor in monitored_zones
        if str(
            sensor.get(
                "risk_level",
                "",
            )
        ).upper()
        == "CRITICAL"
    )

    high_risk_zones = sum(
        1
        for sensor in monitored_zones
        if str(
            sensor.get(
                "risk_level",
                "",
            )
        ).upper()
        == "HIGH"
    )

    moderate_risk_zones = sum(
        1
        for sensor in monitored_zones
        if str(
            sensor.get(
                "risk_level",
                "",
            )
        ).upper()
        == "MODERATE"
    )

    unknown_zones = (
        len(ROOMS)
        - len(risk_map)
    )

    # =====================================================
    # TOTAL OCCUPANCY
    # =====================================================

    total_occupancy = sum(
        max(
            0,
            int(
                risk.get(
                    "occupancy",
                    0,
                )
            ),
        )
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

        "total_zones": len(
            monitored_zones
        ),

        "building_zones": len(
            ROOMS
        ),

        "monitored_zones": len(
            risk_map
        ),

        "unknown_zones": unknown_zones,

        "critical_zones": critical_zones,

        "high_risk_zones": high_risk_zones,

        "moderate_risk_zones": moderate_risk_zones,

        "total_occupancy": total_occupancy,

        "building_graph": BUILDING_GRAPH,
    }
