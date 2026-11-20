
import React from "react";

const floors = [3, 2, 1];

const roomNumbers = {
    1: ["101", "102", "103", "104"],
    2: ["201", "202", "203", "204"],
    3: ["301", "302", "303", "304"]
};

const corridorNames = [
    "LEFT",
    "CENTER",
    "RIGHT"
];

const stairs = ["A", "B", "C"];

const positions = {};

floors.forEach((floor, index) => {
    const y = 55 + index * 190;

    roomNumbers[floor].forEach((room, i) => {
        positions[room] = {
            x: 65 + i * 125,
            y: y
        };
    });

    corridorNames.forEach((name, i) => {
        positions[`CORRIDOR_${floor}_${name}`] = {
            x: 127 + i * 125,
            y: y + 65
        };
    });

    stairs.forEach((stair, i) => {
        positions[`STAIR_${stair}_${floor}`] = {
            x: 127 + i * 125,
            y: y + 125
        };
    });
});

positions.EXIT_A_NODE = { x: 127, y: 625 };
positions.EXIT_B_NODE = { x: 252, y: 625 };
positions.EXIT_C_NODE = { x: 377, y: 625 };

const edges = [];

floors.forEach(floor => {
    const rooms = roomNumbers[floor];

    edges.push(
        [rooms[0], `CORRIDOR_${floor}_LEFT`],
        [rooms[1], `CORRIDOR_${floor}_LEFT`],
        [rooms[1], `CORRIDOR_${floor}_CENTER`],
        [rooms[2], `CORRIDOR_${floor}_CENTER`],
        [rooms[2], `CORRIDOR_${floor}_RIGHT`],
        [rooms[3], `CORRIDOR_${floor}_RIGHT`],

        [`CORRIDOR_${floor}_LEFT`, `CORRIDOR_${floor}_CENTER`],
        [`CORRIDOR_${floor}_CENTER`, `CORRIDOR_${floor}_RIGHT`],

        [`CORRIDOR_${floor}_LEFT`, `STAIR_A_${floor}`],
        [`CORRIDOR_${floor}_CENTER`, `STAIR_B_${floor}`],
        [`CORRIDOR_${floor}_RIGHT`, `STAIR_C_${floor}`]
    );
});

stairs.forEach(stair => {
    edges.push(
        [`STAIR_${stair}_1`, `STAIR_${stair}_2`],
        [`STAIR_${stair}_2`, `STAIR_${stair}_3`]
    );
});

edges.push(
    ["STAIR_A_1", "EXIT_A_NODE"],
    ["STAIR_B_1", "EXIT_B_NODE"],
    ["STAIR_C_1", "EXIT_C_NODE"]
);

export default function EvacuationMap({
    zone,
    path = [],
    exit
}) {
    const selectedZone = String(zone || "");

    const activePath = path.map(node => String(node));

    const pathEdges = new Set();

    for (let i = 0; i < activePath.length - 1; i++) {
        pathEdges.add(
            `${activePath[i]}|${activePath[i + 1]}`
        );

        pathEdges.add(
            `${activePath[i + 1]}|${activePath[i]}`
        );
    }

    const isPathEdge = (a, b) =>
        pathEdges.has(`${a}|${b}`);

    const isPathNode = node =>
        activePath.includes(node);

    const nodeColor = node => {
        if (node === selectedZone) return "#ef4444";
        if (isPathNode(node)) return "#f59e0b";
        return "#15803d";
    };

    const renderNode = (node, label, width = 75) => {
        const point = positions[node];

        if (!point) return null;

        const isSelected = node === selectedZone;

        return (
            <g key={node}>
                <rect
                    x={point.x - width / 2}
                    y={point.y - 17}
                    width={width}
                    height="34"
                    rx="6"
                    fill={nodeColor(node)}
                    stroke={isSelected ? "#ffffff" : "#94a3b8"}
                    strokeWidth={isSelected ? "3" : "1"}
                />

                <text
                    x={point.x}
                    y={point.y + 5}
                    fill="white"
                    textAnchor="middle"
                    fontSize="12"
                    fontWeight="bold"
                >
                    {label}
                </text>
            </g>
        );
    };

    const renderEdge = ([a, b], index) => {
        const start = positions[a];
        const end = positions[b];

        if (!start || !end) return null;

        const highlighted = isPathEdge(a, b);

        return (
            <line
                key={`${a}-${b}-${index}`}
                x1={start.x}
                y1={start.y}
                x2={end.x}
                y2={end.y}
                stroke={highlighted ? "#f59e0b" : "#64748b"}
                strokeWidth={highlighted ? "5" : "2"}
                strokeLinecap="round"
            />
        );
    };

    return (
        <section style={{
            background: "#172334",
            padding: "18px",
            borderRadius: "12px",
            marginBottom: "20px",
            color: "white",
            overflow: "hidden"
        }}>
            <h2>Building Alpha - Evacuation Map</h2>

            <p>
                Selected Emergency Zone: <b>{selectedZone || "None"}</b>
            </p>

            <div style={{
                display: "flex",
                gap: "14px",
                flexWrap: "wrap",
                marginBottom: "15px",
                fontSize: "12px"
            }}>
                <span>🔴 Selected Zone</span>
                <span>🟠 Recommended Route</span>
                <span>🟢 Other Rooms</span>
                <span>⚪ Normal Connections</span>
            </div>

            <div style={{ overflowX: "auto" }}>
                <svg
                    viewBox="0 0 500 680"
                    width="100%"
                    style={{ minWidth: "340px" }}
                >
                    {floors.map((floor, index) => (
                        <g key={floor}>
                            <rect
                                x="5"
                                y={30 + index * 190}
                                width="490"
                                height="175"
                                rx="10"
                                fill="#26374b"
                                stroke="#475569"
                            />

                            <text
                                x="18"
                                y={48 + index * 190}
                                fill="white"
                                fontSize="13"
                                fontWeight="bold"
                            >
                                FLOOR {floor}
                            </text>
                        </g>
                    ))}

                    {edges.map(renderEdge)}

                    {floors.map(floor => (
                        <g key={`rooms-${floor}`}>
                            {roomNumbers[floor].map(room =>
                                renderNode(room, room, 75)
                            )}

                            {corridorNames.map(name => {
                                const node = `CORRIDOR_${floor}_${name}`;

                                return renderNode(
                                    node,
                                    name,
                                    80
                                );
                            })}

                            {stairs.map(stair => {
                                const node = `STAIR_${stair}_${floor}`;

                                return renderNode(
                                    node,
                                    `STAIR ${stair}`,
                                    85
                                );
                            })}
                        </g>
                    ))}

                    {["A", "B", "C"].map(stair =>
                        renderNode(
                            `EXIT_${stair}_NODE`,
                            `EXIT ${stair}`,
                            85
                        )
                    )}
                </svg>
            </div>

            <p>
                <b>Recommended Exit:</b> {exit || "Not available"}
            </p>

            <p style={{
                overflowWrap: "anywhere",
                fontSize: "13px"
            }}>
                <b>Dijkstra Route:</b>{" "}
                {activePath.length
                    ? activePath.join(" → ")
                    : "No route available"}
            </p>
        </section>
    );
}
