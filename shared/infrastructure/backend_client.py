"""Optional forwarder to the SpotFinder cloud backend (Spring Boot).

The edge consolidates raw node telemetry and forwards only *clean* events to the
cloud. Forwarding is DISABLED unless the environment variable
``SPOTFINDER_BACKEND_URL`` is set, so the gateway keeps working offline (LED
guidance and local decisions do not depend on the cloud).

The backend endpoints used here are public (no JWT), matching the SpotFinder
backend security configuration:
    POST /api/v1/sensor-readings    {sensorId, slotId, distance}
    POST /api/v1/emergency/alerts   {sensorId, gasLevel, type, sensorLocation}
"""

import os

import requests

BACKEND_URL = os.environ.get("SPOTFINDER_BACKEND_URL")  # e.g. http://192.168.1.40:8080


class BackendClient:
    def __init__(self, base_url=None, timeout=4):
        self.base_url = (base_url or BACKEND_URL or "").rstrip("/")
        self.timeout = timeout

    @property
    def enabled(self):
        return bool(self.base_url)

    def forward_sensor_reading(self, sensor_id, slot_id, distance_cm):
        """Forward a consolidated occupancy reading. Best-effort: never raises."""
        if not self.enabled:
            return None
        payload = {"sensorId": sensor_id, "distance": distance_cm}
        try:
            payload["slotId"] = int(slot_id)  # backend expects a numeric slot id
        except (TypeError, ValueError):
            payload["slotId"] = slot_id       # leave as-is; backend may map it
        try:
            resp = requests.post(
                f"{self.base_url}/api/v1/sensor-readings", json=payload, timeout=self.timeout
            )
            return resp.status_code
        except requests.RequestException:
            return None

    def forward_emergency_alert(self, sensor_id, gas_level, location="Edge gateway"):
        """Forward a gas emergency. Best-effort: never raises."""
        if not self.enabled:
            return None
        try:
            resp = requests.post(
                f"{self.base_url}/api/v1/emergency/alerts",
                json={
                    "sensorId": sensor_id,
                    "gasLevel": gas_level,
                    "type": "GAS",
                    "sensorLocation": location,
                },
                timeout=self.timeout,
            )
            return resp.status_code
        except requests.RequestException:
            return None
