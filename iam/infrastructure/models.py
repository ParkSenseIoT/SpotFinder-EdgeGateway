"""Peewee persistence model for the IAM bounded context."""

from peewee import CharField, Model

from shared.infrastructure.database import db


class NodeModel(Model):
    device_id = CharField(unique=True)
    api_key = CharField()
    label = CharField(null=True)

    class Meta:
        database = db
        table_name = "nodes"
