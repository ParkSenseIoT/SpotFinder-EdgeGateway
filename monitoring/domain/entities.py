"""Monitoring domain entities."""


class SensorReading:
    """One raw occupancy reading from a Parking Spot Node.

    distance_cm is what the HC-SR04 measured. The edge keeps a short history of
    these so it can decide a *stable* slot status (see OccupancyDebounceService).
    """

    def __init__(self, device_id, slot_id, distance_cm, created_at, id=None):
        self.id = id
        self.device_id = device_id
        self.slot_id = slot_id
        self.distance_cm = distance_cm
        self.created_at = created_at
