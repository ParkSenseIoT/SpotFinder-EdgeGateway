"""Monitoring interface layer (REST API) -- what the ESP32 nodes call.

Translates HTTP requests into application-service calls. Owns no domain logic:
parsing, auth delegation and HTTP status selection only.
"""

from flask import Blueprint, jsonify, request

from iam.interfaces.services import authenticate_request
from monitoring.application.services import (
    MonitoringAnalysisApplicationService,
    SensorReadingApplicationService,
)

monitoring_api = Blueprint("monitoring_api", __name__)

reading_service = SensorReadingApplicationService()
analysis_service = MonitoringAnalysisApplicationService()


@monitoring_api.route("/api/v1/monitoring/sensor-readings", methods=["POST"])
def create_reading():
    """Ingest one raw occupancy reading from a Parking Spot Node.

    Headers: X-API-Key (required), Content-Type: application/json.
    Body: {"device_id": "...", "slot_id": "...", "distance_cm": 87.5}
    """
    auth = authenticate_request()
    if auth:
        return auth

    data = request.json or {}
    try:
        r = reading_service.ingest(
            data["device_id"], data["slot_id"], data["distance_cm"], data.get("created_at")
        )
        return jsonify({
            "id": r.id,
            "device_id": r.device_id,
            "slot_id": r.slot_id,
            "distance_cm": r.distance_cm,
            "created_at": r.created_at.isoformat() + "Z",
        }), 201
    except KeyError:
        return jsonify({"error": "Missing required fields (device_id, slot_id, distance_cm)"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@monitoring_api.route("/api/v1/monitoring/sensor-readings", methods=["GET"])
def list_readings():
    """List recent raw readings for one slot (live view / debugging)."""
    device_id = request.args.get("device_id")
    slot_id = request.args.get("slot_id")
    if not device_id or not slot_id:
        return jsonify({"error": "device_id and slot_id query params are required"}), 400
    limit = request.args.get("limit", default=100, type=int)
    rows = reading_service.recent(device_id, slot_id, limit)
    return jsonify([
        {
            "id": r.id,
            "device_id": r.device_id,
            "slot_id": r.slot_id,
            "distance_cm": r.distance_cm,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]), 200


@monitoring_api.route("/api/v1/monitoring/occupancy", methods=["GET"])
def occupancy():
    """Debounced slot status (AVAILABLE / OCCUPIED / TRANSITION) + LED action.

    This is the edge's core output: it applies the sustained > 2 s rule that
    keeps a pedestrian or a stray echo from flipping the slot.
    """
    device_id = request.args.get("device_id")
    slot_id = request.args.get("slot_id")
    if not device_id or not slot_id:
        return jsonify({"error": "device_id and slot_id query params are required"}), 400
    return jsonify(analysis_service.occupancy(device_id, slot_id)), 200


@monitoring_api.route("/api/v1/monitoring/gas-analysis", methods=["POST"])
def gas_analysis():
    """Evaluate an MQ-2 gas level and return the emergency decision.

    Body: {"device_id": "...", "gas_level": 2450}
    Returns status NORMAL/EMERGENCY and actuator_action IDLE/EVACUATE.
    """
    auth = authenticate_request()
    if auth:
        return auth
    data = request.json or {}
    try:
        return jsonify(analysis_service.gas(data["device_id"], data["gas_level"])), 200
    except KeyError:
        return jsonify({"error": "Missing required fields (device_id, gas_level)"}), 400
