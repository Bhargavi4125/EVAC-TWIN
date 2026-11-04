import { useEffect, useMemo, useState } from "react";

import {
    CartesianGrid,
    Line,
    LineChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";

import {
    getSensorHistory,
    getSensors,
} from "../services/api";

import {
    calculateRisk,
    getRiskBackground,
    getRiskColor,
} from "../utils/riskEngine";

import "./Monitoring.css";


function Monitoring() {

    const [sensors, setSensors] = useState([]);
    const [history, setHistory] = useState([]);

    const [selectedZone, setSelectedZone] = useState("");
    const [dropdownOpen, setDropdownOpen] = useState(false);

    const [error, setError] = useState("");
    const [loading, setLoading] = useState(true);


    /* =========================================================
       GET ZONE ID
    ========================================================= */

    function getZoneId(sensor) {

        if (!sensor) {
            return "";
        }

        if (
            sensor.zone_id !== undefined &&
            sensor.zone_id !== null
        ) {
            return String(sensor.zone_id);
        }

        if (sensor.device_id) {
            return String(sensor.device_id).replace(
                /^sensor-/,
                ""
            );
        }

        return "";
    }


    /* =========================================================
       LOAD LIVE SENSOR DATA
       Polls independently every 3 seconds
    ========================================================= */

    useEffect(() => {

        let mounted = true;

        const loadLiveSensors = async () => {

            try {

                const latestData = await getSensors();

                if (!mounted) {
                    return;
                }

                const latestList =
                    Array.isArray(latestData)
                        ? latestData
                        : [];

                setSensors(latestList);
                setError("");
                setLoading(false);

                /*
                 * Select the first available zone only
                 * when no zone is currently selected.
                 */
                setSelectedZone(previousZone => {

                    if (
                        previousZone ||
                        latestList.length === 0
                    ) {
                        return previousZone;
                    }

                    return getZoneId(
                        latestList[0]
                    );
                });

            } catch (err) {

                console.error(
                    "Monitoring sensor error:",
                    err
                );

                if (mounted) {

                    setError(
                        "Unable to connect to EVAC-TWIN backend."
                    );

                    setLoading(false);
                }
            }
        };


        loadLiveSensors();


        const interval = setInterval(
            loadLiveSensors,
            3000
        );


        return () => {

            mounted = false;

            clearInterval(interval);

        };

    }, []);


    /* =========================================================
       LOAD HISTORY FOR SELECTED ZONE
    ========================================================= */

    useEffect(() => {

        if (!selectedZone) {
            return;
        }

        let mounted = true;

        const loadHistory = async () => {

            try {

                const historyData =
                    await getSensorHistory(
                        selectedZone,
                        100
                    );

                if (!mounted) {
                    return;
                }

                setHistory(
                    Array.isArray(historyData)
                        ? historyData
                        : []
                );

            } catch (err) {

                console.error(
                    "Sensor history error:",
                    err
                );

            }
        };


        loadHistory();


        const interval = setInterval(
            loadHistory,
            3000
        );


        return () => {

            mounted = false;

            clearInterval(interval);

        };

    }, [selectedZone]);


    /* =========================================================
       SORT ZONES
    ========================================================= */

    const zoneSensors = useMemo(() => {

        return [...sensors].sort(
            (a, b) =>
                Number(getZoneId(a)) -
                Number(getZoneId(b))
        );

    }, [sensors]);


    /* =========================================================
       SELECTED SENSOR
    ========================================================= */

    const latest = useMemo(() => {

        if (!zoneSensors.length) {
            return null;
        }

        const found =
            zoneSensors.find(
                sensor =>
                    getZoneId(sensor) ===
                    String(selectedZone)
            );

        return found || zoneSensors[0];

    }, [
        zoneSensors,
        selectedZone,
    ]);


    /* =========================================================
       CURRENT ZONE
    ========================================================= */

    const currentZone =
        latest
            ? getZoneId(latest)
            : selectedZone;


    /* =========================================================
       CENTRALIZED RISK ENGINE
    ========================================================= */

    const risk = useMemo(() => {

        return calculateRisk(latest);

    }, [latest]);


    /* =========================================================
       HISTORY FOR SELECTED ZONE
    ========================================================= */

    const selectedZoneHistory = useMemo(() => {

        return history
            .filter(
                sensor =>
                    getZoneId(sensor) ===
                    String(currentZone)
            )
            .sort(
                (a, b) =>
                    new Date(
                        a.timestamp || 0
                    ) -
                    new Date(
                        b.timestamp || 0
                    )
            );

    }, [
        history,
        currentZone,
    ]);


    /* =========================================================
       CHART DATA
    ========================================================= */

    const chartData = useMemo(() => {

        return selectedZoneHistory
            .slice(-20)
            .map(sensor => ({

                time:
                    sensor.timestamp
                        ? new Date(
                            sensor.timestamp
                        ).toLocaleTimeString()
                        : "--",

                temperature:
                    Number(
                        sensor.temperature || 0
                    ),

                humidity:
                    Number(
                        sensor.humidity || 0
                    ),

                smoke:
                    Number(
                        sensor.smoke || 0
                    ),

                occupancy:
                    Number(
                        sensor.occupancy || 0
                    ),

            }));

    }, [
        selectedZoneHistory,
    ]);


    /* =========================================================
       SENSOR STATUS
    ========================================================= */

    const temperatureStatus =
        !latest
            ? "WAITING"
            : Number(latest.temperature) >= 40
                ? "CRITICAL"
                : Number(latest.temperature) >= 38
                    ? "HIGH"
                    : Number(latest.temperature) >= 35
                        ? "MODERATE"
                        : "NORMAL";


    const smokeStatus =
        !latest
            ? "WAITING"
            : Number(latest.smoke) >= 0.8
                ? "CRITICAL"
                : Number(latest.smoke) >= 0.5
                    ? "HIGH"
                    : Number(latest.smoke) >= 0.3
                        ? "MODERATE"
                        : "NORMAL";


    const occupancyStatus =
        !latest
            ? "WAITING"
            : Number(latest.occupancy) >= 45
                ? "CRITICAL"
                : Number(latest.occupancy) >= 30
                    ? "HIGH"
                    : Number(latest.occupancy) >= 15
                        ? "MODERATE"
                        : "NORMAL";


    /* =========================================================
       LOADING
    ========================================================= */

    if (loading) {

        return (

            <div className="monitoring-page">

                <div className="monitoring-loading">

                    <div className="loading-spinner" />

                    <h2>
                        Connecting to EVAC-TWIN
                    </h2>

                    <p>
                        Waiting for live sensor data...
                    </p>

                </div>

            </div>

        );
    }


    /* =========================================================
       MAIN RENDER
    ========================================================= */

    return (

        <div className="monitoring-page">


            {/* =================================================
               HEADER
            ================================================= */}

            <header className="monitoring-header">

                <div>

                    <span className="monitoring-eyebrow">
                        COMMAND CENTER / LIVE MONITORING
                    </span>

                    <h1>
                        Live Monitoring
                    </h1>

                    <p>
                        Real-time virtual IoT sensor monitoring
                    </p>

                </div>


                <div
                    className="monitoring-status"
                    style={{
                        color:
                            getRiskColor(
                                risk.level
                            ),

                        background:
                            getRiskBackground(
                                risk.level
                            ),
                    }}
                >

                    <span>●</span>

                    {risk.level}

                </div>

            </header>


            {/* =================================================
               ERROR
            ================================================= */}

            {error && (

                <div className="monitoring-error">

                    ⚠️ {error}

                </div>

            )}


            {latest && (

                <>


                    {/* =================================================
                       ZONE SELECTOR
                    ================================================= */}

                    <section className="zone-selector-card">

                        <div>

                            <span className="section-label">
                                BUILDING ALPHA
                            </span>

                            <h2>
                                Monitoring Zones
                            </h2>

                            <p className="zone-count">
                                {zoneSensors.length} / 12 zones online
                            </p>

                        </div>


                        <div className="zone-dropdown-wrapper">


                            <button
                                className="zone-dropdown-button"
                                onClick={() =>
                                    setDropdownOpen(
                                        previous =>
                                            !previous
                                    )
                                }
                            >

                                <span className="selected-zone-content">

                                    <strong>
                                        {currentZone}
                                    </strong>

                                    <span
                                        className="zone-risk-dot"
                                        style={{
                                            background:
                                                getRiskColor(
                                                    risk.level
                                                ),
                                        }}
                                    />

                                    <span
                                        style={{
                                            color:
                                                getRiskColor(
                                                    risk.level
                                                ),
                                        }}
                                    >
                                        {risk.level}
                                    </span>

                                </span>


                                <span
                                    className={`dropdown-arrow ${dropdownOpen
                                        ? "open"
                                        : ""
                                        }`}
                                >
                                    ▼
                                </span>

                            </button>


                            {dropdownOpen && (

                                <div className="zone-dropdown-menu">

                                    {zoneSensors.map(
                                        sensor => {

                                            const zone =
                                                getZoneId(
                                                    sensor
                                                );

                                            const zoneRisk =
                                                calculateRisk(
                                                    sensor
                                                );

                                            const selected =
                                                zone ===
                                                String(
                                                    currentZone
                                                );


                                            return (

                                                <button
                                                    key={zone}
                                                    className={`zone-option ${selected
                                                        ? "selected"
                                                        : ""
                                                        }`}
                                                    onClick={() => {

                                                        setSelectedZone(
                                                            zone
                                                        );

                                                        setDropdownOpen(
                                                            false
                                                        );

                                                    }}
                                                >

                                                    <span>
                                                        Zone {zone}
                                                    </span>


                                                    <span className="zone-option-risk">

                                                        <i
                                                            style={{
                                                                background:
                                                                    getRiskColor(
                                                                        zoneRisk.level
                                                                    ),
                                                            }}
                                                        />

                                                        <span
                                                            style={{
                                                                color:
                                                                    getRiskColor(
                                                                        zoneRisk.level
                                                                    ),
                                                            }}
                                                        >
                                                            {zoneRisk.level}
                                                        </span>

                                                    </span>

                                                </button>

                                            );

                                        }
                                    )}

                                </div>

                            )}

                        </div>

                    </section>


                    {/* =================================================
                       CONNECTION
                    ================================================= */}

                    <div className="monitoring-info-bar">

                        <span>

                            <b className="online-dot">
                                ●
                            </b>

                            Sensor connection active

                        </span>


                        <span>
                            🆔 {latest.device_id || "--"}
                        </span>


                        <span>
                            📍 Zone {currentZone || "--"}
                        </span>


                        <span>

                            🕐{" "}

                            {latest.timestamp
                                ? new Date(
                                    latest.timestamp
                                ).toLocaleString()
                                : "--"
                            }

                        </span>

                    </div>


                    {/* =================================================
                       RISK
                    ================================================= */}

                    <section
                        className="zone-risk-summary"
                        style={{
                            borderColor:
                                getRiskColor(
                                    risk.level
                                ),
                        }}
                    >

                        <div>

                            <span className="section-label">
                                ZONE RISK
                            </span>

                            <h2
                                style={{
                                    color:
                                        getRiskColor(
                                            risk.level
                                        ),
                                }}
                            >
                                {risk.level}
                            </h2>

                            <p>

                                {risk.level === "LOW"

                                    ? "Environmental conditions are stable. Continue normal monitoring."

                                    : risk.level === "MODERATE"

                                        ? "Elevated environmental conditions detected. Continue close monitoring."

                                        : risk.level === "HIGH"

                                            ? "High-risk conditions detected. Prepare for evacuation."

                                            : risk.level === "CRITICAL"

                                                ? "Critical conditions detected. Immediate evacuation may be required."

                                                : "Waiting for sensor data."

                                }

                            </p>

                        </div>


                        <div className="risk-score-display">

                            <strong>
                                {risk.score}
                            </strong>

                            <span>
                                / 100
                            </span>

                            <small>
                                RISK SCORE
                            </small>

                        </div>

                    </section>


                    {/* =================================================
                       SENSOR CARDS
                    ================================================= */}

                    <section className="sensor-section">

                        <div className="section-heading">

                            <div>

                                <span className="section-label">
                                    ENVIRONMENT MONITOR
                                </span>

                                <h2>
                                    Current Conditions
                                </h2>

                            </div>

                            <span className="live-label">
                                ● LIVE
                            </span>

                        </div>


                        <div className="monitoring-sensor-grid">


                            <SensorCard
                                icon="🌡️"
                                label="Temperature"
                                value={`${latest.temperature ?? "--"} °C`}
                                status={
                                    temperatureStatus
                                }
                                color={
                                    getRiskColor(
                                        temperatureStatus ===
                                            "NORMAL"
                                            ? "LOW"
                                            : temperatureStatus
                                    )
                                }
                            />


                            <SensorCard
                                icon="💧"
                                label="Humidity"
                                value={`${latest.humidity ?? "--"} %`}
                                status="NORMAL"
                                color="#35c98a"
                            />


                            <SensorCard
                                icon="💨"
                                label="Smoke Level"
                                value={
                                    latest.smoke ?? "--"
                                }
                                status={
                                    smokeStatus
                                }
                                color={
                                    getRiskColor(
                                        smokeStatus ===
                                            "NORMAL"
                                            ? "LOW"
                                            : smokeStatus
                                    )
                                }
                            />


                            <SensorCard
                                icon="👥"
                                label="Occupancy"
                                value={
                                    latest.occupancy ?? "--"
                                }
                                status={
                                    occupancyStatus
                                }
                                color={
                                    getRiskColor(
                                        occupancyStatus ===
                                            "NORMAL"
                                            ? "LOW"
                                            : occupancyStatus
                                    )
                                }
                            />

                        </div>

                    </section>


                    {/* =================================================
                       TEMPERATURE CHART
                    ================================================= */}

                    <section className="chart-card">

                        <div className="chart-heading">

                            <h2>
                                🌡️ Temperature Trend
                            </h2>

                            <span>
                                Zone {currentZone}
                            </span>

                        </div>


                        <ResponsiveContainer
                            width="100%"
                            height={280}
                        >

                            <LineChart
                                data={chartData}
                            >

                                <CartesianGrid
                                    strokeDasharray="3 3"
                                    stroke="#26364d"
                                />

                                <XAxis
                                    dataKey="time"
                                    stroke="#64748b"
                                />

                                <YAxis
                                    stroke="#64748b"
                                />

                                <Tooltip
                                    contentStyle={{
                                        background:
                                            "#111827",

                                        border:
                                            "1px solid #334155",

                                        color:
                                            "#f8fafc",
                                    }}
                                />

                                <Line
                                    type="monotone"
                                    dataKey="temperature"
                                    stroke="#f97316"
                                    strokeWidth={3}
                                    dot={false}
                                    isAnimationActive={false}
                                />

                            </LineChart>

                        </ResponsiveContainer>

                    </section>


                    {/* =================================================
                       SMOKE + OCCUPANCY
                    ================================================= */}

                    <div className="monitoring-chart-grid">


                        <section className="chart-card">

                            <h2>
                                💨 Smoke Level
                            </h2>

                            <ResponsiveContainer
                                width="100%"
                                height={250}
                            >

                                <LineChart
                                    data={chartData}
                                >

                                    <CartesianGrid
                                        strokeDasharray="3 3"
                                        stroke="#26364d"
                                    />

                                    <XAxis
                                        dataKey="time"
                                        stroke="#64748b"
                                    />

                                    <YAxis
                                        domain={[0, 1]}
                                        stroke="#64748b"
                                    />

                                    <Tooltip
                                        contentStyle={{
                                            background:
                                                "#111827",

                                            border:
                                                "1px solid #334155",

                                            color:
                                                "#f8fafc",
                                        }}
                                    />

                                    <Line
                                        type="monotone"
                                        dataKey="smoke"
                                        stroke="#ef4444"
                                        strokeWidth={3}
                                        dot={false}
                                        isAnimationActive={false}
                                    />

                                </LineChart>

                            </ResponsiveContainer>

                        </section>


                        <section className="chart-card">

                            <h2>
                                👥 Occupancy
                            </h2>

                            <ResponsiveContainer
                                width="100%"
                                height={250}
                            >

                                <LineChart
                                    data={chartData}
                                >

                                    <CartesianGrid
                                        strokeDasharray="3 3"
                                        stroke="#26364d"
                                    />

                                    <XAxis
                                        dataKey="time"
                                        stroke="#64748b"
                                    />

                                    <YAxis
                                        stroke="#64748b"
                                    />

                                    <Tooltip
                                        contentStyle={{
                                            background:
                                                "#111827",

                                            border:
                                                "1px solid #334155",

                                            color:
                                                "#f8fafc",
                                        }}
                                    />

                                    <Line
                                        type="monotone"
                                        dataKey="occupancy"
                                        stroke="#38bdf8"
                                        strokeWidth={3}
                                        dot={false}
                                        isAnimationActive={false}
                                    />

                                </LineChart>

                            </ResponsiveContainer>

                        </section>

                    </div>


                    {/* =================================================
                       HISTORY
                    ================================================= */}

                    <section className="history-card">

                        <div className="section-heading">

                            <div>

                                <span className="section-label">
                                    SENSOR HISTORY
                                </span>

                                <h2>
                                    Recent Readings — Zone{" "}
                                    {currentZone}
                                </h2>

                            </div>

                            <span className="live-label">
                                ● LIVE
                            </span>

                        </div>


                        <div className="history-table">

                            <div className="history-header">

                                <span>
                                    Time
                                </span>

                                <span>
                                    Temperature
                                </span>

                                <span>
                                    Humidity
                                </span>

                                <span>
                                    Smoke
                                </span>

                                <span>
                                    Occupancy
                                </span>

                            </div>


                            {selectedZoneHistory.length === 0 ? (

                                <div className="history-row">

                                    <span>
                                        No history data
                                    </span>

                                    <span>
                                        --
                                    </span>

                                    <span>
                                        --
                                    </span>

                                    <span>
                                        --
                                    </span>

                                    <span>
                                        --
                                    </span>

                                </div>

                            ) : (

                                selectedZoneHistory
                                    .slice()
                                    .reverse()
                                    .slice(0, 10)
                                    .map(
                                        (
                                            sensor,
                                            index
                                        ) => (

                                            <div
                                                className="history-row"
                                                key={`${sensor.timestamp}-${index}`}
                                            >

                                                <span>

                                                    {sensor.timestamp
                                                        ? new Date(
                                                            sensor.timestamp
                                                        ).toLocaleTimeString()
                                                        : "--"
                                                    }

                                                </span>


                                                <span>

                                                    {
                                                        sensor.temperature ??
                                                        "--"
                                                    } °C

                                                </span>


                                                <span>

                                                    {
                                                        sensor.humidity ??
                                                        "--"
                                                    } %

                                                </span>


                                                <span>

                                                    {
                                                        sensor.smoke ??
                                                        "--"
                                                    }

                                                </span>


                                                <span>

                                                    {
                                                        sensor.occupancy ??
                                                        "--"
                                                    }

                                                </span>

                                            </div>

                                        )
                                    )

                            )}

                        </div>

                    </section>


                    {/* =================================================
                       FOOTER
                    ================================================= */}

                    <footer className="monitoring-footer">

                        Automatically updating every 3 seconds
                        {" • "}
                        Monitoring sensor-{currentZone}

                    </footer>

                </>

            )}

        </div>

    );
}


/* =============================================================
   SENSOR CARD
============================================================= */

function SensorCard({
    icon,
    label,
    value,
    status,
    color,
}) {

    return (

        <div className="monitoring-sensor-card">

            <div className="sensor-card-top">

                <span className="sensor-icon">
                    {icon}
                </span>

                <span
                    className="sensor-status"
                    style={{
                        color,
                    }}
                >
                    ● {status}
                </span>

            </div>


            <span className="sensor-card-label">
                {label}
            </span>


            <strong className="sensor-card-value">
                {value}
            </strong>

        </div>

    );
}


export default Monitoring;