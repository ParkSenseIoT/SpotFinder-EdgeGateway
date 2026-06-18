"""Repository mapping SensorReadingModel rows to/from the domain entity."""

from monitoring.domain.entities import SensorReading
from monitoring.infrastructure.models import SensorReadingModel


class SensorReadingRepository:
    def add(self, reading):
        row = SensorReadingModel.create(
            device_id=reading.device_id,
            slot_id=reading.slot_id,
            distance_cm=reading.distance_cm,
            created_at=reading.created_at,
        )
        reading.id = row.id
        return reading

    def recent(self, device_id, slot_id, limit=200):
        query = (
            SensorReadingModel.select()
            .where(
                (SensorReadingModel.device_id == device_id)
                & (SensorReadingModel.slot_id == slot_id)
            )
            .order_by(SensorReadingModel.created_at.asc())
            .limit(limit)
        )
        return [
            SensorReading(r.device_id, r.slot_id, r.distance_cm, r.created_at, r.id)
            for r in query
        ]
