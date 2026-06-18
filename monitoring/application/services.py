"""Monitoring application services: ingest readings and run edge analysis."""

from datetime import datetime, timezone

from dateutil import parser as date_parser

from monitoring.domain.entities import SensorReading
from monitoring.domain.services import GasThresholdService, OccupancyDebounceService
from monitoring.infrastructure.repositories import SensorReadingRepository


class SensorReadingApplicationService:
    def __init__(self):
        self.readings = SensorReadingRepository()

    def ingest(self, device_id, slot_id, distance_cm, created_at=None):
        if distance_cm is None:
            raise ValueError("distance_cm is required")
        if created_at:
            ts = date_parser.parse(created_at).astimezone(timezone.utc)
        else:
            ts = datetime.now(timezone.utc)
        reading = SensorReading(device_id, str(slot_id), float(distance_cm), ts)
        return self.readings.add(reading)

    def recent(self, device_id, slot_id, limit=100):
        return self.readings.recent(device_id, str(slot_id), limit)


class MonitoringAnalysisApplicationService:
    def __init__(self):
        self.readings = SensorReadingRepository()

    def occupancy(self, device_id, slot_id, limit=200):
        recent = self.readings.recent(device_id, str(slot_id), limit)
        result = OccupancyDebounceService.evaluate(recent)
        result["device_id"] = device_id
        result["slot_id"] = str(slot_id)
        return result

    def gas(self, device_id, gas_level):
        result = GasThresholdService.evaluate(gas_level)
        result["device_id"] = device_id
        return result
