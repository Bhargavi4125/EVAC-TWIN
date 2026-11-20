
import os
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx

from app.building_layout import (
    BUILDING_ID,
    ROOMS,
    CORRIDORS,
    STAIRS,
    EXITS,
    EDGES,
    EXIT_NODES
)


BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

RESULTS_DIR = os.path.join(
    BASE_DIR, "app", "ml", "results"
)

os.makedirs(RESULTS_DIR, exist_ok=True)

OUTSIDE_NODE = "OUTSIDE_SAFE_AREA"


def generate_building_topology():

    G = nx.Graph()
    G.add_edges_from(EDGES)

    # --------------------------------------------------
    # SEQUENTIAL EMERGENCY EXIT CONNECTIONS
    # --------------------------------------------------

    exit_1 = EXIT_NODES["EXIT 1"]
    exit_2 = EXIT_NODES["EXIT 2"]
    exit_3 = EXIT_NODES["EXIT 3"]

    G.add_edge(exit_3, exit_2)
    G.add_edge(exit_2, exit_1)
    G.add_edge(exit_1, OUTSIDE_NODE)

    # --------------------------------------------------
    # DYNAMIC FLOOR POSITIONS
    # --------------------------------------------------

    pos = {}
    labels = {}

    floors = sorted(
        {data["floor"] for data in ROOMS.values()}
    )

    floor_spacing = 8

    for floor in floors:

        # Floor 3 at top, Floor 1 at bottom
        y = (floor - min(floors)) * floor_spacing

        floor_rooms = sorted(
            [
                room for room, data in ROOMS.items()
                if data["floor"] == floor
            ],
            key=int
        )

        # Room positions
        for index, room in enumerate(floor_rooms):

            x = index * 2.5

            pos[room] = (x, y)
            labels[room] = ROOMS[room]["name"]

        # Corridor positions
        for corridor, data in CORRIDORS.items():

            if data["floor"] == floor:

                pos[corridor] = (
                    3.75,
                    y - 1.8
                )

                labels[corridor] = corridor.replace("_", "\n")

        # Staircase positions on LEFT
        for stair_name, stair in STAIRS.items():

            stair_node = stair["floor_connections"].get(floor)

            if stair_node in G:

                pos[stair_node] = (
                    -3,
                    y - 1.8
                )

                labels[stair_node] = (
                    f"{stair['name']}\nFloor {floor}"
                )

        # Emergency exits on RIGHT
        for exit_name, exit_data in EXITS.items():

            if exit_data["floor"] == floor:

                exit_node = exit_data["node"]

                pos[exit_node] = (
                    9,
                    y - 1.8
                )

                labels[exit_node] = exit_name

    # --------------------------------------------------
    # OUTSIDE SAFE AREA AT GROUND LEVEL
    # --------------------------------------------------

    ground_exit = EXIT_NODES["EXIT 1"]

    ground_x, ground_y = pos[ground_exit]

    pos[OUTSIDE_NODE] = (
        14,
        ground_y - 3
    )

    labels[OUTSIDE_NODE] = "OUTSIDE /\nSAFE AREA"

    # --------------------------------------------------
    # NODE GROUPS
    # --------------------------------------------------

    room_nodes = list(ROOMS.keys())

    corridor_nodes = list(CORRIDORS.keys())

    stair_nodes = [
        node
        for stair in STAIRS.values()
        for node in stair["floor_connections"].values()
        if node in G
    ]

    exit_nodes = list(EXIT_NODES.values())

    outside_nodes = [OUTSIDE_NODE]

    # Validate positions
    missing_positions = set(G.nodes) - set(pos)

    if missing_positions:
        raise ValueError(
            f"Missing node positions: {missing_positions}"
        )

    # --------------------------------------------------
    # DRAW GRAPH
    # --------------------------------------------------

    fig, ax = plt.subplots(figsize=(23, 15))

    nx.draw_networkx_edges(
        G,
        pos,
        ax=ax,
        edge_color="gray",
        width=2
    )

    # Rooms
    nx.draw_networkx_nodes(
        G, pos,
        nodelist=room_nodes,
        node_color="lightgreen",
        node_shape="s",
        node_size=1900,
        ax=ax
    )

    # Corridors
    nx.draw_networkx_nodes(
        G, pos,
        nodelist=corridor_nodes,
        node_color="orange",
        node_shape="s",
        node_size=2200,
        ax=ax
    )

    # Staircase
    nx.draw_networkx_nodes(
        G, pos,
        nodelist=stair_nodes,
        node_color="skyblue",
        node_shape="s",
        node_size=2000,
        ax=ax
    )

    # Emergency exits
    nx.draw_networkx_nodes(
        G, pos,
        nodelist=exit_nodes,
        node_color="salmon",
        node_shape="D",
        node_size=2000,
        ax=ax
    )

    # Outside safe area
    nx.draw_networkx_nodes(
        G, pos,
        nodelist=outside_nodes,
        node_color="lightgray",
        node_shape="h",
        node_size=3500,
        ax=ax
    )

    # Labels
    nx.draw_networkx_labels(
        G,
        pos,
        labels=labels,
        font_size=8,
        font_weight="bold",
        ax=ax
    )

    # --------------------------------------------------
    # FLOOR LABELS AND SEPARATORS
    # --------------------------------------------------

    for floor in floors:

        y = (floor - min(floors)) * floor_spacing

        ax.text(
            11,
            y,
            f"FLOOR {floor}",
            fontsize=14,
            fontweight="bold"
        )

        if floor != min(floors):

            ax.axhline(
                y - floor_spacing / 2,
                color="gray",
                linestyle="--",
                alpha=0.5
            )

    # --------------------------------------------------
    # TITLE AND LEGEND
    # --------------------------------------------------

    ax.set_title(
        f"EVAC-TWIN - {BUILDING_ID.upper()} TOPOLOGY",
        fontsize=18,
        fontweight="bold"
    )

    ax.text(
        0.01,
        0.01,
        "Green: Rooms | Orange: Corridors | "
        "Blue: Staircase | Red: Exits | "
        "Gray: Outside Safe Area",
        transform=ax.transAxes,
        fontsize=10
    )

    ax.axis("off")
    fig.tight_layout()

    # --------------------------------------------------
    # SAVE IMAGE
    # --------------------------------------------------

    image_path = os.path.join(
        RESULTS_DIR,
        "building_alpha_topology.png"
    )

    fig.savefig(
        image_path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close(fig)

    # --------------------------------------------------
    # SAVE GRAPH DATA
    # --------------------------------------------------

    graph_path = os.path.join(
        RESULTS_DIR,
        "building_alpha_topology.graphml"
    )

    nx.write_graphml(G, graph_path)

    # --------------------------------------------------
    # SAVE CONNECTION DETAILS
    # --------------------------------------------------

    connections_path = os.path.join(
        RESULTS_DIR,
        "building_alpha_connections.txt"
    )

    with open(
        connections_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(f"BUILDING: {BUILDING_ID}\n\n")

        file.write("GRAPH CONNECTIONS\n")
        file.write("==================\n")

        for node in sorted(G.nodes):

            neighbors = sorted(G.neighbors(node))

            file.write(
                f"{node} -> {', '.join(neighbors)}\n"
            )

        file.write("\nSEQUENTIAL EXIT PATH\n")
        file.write("====================\n")

        file.write(
            f"{exit_3} -> {exit_2} -> "
            f"{exit_1} -> {OUTSIDE_NODE}\n"
        )

    # --------------------------------------------------
    # PRINT DETAILS
    # --------------------------------------------------

    print("\nBUILDING TOPOLOGY GENERATED")
    print("--------------------------------")

    print("Building:", BUILDING_ID)

    for floor in reversed(floors):

        floor_rooms = [
            room for room, data in ROOMS.items()
            if data["floor"] == floor
        ]

        print(
            f"Floor {floor} rooms:",
            sorted(floor_rooms, key=int)
        )

    print("\nEXIT CONNECTIONS:")

    print(exit_3, "->", exit_2)
    print(exit_2, "->", exit_1)
    print(exit_1, "->", OUTSIDE_NODE)

    print("\nTotal rooms:", len(room_nodes))
    print("Total corridors:", len(corridor_nodes))
    print("Staircase landings:", len(stair_nodes))
    print("Emergency exits:", len(exit_nodes))
    print("Total connections:", G.number_of_edges())

    print("\nSAVED FILES:")
    print(image_path)
    print(graph_path)
    print(connections_path)

    return G, image_path


if __name__ == "__main__":
    generate_building_topology()
