import os

from flask import jsonify, request

from shared.db import connect
from shared.server import create_service, run

app = create_service("loyalty-repo")
DSN = os.environ["LOYALTY_DB_DSN"]


@app.post("/ledger")
def add_entry():
    data = request.get_json()
    connect(DSN).execute(
        "INSERT INTO ledger (customer_id, month, points) VALUES (?, ?, ?)",
        (data["customer_id"], data["month"], data["points"]),
    )
    return jsonify(accepted_points=data["points"]), 201


@app.get("/balance/<customer_id>")
def balance(customer_id):
    row = connect(DSN).execute(
        "SELECT COALESCE(SUM(points), 0) AS points FROM ledger WHERE customer_id = ?",
        (customer_id,),
    ).fetchone()
    return jsonify(customer_id=customer_id, points=row["points"])


if __name__ == "__main__":
    run(app)
