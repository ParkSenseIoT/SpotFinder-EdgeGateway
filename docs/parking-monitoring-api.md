# Parking Monitoring API -- Edge Contract

HTTP contract of the **Monitoring** bounded context: what a SpotFinder IoT node
must **send**, what the gateway **returns**, and what the edge **processes** in
between.

> A Parking Spot Node (ESP32 + HC-SR04 + MQ-2) streams raw occupancy distance
> (and, for header nodes, gas level) to this gateway. The gateway authenticates
> the node, stores the raw readings, and turns them into a **stable slot status**
> (debounced) and an **emergency decision** (gas threshold).

Base URL during development: `http://<laptop-LAN-ip>:5000` (the gateway listens
on `0.0.0.0:5000`). From Wokwi, use `http://host.wokwi.internal:5000`.

---

## Endpoint summary

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/api/v1/monitoring/sensor-readings` | Yes | Ingest one raw occupancy reading |
| `GET`  | `/api/v1/monitoring/occupancy` | No | Debounced status (AVAILABLE/OCCUPIED) + LED action |
| `GET`  | `/api/v1/monitoring/sensor-readings` | No | List recent raw readings (debug) |
| `POST` | `/api/v1/monitoring/gas-analysis` | Yes | Gas level → emergency decision |
| `GET`  | `/status` | No | Health check |

Authentication (where required): header `X-API-Key` + `device_id` in the body
must match a registered node. Dev node: `spotfinder-node-001` / `test-api-key-123`.

---

## 1. Ingest a reading -- `POST /api/v1/monitoring/sensor-readings`

The endpoint the **embedded node** calls, once per sample (~1/sec).

**Headers:** `X-API-Key` (required), `Content-Type: application/json`.

**Body**

| Field | Type | Required | Rule |
|-------|------|----------|------|
| `device_id` | string | yes | Must match a registered node |
| `slot_id` | string | yes | Logical slot the node monitors (e.g. `B2-A01`) |
| `distance_cm` | number | yes | HC-SR04 distance in cm |
| `created_at` | string (ISO 8601) | no | Defaults to current UTC if omitted |

```json
{ "device_id": "spotfinder-node-001", "slot_id": "B2-A01", "distance_cm": 87.5 }
```

**Returns**

| Status | When |
|--------|------|
| `201 Created` | Reading stored (echoes the persisted record + UTC `created_at`) |
| `400 Bad Request` | Missing/invalid field |
| `401 Unauthorized` | Missing/invalid `device_id` or `X-API-Key` |

---

## 2. Debounced occupancy -- `GET /api/v1/monitoring/occupancy`

The **core processing output**. Aggregates the slot's recent readings and applies
the *sustained > 2 s* rule before committing to a status.

**Query params:** `device_id` (required), `slot_id` (required), `limit` (optional, default 200).

**Returns `200 OK`**

```json
{
  "device_id": "spotfinder-node-001",
  "slot_id": "B2-A01",
  "status": "OCCUPIED",
  "led_action": "RED",
  "occupied_now": true,
  "held_seconds": 3.4,
  "last_distance_cm": 42.0,
  "sample_count": 12
}
```

| Field | Meaning |
|-------|---------|
| `status` | `AVAILABLE` / `OCCUPIED` once stable, else `TRANSITION` (not held long enough), or `UNKNOWN` (no data) |
| `led_action` | What the node's LED should show: `GREEN` / `RED` / `OFF` |
| `held_seconds` | How long the current condition has continuously held |
| `last_distance_cm` | Most recent raw distance |

---

## 3. List raw readings -- `GET /api/v1/monitoring/sensor-readings`

For a live view / debugging.

**Query params:** `device_id` (required), `slot_id` (required), `limit` (optional, default 100).
**Returns `200 OK`:** JSON array of `{id, device_id, slot_id, distance_cm, created_at}` (chronological).

---

## 4. Gas analysis -- `POST /api/v1/monitoring/gas-analysis`

**Headers:** `X-API-Key`, `Content-Type: application/json`.
**Body:** `{ "device_id": "spotfinder-node-001", "gas_level": 2450 }`

**Returns `200 OK`**

```json
{ "device_id": "spotfinder-node-001", "gas_level": 2450, "threshold": 2200,
  "status": "EMERGENCY", "actuator_action": "EVACUATE" }
```

`status` is `EMERGENCY` when `gas_level > threshold`, else `NORMAL`;
`actuator_action` is `EVACUATE` (buzzer + strobe) or `IDLE`.

---

## 5. Health check -- `GET /status`

```json
{ "status": "ok", "service": "spotfinder-edge-gateway" }
```

---

## End-to-end flow

```
ESP32 node ──POST sensor-readings (X-API-Key, 1/sec)──▶ EDGE ──buffer──▶ SQLite
                                                          │
                       GET /occupancy ──▶ debounce (sustained > 2 s) ──▶ AVAILABLE/OCCUPIED + LED
                       POST /gas-analysis ──▶ threshold ──▶ NORMAL/EMERGENCY + EVACUATE
                                                          │
                                          (next step) ──▶ SpotFinder cloud backend
```

## Configuration & next steps

- **Cloud forwarding (implemented, optional).** Set `SPOTFINDER_BACKEND_URL`
  (e.g. `http://192.168.1.40:8080`) to forward consolidated events to the Spring
  Boot backend on stable status change / gas emergency
  (`/api/v1/sensor-readings`, `/api/v1/emergency/alerts`). Unset = fully offline.
- **Thresholds from the backend (next).** `OCCUPIED_CM`, `SUSTAINED_SECONDS` and
  `GAS_THRESHOLD` are constants today; they are meant to be fetched/cached from the cloud.
- **Access Control.** The barrier flow (sessions, payment) is intentionally out of scope here.
