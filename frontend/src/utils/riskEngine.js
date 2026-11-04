
// ============================================================
// EVAC-TWIN - DETERMINISTIC RISK ENGINE
// ============================================================

export function calculateRisk(sensor) {
    if (!sensor) {
        return {
            score: 0,
            level: "NO DATA",
            recommendation: "Waiting for sensor data.",
            factors: {
                temperature: 0,
                smoke: 0,
                occupancy: 0,
            },
        };
    }

    const temperature = Math.max(
        Number(sensor.temperature ?? 0),
        0
    );

    const smoke = Math.max(
        Number(sensor.smoke ?? 0),
        0
    );

    const occupancy = Math.max(
        Number(sensor.occupancy ?? 0),
        0
    );

    // Temperature risk - Maximum 35
    let temperatureRisk = 0;

    if (temperature >= 50) {
        temperatureRisk = 35;
    } else if (temperature >= 45) {
        temperatureRisk = 30;
    } else if (temperature >= 40) {
        temperatureRisk = 25;
    } else if (temperature >= 35) {
        temperatureRisk = 15;
    } else if (temperature >= 32) {
        temperatureRisk = 5;
    }

    // Smoke risk - Maximum 40
    let smokeRisk = 0;

    if (smoke >= 0.8) {
        smokeRisk = 40;
    } else if (smoke >= 0.6) {
        smokeRisk = 35;
    } else if (smoke >= 0.5) {
        smokeRisk = 30;
    } else if (smoke >= 0.3) {
        smokeRisk = 15;
    } else if (smoke >= 0.15) {
        smokeRisk = 5;
    }

    // Occupancy risk - Maximum 25
    let occupancyRisk = 0;

    if (occupancy >= 50) {
        occupancyRisk = 25;
    } else if (occupancy >= 40) {
        occupancyRisk = 20;
    } else if (occupancy >= 30) {
        occupancyRisk = 15;
    } else if (occupancy >= 15) {
        occupancyRisk = 5;
    }

    // Total risk score
    const score = Math.min(
        temperatureRisk + smokeRisk + occupancyRisk,
        100
    );

    // Risk classification
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
            "Elevated conditions detected. Continue close monitoring and prepare for escalation.";
    }

    return {
        score,
        level,
        recommendation,
        factors: {
            temperature: temperatureRisk,
            smoke: smokeRisk,
            occupancy: occupancyRisk,
        },
    };
}


// ============================================================
// RISK TEXT COLOR
// ============================================================

export function getRiskColor(level) {
    const riskLevel = String(level || "").toUpperCase();

    switch (riskLevel) {
        case "CRITICAL":
            return "#dc2626";

        case "HIGH":
            return "#ea580c";

        case "MODERATE":
            return "#d97706";

        case "LOW":
            return "#16a34a";

        default:
            return "#64748b";
    }
}


// ============================================================
// RISK BACKGROUND COLOR
// ============================================================

export function getRiskBackground(level) {
    const riskLevel = String(level || "").toUpperCase();

    switch (riskLevel) {
        case "CRITICAL":
            return "#fee2e2";

        case "HIGH":
            return "#ffedd5";

        case "MODERATE":
            return "#fef3c7";

        case "LOW":
            return "#dcfce7";

        default:
            return "#f1f5f9";
    }
}
