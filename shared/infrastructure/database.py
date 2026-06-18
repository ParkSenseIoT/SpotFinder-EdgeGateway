"""SQLite database handle and one-time initialization for the edge gateway.

The edge keeps a small local store (raw sensor readings + the node registry).
SQLite is enough for a single-floor edge deployed on a laptop/Raspberry Pi.
"""

from peewee import SqliteDatabase

db = SqliteDatabase("spotfinder_edge.db")


def init_db():
    """Create the tables if they do not exist yet (idempotent)."""
    from iam.infrastructure.models import NodeModel
    from monitoring.infrastructure.models import SensorReadingModel

    db.connect(reuse_if_open=True)
    db.create_tables([NodeModel, SensorReadingModel], safe=True)
