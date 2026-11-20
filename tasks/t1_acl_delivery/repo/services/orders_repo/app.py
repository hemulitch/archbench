import json
import os

from flask import jsonify, request

from shared.db import connect
from shared.server import create_service, run

app = create_service("orders-repo")
DSN = os.environ["ORDERS_DB_DSN"]


def to_dict(row):
    order = dict(row)
    order["items"] = json.loads(order["items"])
    return order


@app.post("/orders")
def insert_order():
    data = request.get_json()
    db = connect(DSN)
    cursor = db.execute(
        "INSERT INTO orders (customer_id, items, total, charge_id) VALUES (?, ?, ?, ?)",
        (data["customer_id"], json.dumps(data["items"]), data["total"], data["charge_id"]),
    )
    row = db.execute("SELECT * FROM orders WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(to_dict(row)), 201


@app.get("/orders/<int:order_id>")
def read_order(order_id):
    row = connect(DSN).execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        return jsonify(error="not_found"), 404
    return jsonify(to_dict(row))


if __name__ == "__main__":
    run(app)
