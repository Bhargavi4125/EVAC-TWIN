import { useEffect, useState } from "react";
import {
    Bar,
    BarChart,
    CartesianGrid,
    Line,
    LineChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import { getSensors } from "../services/api";

function Analytics() {
    const [sensors, setSensors] = useState([]);
    const [error, setError] = useState("");

    useEffect(() => {
        const loadSensors = async () => {
            try {
                const data = await getSensors();
                setSensors(data);
                setError("");
            } catch (err) {
                setError("Unable to load analytics data.");
            }
        };

        loadSensors();

        const interval = setInterval(loadSensors, 5000);

        return () => clearInterval(interval);
    }, []);

    if (error) {
        return (
            <div style={styles.page}>
                <h1>Analytics</h1>
                <div style={styles.error}>{error}</div>
            </div>
        );
    }

    if (sensors.length === 0) {
        return (
            <div style={styles.page}>
                <h1>Analytics</h1>
                <div style={styles.loading}>
                    Waiting for sensor data...
                </div>
            </div>
        );
    }

    // Remove duplicate readings
    const uniqueSensors = sensors.filter(
        (sensor, index, self) =>
            index ===
            self.findIndex(
                (item) =>
                    item.timestamp === sensor.timestamp
            )
    );

    const temperatures = uniqueSensors.map(
        (sensor) => sensor.temperature
    );

    const humidities = uniqueSensors.map(
        (sensor) => sensor.humidity
    );

    const smokeValues = uniqueSensors.map(
        (sensor) => sensor.smoke
    );

    const occupancies = uniqueSensors.map(
        (sensor) => sensor.occupancy
    );

    const average = (values) =>
        values.reduce((sum, value) => sum + value, 0) /
        values.length;

    const max = (values) => Math.max(...values);

    const min = (values) => Math.min(...values);

    const warningCount = uniqueSensors.filter(
        (sensor) =>
            sensor.smoke >= 0.8 ||
            sensor.temperature >= 38 ||
            sensor.occupancy >= 45
    ).length;

    // Chart data
    const chartData = [...uniqueSensors]
        .reverse()
        .map((sensor) => ({
            time: new Date(
                sensor.timestamp
            ).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
            }),
            temperature: sensor.temperature,
            humidity: sensor.humidity,
            smoke: sensor.smoke,
            occupancy: sensor.occupancy,
        }));

    const warningPercentage =
        (warningCount / uniqueSensors.length) * 100;

    return (
        <div style={styles.page}>

            {/* HEADER */}
            <div style={styles.header}>
                <div>
                    <h1 style={styles.title}>
                        Analytics
                    </h1>

                    <p style={styles.subtitle}>
                        Historical emergency and sensor analytics
                    </p>
                </div>

                <div style={styles.liveBadge}>
                    <span style={styles.dot}>●</span>
                    LIVE DATA
                </div>
            </div>

            {/* SUMMARY CARDS */}
            <div style={styles.statsGrid}>

                <div style={styles.statCard}>
                    <div style={styles.statIcon}>🌡️</div>
                    <p style={styles.statLabel}>
                        Avg Temperature
                    </p>

                    <h2 style={styles.statValue}>
                        {average(temperatures).toFixed(2)}°C
                    </h2>

                    <small style={styles.statSub}>
                        Range {min(temperatures).toFixed(1)}° -
                        {max(temperatures).toFixed(1)}°
                    </small>
                </div>

                <div style={styles.statCard}>
                    <div style={styles.statIcon}>💧</div>
                    <p style={styles.statLabel}>
                        Avg Humidity
                    </p>

                    <h2 style={styles.statValue}>
                        {average(humidities).toFixed(2)}%
                    </h2>

                    <small style={styles.statSub}>
                        Environmental condition
                    </small>
                </div>

                <div style={styles.statCard}>
                    <div style={styles.statIcon}>💨</div>
                    <p style={styles.statLabel}>
                        Avg Smoke
                    </p>

                    <h2 style={styles.statValue}>
                        {average(smokeValues).toFixed(2)}
                    </h2>

                    <small style={styles.statSub}>
                        0 - 1 scale
                    </small>
                </div>

                <div style={styles.statCard}>
                    <div style={styles.statIcon}>👥</div>
                    <p style={styles.statLabel}>
                        Avg Occupancy
                    </p>

                    <h2 style={styles.statValue}>
                        {average(occupancies).toFixed(1)}
                    </h2>

                    <small style={styles.statSub}>
                        People detected
                    </small>
                </div>

            </div>

            {/* EMERGENCY SUMMARY */}
            <div style={styles.emergencyCard}>

                <div>
                    <p style={styles.emergencyLabel}>
                        Emergency Analysis
                    </p>

                    <h2 style={styles.warningNumber}>
                        {warningCount}
                    </h2>

                    <p style={styles.emergencyText}>
                        Warning readings detected
                    </p>
                </div>

                <div style={styles.emergencyRight}>
                    <div style={styles.progressBackground}>
                        <div
                            style={{
                                ...styles.progress,
                                width: `${Math.min(
                                    warningPercentage,
                                    100
                                )}%`,
                            }}
                        />
                    </div>

                    <span>
                        {warningPercentage.toFixed(1)}% of readings
                    </span>
                </div>

            </div>

            {/* TEMPERATURE CHART */}
            <div style={styles.chartCard}>

                <div style={styles.chartHeader}>
                    <div>
                        <h2 style={styles.chartTitle}>
                            🌡️ Temperature Trend
                        </h2>

                        <p style={styles.chartSubtitle}>
                            Temperature variation over recent readings
                        </p>
                    </div>

                    <span style={styles.chartUnit}>
                        °C
                    </span>
                </div>

                <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={chartData}>
                        <CartesianGrid
                            strokeDasharray="3 3"
                            stroke="#334155"
                        />

                        <XAxis
                            dataKey="time"
                            stroke="#94a3b8"
                        />

                        <YAxis
                            stroke="#94a3b8"
                        />

                        <Tooltip
                            contentStyle={{
                                background: "#0f172a",
                                border: "1px solid #334155",
                                borderRadius: "10px",
                                color: "#fff",
                            }}
                        />

                        <Line
                            type="monotone"
                            dataKey="temperature"
                            stroke="#f97316"
                            strokeWidth={3}
                            dot={false}
                            activeDot={{ r: 6 }}
                        />
                    </LineChart>
                </ResponsiveContainer>

            </div>

            {/* SMOKE + OCCUPANCY */}
            <div style={styles.twoColumn}>

                <div style={styles.chartCard}>

                    <div style={styles.chartHeader}>
                        <div>
                            <h2 style={styles.chartTitle}>
                                💨 Smoke Levels
                            </h2>

                            <p style={styles.chartSubtitle}>
                                Fire/smoke risk indicator
                            </p>
                        </div>
                    </div>

                    <ResponsiveContainer width="100%" height={280}>
                        <LineChart data={chartData}>
                            <CartesianGrid
                                strokeDasharray="3 3"
                                stroke="#334155"
                            />

                            <XAxis
                                dataKey="time"
                                stroke="#94a3b8"
                            />

                            <YAxis
                                domain={[0, 1]}
                                stroke="#94a3b8"
                            />

                            <Tooltip
                                contentStyle={{
                                    background: "#0f172a",
                                    border: "1px solid #334155",
                                    borderRadius: "10px",
                                }}
                            />

                            <Line
                                type="monotone"
                                dataKey="smoke"
                                stroke="#ef4444"
                                strokeWidth={3}
                                dot={false}
                            />
                        </LineChart>
                    </ResponsiveContainer>

                </div>

                <div style={styles.chartCard}>

                    <div style={styles.chartHeader}>
                        <div>
                            <h2 style={styles.chartTitle}>
                                👥 Occupancy Trend
                            </h2>

                            <p style={styles.chartSubtitle}>
                                People detected over time
                            </p>
                        </div>
                    </div>

                    <ResponsiveContainer width="100%" height={280}>
                        <BarChart data={chartData}>
                            <CartesianGrid
                                strokeDasharray="3 3"
                                stroke="#334155"
                            />

                            <XAxis
                                dataKey="time"
                                stroke="#94a3b8"
                            />

                            <YAxis
                                stroke="#94a3b8"
                            />

                            <Tooltip
                                contentStyle={{
                                    background: "#0f172a",
                                    border: "1px solid #334155",
                                    borderRadius: "10px",
                                }}
                            />

                            <Bar
                                dataKey="occupancy"
                                fill="#38bdf8"
                                radius={[5, 5, 0, 0]}
                            />
                        </BarChart>
                    </ResponsiveContainer>

                </div>

            </div>

            {/* RECENT HISTORY */}
            <div style={styles.historyCard}>

                <h2 style={styles.chartTitle}>
                    📊 Recent Sensor History
                </h2>

                <div style={styles.table}>

                    <div style={styles.tableHeader}>
                        <span>Time</span>
                        <span>Temperature</span>
                        <span>Humidity</span>
                        <span>Smoke</span>
                        <span>Occupancy</span>
                    </div>

                    {uniqueSensors
                        .slice(0, 10)
                        .map((sensor) => {

                            const warning =
                                sensor.smoke >= 0.8 ||
                                sensor.temperature >= 38 ||
                                sensor.occupancy >= 45;

                            return (
                                <div
                                    key={sensor.timestamp}
                                    style={{
                                        ...styles.row,
                                        background: warning
                                            ? "#29161a"
                                            : "transparent",
                                    }}
                                >
                                    <span>
                                        {new Date(
                                            sensor.timestamp
                                        ).toLocaleTimeString()}
                                    </span>

                                    <span>
                                        {sensor.temperature} °C
                                    </span>

                                    <span>
                                        {sensor.humidity} %
                                    </span>

                                    <span
                                        style={{
                                            color:
                                                sensor.smoke >= 0.8
                                                    ? "#f87171"
                                                    : "#e2e8f0",
                                        }}
                                    >
                                        {sensor.smoke}
                                    </span>

                                    <span
                                        style={{
                                            color:
                                                sensor.occupancy >= 45
                                                    ? "#f87171"
                                                    : "#e2e8f0",
                                        }}
                                    >
                                        {sensor.occupancy}
                                    </span>
                                </div>
                            );
                        })}

                </div>

            </div>

            <p style={styles.refresh}>
                Automatically updating every 5 seconds •{" "}
                {uniqueSensors.length} unique readings
            </p>

        </div>
    );
}

const styles = {

    page: {
        minHeight: "100vh",
        padding: "30px",
        background: "#0f172a",
        color: "#f8fafc",
        boxSizing: "border-box",
    },

    header: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "30px",
    },

    title: {
        margin: 0,
        fontSize: "34px",
        fontWeight: "700",
    },

    subtitle: {
        marginTop: "8px",
        color: "#94a3b8",
    },

    liveBadge: {
        background: "#103b2a",
        color: "#4ade80",
        padding: "10px 18px",
        borderRadius: "20px",
        fontWeight: "700",
        fontSize: "13px",
    },

    dot: {
        marginRight: "7px",
    },

    statsGrid: {
        display: "grid",
        gridTemplateColumns:
            "repeat(auto-fit, minmax(220px, 1fr))",
        gap: "20px",
        marginBottom: "25px",
    },

    statCard: {
        background: "#1e293b",
        border: "1px solid #334155",
        borderRadius: "16px",
        padding: "22px",
    },

    statIcon: {
        fontSize: "28px",
        marginBottom: "12px",
    },

    statLabel: {
        margin: 0,
        color: "#94a3b8",
        fontSize: "14px",
    },

    statValue: {
        margin: "8px 0",
        fontSize: "30px",
    },

    statSub: {
        color: "#64748b",
    },

    emergencyCard: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: "30px",
        background: "#29161a",
        border: "1px solid #7f1d1d",
        borderRadius: "16px",
        padding: "25px",
        marginBottom: "25px",
    },

    emergencyLabel: {
        margin: 0,
        color: "#fca5a5",
        fontSize: "14px",
    },

    warningNumber: {
        margin: "5px 0",
        fontSize: "36px",
        color: "#f87171",
    },

    emergencyText: {
        margin: 0,
        color: "#cbd5e1",
    },

    emergencyRight: {
        minWidth: "250px",
        color: "#fca5a5",
        fontSize: "13px",
    },

    progressBackground: {
        height: "8px",
        background: "#451a1a",
        borderRadius: "10px",
        overflow: "hidden",
        marginBottom: "8px",
    },

    progress: {
        height: "100%",
        background: "#ef4444",
        borderRadius: "10px",
    },

    chartCard: {
        background: "#1e293b",
        border: "1px solid #334155",
        borderRadius: "16px",
        padding: "25px",
        marginBottom: "25px",
    },

    chartHeader: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "15px",
    },

    chartTitle: {
        margin: 0,
        fontSize: "20px",
    },

    chartSubtitle: {
        marginTop: "6px",
        color: "#64748b",
        fontSize: "13px",
    },

    chartUnit: {
        color: "#94a3b8",
        fontSize: "13px",
    },

    twoColumn: {
        display: "grid",
        gridTemplateColumns:
            "repeat(auto-fit, minmax(400px, 1fr))",
        gap: "25px",
    },

    historyCard: {
        background: "#1e293b",
        border: "1px solid #334155",
        borderRadius: "16px",
        padding: "25px",
        marginTop: "0",
    },

    table: {
        width: "100%",
        overflowX: "auto",
        marginTop: "20px",
    },

    tableHeader: {
        display: "grid",
        gridTemplateColumns:
            "1.3fr 1fr 1fr 1fr 1fr",
        minWidth: "650px",
        gap: "15px",
        padding: "14px 10px",
        color: "#94a3b8",
        fontSize: "13px",
        borderBottom: "1px solid #334155",
    },

    row: {
        display: "grid",
        gridTemplateColumns:
            "1.3fr 1fr 1fr 1fr 1fr",
        minWidth: "650px",
        gap: "15px",
        padding: "14px 10px",
        borderBottom: "1px solid #273449",
        color: "#e2e8f0",
        fontSize: "14px",
    },

    error: {
        background: "#3b1111",
        color: "#ff8080",
        padding: "15px",
        borderRadius: "10px",
    },

    loading: {
        padding: "40px",
        textAlign: "center",
        color: "#94a3b8",
    },

    refresh: {
        textAlign: "right",
        color: "#64748b",
        fontSize: "12px",
        marginTop: "15px",
    },
};

export default Analytics;