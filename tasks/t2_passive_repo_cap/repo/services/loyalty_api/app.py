import os

import requests
from flask import jsonify, request

from shared.server import create_service, run

app = create_service("loyalty-api")
REPO_URL = os.environ["LOYALTY_REPO_URL"]
CUSTOMERS_URL = os.environ["CUSTOMERS_URL"]
POINTS_DIVISOR = 10


@app.post("/accruals")
def accrue():
    data = request.get_json()
    customer = requests.get(f"{CUSTOMERS_URL}/customers/{data['customer_id']}", timeout=5)
    if customer.status_code == 404:
        return jsonify(error="unknown_customer"), 404
    customer.raise_for_status()
    if not customer.json()["active"]:
        return jsonify(error="customer_blocked"), 403

    saved = requests.post(
        f"{REPO_URL}/ledger",
        json={
            "customer_id": data["customer_id"],
            "month": data["occurred_at"][:7],
            "points": data["purchase_amount"] // POINTS_DIVISOR,
        },
        timeout=10,
    )
    saved.raise_for_status()
    return jsonify(saved.json()), 201


@app.get("/balance/<customer_id>")
def balance(customer_id):
    found = requests.get(f"{REPO_URL}/balance/{customer_id}", timeout=5)
    found.raise_for_status()
    return jsonify(found.json())


if __name__ == "__main__":
    run(app)
