"""Monitoring domain services -- the edge's real value-add.

These are the rules SpotFinder's section 5.6 PROMISES (occupancy sustained for
more than 2 s; gas above threshold triggers an emergency) but that the ESP32
firmware does not implement. Centralizing them here keeps the nodes dumb and the
logic testable and consistent across the whole floor.
"""

# Occupancy thresholds (match the firmware constants).
OCCUPIED_CM = 100.0          # < 100 cm => a car is over the slot
SUSTAINED_SECONDS = 2.0      # the reading must hold this long before we trust it


class OccupancyDebounceService:
    """Turns noisy distance readings into a stable AVAILABLE / OCCUPIED status.

    A pedestrian crossing or a stray echo should NOT flip the slot. We only
    commit to a status when the same condition has held for SUSTAINED_SECONDS.
    """

    @staticmethod
    def evaluate(readings, occupied_cm=OCCUPIED_CM, sustained_seconds=SUSTAINED_SECONDS):
        valid = [r for r in readings if r.distance_cm is not None]
        if not valid:
            return {"status": "UNKNOWN", "led_action": "OFF", "sample_count": 0}

        latest = valid[-1]                       # readings come oldest -> newest
        occupied_now = latest.distance_cm < occupied_cm

        # How long has the current condition been continuously held?
        held_seconds = 0.0
        for r in reversed(valid):
            if (r.distance_cm < occupied_cm) != occupied_now:
                break
            held_seconds = (latest.created_at - r.created_at).total_seconds()

        if held_seconds >= sustained_seconds:
            status = "OCCUPIED" if occupied_now else "AVAILABLE"
        else:
            status = "TRANSITION"                 # not stable yet -- keep previous LED

        led_action = {"OCCUPIED": "RED", "AVAILABLE": "GREEN"}.get(status, "OFF")
        return {
            "status": status,
            "led_action": led_action,
            "occupied_now": occupied_now,
            "held_seconds": round(held_seconds, 1),
            "last_distance_cm": latest.distance_cm,
            "sample_count": len(valid),
        }


# Gas threshold (matches the firmware GAS_THRESHOLD; ~900 PPM equivalent).
GAS_THRESHOLD = 2200


class GasThresholdService:
    """Evaluates an MQ-2 gas level against the emergency threshold."""

    @staticmethod
    def evaluate(gas_level, threshold=GAS_THRESHOLD):
        emergency = gas_level is not None and gas_level > threshold
        return {
            "gas_level": gas_level,
            "threshold": threshold,
            "status": "EMERGENCY" if emergency else "NORMAL",
            "actuator_action": "EVACUATE" if emergency else "IDLE",
        }
