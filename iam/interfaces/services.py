"""IAM interface layer: Flask blueprint + shared auth helper.

Other bounded contexts call ``authenticate_request()`` at the start of any
endpoint that must be guarded by node credentials (device_id + X-API-Key).
"""

from flask import Blueprint, jsonify, request

from iam.application.services import AuthApplicationService

iam_api = Blueprint("iam_api", __name__)
auth_service = AuthApplicationService()


def authenticate_request():
    """Validate device_id (body) + X-API-Key (header). Return a 401 tuple on
    failure, or None when the request is authenticated."""
    device_id = request.json.get("device_id") if request.json else None
    api_key = request.headers.get("X-API-Key")
    if not device_id or not api_key:
        return jsonify({"error": "Missing device_id or X-API-Key"}), 401
    if not auth_service.authenticate(device_id, api_key):
        return jsonify({"error": "Invalid device_id or API key"}), 401
    return None
