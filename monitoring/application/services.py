"""Monitoring application services: ingest readings, run edge analysis, and
forward consolidated events to the cloud backend.

The forwarding is what makes this an *edge*: raw readings arrive ~1/sec, but the
backend only hears about a slot when its DEBOUNCED status actually changes
(AVAILABLE <-> OCCUPIED) or when a gas EMERGENCY starts. Forwarding is a no-op
unless SPOTFINDER_BACKEND_URL is configured (see BackendClient).
"""

from datetime import datetime, timezone

from dateutil import parser as date_parser

from monitoring.domain.entities import SensorReading
from monitoring.domain.services import GasThresholdService, OccupancyDebounceService
from monitoring.infrastructure.repositories import SensorReadingRepository
from shared.infrastructure.backend_client import BackendClient


class SensorReadingApplicationService:
    def __init__(self):
        self.readings = SensorReadingRepository()
        self.backend = BackendClient()
        self._last_status = {}  # (device_id, slot_id) -> last status forwarded

    def ingest(self, device_id, slot_id, distance_cm, created_at=None):
        if distance_cm is None:
            raise ValueError("distance_cm is required")
        if created_at:
            ts = date_parser.parse(created_at).astimezone(timezone.utc)
        else:
            ts = datetime.now(timezone.utc)
        reading = SensorReading(device_id, str(slot_id), float(distance_cm), ts)
        saved = self.readings.add(reading)
        self._maybe_forward_occupancy(device_id, str(slot_id))
        return saved

    def recent(self, device_id, slot_id, limit=100):
        return self.readings.recent(device_id, str(slot_id), limit)

    def _maybe_forward_occupancy(self, device_id, slot_id):
        """Forward to the backend only when the stable status changes."""
        if not self.backend.enabled:
            return
        recent = self.readings.recent(device_id, slot_id, 200)
        result = OccupancyDebounceService.evaluate(recent)
        status = result.get("status")
        if status not in ("AVAILABLE", "OCCUPIED"):
            return  # still TRANSITION/UNKNOWN -> not stable yet, do not spam the cloud
        key = (device_id, slot_id)
        if self._last_status.get(key) != status:
            self._last_status[key] = status
            self.backend.forward_sensor_reading(device_id, slot_id, result.get("last_distance_cm"))


class MonitoringAnalysisApplicationService:
    def __init__(self):
        self.readings = SensorReadingRepository()
        self.backend = BackendClient()
        self._last_gas = {}  # device_id -> last gas status forwarded

    def occupancy(self, device_id, slot_id, limit=200):
        recent = self.readings.recent(device_id, str(slot_id), limit)
        result = OccupancyDebounceService.evaluate(recent)
        result["device_id"] = device_id
        result["slot_id"] = str(slot_id)
        return result

    def gas(self, device_id, gas_level):
        result = GasThresholdService.evaluate(gas_level)
        result["device_id"] = device_id
        if self.backend.enabled and result["status"] == "EMERGENCY":
            if self._last_gas.get(device_id) != "EMERGENCY":
                self._last_gas[device_id] = "EMERGENCY"
                result["forwarded_to_backend"] = self.backend.forward_emergency_alert(
                    device_id, gas_level
                )
        elif result["status"] == "NORMAL":
            self._last_gas[device_id] = "NORMAL"
        return result
