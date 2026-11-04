import { useNavigate } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";

import {
    getBuildingSummary,
    getEvacuationRoutes,
    getEvents,
    getSensors,
} from "../services/api";

import "./Dashboard.css";


function Dashboard() {
    const [simulationInput, setSimulationInput] = useState(() => {
  try {
    return JSON.parse(localStorage.getItem("simulationInput") || "null");
  } catch {
    return null;
  }
});

    const [sensors, setSensors] = useState([]);
    const [evacuationData, setEvacuationData] = useState(null);
    const [events, setEvents] = useState([]);
    const [buildingSummary, setBuildingSummary] = useState(null);

    const [error, setError] = useState("");
    const [evacuationError, setEvacuationError] = useState("");

    const [lastSync, setLastSync] = useState(null);

    const navigate = useNavigate();
    
const totalOccupancy = sensors.reduce(
    (total, sensor) =>
        total + (Number(sensor.occupancy) || 0),
    0
);



    // =========================================================
    // LIVE DATA
    // =========================================================

// =========================================================
// LIVE DATA
// =========================================================

useEffect(() => {
    let mounted = true;
    let loading = false;

    const loadDashboardData = async () => {
        if (loading) return;

        loading = true;

        try {
            const results = await Promise.allSettled([
                getSensors(),
                getEvents(),
                getEvacuationRoutes(),
                getBuildingSummary(),
            ]);

            if (!mounted) return;

            const [sensorResult, eventResult, evacuationResult, summaryResult] = results;

            if (sensorResult.status === "fulfilled") {
                setSensors(
                    Array.isArray(sensorResult.value)
                        ? sensorResult.value
                        : []
                );
                setError("");
            } else {
                console.error("Sensor API Error:", sensorResult.reason);
                setError("Sensor data temporarily unavailable. Retrying...");
            }

            if (eventResult.status === "fulfilled") {
                setEvents(
                    Array.isArray(eventResult.value)
                        ? eventResult.value
                        : []
                );
            } else {
                console.error("Events API Error:", eventResult.reason);
            }

            if (evacuationResult.status === "fulfilled") {
                setEvacuationData(evacuationResult.value || null);
                setEvacuationError("");
            } else {
                console.error("Evacuation API Error:", evacuationResult.reason);
                setEvacuationError("Evacuation routing temporarily unavailable.");
            }

            if (summaryResult.status === "fulfilled") {
                setBuildingSummary(summaryResult.value || null);
            } else {
                console.error("Building Summary API Error:", summaryResult.reason);
            }

            setLastSync(new Date());
        } finally {
            loading = false;
        }
    };

    loadDashboardData();

    const interval = setInterval(loadDashboardData, 3000);

    return () => {
        mounted = false;
        clearInterval(interval);
    };
}, []);




    // =========================================================
    // HELPERS
    // =========================================================

    const getZoneId = (sensor) => {

        if (!sensor) return "";

        if (
            sensor.zone_id !== undefined &&
            sensor.zone_id !== null
        ) {
            return String(sensor.zone_id);
        }

        if (sensor.device_id) {

            return String(
                sensor.device_id
            ).replace(/^sensor-/, "");

        }

        return "";
    };




const getRiskLevel = (sensor) => {
    if (!sensor) return "LOW";

    const score = getRiskScore(sensor);

    if (score >= 70) return "CRITICAL";
    if (score >= 40) return "HIGH";
    if (score >= 20) return "MODERATE";

    return "LOW";
};





    const getRiskScore = (sensor) => {

        if (!sensor) return 0;

        const value =
            sensor.risk_score ??
            sensor.score ??
            0;

        const numeric = Number(value);

        if (Number.isNaN(numeric)) return 0;

        return Math.max(
            0,
            Math.min(100, numeric)
        );
    };


    const getSensorForZone = (zoneId) => {

        return sensors.find(
            sensor =>
                getZoneId(sensor) ===
                String(zoneId)
        );

    };


    const getRiskClassForZone = (sensor) => {

        if (!sensor) {
            return "room-normal";
        }

        const level = getRiskLevel(sensor);

        if (level === "CRITICAL") {
            return "room-critical";
        }

        if (
            level === "HIGH" ||
            level === "MODERATE"
        ) {
            return "room-warning";
        }

        return "room-normal";
    };



// =========================================================
// LATEST SENSOR
// =========================================================

const latest = useMemo(() => {
    if (!sensors.length) {
        return null;
    }

    return [...sensors].sort((a, b) => {
        const scoreDifference =
            getRiskScore(b) - getRiskScore(a);

        if (scoreDifference !== 0) {
            return scoreDifference;
        }

        return Number(getZoneId(b)) - Number(getZoneId(a));
    })[0];
}, [sensors]);





    // =========================================================
    // ACTIVE EVENT
    // =========================================================




const activeEvent = useMemo(() => {
    const priority = {
        CRITICAL: 4,
        HIGH: 3,
        MODERATE: 2,
        LOW: 1,
    };

    return events
        .filter((event) => {
            const status = String(event.status || "").toUpperCase();
            const score = Number(event.risk_score ?? event.score ?? 0);
            const type = String(event.event_type || "").toUpperCase();

            if (status !== "ACTIVE") return false;

            // Old fire predictions with low risk scores
            // should not automatically become critical alerts.
            if (
                type === "FIRE_ALARM_PREDICTED" &&
                score < 70
            ) {
                return false;
            }

            return true;
        })
        .sort((a, b) => {
            const levelA = String(
                a.level || a.risk_level || a.severity || "LOW"
            ).toUpperCase();

            const levelB = String(
                b.level || b.risk_level || b.severity || "LOW"
            ).toUpperCase();

            return (priority[levelB] || 0) - (priority[levelA] || 0);
        })[0] || null;
}, [events]);

console.log("Selected active event:", activeEvent);


    // =========================================================
    // MOST DANGEROUS SENSOR
    // =========================================================

    const mostDangerousSensor = useMemo(() => {

        if (!sensors.length) {
            return null;
        }

        return [...sensors].sort(
            (a, b) =>
                getRiskScore(b) -
                getRiskScore(a)
        )[0];

    }, [sensors]);



// =========================================================
// FINAL RISK
// =========================================================

const risk = useMemo(() => {

    const buildingRisk = {
        level: String(
            buildingSummary?.risk_level ||
            buildingSummary?.level ||
buildingSummary?.overall_risk ||
"LOW"
        ).toUpperCase(),

        score: Number(
            buildingSummary?.risk_score ??
            buildingSummary?.score ??
            0
        ),
    };

    if (activeEvent) {

        const level = String(
            activeEvent.level ||
            activeEvent.risk_level ||
            ""
        ).toUpperCase();

        const score = Number(
            activeEvent.score ??
            activeEvent.risk_score ??
            0
        );

        return {
            level: level || buildingRisk.level,
            score: activeEvent.score != null ||
                activeEvent.risk_score != null
                ? score
                : buildingRisk.score,

            recommendation:
                activeEvent.recommendation ||
                "Emergency condition detected.",
        };
    }

    return {
        level: buildingRisk.level,
        score: buildingRisk.score,

        recommendation:
            buildingRisk.level === "CRITICAL"
                ? "Immediate evacuation recommended."
                : buildingRisk.level === "HIGH"
                    ? "High-risk conditions detected."
                    : buildingRisk.level === "MODERATE"
                        ? "Elevated conditions detected."
                        : "No significant hazards detected.",
    };

}, [activeEvent, buildingSummary]);


const riskScore = latest
    ? getRiskScore(latest)
    : 0;

const riskLevel = getRiskLevel(latest);


    // =========================================================
    // BUILDING STATUS
    // =========================================================




const buildingStatus = useMemo(() => {
    if (!sensors.length) return "WAITING";

    const levels = sensors.map((sensor) => {
        const score = getRiskScore(sensor);

        if (score >= 70) return "CRITICAL";
        if (score >= 40) return "HIGH";
        if (score >= 20) return "MODERATE";

        return "LOW";
    });

    if (levels.includes("CRITICAL")) return "EVACUATE";
    if (levels.includes("HIGH") || levels.includes("MODERATE")) {
        return "WARNING";
    }

    return "NORMAL";
}, [sensors]);




    // =========================================================
    // RISK CLASS
    // =========================================================

    const getRiskClass = () => {

        if (riskLevel === "CRITICAL") {
            return "critical";
        }

        if (riskLevel === "HIGH") {
            return "high";
        }

        if (riskLevel === "MODERATE") {
            return "moderate";
        }

        return "low";
    };


    // =========================================================
    // SENSOR STATUS
    // =========================================================

    const getTemperatureStatusForSensor = (sensor) => {

        const temperature =
            Number(sensor?.temperature || 0);


        if (temperature >= 40) {
            return "Critical";
        }

        if (temperature >= 38) {
            return "Elevated";
        }

        if (temperature >= 35) {
            return "Moderate";
        }

        return "Stable";
    };


    const getSmokeStatusForSensor = (sensor) => {

        const smoke =
            Number(sensor?.smoke || 0);


        if (smoke >= 0.9) {
            return "Critical";
        }

        if (smoke >= 0.7) {
            return "High";
        }

        if (smoke >= 0.5) {
            return "Moderate";
        }

        return "Normal";
    };


    const getOccupancyStatusForSensor = (sensor) => {

        const occupancy =
            Number(sensor?.occupancy || 0);


        if (occupancy >= 48) {
            return "Critical";
        }

        if (occupancy >= 40) {
            return "High";
        }

        if (occupancy >= 30) {
            return "Moderate";
        }

        return "Normal";
    };


    const getDLConfidence = () => {
    const sensor = mostDangerousSensor || latest;

    if (!sensor) return null;

    const confidence =
        sensor.dl_confidence ??
        sensor.confidence;

    if (
        confidence === undefined ||
        confidence === null ||
        confidence === ""
    ) {
        return null;
    }

    const numeric = Number(confidence);

    if (Number.isNaN(numeric)) return null;

    if (numeric > 0 && numeric <= 1) {
        return Math.round(numeric * 100);
    }

    return Math.round(numeric);
};

const dlConfidence = getDLConfidence();

    // =========================================================
    // EVENT HELPERS
    // =========================================================

    const getEventLevel = (event) => {

        if (!event) {
            return null;
        }


        const explicitLevel =
    event.event_type === "FIRE_ALARM_PREDICTED"
        ? event.severity || "CRITICAL"
        : event.level || event.risk_level || event.severity;


        if (explicitLevel) {

            return String(
                explicitLevel
            ).toUpperCase();
        }


        const score =
            Number(
                event.score ??
                event.risk_score ??
                0
            );


        if (score >= 75) {
            return "CRITICAL";
        }

        if (score >= 60) {
            return "HIGH";
        }

        if (score >= 35) {
            return "MODERATE";
        }

        return "LOW";
    };



const getEventMessage = (event) => {
    if (!event) {
        return "";
    }

    const level = getEventLevel(event);

    if (level === "CRITICAL") {
        return "CRITICAL EMERGENCY! Evacuate the affected area immediately using the recommended route, after confirming the exit is clear.";
    }

    if (level === "HIGH") {
        return "HIGH RISK DETECTED! Avoid the affected zone and follow the recommended evacuation route. Verify that the route is clear.";
    }

    if (level === "MODERATE") {
        return "WARNING! Elevated risk conditions detected. Stay alert and monitor the recommended evacuation route.";
    }

    return (
        event.recommendation ||
        event.message ||
        event.description ||
        "Conditions are currently normal. Continue monitoring live sensor readings."
    );
};




// =========================================================
// LIVE SENSOR EMERGENCIES
// =========================================================



const sensorEmergencies = useMemo(() => {
    return sensors
        .map((sensor) => {
            const score = getRiskScore(sensor);

            let level = "LOW";

            if (score >= 70) level = "CRITICAL";
            else if (score >= 40) level = "HIGH";
            else if (score >= 20) level = "MODERATE";

            return {
                ...sensor,
                level,
                risk_score: score,
                device_id:
                    sensor.device_id ||
                    `sensor-${getZoneId(sensor)}`,
            };
        })
        .filter((sensor) =>
            ["CRITICAL", "HIGH", "MODERATE"].includes(sensor.level)
        )
        .sort((a, b) => b.risk_score - a.risk_score);
}, [sensors]);

const sensorEmergency = sensorEmergencies[0] || null;

const displayEvent = activeEvent || sensorEmergency || null;



const alertZoneId = String(
    displayEvent?.zone_id ??
    displayEvent?.device_id?.replace(/^sensor-/, "") ??
    latest?.zone_id ??
    latest?.device_id?.replace(/^sensor-/, "") ??
    ""
);

const alertZoneRoute = evacuationData?.zones?.find(
    (zone) => String(zone.zone_id) === alertZoneId
);

const recommendedExit =
    alertZoneRoute?.recommended_exit ??
    (!alertZoneId ? evacuationData?.recommended_exit : null);

const alternativeExits =
    alertZoneRoute?.alternative_exits ??
    (!alertZoneId ? evacuationData?.alternative_exits : []) ??
    [];




    // =========================================================
    // TIME
    // =========================================================

    const formatTime = (date) => {

        if (!date) {
            return "--:--:--";
        }


        try {

            return new Date(
                date
            ).toLocaleTimeString(
                [],
                {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                }
            );

        } catch {

            return "--:--:--";
        }
    };


    // =========================================================
    // BUILDING ALPHA
    // =========================================================

    const floors = [
        {
            floor: 3,
            zones: [
                "301",
                "302",
                "303",
                "304",
            ],
        },
        {
            floor: 2,
            zones: [
                "201",
                "202",
                "203",
                "204",
            ],
        },
        {
            floor: 1,
            zones: [
                "101",
                "102",
                "103",
                "104",
            ],
        },
    ];


    // =========================================================
    // LOADING
    // =========================================================

    if (!latest && !error) {

        return (

            <div className="dashboard">

                <header className="dashboard-topbar">

                    <div>

                        <p className="dashboard-eyebrow">
                            DIGITAL TWIN / COMMAND CENTER
                        </p>

                        <h1>
                            Building Overview
                        </h1>

                    </div>


                    <div className="dashboard-live-status">

                        <span className="dashboard-live-dot"></span>

                        <strong>
                            LIVE
                        </strong>

                        <span className="dashboard-divider"></span>

                        Synchronizing sensors...

                    </div>

                </header>


                <div className="dashboard-loading">

                    <div className="loading-ring"></div>

                    <h2>
                        Connecting to Digital Twin
                    </h2>

                    <p>
                        Waiting for live virtual sensor data...
                    </p>

                </div>

            </div>
        );
    }


    // =========================================================
    // MAIN
    // =========================================================

    return (

        <div className="dashboard">


            {/* HEADER */}

            <header className="dashboard-topbar">

                <div>

                    <p className="dashboard-eyebrow">
                        DIGITAL TWIN / COMMAND CENTER
                    </p>

                    <h1>
                        Building Overview
                    </h1>

                </div>


                <div
                    className={`dashboard-live-status ${buildingStatus !== "NORMAL"
                        ? "warning-status"
                        : ""
                        }`}
                >

                    <span className="dashboard-live-dot"></span>

                    <strong>
                        LIVE
                    </strong>

                    <span className="dashboard-divider"></span>

                    {buildingStatus === "NORMAL"
                        ? "All systems normal"
                        : buildingStatus === "WARNING"
                            ? "Elevated conditions detected"
                            : buildingStatus === "EVACUATE"
                                ? "Emergency conditions"
                                : "Waiting for sensor data"
                    }

                </div>

            </header>


            {/* ERRORS */}

            {error && (
                <div className="dashboard-error">
                    ⚠️ {error}
                </div>
            )}


            {evacuationError && (
                <div className="dashboard-error">
                    ⚠️ {evacuationError}
                </div>
            )}


{/* SIMULATION RESULT */}
{simulationInput && (
    <section className="dashboard-panel simulation-panel">
        <div className="simulation-header">
            <div>
                <span className="panel-label">
                    
                </span>
                <h2>Latest Simulation Result</h2>
                <p>Scenario analysis · Zone {simulationInput.zone_id}</p>
            </div>

            <span className="simulation-badge">
                {simulationInput.risk_level || "SIMULATED"}
            </span>
        </div>

        <div className="simulation-grid">
            <div className="simulation-metric">
                <span>Temperature</span>
                <strong>{simulationInput.temperature}°C</strong>
            </div>

            <div className="simulation-metric">
                <span>Smoke Level</span>
                <strong>{simulationInput.smoke}</strong>
            </div>

            <div className="simulation-metric">
                <span>Occupancy</span>
                <strong>{simulationInput.occupancy}</strong>
            </div>

            <div className="simulation-metric">
                <span>Risk Score</span>
                <strong>
                    {simulationInput.risk_score ?? "--"}
                    {simulationInput.risk_score != null ? "/100" : ""}
                </strong>
            </div>
        </div>
    </section>
)}

            {/* =================================================
                EMERGENCY ALERT
            ================================================= */}

            {displayEvent && (

                <section className="emergency-alert">

                    


                    <div className="emergency-alert-content">

                        <span className="emergency-alert-label">

                            {activeEvent
                                ? "ACTIVE EMERGENCY EVENT"
                                : "LIVE SENSOR ALERT"
                            }

                        </span>


<h2>
    {displayEvent.event_type === "FIRE_ALARM_PREDICTED"
        ? "FIRE ALARM DETECTED"
        : `${getEventLevel(displayEvent)} RISK DETECTED`}
</h2>


                        <p>
                            {getEventMessage(
                                displayEvent
                            )}
                        </p>


                        <div className="emergency-alert-meta">

                            <span>
                                Zone:
                                <strong>
                                    {" "}
                                    {displayEvent.device_id ||
    (displayEvent.zone_id != null
        ? `sensor-${displayEvent.zone_id}`
        : latest?.device_id) ||
    "--"}
                                </strong>
                            </span>


                            <span>
                                Risk Score:
                                <strong>
                                    {" "}
                                    {displayEvent.score ??
                                        displayEvent.risk_score ??
                                        riskScore
                                    }
                                    /100
                                </strong>
                            </span>


                            <span>
                                Temperature:
                                <strong>
                                    {" "}
                                    {displayEvent.temperature ??
                                        latest?.temperature ??
                                        "--"
                                    }°C
                                </strong>
                            </span>


                            <span>
                                Smoke:
                                <strong>
                                    {" "}
                                    {displayEvent.smoke ??
                                        latest?.smoke ??
                                        "--"
                                    }
                                </strong>
                            </span>


                            <span>
                                Occupancy:
                                <strong>
                                    {" "}
                                    {displayEvent.occupancy ??
                                        latest?.occupancy ??
                                        "--"
                                    }
                                </strong>
                            </span>
</div>

{/* RECOMMENDED EVACUATION ROUTE */}
{recommendedExit && (
    <div className="recommended-route-panel">
        <h3>RECOMMENDED EVACUATION ROUTE</h3>

        <p>
            <strong>Recommended Exit: </strong>
            {recommendedExit.exit} — {recommendedExit.name}
        </p>

        <p>
            <strong>Status: </strong>
            {recommendedExit.status}
        </p>

        <p>
            <strong>Safe Route: </strong>
            {(recommendedExit.path || []).join(" → ")}
        </p>

        {alternativeExits.map((exit) => (
            <p key={exit.exit}>
                <strong>Alternative Exit: </strong>
                {exit.exit} — {exit.name}
            </p>
        ))}
    </div>
)}

</div>


<button
    className="emergency-alert-button"
    onClick={() => {
        if (alertZoneId) {
            localStorage.setItem(
                "selectedZone",
                String(alertZoneId)
            );
        }

        navigate("/evacuation");
    }}
>
    EVACUATION CONTROL →
</button>


                </section>
            )}


            {/* =================================================
                ALL AFFECTED ZONES — every HIGH / CRITICAL /
                MODERATE zone shown as a separate alert card.
            ================================================= */}

            {sensorEmergencies.length >= 1 && (
                <section className="affected-zones-section">

                    <div className="affected-zones-header">
                        <span className="affected-zones-label">AFFECTED ZONES</span>
                        <span className="affected-zones-count">
                            {sensorEmergencies.length} zone{sensorEmergencies.length !== 1 ? "s" : ""} require attention
                        </span>
                    </div>

                    <div className="affected-zones-grid">
                        {sensorEmergencies.map((sensor) => {
                            const zid = getZoneId(sensor);
                            const level = getRiskLevel(sensor);
                            const score = getRiskScore(sensor);
                            const levelClass =
                                level === "CRITICAL" ? "az-critical"
                                : level === "HIGH"   ? "az-high"
                                : "az-moderate";
                            return (
                                <div
                                    key={`az-${zid}`}
                                    className={`affected-zone-card ${levelClass}`}
                                >
                                    <div className="az-card-top">
                                        <span className="az-zone-id">Zone {zid}</span>
                                        <span className={`az-badge ${levelClass}`}>{level}</span>
                                    </div>

                                    <div className="az-score-bar-wrapper">
                                        <div
                                            className={`az-score-bar-fill ${levelClass}`}
                                            style={{ width: `${score}%` }}
                                        />
                                        <span className="az-score-label">{score}/100</span>
                                    </div>

                                    <div className="az-readings">
                                        <span>🌡️ {sensor.temperature !== undefined ? `${Number(sensor.temperature).toFixed(1)}°C` : "--"}</span>
                                        <span>💨 Smoke {sensor.smoke !== undefined ? Number(sensor.smoke).toFixed(3) : "--"}</span>
                                        <span>👥 {sensor.occupancy ?? "--"} people</span>
                                    </div>

                                    {sensor.recommendation && (
                                        <p className="az-recommendation">
                                            {sensor.recommendation}
                                        </p>
                                    )}

                                    {sensor.timestamp && (
                                        <span className="az-timestamp">
                                            Updated: {formatTime(sensor.timestamp)}
                                        </span>
                                    )}

                                    {sensor.fire_alarm_dl_prediction === 1 && (
    <span className="az-fire-badge">🔥 FIRE MODEL ALERT</span>
)}
                                </div>
                            );
                        })}
                    </div>

                </section>
            )}


            {/* =================================================
                STATS
            ================================================= */}

            <section className="stats-grid">


                <div className="stat-card">

                    <span className="stat-label">
                        BUILDING STATUS
                    </span>

                    <strong
                        className={
                            buildingStatus === "NORMAL"
                                ? "safe-text"
                                : buildingStatus === "WARNING"
                                    ? "warning-text"
                                    : "critical-text"
                        }
                    >
                        {buildingStatus}
                    </strong>

                    <span className="stat-description">

                        {buildingStatus === "NORMAL"
                            ? "No active emergencies"
                            : buildingStatus === "WARNING"
                                ? "Attention required"
                                : buildingStatus === "EVACUATE"
                                    ? "Immediate action required"
                                    : "Waiting for sensor data"
                        }

                    </span>

                </div>


                <div className="stat-card">

                    <span className="stat-label">
                        TOTAL OCCUPANCY
                    </span>

                    <strong>
                        {totalOccupancy}
                    </strong>

                    <span className="stat-description">
                        People across monitored zones
                    </span>

                </div>


                <div className="stat-card">

                    <span className="stat-label">
                        ACTIVE SENSORS
                    </span>

                    <strong>
                        {sensors.length} / {
                            buildingSummary?.total_zones ??
                            floors.reduce(
                                (total, floor) =>
                                    total + floor.zones.length,
                                0
                            )
                        }
                    </strong>

                    <span className="stat-description">
                        Virtual zones responding
                    </span>

                </div>


                <div className="stat-card">
    <span className="stat-label">
        AI RISK SCORE
    </span>

    <strong
    className={
        (mostDangerousSensor?.dl_prediction || "LOW") === "LOW"
            ? "safe-text"
            : (mostDangerousSensor?.dl_prediction || "").toUpperCase() === "MODERATE"
                ? "warning-text"
                : "critical-text"
    }
>
    {mostDangerousSensor?.risk_score ?? riskScore}%
</strong>

<span className="stat-description">
    {mostDangerousSensor?.dl_prediction || "No prediction"} predicted risk
</span>
</div>

            </section>


            {/* =================================================
                MAIN GRID
            ================================================= */}

            <section className="dashboard-main-grid">


                {/* =================================================
                    BUILDING ALPHA
                ================================================= */}

                <div className="dashboard-panel twin-panel">

                    <div className="panel-header">

                        <div>

                            <span className="panel-label">
                                LIVE DIGITAL TWIN
                            </span>

                            <h2>
                                Building Alpha
                            </h2>

                        </div>


                        <button
                            className="panel-button"
                            onClick={() =>
                                navigate("/monitoring")
                            }
                        >
                            Open Monitoring →
                        </button>

                    </div>


                    <div className="building-view">

                        <div
                            className={`building ${getRiskClass()}`}
                        >

                            {floors.map(
                                ({
                                    floor,
                                    zones,
                                }) => (

                                    <div
                                        key={floor}
                                        className="building-floor"
                                    >

                                        <div className="floor-label">

                                            FLOOR

                                            <b>
                                                0{floor}
                                            </b>

                                        </div>


                                        <div className="rooms">

                                            {zones.map(
                                                zoneId => {

                                                    const sensor =
                                                        getSensorForZone(
                                                            zoneId
                                                        );

                                                    const score =
                                                        getRiskScore(
                                                            sensor
                                                        );

                                                    const level =
                                                        getRiskLevel(
                                                            sensor
                                                        );


                                                    return (

                                                        <div
                                                            key={zoneId}
                                                            className={`building-room ${getRiskClassForZone(
                                                                sensor
                                                            )}`}
                                                            title={
                                                                sensor
                                                                    ? `Zone ${zoneId} • ${level} • Risk ${score}% • ${sensor.temperature ?? "--"}°C • Occupancy ${sensor.occupancy ?? "--"}`
                                                                    : `Zone ${zoneId} • No sensor data`
                                                            }
                                                        >

                                                            <div className="room-info">

                                                                <strong>
                                                                    {zoneId}
                                                                </strong>

                                                                {sensor && (
                                                                    <span>
                                                                        {score.toFixed(1)}%
                                                                    </span>
                                                                )}

                                                            </div>

                                                        </div>

                                                    );

                                                }
                                            )}

                                        </div>

                                    </div>

                                )
                            )}

                        </div>


                        <div className="building-meta">

                            <span>
                                {buildingSummary?.building_id
                                    ? String(
                                        buildingSummary.building_id
                                    ).toUpperCase()
                                    : "BUILDING ALPHA"
                                }
                            </span>

                            <span>
                                {buildingSummary?.total_zones ??
                                    floors.reduce(
                                        (total, floor) =>
                                            total + floor.zones.length,
                                        0
                                    )
                                } monitored zones
                            </span>

                        </div>


                        <div className="twin-sync">

                            <span className="sync-pulse"></span>

                            DIGITAL TWIN SYNCHRONIZED

                        </div>

                    </div>

                </div>


                {/* =================================================
                    AI RISK
                ================================================= */}

                <div className="dashboard-panel risk-panel">

                    <div className="panel-header">

                        <div>

                            <span className="panel-label">
                                AI INTELLIGENCE
                            </span>

                            <h2>
                                Risk Analysis
                            </h2>

                        </div>

                    </div>


                    <div
                        className={`risk-circle ${getRiskClass()}`}
                    >

                        <strong>
                            {riskScore}%
                        </strong>

                        <span>
                            {riskLevel}
                        </span>

                    </div>


                    <div className="risk-details">

                        <div className="risk-row">
    <span>DL prediction</span>
    <strong>
        {mostDangerousSensor?.dl_prediction || "NO PREDICTION"}
    </strong>
</div>

<div className="risk-row">
    <span>DL confidence</span>
    <strong>
        {dlConfidence !== null
            ? `${dlConfidence}%`
            : "Unavailable"}
    </strong>
</div>

                        <div className="risk-row">

                            <span>
                                Temperature
                            </span>

                            <strong>

                                {mostDangerousSensor
                                    ? getTemperatureStatusForSensor(
                                        mostDangerousSensor
                                    )
                                    : "Waiting"
                                }

                            </strong>

                        </div>


                        <div className="risk-row">

                            <span>
                                Smoke levels
                            </span>

                            <strong>

                                {mostDangerousSensor
                                    ? getSmokeStatusForSensor(
                                        mostDangerousSensor
                                    )
                                    : "Waiting"
                                }

                            </strong>

                        </div>


                        <div className="risk-row">

                            <span>
                                Occupancy load
                            </span>

                            <strong>

                                {mostDangerousSensor
                                    ? getOccupancyStatusForSensor(
                                        mostDangerousSensor
                                    )
                                    : "Waiting"
                                }

                            </strong>

                        </div>

                    </div>


                    <button
                        className="ai-button"
                        onClick={() =>
                            navigate("/ai-insights")
                        }
                    >
                        View AI Insights →
                    </button>

                </div>

            </section>


            {/* =================================================
                SENSOR OVERVIEW
            ================================================= */}

            <section className="sensor-overview">

                <div className="panel-header">

                    <div>

                        <span className="panel-label">
                            ENVIRONMENT MONITOR
                        </span>

                        <h2>
                            Current Sensor Conditions
                        </h2>

                    </div>


                    <span className="sensor-device">

                        {latest?.device_id ||
                            "LIVE SENSOR NETWORK"
                        }

                    </span>

                </div>


                <div className="dashboard-sensor-grid">


                    <div className="dashboard-sensor-card">

                        <span className="dashboard-sensor-icon">
                            🌡️
                        </span>

                        <div>

                            <span>
                                TEMPERATURE
                            </span>

                            <strong>
                                {latest?.temperature ?? "--"}°C
                            </strong>

                        </div>

                    </div>


                    <div className="dashboard-sensor-card">

                        <span className="dashboard-sensor-icon">
                            💧
                        </span>

                        <div>

                            <span>
                                HUMIDITY
                            </span>

                            <strong>
                                {latest?.humidity ?? "--"}%
                            </strong>

                        </div>

                    </div>


                    <div className="dashboard-sensor-card">

                        <span className="dashboard-sensor-icon">
                            💨
                        </span>

                        <div>

                            <span>
                                SMOKE LEVEL
                            </span>

                            <strong>
                                {latest?.smoke ?? "--"}
                            </strong>

                        </div>

                    </div>


                    <div className="dashboard-sensor-card">

                        <span className="dashboard-sensor-icon">
                            👥
                        </span>

                        <div>

                            <span>
                                OCCUPANCY
                            </span>

                            <strong>
                                {latest?.occupancy ?? "--"}
                            </strong>

                        </div>

                    </div>

                </div>

            </section>


            {/* =================================================
                BOTTOM GRID
            ================================================= */}

            <section className="dashboard-bottom-grid">


                {/* EVENTS */}

                <div className="dashboard-panel activity-panel">

                    <div className="panel-header">

                        <div>

                            <span className="panel-label">
                                EVENT MONITOR
                            </span>

                            <h2>
                                Recent Activity
                            </h2>

                        </div>


                       {events.some(
    event => String(event.status || "").toUpperCase() === "ACTIVE"
) && (

                            <span className="sensor-device">

                                {events.filter(
    event => String(event.status || "").toUpperCase() === "ACTIVE"
).length} ACTIVE EVENTS

                            </span>

                        )}

                    </div>


                    {displayEvent ? (

                        <div className="event-row">

                            <span
                                className={
                                    getEventLevel(
                                        displayEvent
                                    ) === "CRITICAL"
                                        ? "event-indicator danger"
                                        : "event-indicator warning"
                                }
                            ></span>


                            <div>

                                <strong>
                                    {getEventLevel(
                                        displayEvent
                                    )} risk event
                                </strong>

                                <span>
                                    {getEventMessage(
                                        displayEvent
                                    )}
                                </span>

                            </div>


                            <time>
                                {formatTime(
                                    displayEvent.timestamp
                                )}
                            </time>

                        </div>

                    ) : !events.some(
    event => String(event.status || "").toUpperCase() === "ACTIVE"
) ? (

                        <div className="no-events">

                            <span className="no-events-icon">
                                ✓
                            </span>

                            <div>

                                <strong>
                                    No active emergency events
                                </strong>

                                <span>
                                    Building systems are being monitored
                                </span>

                            </div>

                        </div>

                    ) : (

    events
        .filter(
            event =>
                String(event.status || "").toUpperCase() === "ACTIVE"
        )
        .slice(0, 4)
        .map((event, index) => {

            const level = getEventLevel(event);

            return (
                <div
                    className="event-row"
                    key={`${event.timestamp || "event"}-${index}`}
                >
                    <span
                        className={
                            level === "CRITICAL"
                                ? "event-indicator danger"
                                : level === "HIGH" ||
                                  level === "MODERATE"
                                    ? "event-indicator warning"
                                    : "event-indicator safe"
                        }
                    ></span>

                    <div>
                        <strong>{level} risk event</strong>
                        <span>{getEventMessage(event)}</span>
                    </div>

                    <time>{formatTime(event.timestamp)}</time>
                </div>
            );
        })

)}

                </div>


                {/* QUICK ACTION */}

                <div className="dashboard-panel quick-panel">

                    <span className="panel-label">
                        QUICK ACTION
                    </span>


                    <h2>
                        Emergency Simulation
                    </h2>


                    <p>
                        Test how the Digital Twin
                        responds to different
                        emergency scenarios.
                    </p>


                    <button
                        className="simulation-button"
                        onClick={() =>
                            navigate("/simulation")
                        }
                    >
                        Start Simulation →
                    </button>


                    <button
                        className="evacuation-button"
                        onClick={() =>
                            navigate("/evacuation")
                        }
                    >
                        Open Evacuation Control →
                    </button>

                </div>

            </section>


            {/* FOOTER */}

            <footer className="dashboard-footer">

                <span>

                    <i className="footer-live-dot"></i>

                    Digital Twin synchronized

                </span>


                <span>

                    Last sync:

                    {" "}

                    <strong>
                        {formatTime(lastSync)}
                    </strong>

                </span>


                <span>
                    Auto-refresh: 3 seconds
                </span>

            </footer>

        </div>
    );
}


export default Dashboard;