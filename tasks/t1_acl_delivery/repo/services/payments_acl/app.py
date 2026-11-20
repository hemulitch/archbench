"""Translates between our charge model and PayGate's."""
import os

import requests
from flask import jsonify, request

from shared.server import create_service, run

app = create_service("payments-acl")
PAYGATE_URL = os.environ["PAYGATE_URL"]


@app.post("/charges")
def charge():
    data = request.get_json()
    response = requests.post(
        f"{PAYGATE_URL}/charges",
        json={"customer": data["customer_id"], "amount_minor": data["amount"] * 100},
        timeout=5,
    )
    response.raise_for_status()
    body = response.json()
    if body["status"] != "succeeded":
        return jsonify(error="declined"), 402
    return jsonify(charge_id=body["id"])


if __name__ == "__main__":
    run(app)
