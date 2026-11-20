"""
EVAC-TWIN Jupyter Notebook Generator
------------------------------------
Run this script from the EVAC-TWIN project root:

    python create_evactwin_flow_notebook.py

It creates EVAC_TWIN_Execution_Flow.ipynb in the project root.
It reads project files but does NOT modify them or start any services.
Only Python standard-library modules are required to generate the notebook.
"""

from pathlib import Path
import json
import textwrap
from datetime import datetime

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "EVAC_TWIN_Execution_Flow.ipynb"

# Candidate virtual-environment locations are documented and checked in the notebook.
VENV_CANDIDATES = [
    ROOT / ".venv",
    ROOT / "backend" / ".venv",
    ROOT.parent / ".venv",
]

def md(source):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": textwrap.dedent(source).strip("\n").splitlines(keepends=True),
    }


def code(source, language="python"):
    # Source files are displayed as Markdown, never executed.
    fence = "````" if "```" in source else "```"

    rendered = (
        f"{fence}{language}\n"
        f"{source.rstrip()}\n"
        f"{fence}"
    )

    return {
        "cell_type": "markdown",
        "metadata": {
            "evactwin_role": "source_reference",
            "language": language
        },
        "source": rendered.splitlines(keepends=True),
    }


def py_check(source):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {"evactwin_role": "optional_diagnostic"},
        "outputs": [],
        "source": textwrap.dedent(source).strip("\n").splitlines(keepends=True),
    }

def read_text(relative):
    path = ROOT / relative
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")

def add_source_section(cells, relative, title=None, language=None, max_lines=None):
    content = read_text(relative)
    cells.append(md(f"""
    ### {title or relative}

    **File:** `{relative}`

    This is the actual project source copied into the notebook for inspection.
    It is a reference section, not an instruction to execute the entire file in a notebook cell.
    """))
    if content is None:
        cells.append(md(f"> File not found at generation time: `{relative}`. The notebook generator continues; add the file and run this generator again to include it."))
        return
    lines = content.splitlines(keepends=True)
    if max_lines and len(lines) > max_lines:
        cells.append(md(f"> This file has {len(lines)} lines and is split into numbered reference sections of at most {max_lines} lines. All lines are included."))
        for start in range(0, len(lines), max_lines):
            end = min(start + max_lines, len(lines))
            cells.append(md(f"#### {relative} — lines {start + 1}–{end}"))
            cells.append(code("".join(lines[start:end]), language or ("python" if relative.endswith(".py") else "text")))
    else:
        cells.append(code(content, language or ("python" if relative.endswith(".py") else "text")))

cells = []

cells.append(md("""
# EVAC-TWIN
## Complete Project Architecture, Connectivity, Training and Execution Notebook

**Project title:** Digital Twin-Based Intelligent Emergency Response and Evacuation System

**Purpose of this notebook:** explain the complete project structure, data flow, model-training workflow, deployment flow, API connectivity, route planning and frontend integration. It also embeds the current source files found in the project folder for review.

> **Important:** This notebook is a technical walkthrough and source-code companion. It does not automatically start services when opened. It provides optional cells to start and stop FastAPI and the IoT simulator. MongoDB, Mosquitto and the React frontend must be started separately. Training jobs must be started deliberately.
"""))

cells.append(md("""
## 1. How to use this notebook

1. Read the architecture and execution-order sections first.
2. Confirm the project root and environment paths.
3. Start MongoDB and Mosquitto outside Jupyter.
4. Use the optional notebook cells to start FastAPI and the IoT simulator, or start them in separate terminals. Start the React frontend in a separate terminal.
5. Use the optional diagnostic cells only when the relevant service is already running.
6. Read the source-reference sections to inspect the actual implementation.
7. Training scripts are included as source references. Run them from the backend package context only when intentionally retraining.

Cells marked **SOURCE REFERENCE** contain original Python or JavaScript source. They are not ordinary notebook exercises and should not be run as Python cells. JavaScript/JSX is shown as fenced text in Markdown cells.
"""))

cells.append(md("""
## 2. Project architecture at a glance

```text
                         BUILDING ALPHA DIGITAL TWIN
                 Static topology + dynamic virtual sensor state
                                  |
                                  v
                      Virtual IoT Sensor Simulator
                         (12 zones / 3 floors)
                                  |
                       MQTT publish: JSON messages
                                  |
                                  v
                    Mosquitto Broker (localhost:1883)
                     Topic: evac-twin/sensors
                                  |
                                  v
                    FastAPI MQTT Subscriber
                    (backend/app/mqtt_subscriber.py)
                       |          |          |
                       |          |          +--> Emergency alert / SMS
                       |          |
                       |          +--> FireModel (6 sensor features)
                       |
                       +--> RiskNet (4 sensor features)
                                  |
                                  v
                       MongoDB: evac_twin
                  sensors / events / buildings / contacts
                                  |
                    +-------------+--------------+
                    |                            |
                    v                            v
             FastAPI REST API              Routing services
             (port 8001)                   Dijkstra / BFS / DFS / A*
                    |                            |
                    +-------------+--------------+
                                  |
                                  v
                         React + Vite Frontend
                            (port 5173)
                    Dashboard / Monitoring / Evacuation
                    Simulation / AI Insights / Analytics
```

### Main connectivity chain

**Sensor → MQTT → Subscriber → AI prediction → MongoDB → FastAPI endpoints → frontend API service → React pages.**

For evacuation, the backend combines the static building graph with current zone-risk data. The production route calculation uses Dijkstra with risk-aware edge costs. BFS, DFS and A* are available for algorithm comparison.
"""))

cells.append(md("""
## 3. Main project folders

The generator discovers files from the current project folder. The expected layout is broadly:

```text
EVAC-TWIN/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── building_layout.py
│   │   ├── building_structure.py
│   │   ├── iot_simulator.py
│   │   ├── mqtt_subscriber.py
│   │   ├── risk_engine.py
│   │   ├── ml/
│   │   │   ├── predict.py
│   │   │   ├── fire_predict.py
│   │   │   ├── train_risk_model.py
│   │   │   ├── train_fire_model.py
│   │   │   ├── compare_models.py
│   │   │   └── compare_dl_models.py
│   │   ├── routing/
│   │   └── services/
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── package.json
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── services/api.js
│       └── pages/
├── datasets/
├── models/
├── run_evactwin.bat
└── create_evactwin_flow_notebook.py
```

Actual filenames can differ. The source inventory near the end lists the files that were found when this notebook was generated.
"""))

cells.append(md("""
## 4. Component responsibilities

| Component | Responsibility | Connects to |
|---|---|---|
| `building_layout.py` | Building Alpha rooms, corridors, stairs, exits and graph edges | Routing service |
| `iot_simulator.py` | Generates virtual sensor readings for zones and publishes JSON | Mosquitto |
| Mosquitto | MQTT message broker | Simulator and subscriber |
| `mqtt_subscriber.py` | Receives readings, invokes predictions, handles events/alerts and stores readings | MQTT, models, MongoDB, routing, SMS |
| `predict.py` | Four-feature multi-class building risk prediction | Risk model artifacts |
| `fire_predict.py` | Six-feature binary fire-alarm prediction | Fire model artifacts |
| `database.py` | MongoDB client, collections and indexes | MongoDB |
| `sensor_service.py` | Retrieves/enriches latest zone readings and history | MongoDB, risk prediction |
| `routing_service.py` | Risk-aware graph route calculation and algorithm comparisons | Building topology, sensor risk |
| `evacuation_router.py` | REST endpoints for routes, exits, summaries and simulations | Routing and sensor services |
| `main.py` | FastAPI app, API endpoints and MQTT subscriber lifecycle | All backend services |
| `frontend/src/services/api.js` | HTTP communication from React to FastAPI | FastAPI |
| React pages | Present monitoring, insights, evacuation, simulation and analytics | API service |

`building_structure.py` is a compatibility module that imports the topology from `building_layout.py`; it intentionally does not define a second building graph.
"""))

cells.append(md("""
## 5. Digital Twin representation

The Building Alpha representation has two complementary parts:

- **Static building model:** room/zone identifiers, floors, corridors, stairs, exits and graph connectivity are defined in `building_layout.py`.
- **Dynamic building state:** virtual IoT readings (temperature, humidity, smoke, occupancy and fire-related air-quality features) update over MQTT and are stored in MongoDB.

The routing engine combines the static graph with current sensor-derived risk values. Therefore, the route can change as zone conditions change. The simulator is a virtual sensor source; it does not mean physical sensors are installed in the building.
"""))

cells.append(md("""
## 6. Risk and fire prediction models

### 6.1 Overall zone-risk model

The deployed risk model uses four inputs:

1. `temperature`
2. `humidity`
3. `smoke`
4. `occupancy`

The supplied `risk_config.json` describes an MLP with input size 4, hidden sizes `[64, 32]`, and four output classes: `CRITICAL`, `HIGH`, `LOW`, `MODERATE`.

The deployed prediction code loads the trained model/scaler artifacts, predicts class probabilities and combines the model result with a rule-based safety check. If model artifacts cannot be loaded, the code has a fallback prediction path. The exact runtime result depends on the artifacts present in the local project.
"""))

cells.append(md("""
### 6.2 Fire-alarm model

The separate fire model uses six features:

- `Temperature[C]`
- `Humidity[%]`
- `TVOC[ppb]`
- `eCO2[ppm]`
- `PM1.0`
- `PM2.5`

The supplied fire configuration contains calibration temperature `0.8120764493942261` and threshold `0.5`. The subscriber also applies its own final probability gate (80% in the reviewed implementation) before treating a prediction as a final fire alarm. This is distinct from the four-feature zone-risk classifier.
"""))

cells.append(md("""
### 6.3 Model training, comparison and deployment are different

| Workflow | Purpose | Main files |
|---|---|---|
| Train risk model | Train the multi-class risk classifier | `train_risk_model.py` (and any older/alternate `train_model.py`) |
| Train fire model | Train the binary fire classifier | `train_fire_model.py` |
| Compare models | Compare candidate ML/DL models on the fire dataset | `compare_models.py`, `compare_dl_models.py` |
| Deploy predictions | Load saved model artifacts for live readings | `predict.py`, `fire_predict.py` |

A model with the best comparison score is **not automatically deployed**. Deployment changes only when the training/deployment code and compatible saved artifacts are deliberately updated.

`compare_models.py` compares Random Forest, Logistic Regression, KNN, SVM, MLP, TabNet, FT-Transformer and SAINT-style Transformer. `compare_dl_models.py` trains/evaluates TabNet separately. These comparison scripts are offline experiments, not part of the per-message MQTT prediction path.
"""))

cells.append(md("""
## 7. Sensor message flow in detail

1. The simulator creates a payload for a zone. The reviewed simulator generates readings for 12 zones across three floors and publishes repeatedly (default interval: 3 seconds).
2. The payload is published to the MQTT topic `evac-twin/sensors` on `localhost:1883`.
3. FastAPI startup starts the MQTT subscriber. The subscriber receives and decodes each JSON message.
4. It normalizes sensor fields and invokes the four-feature risk predictor.
5. When all six fire-model features are available, it invokes the separate fire predictor.
6. It creates or updates emergency/risk events and applies duplicate-alert protection.
7. For qualifying emergencies, it can calculate evacuation routes and attempt to send an SMS alert.
8. The processed sensor record is inserted into MongoDB.
9. REST endpoints expose the latest sensor intelligence, history, events, building summary and evacuation information.
10. React pages poll the backend APIs and render the current state.
"""))

cells.append(md("""
## 8. MongoDB data layer

Reviewed default settings:

- MongoDB URI: `mongodb://127.0.0.1:27017`
- Database: `evac_twin`
- Collections: `sensors`, `events`, `buildings`, `emergency_contacts`

The application code creates indexes when the database module is imported. A MongoDB client object being constructed does not, by itself, prove that the server is reachable. Use the explicit ping/health diagnostic after MongoDB is running.

The notebook does not create or delete database data automatically.
"""))

cells.append(md("""
## 9. Risk-aware evacuation routing

The building graph is constructed from the topology in `building_layout.py`. The routing service applies risk-dependent costs to graph nodes/edges. Critical-risk rooms can be blocked as route destinations (except the starting room handling), while high/moderate/unknown-risk areas receive penalties or caution treatment.

- **Production route:** `shortest_path()` uses Dijkstra with risk-aware costs.
- **BFS / DFS / A*:** used for comparison and analysis.
- **Route status:** AVAILABLE, CAUTION or BLOCKED.
- **Exit selection:** routes to the available exits are evaluated and a recommended exit is selected using route/risk scores.

The React frontend visualizes route data returned by the backend; it is not the source of the Dijkstra calculation.
"""))

cells.append(md("""
## 10. Frontend connectivity

```text
frontend/index.html
        |
        v
frontend/src/main.jsx
        |
        v
frontend/src/App.jsx
        |
        +--> Dashboard
        +--> Monitoring
        +--> Evacuation
        +--> Simulation
        +--> AI Insights
        +--> Analytics
                    |
                    v
          frontend/src/services/api.js
                    |
          HTTP requests to localhost:8001
                    |
                    v
              FastAPI backend
```

`vite.config.js` enables the React plugin. The reviewed configuration does not define a development proxy; `api.js` uses the backend base URL directly. `index.html` provides the `root` element and loads `src/main.jsx`.
"""))

cells.append(md("""
## 11. API endpoints to know

The reviewed backend exposes these main routes (confirm the current local code if it has changed):

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Backend service information |
| GET | `/api/health` | Backend, database and subsystem health |
| GET | `/api/sensors` | Latest zone sensor intelligence |
| GET | `/api/sensors/history` | Sensor history |
| GET | `/api/sensors/{zone_id}` | Latest reading for a zone |
| POST | `/api/ai/predict-risk` | On-demand overall risk prediction |
| GET | `/api/events` | Recent/active events |
| GET | `/api/buildings` | Building topology/data |
| GET | `/api/buildings/summary` | Building-level risk summary |
| GET | `/api/evacuation/topology` | Building route topology |
| GET | `/api/evacuation/routes` | Route data |
| POST | `/api/evacuation/route/{device_id}` | Calculate a zone route |
| POST | `/api/evacuation/compare/{device_id}` | Compare route algorithms |
| GET | `/api/evacuation/summary` | Evacuation summary |
| GET | `/api/evacuation/exits` | Exit information |
| POST | `/api/evacuation/simulation/{device_id}` | Scenario simulation / alert workflow |

FastAPI Swagger documentation is normally available at `http://localhost:8001/docs` while the backend is running.
"""))

cells.append(md("""
## 12. Environment and dependency setup

### 12.1 Find the existing virtual environment

The `.venv` location was reported as **Other / not one of the two standard locations**, so do not assume it is in the root or backend folder. In the next cell, inspect candidate locations and the active Python executable. This cell does not activate or modify an environment.
"""))

cells.append(py_check("""
from pathlib import Path
import sys

root = Path.cwd()
print("Notebook working directory:", root)
print("Active Python:", sys.executable)

candidates = [
    root / ".venv",
    root / "backend" / ".venv",
    root.parent / ".venv",
]
print("\\nCommon .venv candidates:")
for path in candidates:
    print(path, "->", "FOUND" if path.exists() else "not found")

print("\\nIf your environment is elsewhere, use its actual Python executable when launching Jupyter/backend.")
"""))

cells.append(md("""
### 12.2 Backend packages

The supplied `backend/requirements.txt` lists FastAPI, Uvicorn, PyMongo, dotenv, Paho MQTT, scikit-learn, NumPy, pandas, joblib and PyTorch.

Additional imports observed in the source need to be checked against the actual environment:
- `pytorch-tabnet` is required by the model-comparison scripts.
- `requests` may be required by the TextBee SMS service if it is imported by the current implementation.
- Plotting packages such as `matplotlib` (and `seaborn` only if imported) may be required by training/evaluation scripts.

Do not install blindly into a different Python environment. Install missing packages into the environment actually used by the project.
"""))

cells.append(md("""
### 12.3 Frontend packages

The supplied `frontend/package.json` uses React, React DOM, React Router, Vite, the React Vite plugin, Recharts, Three.js-related packages, Lucide React and Oxlint. Install frontend packages from the frontend folder with `npm install` if `node_modules` is absent or dependencies need restoring.
"""))

cells.append(md("""
## 13. Correct service startup order

Start these services in separate terminals. Keep each terminal open while the service is running.

### Step 1 — MongoDB

Start the MongoDB service using the installation/service configuration on the machine. The supplied `run_evactwin.bat` does not start MongoDB.

### Step 2 — Mosquitto broker

```powershell
mosquitto -v
```

Expected broker address: `localhost:1883`.

### Step 3 — FastAPI backend

Open a new terminal. Change to the backend folder and activate the **actual** virtual environment path. Example only, if `.venv` is in the project root:

```powershell
cd C:\\EVAC-TWIN\\backend
..\\.venv\\Scripts\\Activate.ps1
python -m uvicorn app.main:app --reload --port 8001
```

If the environment is elsewhere, replace the activation path with the correct one. The backend startup imports the app and starts the MQTT subscriber through its FastAPI startup lifecycle.

### Step 4 — IoT simulator

Open another terminal:

```powershell
cd C:\\EVAC-TWIN\\backend
..\\.venv\\Scripts\\Activate.ps1
python -m app.iot_simulator
```

The simulator is a separate process. Starting the backend alone does not publish simulated readings.

### Step 5 — React frontend

Open another terminal:

```powershell
cd C:\\EVAC-TWIN\\frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

### Step 6 — Verify

- Backend root: `http://localhost:8001/`
- Backend health: `http://localhost:8001/api/health`
- Swagger UI: `http://localhost:8001/docs`
- Frontend: `http://localhost:5173`

The Vite port can change if 5173 is already occupied; use the URL printed by Vite in that case.
"""))

cells.append(md("""
## 14. About the supplied `run_evactwin.bat`

The reviewed batch file starts Mosquitto, FastAPI, Vite and the simulator in separate command windows, then opens the frontend. It does **not** start MongoDB.

One path needs verification: the batch file changes directory to `C:\\EVAC-TWIN\\backend` and then runs `.\.venv\\Scripts\\activate`. If the environment is in the project root, that relative path is incorrect; from the backend folder the expected relative path is `..\\.venv\\Scripts\\activate`. If the environment is elsewhere, use its actual path. The generator does not edit the batch file.

The launcher contains machine-specific absolute paths (`C:\\EVAC-TWIN` and the Mosquitto installation path). Update those manually if the project is located elsewhere.
"""))

cells.append(md("""
## 15. Start and Stop Background Services

The following cells launch the FastAPI backend and IoT simulator
as separate processes. Their continuous loops will not block
the Jupyter kernel.

Before starting these processes:
1. Start MongoDB.
2. Start Mosquitto.
3. Confirm the required Python environment is active.
"""))

cells.append(py_check("""
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path.cwd()

if not (ROOT / "backend").is_dir():
    raise FileNotFoundError(
        "Backend folder not found. Open Jupyter Notebook from the EVAC-TWIN project root."
    )

BACKGROUND_PROCESSES = {}

def start_background(name, command, working_directory):
    existing = BACKGROUND_PROCESSES.get(name)

    if existing is not None and existing.poll() is None:
        print(name, "is already running. PID:", existing.pid)
        return existing

    process = subprocess.Popen(
        command,
        cwd=str(working_directory)
    )

    BACKGROUND_PROCESSES[name] = process

    print(name, "started.")
    print("PID:", process.pid)

    return process


def start_fastapi():
    return start_background(
        "FastAPI",
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8001"
        ],
        ROOT / "backend"
    )


def start_iot_simulator():
    return start_background(
        "IoT Simulator",
        [
            sys.executable,
            "-m",
            "app.iot_simulator"
        ],
        ROOT / "backend"
    )


def stop_background(name):
    process = BACKGROUND_PROCESSES.get(name)

    if process is None or process.poll() is not None:
        print(name, "is not running.")
        return

    process.terminate()

    try:
        process.wait(timeout=5)
        print(name, "stopped.")
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        print(name, "force stopped.")


def show_process_status():
    for name, process in BACKGROUND_PROCESSES.items():
        status = (
            "RUNNING"
            if process.poll() is None
            else "STOPPED"
        )
        print(name, status, "PID:", process.pid)


print("Background service controls are ready.")
"""))

cells.append(md("""
### Start the backend

Run this cell after MongoDB and Mosquitto are running.
"""))

cells.append(py_check("""
start_fastapi()
"""))

cells.append(md("""
### Start the IoT simulator

Run this cell after the backend has started.
"""))

cells.append(py_check("""
start_iot_simulator()
"""))

cells.append(md("""
### Check running processes
"""))

cells.append(py_check("""
show_process_status()
"""))

cells.append(md("""
### Stop services when testing is complete
"""))

cells.append(py_check("""
stop_background("IoT Simulator")
stop_background("FastAPI")
"""))

cells.append(md("""
## 16. Safe Diagnostic Cells

These cells only inspect connectivity. They do not start or stop services and do not write project files.
"""))

cells.append(py_check("""
# Check whether the backend HTTP service is already running.
# Run only after starting FastAPI in a separate terminal.
from urllib.request import urlopen
from urllib.error import URLError

url = "http://localhost:8001/api/health"
try:
    with urlopen(url, timeout=3) as response:
        print("HTTP status:", response.status)
        print(response.read().decode("utf-8"))
except (URLError, TimeoutError, OSError) as exc:
    print("Backend health endpoint is not reachable:", exc)
    print("Start the FastAPI backend in a separate terminal, then retry.")
"""))

cells.append(py_check("""
# Optional MongoDB ping. Requires pymongo in the active Jupyter environment
# and MongoDB already running locally.
try:
    from pymongo import MongoClient
    client = MongoClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=2500)
    client.admin.command("ping")
    print("MongoDB ping successful.")
    print("Databases:", client.list_database_names())
    client.close()
except Exception as exc:
    print("MongoDB ping failed or pymongo is unavailable:", repr(exc))
"""))

cells.append(py_check("""
# Optional MQTT broker TCP check. This checks the port only;
# it does not publish or subscribe to messages.
import socket

host, port = "127.0.0.1", 1883
sock = socket.socket()
sock.settimeout(2)
try:
    sock.connect((host, port))
    print(f"MQTT broker TCP port is reachable at {host}:{port}")
except OSError as exc:
    print("MQTT broker is not reachable:", exc)
finally:
    sock.close()
"""))




cells.append(md("""
## 17. Training workflow — run deliberately, not during normal startup

The project has separate scripts for risk-model training, fire-model training and model comparison. Training may take time and may overwrite model artifacts used by live prediction. Before training:

1. Confirm the correct dataset exists.
2. Confirm the Python environment has all required packages.
3. Back up existing model/scaler/config artifacts.
4. Confirm which risk training script is the current intended one (`train_risk_model.py` versus any older/alternate `train_model.py`).
5. Run one training script at a time from the correct project context.
6. Check its output metrics and generated artifacts.
7. Verify that deployment code expects the same model architecture, feature order, class order and artifact filenames.

### Example commands (PowerShell)

```powershell
cd C:\\EVAC-TWIN\\backend
# Activate the actual virtual environment first.

python -m app.ml.train_risk_model
python -m app.ml.train_fire_model
python -m app.ml.compare_models
python -m app.ml.compare_dl_models
```

These are examples based on module paths. Check each file's package location and `if __name__ == "__main__"` entry point before running. The comparison scripts are experiments; they are not required to start the live dashboard.
"""))

cells.append(md("""
## 17. Important implementation notes and limitations

- The simulator publishes virtual readings; it is not a physical sensor network.
- MongoDB must be running separately; the provided batch launcher does not start it.
- MQTT broker must be running before the subscriber can receive simulator messages.
- The backend starts the MQTT subscriber during FastAPI startup; the simulator is started separately.
- RiskNet and FireModel are separate models with different feature sets and targets.
- The fire subscriber's final alarm decision includes an additional probability gate.
- The frontend displays backend predictions; frontend rule-based calculations are fallback/preview logic and should not be confused with the deployed PyTorch model.
- The frontend simulation preview, backend on-demand prediction and backend scenario-alert calculation are distinct paths.
- Analytics that fetches `/api/sensors` works on the latest per-zone readings returned by that endpoint; it is not automatically the full historical MongoDB dataset.
- The building topology is defined in `building_layout.py`; `building_structure.py` re-exports it.
- A successful SMS API request does not independently prove that the recipient's phone received the message.
- Model comparison results depend on the dataset, preprocessing, random split, environment and package versions. Do not state performance values unless they are taken from the actual run output.
"""))

cells.append(md("""
## 18. Source code reference library

The following sections embed project source files that exist at notebook-generation time. Python files are included as unexecuted reference cells. JavaScript/JSX, JSON, CSS, HTML and batch files are shown as fenced text in Markdown so they are not mistakenly executed by the Python kernel.

**Long files are split into sequential chunks; all lines are retained.** Re-run the generator after source-code changes to refresh the notebook.
"""))

# Core backend source files
python_files = [
    "backend/app/main.py",
    "backend/app/database.py",
    "backend/app/building_layout.py",
    "backend/app/building_structure.py",
    "backend/app/iot_simulator.py",
    "backend/app/mqtt_subscriber.py",
    "backend/app/risk_engine.py",
    "backend/app/ml/predict.py",
    "backend/app/ml/fire_predict.py",
    "backend/app/ml/zone_risk.py",
    "backend/app/ml/train_risk_model.py",
    "backend/app/ml/train_fire_model.py",
    "backend/app/ml/train_model.py",
    "backend/app/ml/compare_models.py",
    "backend/app/ml/compare_dl_models.py",
    "backend/app/routing/evacuation_router.py",
    "backend/app/services/routing_service.py",
    "backend/app/services/sensor_service.py",
    "backend/app/services/alert_state.py",
    "backend/app/services/sms_service.py",
    "backend/test_routing.py",
    "backend/test_sms.py",
]
for file in python_files:
    add_source_section(cells, file, max_lines=220)

# Config/data/dependency references
text_files = [
    "backend/requirements.txt",
    "backend/app/ml/models/risk_config.json",
    "backend/app/ml/models/fire_alarm_config.json",
    "frontend/package.json",
    "frontend/vite.config.js",
    "frontend/index.html",
    "run_evactwin.bat",
    "CommandsList.txt",
]
for file in text_files:
    content = read_text(file)
    cells.append(md(f"### {file}\n\nConfiguration or command reference."))
    if content is None:
        cells.append(md(f"> File not found at generation time: `{file}`."))
    else:
        lang = "json" if file.endswith(".json") else "powershell" if file.endswith(".bat") else "text"
        cells.append(md(f"```{lang}\n{content.rstrip()}\n```"))

# Frontend JavaScript / JSX / CSS sources as Markdown code fences.
frontend_files = [
    "frontend/src/main.jsx",
    "frontend/src/App.jsx",
    "frontend/src/services/api.js",
    "frontend/src/utils/riskEngine.js",
    "frontend/src/pages/Dashboard.jsx",
    "frontend/src/pages/Monitoring.jsx",
    "frontend/src/pages/Evacuation.jsx",
    "frontend/src/pages/EvacuationMap.jsx",
    "frontend/src/pages/Simulation.jsx",
    "frontend/src/pages/AIInsights.jsx",
    "frontend/src/pages/Analytics.jsx",
    "frontend/src/App.css",
    "frontend/src/index.css",
]
for file in frontend_files:
    content = read_text(file)
    cells.append(md(f"### {file}\n\nFrontend source reference — not executable in this Python notebook."))
    if content is None:
        cells.append(md(f"> File not found at generation time: `{file}`."))
    else:
        lang = "jsx" if file.endswith(".jsx") else "javascript" if file.endswith(".js") else "css"
        lines = content.splitlines(keepends=True)
        chunk_size = 220
        for start in range(0, len(lines), chunk_size):
            end = min(start + chunk_size, len(lines))
            if len(lines) > chunk_size:
                cells.append(md(f"#### Lines {start + 1}–{end}"))
            cells.append(md(f"```{lang}\n{''.join(lines[start:end]).rstrip()}\n```"))

cells.append(md("""
## 19. Project file inventory

This section lists source/configuration files discovered during generation. Dataset files, model binaries, virtual-environment files, `node_modules`, caches and Git internals are intentionally excluded from the source listing because they can be large or machine-specific.
"""))

inventory = []
exclude_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", "dist", "build"}
exclude_suffixes = {".pyc", ".pyo", ".pkl", ".pickle", ".pth", ".pt", ".joblib", ".csv", ".xlsx", ".parquet"}
for path in sorted(ROOT.rglob("*")):
    if not path.is_file():
        continue
    rel_parts = path.relative_to(ROOT).parts
    if any(part in exclude_dirs for part in rel_parts):
        continue
    if path.suffix.lower() in exclude_suffixes:
        continue
    if path.name == OUTPUT.name:
        continue
    if len(rel_parts) > 5:
        continue
    inventory.append(str(path.relative_to(ROOT)).replace("\\", "/"))

cells.append(md("```text\n" + "\n".join(inventory) + "\n```"))

cells.append(md(f"""
## 20. Notebook generation record

- Generated from: `{ROOT}`
- Generated at: `{datetime.now().isoformat(timespec="seconds")}`
- Output: `{OUTPUT.name}`
- Original project files: read-only; not modified by this generator.
- Missing source files: marked in their corresponding sections.
- Rebuild after changing source code by running `python create_evactwin_flow_notebook.py` again.

**End of EVAC-TWIN execution-flow notebook.**
"""))

notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3",
            "mimetype": "text/x-python",
            "file_extension": ".py",
            "pygments_lexer": "ipython3",
            "nbconvert_exporter": "python",
            "codemirror_mode": {"name": "ipython", "version": 3},
        },
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

OUTPUT.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")
print("Notebook generated successfully:")
print(OUTPUT)
print("Cells:", len(cells))
print("Project root:", ROOT)
print("No original project files were modified.")
