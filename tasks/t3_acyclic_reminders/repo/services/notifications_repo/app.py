import os

from flask import jsonify, request

from shared.db import connect
from shared.server import create_service, run

app = create_service("notifications-repo")
DSN = os.environ["NOTIFICATIONS_DB_DSN"]


@app.post("/reminders")
def insert_reminder():
    data = request.get_json()
    connect(DSN).execute(
        "INSERT INTO reminders (booking_id, email, due_date) VALUES (?, ?, ?)",
        (data["booking_id"], data["email"], data["due_date"]),
    )
    return jsonify(data), 201


@app.get("/reminders")
def list_due():
    rows = connect(DSN).execute(
        "SELECT * FROM reminders WHERE sent = 0 AND due_date <= ?",
        (request.args["due_by"],),
    ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.post("/reminders/<int:booking_id>/sent")
def mark_sent(booking_id):
    connect(DSN).execute("UPDATE reminders SET sent = 1 WHERE booking_id = ?", (booking_id,))
    return jsonify(booking_id=booking_id)


if __name__ == "__main__":
    run(app)
