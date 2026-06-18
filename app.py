"""Flask application entry point for the SpotFinder Edge Gateway.

Wires together the Flask app, registers the IAM and Monitoring bounded-context
Blueprints, and initializes the SQLite database (tables created, dev test node
seeded) once before the first request.

Run:
    python app.py            # debug server on 0.0.0.0:5000
"""

from flask import Flask

import iam.application.services
from iam.interfaces.services import iam_api
from monitoring.interfaces.services import monitoring_api
from shared.infrastructure.database import init_db

app = Flask(__name__)
app.register_blueprint(iam_api)
app.register_blueprint(monitoring_api)

_first_request = True


@app.before_request
def _setup():
    """Create the DB schema and seed the dev test node on the first request."""
    global _first_request
    if _first_request:
        _first_request = False
        init_db()
        iam.application.services.AuthApplicationService().get_or_create_test_node()


@app.route("/status", methods=["GET"])
def status():
    """Health check: confirm the edge gateway is up and reachable on the LAN."""
    return {"status": "ok", "service": "spotfinder-edge-gateway"}, 200


if __name__ == "__main__":
    # host="0.0.0.0" => listen on all interfaces so the ESP32 nodes can reach
    # the laptop by its LAN IP (not just localhost).
    app.run(host="0.0.0.0", port=5000, debug=True)
