"""Peewee persistence model for the Monitoring bounded context."""

from peewee import AutoField, CharField, DateTimeField, FloatField, Model

from shared.infrastructure.database import db


class SensorReadingModel(Model):
    id = AutoField()
    device_id = CharField(index=True)
    slot_id = CharField(index=True)
    distance_cm = FloatField()
    created_at = DateTimeField()

    class Meta:
        database = db
        table_name = "sensor_readings"
