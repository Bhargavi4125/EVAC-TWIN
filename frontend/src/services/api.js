const API_BASE_URL = "http://localhost:8001";


// ============================================================
// GENERIC API HELPER
// ============================================================

async function apiRequest(url) {
    const controller = new AbortController();

    const timeout = setTimeout(() => {
        controller.abort();
    }, 10000);

    try {
        const response = await fetch(url, {
            signal: controller.signal
        });

        if (!response.ok) {
            let message = `Request failed: ${response.status}`;

            try {
                const data = await response.json();

                if (data?.detail) {
                    message = data.detail;
                }
            } catch {
                // Ignore JSON parsing errors
            }

            throw new Error(message);
        }

        return await response.json();
    } catch (error) {
        if (error.name === "AbortError") {
            throw new Error("API request timed out after 10 seconds");
        }

        throw error;
    } finally {
        clearTimeout(timeout);
    }
}



// ============================================================
// CURRENT SENSOR DATA
// ============================================================

export async function getSensors() {

    return apiRequest(
        `${API_BASE_URL}/api/sensors`
    );
}


// ============================================================
// SENSOR HISTORY
// ============================================================

export async function getSensorHistory(
    zoneId,
    limit = 100
) {

    const url =
        `${API_BASE_URL}/api/sensors/history` +
        `?zone_id=${encodeURIComponent(zoneId)}` +
        `&limit=${limit}`;

    return apiRequest(url);
}


// ============================================================
// BUILDING SUMMARY
// ============================================================

export async function getBuildingSummary() {

    return apiRequest(
        `${API_BASE_URL}/api/buildings/summary`
    );
}


// ============================================================
// EVENTS
// ============================================================

export async function getEvents() {

    return apiRequest(
        `${API_BASE_URL}/api/events`
    );
}


// ============================================================
// BUILDINGS
// ============================================================

export async function getBuildings() {

    return apiRequest(
        `${API_BASE_URL}/api/buildings`
    );
}


// ============================================================
// EVACUATION — ALL ROUTES
// ============================================================

export async function getEvacuationRoutes(zoneId) {

    return apiRequest(
        `${API_BASE_URL}/api/evacuation/routes${zoneId ? `?zone_id=${zoneId}` : ""}`
    );
}

// ============================================================
// EVACUATION — SUMMARY
// ============================================================

export async function getEvacuationSummary() {

    return apiRequest(
        `${API_BASE_URL}/api/evacuation/summary`
    );
}


// ============================================================
// EVACUATION — EXITS
// ============================================================

export async function getEvacuationExits() {

    return apiRequest(
        `${API_BASE_URL}/api/evacuation/exits`
    );
}


// ============================================================
// EVACUATION — SINGLE ZONE
// ============================================================

export async function getZoneEvacuationRoute(
    deviceId,
    temperature,
    smoke,
    occupancy
) {
    const response = await fetch(
        `${API_BASE_URL}/api/evacuation/route/${encodeURIComponent(deviceId)}`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                temperature,
                smoke,
                occupancy
            })
        }
    );

    if (!response.ok) {
        throw new Error("Route request failed");
    }

    return response.json();
}
export async function getAlgorithmComparison(
    deviceId,
    temperature,
    smoke,
    occupancy
) {
    const response = await fetch(
        `${API_BASE_URL}/api/evacuation/compare/${encodeURIComponent(deviceId)}`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                temperature,
                smoke,
                occupancy
            })
        }
    );

    if (!response.ok) {
        throw new Error("Algorithm comparison failed");
    }

    return response.json();
}

// ============================================================
// EVACUATION — ZONE ALIAS
// ============================================================

export async function getZoneRoute(
    deviceId
) {

    return apiRequest(
        `${API_BASE_URL}/api/evacuation/zone/${encodeURIComponent(deviceId)}`
    );
}


// ============================================================
// BACKEND HEALTH
// ============================================================

export async function getHealth() {

    return apiRequest(
        `${API_BASE_URL}/api/health`
    );
}


// ============================================================
// EVACUATION HEALTH
// ============================================================

export async function getEvacuationHealth() {

    return apiRequest(
        `${API_BASE_URL}/api/evacuation/health`
    );
}

// ============================================================
// SIMULATION — EMERGENCY SMS ALERT
// ============================================================

export async function sendSimulationAlert(
    deviceId,
    temperature,
    smoke,
    occupancy,
    scenario
) {
    const response = await fetch(
        `${API_BASE_URL}/api/evacuation/simulation/${encodeURIComponent(deviceId)}`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                temperature,
                smoke,
                occupancy,
                scenario
            })
        }
    );

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));

        throw new Error(
            data.detail || "Simulation SMS request failed"
        );
    }

    return response.json();
}
// ============================================================
// DEEP LEARNING — RISK PREDICTION
// ============================================================

export async function predictRiskDL(
    temperature,
    humidity,
    smoke,
    occupancy
) {
    const response = await fetch(
        `${API_BASE_URL}/api/ai/predict-risk`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                temperature,
                humidity,
                smoke,
                occupancy
            })
        }
    );

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));

        throw new Error(
            data.detail || "Deep Learning risk prediction failed"
        );
    }

    return response.json();
}