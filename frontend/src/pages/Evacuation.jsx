import { useEffect, useState } from "react";
import {
    getEvacuationRoutes,
    getEvents,
    getSensors,
    getAlgorithmComparison,
} from "../services/api";
import { calculateRisk } from "../utils/riskEngine";
import "./Evacuation.css";

function Evacuation() {
    const [sensors, setSensors] = useState([]);
    const [selectedDevice, setSelectedDevice] = useState(
    () => `sensor-${localStorage.getItem("selectedZone") || "101"}`
);
    const [events, setEvents] = useState([]);
    const [evacuationRoutes, setEvacuationRoutes] = useState(null);
    const [error, setError] = useState("");
    const [algorithmComparison, setAlgorithmComparison] = useState([]);
    useEffect(() => {
    const savedComparison = localStorage.getItem(
        "algorithmComparison"
    );

    if (savedComparison) {
        setAlgorithmComparison(
            JSON.parse(savedComparison)
        );
    }
}, []);

    useEffect(() => {
        const loadData = async () => {
            try {
                const [sensorData, eventData] =
    await Promise.all([
        getSensors(),
        getEvents(),
    ]);

                setSensors(sensorData || []);
                setEvents(eventData || []);
                setError("");
            } catch (err) {
                console.error(err);
                setError(
                    "Unable to connect to EVAC-TWIN backend."
                );
            }
        };

        loadData();

        const interval = setInterval(
            loadData,
            3000
        );

        return () =>
            clearInterval(interval);
    }, []);

    /* =====================================================
       LATEST SENSOR
    ===================================================== */


  
const liveLatest =
    sensors.find(
        (sensor) => sensor.device_id === selectedDevice
    ) || null;


// =====================================================
// LATEST LIVE SENSOR
// =====================================================

const latest = liveLatest;

useEffect(() => {
    if (!latest?.zone_id) {
        return;
    }

    // Mee existing useEffect code ikkada continue avvali

    const loadRoutes = async () => {
        try {
            const routeData = await getEvacuationRoutes(latest.zone_id);
            setEvacuationRoutes(routeData || null);
        } catch (err) {
            console.error("Evacuation routes failed:", err);
        }
    };

    loadRoutes();

}, [
    latest?.zone_id,
    latest?.temperature,
    latest?.smoke,
    latest?.occupancy
]);
    useEffect(() => {
    if (!latest?.device_id) {
        return;
    }

    const loadComparison = async () => {
        try {
            const data =
    await getAlgorithmComparison(
        latest.device_id,
        latest.temperature,
        latest.smoke,
        latest.occupancy
    );

           setAlgorithmComparison(
    Array.isArray(data) ? data : data?.comparison || []
);
        } catch (err) {
            console.error(
                "Algorithm comparison failed:",
                err
            );
        }
    };

    loadComparison();
}, [latest?.device_id, latest?.temperature, latest?.smoke, latest?.occupancy]);

    /* =====================================================
       ACTIVE EVENT
    ===================================================== */

   const activeEvent = events.find(
    (event) =>
        event.status === "ACTIVE" &&
        String(event.zone_id) === String(latest?.zone_id)
);

    /* =====================================================
       RISK
    ===================================================== */

    const calculatedRisk = latest
    ? calculateRisk(latest)
    : {
        level: "WAITING",
        score: 0,
        recommendation:
            "Waiting for live sensor information.",
        factors: {
            temperature: 0,
            smoke: 0,
            occupancy: 0,
        },
    };

const risk = latest
    ? {
        ...calculatedRisk,
        level:
            latest.dl_prediction ||
            latest.risk_level ||
            calculatedRisk.level,
        score:
            latest.risk_score ??
            calculatedRisk.score,
        recommendation:
            latest.recommendation ||
            calculatedRisk.recommendation,
    }
    : calculatedRisk;
console.log("Selected Zone:", latest?.zone_id);
console.log("Calculated Risk:", calculatedRisk);
console.log("Active Event:", activeEvent);

    const riskLevel = risk.level;

const riskScore = Number(risk.score ?? 0);

    /* =====================================================
       RISK THEME
    ===================================================== */

    const getRiskTheme = () => {
        switch (riskLevel) {
            case "CRITICAL":
                return {
                    color: "#ff5c5c",
                    soft: "#321b22",
                    border: "#71323c",
                    icon: "!",
                    title:
                        "EVACUATE IMMEDIATELY",
                };

            case "HIGH":
                return {
                    color: "#f59e0b",
                    soft: "#332714",
                    border: "#70531b",
                    icon: "!",
                    title:
                        "PREPARE FOR EVACUATION",
                };

            case "MODERATE":
                return {
                    color: "#38a0ca",
                    soft: "#122d3d",
                    border: "#24536b",
                    icon: "•",
                    title:
                        "MONITOR CONDITIONS",
                };

            default:
                return {
                    color: "#35c98a",
                    soft: "#12352b",
                    border: "#24654c",
                    icon: "✓",
                    title: "SAFE",
                };
        }
    };

    const theme =
        getRiskTheme();

    /* =====================================================
       EVACUATION STATUS
    ===================================================== */
const getEvacuationStatus = () => {
    if (!latest)
        return "WAITING FOR DATA";

    if (riskLevel === "CRITICAL") {
        return "EVACUATE IMMEDIATELY";
    }

    if (riskLevel === "HIGH") {
        return "PREPARE FOR EVACUATION";
    }

    if (riskLevel === "MODERATE") {
        return "MONITOR CONDITIONS";
    }

    if (evacuationRoutes?.route_status) {
        return evacuationRoutes.route_status;
    }

    return "SAFE";
};

    const evacuationStatus =
        getEvacuationStatus();

    /* =====================================================
       SENSOR STATUS
    ===================================================== */

    const getTemperatureStatus =
        () => {
            if (!latest)
                return "WAITING";

            if (
                latest.temperature >=
                40
            )
                return "CRITICAL";

            if (
                latest.temperature >=
                38
            )
                return "ELEVATED";

            return "NORMAL";
        };

    const getSmokeStatus = () => {
        if (!latest)
            return "WAITING";

        if (
            latest.smoke >=
            0.9
        )
            return "CRITICAL";

        if (
            latest.smoke >=
            0.7
        )
            return "HIGH";

        if (
            latest.smoke >=
            0.5
        )
            return "MODERATE";

        return "NORMAL";
    };

    const getOccupancyStatus =
        () => {
            if (!latest)
                return "WAITING";

            if (
                latest.occupancy >=
                48
            )
                return "CRITICAL";

            if (
                latest.occupancy >=
                40
            )
                return "HIGH";

            if (
                latest.occupancy >=
                30
            )
                return "MODERATE";

            return "NORMAL";
        };

    const getSensorColor =
        (status) => {
            if (
                status ===
                "CRITICAL"
            )
                return "#ff5c5c";

            if (
                status === "HIGH" ||
                status === "ELEVATED"
            )
                return "#f59e0b";

            if (
                status ===
                "MODERATE"
            )
                return "#38a0ca";

            return "#35c98a";
        };

    /* =====================================================
       ACTION
    ===================================================== */

    const getAction = () => {
        if (
            riskLevel ===
            "CRITICAL"
        ) {
            return {
                title:
                    "Evacuate Immediately",
                text:
                    "Emergency conditions require immediate evacuation. Follow the dynamically recommended route and avoid blocked exits.",
            };
        }

        if (
            riskLevel ===
            "HIGH"
        ) {
            return {
                title:
                    "Prepare for Evacuation",
                text:
                    "Conditions are deteriorating. Prepare occupants and keep the safest emergency route ready.",
            };
        }

        if (
            riskLevel ===
            "MODERATE"
        ) {
            return {
                title:
                    "Continue Monitoring",
                text:
                    "Elevated conditions detected. Continue monitoring live sensor data for further changes.",
            };
        }

        return {
            title:
                "No Evacuation Required",
            text:
                "Environmental conditions are currently within the safe operating range.",
        };
    };

    const action =
        getAction();

    /* =====================================================
       ROUTE COLOR
    ===================================================== */

    const getRouteColor =
        (status) => {
            switch (status) {
                case "AVAILABLE":
                    return "#35c98a";

                case "CAUTION":
                    return "#f59e0b";

                case "BLOCKED":
                    return "#ff5c5c";

                default:
                    return "#64748b";
            }
        };

  const simulationRoute = (() => {
    try {
        const data = localStorage.getItem("simulationRoute");
        return data ? JSON.parse(data) : null;
    } catch {
        return null;
    }
})();


const recommendedExit =
    evacuationRoutes?.selected_zone_recommendation ||
    evacuationRoutes?.recommended_exit;

const routeList =
    evacuationRoutes?.selected_zone_routes ||
    evacuationRoutes?.all_routes ||
    [];

const hasSafeRoute = routeList.some(
    (route) => route.status === "AVAILABLE"
);
    /* =====================================================
       RENDER
    ===================================================== */

    
return (
    <div className="evacuation-page">

        <div className="sensor-select">
            <label>Select Starting Zone: </label>

            <select
                value={selectedDevice}
                onChange={(e) => {
                    const deviceId = e.target.value;

                    setSelectedDevice(deviceId);

                    localStorage.setItem(
                        "selectedZone",
                        deviceId.replace(/^sensor-/, "")
                    );
                }}
            >
                {sensors.map((sensor) => (
                    <option
                        key={sensor.device_id}
                        value={sensor.device_id}
                    >
                        {sensor.zone_id}
                    </option>
                ))}
            </select>
        </div>

        {/* =================================================
           HEADER
        ================================================= */}




            <header className="evac-header">

                <div>
                    <div className="evac-breadcrumb">
                        COMMAND CENTER
                        <span>/</span>
                        EVACUATION
                    </div>

                    <h1>
                        Evacuation Management
                    </h1>

                    <p>
                        Real-time emergency
                        response and intelligent
                        route management
                    </p>
                </div>

                <div className="evac-header-status">

                    <div className="system-online">
                        <span>●</span>
                        SYSTEM ONLINE
                    </div>

                    <div className="live-badge">
                        LIVE
                    </div>

                </div>

            </header>

            {/* =================================================
               ERROR
            ================================================= */}

            {error && (
                <div className="error-box">

                    <div className="error-icon">
                        !
                    </div>

                    <div>
                        <strong>
                            Backend Connection Error
                        </strong>

                        <p>
                            {error}
                        </p>
                    </div>

                </div>
            )}

            {/* =================================================
               LOADING
            ================================================= */}

            {!latest &&
                !error && (
                    <div className="loading-state">

                        <div className="loading-spinner" />

                        <h3>
                            Synchronizing
                            Digital Twin
                        </h3>

                        <p>
                            Waiting for live
                            sensor data...
                        </p>

                    </div>
                )}

            {latest && (
                <>

                    {/* =================================================
                       COMMAND STATUS
                    ================================================= */}

                    <section
                        className="command-status"
                        style={{
                            "--status-color":
                                theme.color,

                            "--status-soft":
                                theme.soft,

                            "--status-border":
                                theme.border,
                        }}
                    >

                        <div className="command-main">

                            <div className="status-icon">
                                {theme.icon}
                            </div>

                            <div className="status-text">

                                <span className="eyebrow">
                                    CURRENT EVACUATION STATUS
                                </span>

                                <h2>
                                    {evacuationStatus}
                                </h2>

                                <p>
                                    {
                                        risk.recommendation
                                    }
                                </p>

                            </div>

                        </div>

                        <div className="risk-score-block">

                            <div className="risk-number">
                                {riskScore}
                            </div>

                            <div className="risk-score-info">

                                <strong>
                                    RISK SCORE
                                </strong>

                                <span>
                                    OUT OF 100
                                </span>

                            </div>

                        </div>

                        <div className="command-route">

                            <span className="eyebrow">
                                ROUTE DECISION
                            </span>

                            <strong>
                                {recommendedExit
                                    ? recommendedExit.exit
                                    : "NO SAFE EXIT"}
                            </strong>

                            <span>
                                {recommendedExit
                                    ? recommendedExit.name
                                    : "No currently safe evacuation route"}
                            </span>

                        </div>

                    </section>

                    {/* =================================================
                       RISK METER
                    ================================================= */}

                    <section className="risk-meter-card">

                        <div className="risk-meter-header">

                            <div>

                                <span className="section-label">
                                    THREAT ASSESSMENT
                                </span>

                                <h2>
                                    Current Risk Level
                                </h2>

                            </div>

                            <span
                                className="risk-level-badge"
                                style={{
                                    color:
                                        theme.color,

                                    background:
                                        theme.soft,

                                    borderColor:
                                        theme.border,
                                }}
                            >
                                {riskLevel}
                            </span>

                        </div>

                        <div className="risk-meter">

                            <div
                                className="risk-meter-fill"
                                style={{
                                    width: `${Math.min(
                                        riskScore,
                                        100
                                    )}%`,

                                    background:
                                        theme.color,
                                }}
                            />

                        </div>

                        <div className="risk-scale">

                            <span>
                                SAFE
                            </span>

                            <span>
                                MODERATE
                            </span>

                            <span>
                                HIGH
                            </span>

                            <span>
                                CRITICAL
                            </span>

                        </div>

                    </section>

                    {/* =================================================
                       ACTIVE EVENT
                    ================================================= */}

                    {activeEvent && (
                        <section
                            className="active-event"
                            style={{
                                borderColor:
                                    theme.border,
                            }}
                        >

                            <div
                                className="event-icon"
                                style={{
                                    color:
                                        theme.color,

                                    background:
                                        theme.soft,
                                }}
                            >
                                !
                            </div>

                            <div className="event-content">

                                <span
                                    style={{
                                        color:
                                            theme.color,
                                    }}
                                >
                                    ACTIVE EMERGENCY EVENT
                                </span>

                                <strong>
                                    {
                                        activeEvent.level
                                    }{" "}
                                    RISK DETECTED
                                </strong>

                                <p>
                                    {
                                        activeEvent.recommendation ||
                                        "Emergency condition detected."
                                    }
                                </p>

                            </div>

                            <div className="event-score">

                                <span>
                                    SCORE
                                </span>

                                <strong>
                                    {
                                        activeEvent.score
                                    }
                                </strong>

                            </div>

                        </section>
                    )}

                    {/* =================================================
                       SENSOR MONITOR
                    ================================================= */}

                    <section className="section-block">

                        <div className="section-header">

                            <div>

                                <span className="section-label">
                                    ENVIRONMENT MONITOR
                                </span>

                                <h2>
                                    Live Risk Factors
                                </h2>

                            </div>

                            <div className="device-badge">

                                DEVICE

                                <strong>
                                    {
                                        latest.device_id
                                    }
                                </strong>

                            </div>

                        </div>

                        <div className="sensor-grid">

                            
<SensorCard
    icon="°"
    label="TEMPERATURE"
    value={`${latest.temperature}°C`}
    status={getTemperatureStatus()}
    color={getSensorColor(
        getTemperatureStatus()
    )}
    description={`Indicator value: ${risk.factors.temperature}`}
/>

                            
<SensorCard
    icon="◈"
    label="SMOKE LEVEL"
    value={latest.smoke}
    status={getSmokeStatus()}
    color={getSensorColor(
        getSmokeStatus()
    )}
    description={`Indicator value: ${risk.factors.smoke}`}
/>


                            
<SensorCard
    icon="♙"
    label="OCCUPANCY"
    value={latest.occupancy}
    status={getOccupancyStatus()}
    color={getSensorColor(
        getOccupancyStatus()
    )}
    description={`Indicator value: ${risk.factors.occupancy}`}
/>


                            <SensorCard
                                icon="◌"
                                label="HUMIDITY"
                                value={`${latest.humidity}%`}
                                status="NORMAL"
                                color="#35c98a"
                                description="Environmental data"
                            />

                        </div>

                    </section>

                    {/* =================================================
                       RESPONSE ENGINE
                    ================================================= */}

                    <section className="response-card">

                        <div className="section-header">

                            <div>

                                <span className="section-label">
                                    RESPONSE ENGINE
                                </span>

                                <h2>
                                    Recommended Action
                                </h2>

                            </div>

                            <span
                                className="risk-level-badge"
                                style={{
                                    color:
                                        theme.color,

                                    background:
                                        theme.soft,

                                    borderColor:
                                        theme.border,
                                }}
                            >
                                {riskLevel}
                            </span>

                        </div>

                        <div
                            className="action-panel"
                            style={{
                                background:
                                    theme.soft,

                                borderColor:
                                    theme.border,
                            }}
                        >

                            <div
                                className="action-icon"
                                style={{
                                    color:
                                        theme.color,
                                }}
                            >
                                {theme.icon}
                            </div>

                            <div className="action-content">

                                <h3
                                    style={{
                                        color:
                                            theme.color,
                                    }}
                                >
                                    {action.title}
                                </h3>

                                <p>
                                    {action.text}
                                </p>

                            </div>

                            <div className="automated">

                                <span>
                                    DECISION
                                </span>

                                <strong>
                                    AUTOMATED
                                </strong>

                            </div>

                        </div>

                    </section>

                    {/* =================================================
                       ROUTES
                    ================================================= */}

                    <section className="route-card">

                        <div className="route-header">

                            <div>

                                <span className="section-label">
                                    DIGITAL TWIN ROUTING
                                </span>

                                <h2>
                                    Evacuation Routes
                                </h2>

                                <p>
                                    Routes dynamically
                                    evaluated from
                                    current environmental
                                    and occupancy
                                    conditions.
                                </p>

                            </div>

                            <div className="routes-live">

                                <span>
                                    ●
                                </span>

                                ROUTES LIVE

                            </div>

                        </div>

                        
<div className="route-list">
    {routeList.map((exit, index) => (
        <Route
            key={exit.exit}
            number={String(index + 1).padStart(2, "0")}
            title={exit.name}
            code={exit.exit}
            description={exit.reason}
            status={exit.status}
            color={getRouteColor(exit.status)}
            riskScore={exit.risk_score}
            connectedZones={exit.connected_zones}
            path={exit.path}
            distance={exit.distance}
            isRecommended={recommendedExit?.exit === exit.exit}
        />
    ))}

    {!evacuationRoutes && (
        <div style={{ padding: "30px", textAlign: "center", color: "#64748b" }}>
            Calculating evacuation routes...
        </div>
    )}

    {evacuationRoutes && routeList.length === 0 && (
        <div style={{ padding: "30px", textAlign: "center", color: "#ff5c5c" }}>
            No evacuation routes returned by the backend.
        </div>
    )}
</div>

                        {/* =================================================
                           ROUTE STATS
                        ================================================= */}

                        <div className="route-stats">

                            <Stat
                                label="RISK LEVEL"
                                value={
                                    riskLevel
                                }
                                color={
                                    theme.color
                                }
                            />

                            <Stat
                                label="RISK SCORE"
                                value={`${riskScore}/100`}
                            />

                            <Stat
                                label="OCCUPANTS"
                                value={
                                    latest.occupancy
                                }
                            />




<Stat
    label="ROUTE STATUS"
    value={
        riskLevel === "CRITICAL"
            ? routeList.some(
                route => route.status === "AVAILABLE"
            )
                ? "EVACUATION REQUIRED"
                : routeList.some(
                    route => route.status === "CAUTION"
                )
                    ? "CAUTION ROUTE — EVACUATE"
                    : "NO AVAILABLE ROUTE"
            : riskLevel === "HIGH"
                ? "PREPARE TO EVACUATE"
                : routeList.some(
                    route => route.status === "AVAILABLE"
                )
                    ? "SAFE ROUTE"
                    : routeList.some(
                        route => route.status === "CAUTION"
                    )
                        ? "CAUTION ROUTE"
                        : "NO AVAILABLE ROUTE"
    }
    color={
        riskLevel === "CRITICAL"
            ? "#ff5c5c"
            : riskLevel === "HIGH"
                ? "#f59e0b"
                : routeList.some(
                    route => route.status === "AVAILABLE"
                )
                    ? "#35c98a"
                    : routeList.some(
                        route => route.status === "CAUTION"
                    )
                        ? "#f59e0b"
                        : "#ff5c5c"
    }
/>



                                
                            

                        </div>

                    </section>

       
{/* =================================================
   ALGORITHM COMPARISON
================================================= */}

<section className="system-card">

    <div className="system-header">
        <div>
            <span className="section-label">
                ROUTING ALGORITHM ANALYSIS
            </span>

            <h2>Algorithm Comparison</h2>

            <small>
                Comparing route search methods for the selected zone.
            </small>
        </div>

        <span className="connected">
            ● LIVE
        </span>
    </div>

    <div className="algorithm-grid">

        {algorithmComparison
            .filter((item) => {
                const recommended =
                    evacuationRoutes?.selected_zone_recommendation?.exit ||
                    evacuationRoutes?.recommended_exit?.exit;

                if (!recommended) return true;

                const normalize = (value) =>
                    String(value)
                        .toLowerCase()
                        .replace(/[^a-z0-9]/g, "");

                return (
                    normalize(item.exit).includes(normalize(recommended)) ||
                    normalize(recommended).includes(normalize(item.exit))
                );
            })
            .map((item) => (

                <div className="algorithm-card" key={item.exit}>

                    <strong>{item.exit}</strong>

                    <div>
                        <span>BFS</span>

                        <small>
                            Finds a path with the minimum number of edges.
                        </small>

                        <small>
                            {item.bfs?.path?.join(" → ") || "No path available"}
                        </small>

                        <small>
                            Edges: {item.bfs?.edges ?? "N/A"}
                        </small>

                    
                    </div>

                    <div>
                        <span>DFS</span>

                        <small>
                            Explores the graph depth-first; it does not guarantee
                            the shortest path.
                        </small>

                        <small>
                            {item.dfs?.path?.join(" → ") || "No path available"}
                        </small>

                        <small>
                            Edges: {item.dfs?.edges ?? "N/A"}
                        </small>

                        
                    </div>

                    <div className="recommended-algorithm">

                        <span>
                            Dijkstra <b>PRIMARY</b>
                        </span>

                        <small>
                            Finds the minimum accumulated cost using
                            non-negative risk-aware edge weights.
                        </small>

                        <small>
                            {item.dijkstra?.path?.join(" → ") || "No path available"}
                        </small>

                        <small>
                            Cost: {item.dijkstra?.cost ?? "N/A"}
                            {" | "}
                            Edges: {item.dijkstra?.edges ?? "N/A"}
                        </small>

                        

                        <small className="why-dijkstra">
                            Primary algorithm because EVAC-TWIN uses
                            risk-aware weighted route costs.
                        </small>

                    </div>

                    <div>
                        <span>A*</span>

                        <small>
                            Uses weighted route cost and a destination-guided
                            heuristic to search for a route.
                        </small>

                        <small>
                            {item.a_star?.path?.join(" → ") || "No path available"}
                        </small>

                        <small>
                            Cost: {item.a_star?.cost ?? "N/A"}
                            {" | "}
                            Edges: {item.a_star?.edges ?? "N/A"}
                        </small>

                        

                    </div>

                </div>
            ))}

    </div>

</section>


                    {/* =================================================
                       SYSTEM STATUS
                    ================================================= */}

                    <section className="system-card">

                        <div className="system-header">

                            <div>

                                <span className="section-label">
                                    SYSTEM STATUS
                                </span>

                                <h2>
                                    Digital Twin Connection
                                </h2>

                            </div>

                            <span className="connected">
                                ● CONNECTED
                            </span>

                        </div>

                        <div className="system-grid">

                            <Info
                                label="DEVICE"
                                value={
                                    latest.device_id
                                }
                            />

                            <Info
                                label="LAST UPDATED"
                                value={
                                    latest.timestamp
                                        ? new Date(
                                            latest.timestamp
                                        ).toLocaleTimeString()
                                        : "—"
                                }
                            />

                            <Info
                                label="UPDATE FREQUENCY"
                                value="3 seconds"
                            />

                            <Info
                                label="BACKEND"
                                value="ONLINE"
                                green
                            />

                        </div>

                    </section>

                    {/* =================================================
                       FOOTER
                    ================================================= */}

                    <footer className="evac-footer">

                        <span>
                            <b>●</b>{" "}
                            EVAC-TWIN DIGITAL
                            TWIN SYNCHRONIZED
                        </span>

                        <span>
                            Real-time monitoring
                            · 3 second refresh
                        </span>

                    </footer>

                </>
            )}

        </div>
    );
}


/* =========================================================
   SENSOR CARD
========================================================= */

function SensorCard({
    icon,
    label,
    value,
    status,
    color,
    description,
}) {
    return (
        <div
            className="sensor-card"
            style={{
                "--sensor-color":
                    color,
            }}
        >

            <div className="sensor-top">

                <div
                    className="sensor-icon"
                    style={{
                        color,
                        background:
                            `${color}12`,
                    }}
                >
                    {icon}
                </div>

                <span
                    className="sensor-status"
                    style={{
                        color,
                    }}
                >
                    ● {status}
                </span>

            </div>

            <span className="sensor-label">
                {label}
            </span>

            <strong className="sensor-value">
                {value}
            </strong>

            <div className="sensor-bottom">

                <span>
                    {description}
                </span>

                <span
                    style={{
                        color,
                    }}
                >
                    ●
                </span>

            </div>

        </div>
    );
}


/* =========================================================
   ROUTE
========================================================= */

function Route({
    number,
    title,
    code,
    description,
    status,
    color,
    riskScore,
    connectedZones,
    path,
    distance,
    isRecommended,
}) {
    return (
        <div
            className="route"
            style={{
                "--route-color":
                    color,
            }}
        >

            {/* NUMBER */}

            <div className="route-number">
                {number}
            </div>

            {/* MARKER */}

            <div className="route-marker">

                <div
                    className="marker-dot"
                    style={{
                        background:
                            color,

                        boxShadow:
                            `0 0 0 5px ${color}20`,
                    }}
                />

            </div>

            {/* CONTENT */}

            <div className="route-content">

                <div className="route-title-row">

                    <strong>
                        {title}
                    </strong>

                    <span className="route-code">
                        {code}
                    </span>

                    {isRecommended && (
                        <span
                            style={{
                                padding:
                                    "3px 7px",
                                borderRadius:
                                    "999px",
                                background:
                                    "#12352b",
                                border:
                                    "1px solid #24654c",
                                color:
                                    "#35c98a",
                                fontSize:
                                    "7px",
                                fontWeight:
                                    "900",
                                letterSpacing:
                                    "0.6px",
                            }}
                        >
                            RECOMMENDED
                        </span>
                    )}

                </div>

                <p>
                    {description}
                </p>

                {/* =================================================
                   PHYSICAL PATH
                ================================================= */}

                {path?.length > 0 && (
                    <div
                        className="route-path"
                        title={path.join(
                            " → "
                        )}
                    >

                        <span className="route-path-label">
                            PATH
                        </span>

                        <div className="route-path-nodes">

                            {path.map(
                                (
                                    node,
                                    index
                                ) => (

                                    <div
                                        className="route-path-node-wrapper"
                                        key={`${node}-${index}`}
                                    >

                                        <span
                                            className={`route-path-node ${node.startsWith(
                                                "EXIT_"
                                            )
                                                ? "exit-node"
                                                : node.startsWith(
                                                    "STAIR_"
                                                )
                                                    ? "stair-node"
                                                    : "room-node"
                                                }`}
                                        >
                                            {formatNodeName(
                                                node
                                            )}
                                        </span>

                                        {index <
                                            path.length -
                                            1 && (
                                                <span className="route-path-arrow">
                                                    →
                                                </span>
                                            )}

                                    </div>

                                )
                            )}

                        </div>

                    </div>
                )}

                {distance !==
                    null &&
                    distance !==
                    undefined && (
                        <div className="route-distance">
    ROUTE EDGES{" "}
    <strong>{distance}</strong>
</div>
                    )}

                {connectedZones?.length >
                    0 && (
                        <div className="connected-zones">
                            Zones:{" "}
                            {connectedZones.join(
                                ", "
                            )}
                        </div>
                    )}

            </div>

            {/* RIGHT */}

            <div className="route-right">

                <span
                    className="route-status"
                    style={{
                        color,
                        background:
                            `${color}12`,
                    }}
                >
                    {status}
                </span>

                <span className="route-risk">
                    Risk {riskScore}
                </span>

            </div>

        </div>
    );
}


/* =========================================================
   FORMAT TOPOLOGY NODE
========================================================= */

function formatNodeName(
    node
) {
    if (
        node === "EXIT_A"
    )
        return "EXIT A";

    if (
        node === "EXIT_B"
    )
        return "EXIT B";

    if (
        node === "EXIT_C"
    )
        return "EXIT C";

    if (
        node === "STAIR_A"
    )
        return "STAIR A";

    if (
        node === "STAIR_B"
    )
        return "STAIR B";

    return node;
}


/* =========================================================
   STAT
========================================================= */

function Stat({
    label,
    value,
    color,
}) {
    return (
        <div className="stat">

            <span>
                {label}
            </span>

            <strong
                style={{
                    color:
                        color ||
                        "#f8fafc",
                }}
            >
                {value}
            </strong>

        </div>
    );
}


/* =========================================================
   INFO
========================================================= */

function Info({
    label,
    value,
    green,
}) {
    return (
        <div className="info">

            <span>
                {label}
            </span>

            <strong
                style={{
                    color: green
                        ? "#35c98a"
                        : "#d8e0ea",
                }}
            >
                {green &&
                    "● "}

                {value}

            </strong>

        </div>
    );
}


export default Evacuation;