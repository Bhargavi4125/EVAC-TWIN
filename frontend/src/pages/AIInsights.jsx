import { useEffect, useState } from "react";
import { getSensors } from "../services/api";
import {
    calculateRisk,
    getRiskBackground,
    getRiskColor,
} from "../utils/riskEngine";
import "./AIInsights.css";

function AIInsights() {
    const [sensors, setSensors] = useState([]);
    const [error, setError] = useState("");

    useEffect(() => {
        const loadSensors = async () => {
            try {
                const data = await getSensors();
                setSensors(data);
                setError("");
            } catch (err) {
                setError("Unable to connect to EVAC-TWIN backend.");
            }
        };

        loadSensors();

        const interval = setInterval(loadSensors, 3000);

        return () => clearInterval(interval);
    }, []);

    const latest = sensors[0];

const calculatedRisk = latest
    ? calculateRisk(latest)
    : {
        level: "WAITING",
        score: 0,
        recommendation: "Waiting for live sensor information.",
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

    const getInsight = () => {
        if (!latest) {
            return {
                title: "Waiting for sensor data",
                text: "AI analysis will begin when live sensor readings are available.",
            };
        }

        if (risk.level === "CRITICAL") {
            return {
                title: "Critical emergency conditions",
                text: "Multiple environmental indicators are showing dangerous values. Immediate evacuation procedures should be considered.",
            };
        }

        if (risk.level === "HIGH") {
            return {
                title: "High-risk conditions detected",
                text: "Sensor readings indicate a significant increase in emergency risk. Monitor affected zones and prepare evacuation routes.",
            };
        }

        if (risk.level === "MODERATE") {
            return {
                title: "Elevated risk detected",
                text: "Some environmental conditions are above normal levels. Continue monitoring for changes.",
            };
        }

        return {
            title: "Building conditions are stable",
            text: "Current environmental and occupancy readings remain within acceptable ranges.",
        };
    };

    const insight = getInsight();
    const dlConfidence = Number(latest?.dl_confidence ?? latest?.confidence ?? 0);

    return (
        <div className="ai-page">

            {/* HEADER */}
            <header className="ai-header">
                <div>
                    <p className="ai-eyebrow">
                        AI INTELLIGENCE / DECISION SUPPORT
                    </p>

                    <h1>AI Insights</h1>

                    <p className="ai-subtitle">
                        Automated emergency risk analysis from live Digital Twin data.
                    </p>
                </div>

                <div className="ai-live">
                    <span></span>
                    LIVE ANALYSIS
                </div>
            </header>

            {/* ERROR */}
            {error && (
                <div className="ai-error">
                    ⚠️ {error}
                </div>
            )}

            {/* LOADING */}
            {!latest && !error && (
                <div className="ai-loading">
                    <div className="ai-loader">◌</div>

                    <h2>Waiting for Digital Twin data</h2>

                    <p>
                        AI analysis will update automatically.
                    </p>
                </div>
            )}

            {latest && (
                <>
                    {/* AI OVERVIEW */}
                    <section className="ai-overview">

                        <div className="ai-risk-card">
                            <div className="ai-dl-confidence">
    <span>DEEP LEARNING CONFIDENCE</span>
    <strong>{dlConfidence.toFixed(2)}%</strong>
</div>

                            <div>
                                <span className="ai-label">
                                    CURRENT AI RISK SCORE
                                </span>

                                <div
                                    className="ai-risk-number"
                                    style={{
                                        color: getRiskColor(risk.level),
                                    }}
                                >
                                    {risk.score}%
                                </div>

                                <strong
                                    className="ai-risk-level"
                                    style={{
                                        color: getRiskColor(risk.level),
                                    }}
                                >
                                    {risk.level} RISK
                                </strong>
                            </div>

                            <div
                                className="ai-risk-ring"
                                style={{
                                    borderColor: getRiskColor(risk.level),
                                }}
                            >
                                <span>{risk.score}</span>
                                <small>/100</small>
                            </div>

                        </div>

                        {/* RECOMMENDATION */}
                        <div
                            className="ai-recommendation"
                            style={{
                                background: getRiskBackground(risk.level),
                                borderColor: getRiskColor(risk.level),
                            }}
                        >
                            <span className="ai-label">
                                AI RECOMMENDATION
                            </span>

                            <h2>{insight.title}</h2>

                            <p>{insight.text}</p>

                            <div className="recommendation-action">
                                <strong>Recommended Action</strong>

                                <span>
                                    {risk.recommendation}
                                </span>
                            </div>
                        </div>

                    </section>

                    {/* SENSOR INTELLIGENCE */}
                    <section className="ai-panel">

                        <div className="ai-panel-header">
                            <div>
                                <span className="ai-label">
                                    SENSOR INTELLIGENCE
                                </span>

                                <h2>Risk Factors</h2>
                            </div>

                            <span className="ai-device">
                                {latest.device_id}
                            </span>
                        </div>

                        <div className="factor-grid">

                            {/* TEMPERATURE */}
                            <div className="factor-card">

                                <div className="factor-top">
                                    <span>🌡️</span>
                                    <strong>Temperature</strong>
                                </div>

                                <div className="factor-value">
                                    {latest.temperature}°C
                                </div>

                                <div className="factor-bar">
                                    <div
                                        style={{
                                            width: `${Math.min(
                                                (latest.temperature / 50) * 100,
                                                100
                                            )
                                                }% `,
                                        }}
                                    ></div>
                                </div>

                                <p>
                                    {latest.temperature >= 40
                                        ? "Critical temperature detected"
                                        : latest.temperature >= 38
                                            ? "High temperature detected"
                                            : latest.temperature >= 35
                                                ? "Elevated temperature detected"
                                                : "Temperature remains stable"}
                                </p>

                            </div>

                            {/* SMOKE */}
                            <div className="factor-card">

                                <div className="factor-top">
                                    <span>💨</span>
                                    <strong>Smoke</strong>
                                </div>

                                <div className="factor-value">
                                    {latest.smoke}
                                </div>

                                <div className="factor-bar">
                                    <div
                                        style={{
                                            width: `${latest.smoke * 100}% `,
                                        }}
                                    ></div>
                                </div>

                                <p>
                                    {latest.smoke >= 0.8
                                        ? "High smoke concentration"
                                        : latest.smoke >= 0.5
                                            ? "Elevated smoke level"
                                            : latest.smoke >= 0.3
                                                ? "Low smoke detected"
                                                : "Smoke level normal"}
                                </p>

                            </div>

                            {/* OCCUPANCY */}
                            <div className="factor-card">

                                <div className="factor-top">
                                    <span>👥</span>
                                    <strong>Occupancy</strong>
                                </div>

                                <div className="factor-value">
                                    {latest.occupancy}
                                </div>

                                <div className="factor-bar">
                                    <div
                                        style={{
                                            width: `${Math.min(
                                                (latest.occupancy / 50) * 100,
                                                100
                                            )
                                                }% `,
                                        }}
                                    ></div>
                                </div>

                                <p>
                                    {latest.occupancy >= 45
                                        ? "Critical occupancy load"
                                        : latest.occupancy >= 30
                                            ? "Moderate occupancy"
                                            : latest.occupancy >= 15
                                                ? "Elevated occupancy"
                                                : "Occupancy load normal"}
                                </p>

                            </div>

                            {/* HUMIDITY */}
                            <div className="factor-card">

                                <div className="factor-top">
                                    <span>💧</span>
                                    <strong>Humidity</strong>
                                </div>

                                <div className="factor-value">
                                    {latest.humidity}%
                                </div>

                                <div className="factor-bar">
                                    <div
                                        style={{
                                            width: `${Math.min(
                                                latest.humidity,
                                                100
                                            )
                                                }% `,
                                        }}
                                    ></div>
                                </div>

                                <p>
                                    Environmental humidity monitoring active
                                </p>

                            </div>

                        </div>

                    </section>

                    {/* DECISION ENGINE */}
                    <section className="ai-panel">

                        <div className="ai-panel-header">

                            <div>
                                <span className="ai-label">
                                    DECISION ENGINE
                                </span>

                                <h2>Risk Assessment</h2>
                            </div>

                        </div>

                        <div className="assessment-list">

                            <div className="assessment-row">
                                <span>
                                    Temperature contribution
                                </span>

                                <strong>
                                    {risk.factors.temperature > 0
                                        ? `+ ${risk.factors.temperature} `
                                        : "0"}
                                </strong>
                            </div>

                            <div className="assessment-row">
                                <span>
                                    Smoke contribution
                                </span>

                                <strong>
                                    {risk.factors.smoke > 0
                                        ? `+ ${risk.factors.smoke} `
                                        : "0"}
                                </strong>
                            </div>

                            <div className="assessment-row">
                                <span>
                                    Occupancy contribution
                                </span>

                                <strong>
                                    {risk.factors.occupancy > 0
                                        ? `+ ${risk.factors.occupancy} `
                                        : "0"}
                                </strong>
                            </div>

                            <div className="assessment-total">

                                <span>
                                    Total AI Risk Score
                                </span>

                                <strong
                                    style={{
                                        color: getRiskColor(risk.level),
                                    }}
                                >
                                    {risk.score} / 100
                                </strong>

                            </div>

                        </div>

                    </section>

                    {/* FOOTER */}
                    <div className="ai-footer">
                        🟢 AI engine synchronized · Analysis updates every 3 seconds
                    </div>
                </>
            )}

        </div>
    );
}

export default AIInsights;