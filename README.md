<h1 align="center">SpotFinder Edge Gateway</h1>

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Flask-REST-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask" />
  <img src="https://img.shields.io/badge/Peewee-SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="Peewee + SQLite" />
  <img src="https://img.shields.io/badge/Architecture-DDD%20Bounded%20Contexts-blue?style=flat-square" alt="DDD" />
</div>

---

`spotfinder-edge-gateway` is the **edge component** of the SpotFinder smart-parking
platform. It runs on a machine inside the parking facility (a laptop or a
Raspberry Pi on the same Wi-Fi/LAN as the IoT nodes) and sits **between the ESP32
nodes and the cloud backend** (Spring Boot).

Its job is to:

1. **Authenticate** each IoT node (`device_id` + `X-API-Key`).
2. **Ingest** raw sensor readings from the nodes over HTTP/REST.
3. **Process at the edge** — turn noisy raw readings into stable decisions:
   - debounce occupancy so a pedestrian or a stray echo does not flip a slot
     (the *"sustained > 2 s"* rule that the report's §5.6 describes), and
   - evaluate MQ-2 gas levels against the emergency threshold.
4. (Next step) **Forward** the consolidated events to the SpotFinder cloud backend.

> This repository was scaffolded using another team's IoT project (uFlex) **only
> as a structural reference**. The domain here is parking — occupancy and
> emergency — not their rehabilitation context.

## Why an edge gateway?

The ESP32 nodes are deliberately dumb: they read sensors and drive LEDs/servo.
Putting the *decision* logic (debounce, thresholds, aggregation) on the edge
instead of on every node means:

- one consistent rule for the whole floor (no firmware reflash to tune a threshold),
- the cloud backend receives clean, consolidated events instead of raw spam,
- the floor keeps working (LED guidance, barrier) even if the internet/cloud is down.

This is exactly the "Edge Server" that the SpotFinder C4 Container/Component
diagrams already show — this repo makes it real. (Note: it speaks **HTTP/REST**,
not MQTT; see *Architecture decisions* below.)

## Current scope

- **Implemented**
  - node (IoT Kit) registration + `device_id` + `X-API-Key` authentication
  - ingestion of occupancy readings (`distance_cm`) with UTC timestamp normalization
  - occupancy debounce → stable `AVAILABLE` / `OCCUPIED` / `TRANSITION` + `led_action`
  - MQ-2 gas threshold evaluation → `NORMAL` / `EMERGENCY` + `actuator_action`
  - SQLite persistence (Peewee ORM) of raw readings
  - health check (`GET /status`)
  - **forwarding consolidated events to the SpotFinder cloud backend** on stable
    status change / gas emergency (`POST /api/v1/sensor-readings`,
    `/api/v1/emergency/alerts`) — enabled by setting `SPOTFINDER_BACKEND_URL`
- **Not implemented yet (next steps)**
  - the Access Control flow (barrier sessions / payment) — kept out on purpose
  - a secure node-provisioning flow (replace the hard-coded dev key)

## Bounded contexts

| Context | Core concept | Responsibility |
|---|---|---|
| **IAM** | `Node` | Identify and authenticate IoT nodes by `device_id` + `X-API-Key` |
| **Monitoring** | `SensorReading` | Ingest occupancy/gas readings and derive stable decisions |

Each context follows the same DDD layering: `domain/` (entities + rules),
`application/` (use cases), `infrastructure/` (Peewee models + repositories),
`interfaces/` (Flask endpoints).

## Project structure

```text
spotfinder-edge-gateway/
├── app.py                     # Flask entry point, blueprint registration, DB bootstrap
├── iam/                       # node authentication bounded context
│   ├── domain/ application/ infrastructure/ interfaces/
├── monitoring/                # occupancy + gas bounded context (the edge logic)
│   ├── domain/ application/ infrastructure/ interfaces/
├── shared/infrastructure/     # SQLite database handle + init
└── docs/                      # API contract + edge design
```

## Tech stack

Python 3.11+ · Flask · Peewee · SQLite · python-dateutil
(exact versions in [`requirements.txt`](requirements.txt))

## Getting started

```sh
python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell
# source .venv/bin/activate   # Linux / macOS
pip install -r requirements.txt
python app.py                 # serves on http://0.0.0.0:5000 (debug)
```

The gateway listens on `0.0.0.0:5000` so the ESP32 nodes can reach the laptop by
its **LAN IP** (run `ipconfig` to find it). From a Wokwi simulation use the host
`host.wokwi.internal`.

### Dev test node (local only)

Seeded automatically on first request:

- `device_id`: `spotfinder-node-001`
- `api_key`: `test-api-key-123`

> Hard-coded for local development only. Do not reuse in production.

## API contract (summary)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/api/v1/monitoring/sensor-readings` | Yes | Ingest one occupancy reading |
| `GET`  | `/api/v1/monitoring/occupancy` | No | Debounced slot status + LED action |
| `GET`  | `/api/v1/monitoring/sensor-readings` | No | List recent raw readings |
| `POST` | `/api/v1/monitoring/gas-analysis` | Yes | Gas level → emergency decision |
| `GET`  | `/status` | No | Health check |

Full request/response details: [`docs/parking-monitoring-api.md`](docs/parking-monitoring-api.md).

### Quick example

```sh
curl -X POST http://127.0.0.1:5000/api/v1/monitoring/sensor-readings \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-api-key-123" \
  -d '{"device_id":"spotfinder-node-001","slot_id":"B2-A01","distance_cm":87.5}'

curl "http://127.0.0.1:5000/api/v1/monitoring/occupancy?device_id=spotfinder-node-001&slot_id=B2-A01"
```

## How it fits the SpotFinder ecosystem

```
ESP32 nodes ──HTTP POST (X-API-Key)──▶ EDGE GATEWAY ──(next step)──▶ Spring Boot backend
 (occupancy / gas)                      debounce + threshold          /api/v1/sensor-readings
                                        + decision (LED/EVACUATE)     /api/v1/emergency/alerts
```

- **Embedded app** (ESP32 firmware): [`SpotFinder-EmbeddedApp`](https://github.com/ParkSenseIoT/SpotFinder-EmbeddedApp).
- **Cloud backend**: `SpotFinder-Backend` (Spring Boot, already exists).

To enable forwarding, set the backend URL before launching:

```sh
# Windows PowerShell
$env:SPOTFINDER_BACKEND_URL = "http://192.168.1.40:8080"
python app.py
```

Leave `SPOTFINDER_BACKEND_URL` unset to run the edge fully offline (local
decisions only).

## License

MIT — see [`LICENSE.md`](LICENSE.md).
