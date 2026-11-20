import os

import requests
from flask import jsonify, request

from shared.server import create_service, run

app = create_service("orders-api")
ORDERS_REPO_URL = os.environ["ORDERS_REPO_URL"]
PAYMENTS_URL = os.environ["PAYMENTS_URL"]
TIMEOUT = 5


@app.post("/orders")
def create_order():
    payload = request.get_json()
    total = sum(item["price"] * item["qty"] for item in payload["items"])

    charge = requests.post(
        f"{PAYMENTS_URL}/charges",
        json={"customer_id": payload["customer_id"], "amount": total},
        timeout=TIMEOUT,
    )
    if charge.status_code == 402:
        return jsonify(error="payment_declined"), 402
    charge.raise_for_status()

    saved = requests.post(
        f"{ORDERS_REPO_URL}/orders",
        json={
            "customer_id": payload["customer_id"],
            "items": payload["items"],
            "total": total,
            "charge_id": charge.json()["charge_id"],
        },
        timeout=TIMEOUT,
    )
    saved.raise_for_status()
    return jsonify(saved.json()), 201


@app.get("/orders/<int:order_id>")
def get_order(order_id):
    found = requests.get(f"{ORDERS_REPO_URL}/orders/{order_id}", timeout=TIMEOUT)
    if found.status_code == 404:
        return jsonify(error="not_found"), 404
    found.raise_for_status()
    return jsonify(found.json())


if __name__ == "__main__":
    run(app)
