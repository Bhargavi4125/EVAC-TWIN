import { useEffect, useMemo, useState } from "react";

import {
    calculateRisk,
    getRiskBackground,
    getRiskColor,
} from "../utils/riskEngine";

import {
    getSensors,
    getZoneEvacuationRoute,
    getAlgorithmComparison,
    sendSimulationAlert,
    predictRiskDL,
} from "../services/api";

import "./Simulation.css";

function Simulation() {
    const [scenario, setScenario] =
        useState("Fire Emergency");

    const [temperature, setTemperature] =
        useState(38);

    const [smoke, setSmoke] =
        useState(0.7);

    const [algorithmComparison, setAlgorithmComparison] =
        useState([]);

    const [occupancy, setOccupancy] =
        useState(30);

    const [result, setResult] =
        useState(null);

    const [loadingSensors, setLoadingSensors] =
        useState(true);

    const [simulationLoading, setSimulationLoading] =
        useState(false);

    const [sensorError, setSensorError] =
        useState("");

    const [liveSensor, setLiveSensor] =
        useState(null);

    const [sensors, setSensors] =
        useState([]);

    const [selectedZone, setSelectedZone] =
        useState("");

    const [route, setRoute] =
        useState(null);

    // =========================================================
    // LOAD LIVE SENSOR DATA
    // =========================================================

    useEffect(() => {
        const loadSensors = async () => {
            try {
                setSensorError("");

                const sensorData = await getSensors();

                if (
                    Array.isArray(sensorData) &&
                    sensorData.length > 0
                ) {
                    setSensors(sensorData);

                    setSelectedZone((currentZone) =>
                        currentZone ||
                        String(sensorData[0].zone_id)
                    );
                }
            } catch (error) {
                console.error(
                    "Failed to load live sensors:",
                    error
                );

                setSensorError(
                    "Unable to connect to live sensor data."
                );
            } finally {
                setLoadingSensors(false);
            }
        };

        loadSensors();

        const interval = setInterval(
            loadSensors,
            5000
        );

        return () => {
            clearInterval(interval);
        };
    }, []);

    // =========================================================
    // SELECTED LIVE SENSOR
    // =========================================================

    useEffect(() => {
        if (!selectedZone || sensors.length === 0) {
            return;
        }

        const sensor = sensors.find(
            (item) =>
                String(item.zone_id) ===
                String(selectedZone)
        );

        if (sensor) {
            setLiveSensor(sensor);
        }
    }, [selectedZone, sensors]);

    // =========================================================
    // SCENARIO CONFIGURATION
    // =========================================================

    const scenarioConfig = {
        "Fire Emergency": {
            description:
                "Simulate a developing fire inside the building.",
            temperatureMultiplier: 1.2,
            smokeMultiplier: 1.4,
            occupancyMultiplier: 0.8,
        },

        "High Temperature": {
            description:
                "Evaluate the building under extreme heat conditions.",
            temperatureMultiplier: 1.6,
            smokeMultiplier: 0.5,
            occupancyMultiplier: 0.6,
        },

        "Smoke Emergency": {
            description:
                "Simulate increasing smoke concentration.",
            temperatureMultiplier: 0.7,
            smokeMultiplier: 1.7,
            occupancyMultiplier: 0.7,
        },

        "Overcrowding": {
            description:
                "Evaluate evacuation pressure from high occupancy.",
            temperatureMultiplier: 0.5,
            smokeMultiplier: 0.6,
            occupancyMultiplier: 1.8,
        },

        "Combined Emergency": {
            description:
                "Simulate simultaneous environmental hazards.",
            temperatureMultiplier: 1.3,
            smokeMultiplier: 1.3,
            occupancyMultiplier: 1.3,
        },
    };

    // =========================================================
    // LIVE PREVIEW - FRONTEND RISK CALCULATION
    // =========================================================

    const calculateScenarioRisk = () => {
        const sensor = {
            temperature: Number(temperature),
            smoke: Number(smoke),
            occupancy: Number(occupancy),
            humidity: 50,
            device_id: "simulation",
            timestamp: new Date().toISOString(),
        };

        const baseRisk = calculateRisk(sensor);

        const config = scenarioConfig[scenario];

        if (!config) {
            return baseRisk;
        }

        const adjustedTemperature =
            baseRisk.factors.temperature *
            config.temperatureMultiplier;

        const adjustedSmoke =
            baseRisk.factors.smoke *
            config.smokeMultiplier;

        const adjustedOccupancy =
            baseRisk.factors.occupancy *
            config.occupancyMultiplier;

        const score = Math.min(
            Math.round(
                adjustedTemperature +
                adjustedSmoke +
                adjustedOccupancy
            ),
            100
        );

        let level = "LOW";

        let recommendation =
            "Environmental conditions are stable. Continue normal monitoring.";

        if (score >= 70) {
            level = "CRITICAL";

            recommendation =
                "Immediate evacuation recommended. Activate emergency procedures.";
        } else if (score >= 40) {
            level = "HIGH";

            recommendation =
                "High-risk conditions detected. Prepare evacuation routes and alert occupants.";
        } else if (score >= 20) {
            level = "MODERATE";

            recommendation =
                "Elevated conditions detected. Continue monitoring sensor values.";
        }

        return {
            score,
            level,
            recommendation,

            factors: {
                temperature: Math.round(adjustedTemperature),
                smoke: Math.round(adjustedSmoke),
                occupancy: Math.round(adjustedOccupancy),
            },
        };
    };

    // =========================================================
    // LIVE RISK PREVIEW
    // =========================================================

    const liveRisk = useMemo(
        () => calculateScenarioRisk(),
        [
            scenario,
            temperature,
            smoke,
            occupancy,
        ]
    );

    const activeRisk = result || liveRisk;

    const riskColor = getRiskColor(
        activeRisk.level
    );

    const riskBackground = getRiskBackground(
        activeRisk.level
    );

    // =========================================================
    // RUN SIMULATION - PYTORCH MLP
    // =========================================================

    const runSimulation = async () => {
        try {
            if (!selectedZone) {
                alert("Please select a zone.");
                return;
            }

            const selectedSensor = sensors.find(
                (sensor) =>
                    String(sensor.zone_id) ===
                    String(selectedZone)
            );

            if (!selectedSensor) {
                alert("No sensor found for the selected zone.");
                return;
            }

            setSimulationLoading(true);

            const simulationInput = {
                temperature: Number(temperature),
                humidity: Number(
                    liveSensor?.humidity ?? 50
                ),
                smoke: Number(smoke),
                occupancy: Number(occupancy),
            };

            console.log(
                "SIMULATION INPUT:",
                {
                    zone: selectedZone,
                    scenario,
                    ...simulationInput,
                }
            );

            // Get prediction from backend PyTorch MLP
            const dlResult = await predictRiskDL(
                simulationInput.temperature,
                simulationInput.humidity,
                simulationInput.smoke,
                simulationInput.occupancy
            );

            console.log(
                "DEEP LEARNING PREDICTION:",
                dlResult
            );

            const predictionLevel = String(
                dlResult.prediction || "LOW"
            ).toUpperCase();

            const simulationResult = {
                score: Math.max(
                    0,
                    Math.min(
                        100,
                        Number(dlResult.risk_score ?? 0)
                    )
                ),

                level: predictionLevel,

                confidence: Number(
                    dlResult.confidence ?? 0
                ),

                probabilities:
                    dlResult.probabilities || {},

                recommendation:
                    dlResult.recommendation ||
                    "Continue monitoring the building conditions.",

                factors: {
                    temperature:
                        simulationInput.temperature,

                    smoke:
                        simulationInput.smoke,

                    occupancy:
                        simulationInput.occupancy,
                },
            };

            // Algorithm comparison
            const comparisonData =
                await getAlgorithmComparison(
                    selectedSensor.device_id,
                    simulationInput.temperature,
                    simulationInput.smoke,
                    simulationInput.occupancy
                );

            setAlgorithmComparison(
                comparisonData?.comparison || []
            );

            // Dynamic evacuation route
            const routeResult =
                await getZoneEvacuationRoute(
                    selectedSensor.device_id,
                    simulationInput.temperature,
                    simulationInput.smoke,
                    simulationInput.occupancy
                );

            setRoute(routeResult);

            // Emergency SMS
            let smsResult = {
                sms_sent: false,
                message: "No emergency SMS required.",
            };

            if (
                predictionLevel === "HIGH" ||
                predictionLevel === "CRITICAL"
            ) {
                smsResult = await sendSimulationAlert(
                    selectedSensor.device_id,
                    simulationInput.temperature,
                    simulationInput.smoke,
                    simulationInput.occupancy,
                    scenario
                );
            }

            console.log(
                "SIMULATION ROUTE:",
                routeResult
            );

            console.log(
                "SIMULATION SMS RESULT:",
                smsResult
            );

            if (smsResult.sms_sent) {
                alert("Emergency SMS sent successfully!");
            } else {
                alert(smsResult.message);
            }

            // Save simulation data
            localStorage.setItem(
                "selectedZone",
                selectedZone
            );

            localStorage.setItem(
                "algorithmComparison",
                JSON.stringify(
                    comparisonData?.comparison || []
                )
            );

            localStorage.setItem(
                "simulationInput",
                JSON.stringify({
                    zone_id: selectedZone,
                    scenario,
                    ...simulationInput,
                    risk_score: simulationResult.score,
                    risk_level: simulationResult.level,
                    dl_confidence: simulationResult.confidence,
                })
            );

            localStorage.setItem(
                "simulationRoute",
                JSON.stringify(routeResult)
            );

            setResult(simulationResult);

        } catch (error) {
            console.error(
                "Simulation failed:",
                error
            );

            alert(
                `Simulation failed: ${error.message}`
            );
        } finally {
            setSimulationLoading(false);
        }
    };

    // =========================================================
    // RESET
    // =========================================================

    const resetSimulation = () => {
        setScenario("Fire Emergency");

        if (liveSensor) {
            setTemperature(
                Number(liveSensor.temperature ?? 38)
            );

            setSmoke(
                Number(liveSensor.smoke ?? 0.7)
            );

            setOccupancy(
                Number(liveSensor.occupancy ?? 30)
            );
        } else {
            setTemperature(38);
            setSmoke(0.7);
            setOccupancy(30);
        }

        setResult(null);
        setRoute(null);
        setAlgorithmComparison([]);
    };

    // =========================================================
    // SCENARIO DESCRIPTION
    // =========================================================

    const getScenarioDescription = () => {
        return (
            scenarioConfig[scenario]?.description ||
            "Configure emergency conditions."
        );
    };

    // =========================================================
    // FLOOR STATUS
    // =========================================================

    const getFloorClass = (floor) => {
    return "simulation-floor";
};
    // =========================================================
    // ROOM STATUS
    // =========================================================

    const getRoomClass = (floor, room) => {
    const zoneId = `${floor}0${room}`;

    const roomSensor = sensors.find(
        (sensor) => String(sensor.zone_id) === zoneId
    );

    if (!roomSensor) return "normal-room";

    const risk =
        String(selectedZone) === zoneId
            ? activeRisk
            : calculateRisk(roomSensor);

    if (risk.level === "CRITICAL") return "critical-room";

    if (risk.level === "HIGH" || risk.level === "MODERATE") {
        return "warning-room";
    }

    return "normal-room";
};
    // =========================================================
    // SCENARIO IMPACT
    // =========================================================

    const scenarioImpact = {
        "Fire Emergency":
            "Fire conditions are primarily influenced by heat and smoke.",

        "High Temperature":
            "Extreme temperature is the dominant risk factor.",

        "Smoke Emergency":
            "Smoke concentration is the dominant emergency factor.",

        "Overcrowding":
            "High occupancy increases evacuation pressure across the building.",

        "Combined Emergency":
            "Multiple environmental hazards are contributing simultaneously.",
    };

    // =========================================================
    // RENDER
    // =========================================================

    return (
        <div
            className="simulation-page"
            style={{
                "--simulation-risk-color": riskColor,
                "--simulation-risk-background": riskBackground,
            }}
        >
            {/* HEADER */}

            <header className="simulation-header">
                <div>
                    <p className="simulation-eyebrow">
                        DIGITAL TWIN / WHAT-IF ENGINE
                    </p>

                    <h1>
                        Emergency Simulation
                    </h1>

                    <p className="simulation-subtitle">
                        Test emergency conditions and evaluate how
                        Building Alpha responds.
                    </p>
                </div>

                <div className="simulation-mode">
                    <span className="simulation-mode-dot"></span>
                    SIMULATION MODE
                </div>
            </header>

            {/* MAIN GRID */}

            <section className="simulation-grid">

                {/* CONTROLS */}

                <div className="simulation-panel controls-panel">

                    <div className="simulation-panel-header">
                        <div>
                            <span>
                                SCENARIO CONFIGURATION
                            </span>

                            <h2>
                                Emergency Conditions
                            </h2>
                        </div>

                        <div className="simulation-number">
                            01
                        </div>
                    </div>

                    {/* LIVE SENSOR STATUS */}

                    <div className="simulation-live-status">
                        <div>
                            <span className="live-status-dot"></span>

                            <span>
                                {loadingSensors
                                    ? "CONNECTING TO LIVE SENSORS"
                                    : sensorError
                                        ? "LIVE SENSOR CONNECTION FAILED"
                                        : "LIVE SENSOR DATA CONNECTED"}
                            </span>
                        </div>

                        {liveSensor && (
                            <small>
                                {liveSensor.zone_id ||
                                    liveSensor.device_id ||
                                    "Building Alpha"}
                            </small>
                        )}
                    </div>

                    {/* ZONE */}

                    <label className="simulation-label">
                        Sensor / Zone
                    </label>

                    <select
                        className="simulation-select"
                        value={selectedZone}
                        onChange={(event) => {
                            const zone = event.target.value;

                            setSelectedZone(zone);

                            localStorage.setItem(
                                "selectedZone",
                                zone
                            );

                            setResult(null);
                        }}
                    >
                        {sensors.map((sensor) => (
                            <option
                                key={sensor.zone_id}
                                value={sensor.zone_id}
                            >
                                Zone {sensor.zone_id}
                            </option>
                        ))}
                    </select>

                    {/* SCENARIO */}

                    <label className="simulation-label">
                        Emergency Scenario
                    </label>

                    <select
                        className="simulation-select"
                        value={scenario}
                        onChange={(event) => {
                            setScenario(event.target.value);
                            setResult(null);
                        }}
                    >
                        <option>Fire Emergency</option>
                        <option>High Temperature</option>
                        <option>Smoke Emergency</option>
                        <option>Overcrowding</option>
                        <option>Combined Emergency</option>
                    </select>

                    <p className="scenario-description">
                        {getScenarioDescription()}
                    </p>

                    {/* SCENARIO IMPACT */}

                    <div className="scenario-impact">
                        <span>
                            SCENARIO IMPACT
                        </span>

                        <p>
                            {scenarioImpact[scenario]}
                        </p>
                    </div>

                    {/* TEMPERATURE */}

                    <div className="simulation-control">
                        <div className="control-heading">
                            <div>
                                <span className="control-icon temperature">
                                    🌡
                                </span>

                                <span>
                                    Temperature
                                </span>
                            </div>

                            <strong>
                                {temperature}°C
                            </strong>
                        </div>

                        <input
                            className="simulation-range temperature-range"
                            type="range"
                            min="20"
                            max="50"
                            value={temperature}
                            onChange={(event) => {
                                setTemperature(
                                    Number(event.target.value)
                                );

                                setResult(null);
                            }}
                        />

                        <div className="range-labels">
                            <span>20°C</span>
                            <span>Normal</span>
                            <span>50°C</span>
                        </div>
                    </div>

                    {/* SMOKE */}

                    <div className="simulation-control">
                        <div className="control-heading">
                            <div>
                                <span className="control-icon smoke">
                                    ◉
                                </span>

                                <span>
                                    Smoke Level
                                </span>
                            </div>

                            <strong>
                                {Number(smoke).toFixed(2)}
                            </strong>
                        </div>

                        <input
                            className="simulation-range smoke-range"
                            type="range"
                            min="0"
                            max="1"
                            step="0.01"
                            value={smoke}
                            onChange={(event) => {
                                setSmoke(
                                    Number(event.target.value)
                                );

                                setResult(null);
                            }}
                        />

                        <div className="range-labels">
                            <span>0.00</span>
                            <span>Safe</span>
                            <span>1.00</span>
                        </div>
                    </div>

                    {/* OCCUPANCY */}

                    <div className="simulation-control">
                        <div className="control-heading">
                            <div>
                                <span className="control-icon occupancy">
                                    👥
                                </span>

                                <span>
                                    Occupancy
                                </span>
                            </div>

                            <strong>
                                {occupancy}
                            </strong>
                        </div>

                        <input
                            className="simulation-range occupancy-range"
                            type="range"
                            min="0"
                            max="60"
                            value={occupancy}
                            onChange={(event) => {
                                setOccupancy(
                                    Number(event.target.value)
                                );

                                setResult(null);
                            }}
                        />

                        <div className="range-labels">
                            <span>0</span>
                            <span>Capacity</span>
                            <span>60</span>
                        </div>
                    </div>

                    {/* LIVE RISK */}

                    <div className="simulation-live-summary">
                        <div>
                            <span>
                                LIVE RISK PREVIEW
                            </span>

                            <strong
                                style={{
                                    color: getRiskColor(liveRisk.level),
                                }}
                            >
                                {liveRisk.score}
                            </strong>
                        </div>

                        <div>
                            <span>
                                LEVEL
                            </span>

                            <strong
                                style={{
                                    color: getRiskColor(liveRisk.level),
                                }}
                            >
                                {liveRisk.level}
                            </strong>
                        </div>
                    </div>

                    {/* ACTIONS */}

                    <div className="simulation-actions">
                        <button
                            className="run-simulation"
                            onClick={runSimulation}
                            disabled={simulationLoading || loadingSensors}
                        >
                            <span>▶</span>

                            {simulationLoading
                                ? "Running DL Model..."
                                : "Run Simulation"}
                        </button>

                        <button
                            className="reset-simulation"
                            onClick={resetSimulation}
                            disabled={simulationLoading}
                        >
                            Reset
                        </button>
                    </div>
                </div>

                {/* DIGITAL TWIN */}

                <div className="simulation-panel building-panel">

                    <div className="simulation-panel-header">
                        <div>
                            <span>
                                DIGITAL TWIN PREVIEW
                            </span>

                            <h2>
                                Building Alpha
                            </h2>
                        </div>

                        <div className="building-live">
                            <span></span>
                            SIMULATION MODEL
                        </div>
                    </div>

                    <div className="simulation-building-area">
                        <div className="simulation-building">

                            {/* FLOOR 03 */}

                            <div className={getFloorClass(3)}>
                                <div className="floor-number">
                                    <small>03</small>
                                    <span>FLOOR</span>
                                </div>

                                <div className="simulation-rooms">
                                    <i className={getRoomClass(3, 1)}></i>
                                    <i className={getRoomClass(3, 2)}></i>
                                    <i className={getRoomClass(3, 3)}></i>
                                    <i className={getRoomClass(3, 4)}></i>
                                </div>
                            </div>

                            {/* FLOOR 02 */}

                            <div className={getFloorClass(2)}>
                                <div className="floor-number">
                                    <small>02</small>
                                    <span>FLOOR</span>
                                </div>

                                <div className="simulation-rooms">
                                    <i className={getRoomClass(2, 1)}></i>
                                    <i className={getRoomClass(2, 2)}></i>
                                    <i className={getRoomClass(2, 3)}></i>
                                    <i className={getRoomClass(2, 4)}></i>
                                </div>
                            </div>

                            {/* FLOOR 01 */}

                            <div className={getFloorClass(1)}>
                                <div className="floor-number">
                                    <small>01</small>
                                    <span>FLOOR</span>
                                </div>

                                <div className="simulation-rooms">
                                    <i className={getRoomClass(1, 1)}></i>
                                    <i className={getRoomClass(1, 2)}></i>
                                    <i className={getRoomClass(1, 3)}></i>
                                    <i className={getRoomClass(1, 4)}></i>
                                </div>
                            </div>
                        </div>

                        <div className="building-ground">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                    </div>

                    {/* LEGEND */}

                    <div className="building-legend">
                        <div>
                            <span className="legend-dot safe"></span>
                            Normal
                        </div>

                        <div>
                            <span className="legend-dot warning"></span>
                            Warning
                        </div>

                        <div>
                            <span className="legend-dot danger"></span>
                            Critical
                        </div>
                    </div>
                </div>
            </section>

            {/* SIMULATION RESULT */}

            <section
                className={`simulation-result ${
                    result ? "result-visible" : ""
                }`}
                style={{
                    "--risk-color": riskColor,
                }}
            >
                <div className="result-top">
                    <div>
                        <span className="result-eyebrow">
                            {result
                                ? "SIMULATION COMPLETE"
                                : "LIVE RISK PREVIEW"}
                        </span>

                        <h2>
                            {result
                                ? "Simulation Result"
                                : "Current Scenario Risk"}
                        </h2>
                    </div>

                    <div
                        className="risk-score"
                        style={{
                            borderColor: riskColor,
                            color: riskColor,
                        }}
                    >
                        <strong>
                            {activeRisk.score}
                        </strong>

                        <span>/100</span>
                    </div>
                </div>

                {/* RISK SUMMARY */}

                <div className="risk-summary">
                    <div className="risk-level-box">
                        <span>RISK LEVEL</span>

                        <strong
                            style={{
                                color: riskColor,
                            }}
                        >
                            {activeRisk.level}
                        </strong>
                    </div>

                    <div className="risk-bar-container">
                        <div className="risk-bar">
                            <div
                                className="risk-bar-fill"
                                style={{
                                    width: `${activeRisk.score}%`,
                                    background: riskColor,
                                }}
                            ></div>
                        </div>

                        <div className="risk-scale">
                            <span>LOW</span>
                            <span>MODERATE</span>
                            <span>HIGH</span>
                            <span>CRITICAL</span>
                        </div>
                    </div>

                    <div className="risk-scenario">
                        <span>SCENARIO</span>

                        <strong>
                            {scenario}
                        </strong>
                    </div>
                </div>

                {/* DL CONFIDENCE */}

                {result && (
                    <div className="simulation-dl-confidence">
                        <span>
                            PYTORCH MLP CONFIDENCE
                        </span>

                        <strong>
                            {result.confidence.toFixed(2)}%
                        </strong>
                    </div>
                )}

                {/* FACTORS */}

                <div className="simulation-factors">
                    <div>
                        <span>TEMPERATURE</span>

                        <strong>
                            {activeRisk.factors.temperature}
                        </strong>
                    </div>

                    <div>
                        <span>SMOKE LEVEL</span>

                        <strong>
                            {activeRisk.factors.smoke}
                        </strong>
                    </div>

                    <div>
                        <span>OCCUPANCY</span>

                        <strong>
                            {activeRisk.factors.occupancy}
                        </strong>
                    </div>
                </div>

                {/* RECOMMENDATION */}

                <div className="risk-recommendation">
                    <div className="recommendation-icon">
                        {activeRisk.level === "CRITICAL"
                            ? "!"
                            : activeRisk.level === "HIGH"
                                ? "!"
                                : activeRisk.level === "MODERATE"
                                    ? "•"
                                    : "✓"}
                    </div>

                    <div>
                        <span>
                            RECOMMENDED ACTION
                        </span>

                        <p>
                            {activeRisk.recommendation}
                        </p>
                    </div>
                </div>

                {!result && (
                    <p className="preview-note">
                        Adjust the conditions above, then run the
                        simulation to generate a final Deep Learning
                        assessment.
                    </p>
                )}
            </section>

            {/* FOOTER */}

            <footer className="simulation-footer">
                <span>
                    ● Deep Learning risk engine
                </span>

                <span>
                    Digital Twin simulation environment
                </span>

                <span>
                    Scenario: {scenario}
                </span>
            </footer>
        </div>
    );
}

export default Simulation;
