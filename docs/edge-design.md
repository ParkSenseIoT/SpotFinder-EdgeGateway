# Edge Execution Design

Short rationale for what lives on the edge vs. the node vs. the cloud in SpotFinder.

## Responsibility split

| Layer | Owns | Examples |
|-------|------|----------|
| **Node (ESP32 firmware)** | Sensing + acting. No business decisions. | Read HC-SR04 / MQ-2; drive LED, buzzer, servo on command |
| **Edge gateway (this repo)** | Per-floor decisions + buffering. | Occupancy debounce, gas threshold, consolidation, (next) forwarding |
| **Cloud backend (Spring Boot)** | System of record + cross-floor logic. | Sessions, payments, reservations, analytics, notifications |

Keeping decisions on the edge means the floor keeps guiding drivers (LED) and
running the barrier even when the internet or the cloud is unavailable, and a
threshold change does not require reflashing every node.

## Why HTTP/REST (not MQTT)

The SpotFinder C4 diagrams originally labelled the node→edge link as MQTT. For the
prototype we use plain **HTTP/REST** because:

- the firmware already speaks HTTP (`HTTPClient`), so there is no broker to deploy;
- it is trivial to test with `curl` and Swagger/Scalar;
- one reading per second per node is well within HTTP's comfort zone.

MQTT remains a valid future optimization for large deployments (many nodes, QoS,
last-will). If adopted, only the transport layer changes — the edge's domain
logic stays the same.

## Occupancy debounce (the core rule)

A raw HC-SR04 reading flips around when a person walks past or an echo scatters.
The edge requires the same condition (occupied / free) to hold for
`SUSTAINED_SECONDS` (2 s) before it commits to a status. Until then the status is
`TRANSITION` and the node keeps its previous LED. This is the
"sustained > 2 s" behaviour the report's §5.6 describes but the firmware does not
implement on its own.

## Gas / emergency

A single MQ-2 reading above `GAS_THRESHOLD` (~900 PPM equivalent) yields
`status = EMERGENCY` and `actuator_action = EVACUATE`. In a full deployment the
edge would broadcast EVACUATE to every node on the floor and forward an alert to
the backend's Emergency & Safety context.

## Roadmap

1. **Cloud forwarding** — push consolidated events to the Spring Boot backend.
2. **Backend-driven thresholds** — fetch/cache `OCCUPIED_CM`, `SUSTAINED_SECONDS`,
   `GAS_THRESHOLD` per facility.
3. **Actuator push** — return LED/EVACUATE decisions to the node (today the node polls `/occupancy`).
4. **Access Control** — optional barrier/session context if the edge needs to own it.
