import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";

import AIInsights from "./pages/AIInsights";
import Analytics from "./pages/Analytics";
import Dashboard from "./pages/Dashboard";
import Evacuation from "./pages/Evacuation";
import Monitoring from "./pages/Monitoring";
import Simulation from "./pages/Simulation";

import "./App.css";

function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-icon">E</div>

        <div>
          <h1>EVAC-TWIN</h1>
          <span>Emergency Intelligence</span>
        </div>
      </div>

      <nav className="navigation">

        <div className="nav-section">
          COMMAND CENTER
        </div>

        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            `nav-item ${isActive ? "active" : ""}`
          }
        >
          <span>◈</span>
          Overview
        </NavLink>

        <NavLink
          to="/monitoring"
          className={({ isActive }) =>
            `nav-item ${isActive ? "active" : ""}`
          }
        >
          <span>⌁</span>
          Live Monitoring
        </NavLink>

        <NavLink
          to="/evacuation"
          className={({ isActive }) =>
            `nav-item ${isActive ? "active" : ""}`
          }
        >
          <span>◎</span>
          Evacuation
        </NavLink>

        <NavLink
          to="/simulation"
          className={({ isActive }) =>
            `nav-item ${isActive ? "active" : ""}`
          }
        >
          <span>◇</span>
          Simulation
        </NavLink>

        <div className="nav-section intelligence">
          INTELLIGENCE
        </div>

        <NavLink
          to="/ai-insights"
          className={({ isActive }) =>
            `nav-item ${isActive ? "active" : ""}`
          }
        >
          <span>⌁</span>
          AI Insights
        </NavLink>

        <NavLink
          to="/analytics"
          className={({ isActive }) =>
            `nav-item ${isActive ? "active" : ""}`
          }
        >
          <span>▦</span>
          Analytics
        </NavLink>

      </nav>

      <div className="system-card">
        <div className="system-status-dot"></div>

        <div>
          <strong>System Operational</strong>
          <span>All services online</span>
        </div>
      </div>
    </aside>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">

        <Sidebar />

        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/monitoring" element={<Monitoring />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/evacuation" element={<Evacuation />} />
            <Route path="/simulation" element={<Simulation />} />
            <Route path="/ai-insights" element={<AIInsights />} />
          </Routes>
        </main>

      </div>
    </BrowserRouter>
  );
}

export default App;