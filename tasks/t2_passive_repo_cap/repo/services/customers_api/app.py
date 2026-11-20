from flask import jsonify

from shared.server import create_service, run

app = create_service("customers-api")
CUSTOMERS = {
    "c1": {"id": "c1", "tier": "basic", "active": True},
    "c2": {"id": "c2", "tier": "silver", "active": True},
    "c3": {"id": "c3", "tier": "gold", "active": True},
    "c4": {"id": "c4", "tier": "basic", "active": False},
}


@app.get("/customers/<customer_id>")
def get_customer(customer_id):
    if customer_id not in CUSTOMERS:
        return jsonify(error="not_found"), 404
    return jsonify(CUSTOMERS[customer_id])


if __name__ == "__main__":
    run(app)
