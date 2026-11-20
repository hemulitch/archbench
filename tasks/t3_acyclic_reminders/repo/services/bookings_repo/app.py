import os

from flask import jsonify, request

from shared.db import connect
from shared.server import create_service, run

app = create_service("bookings-repo")
DSN = os.environ["BOOKINGS_DB_DSN"]


def read(db, booking_id):
    return db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()


@app.post("/bookings")
def insert_booking():
    data = request.get_json()
    db = connect(DSN)
    cursor = db.execute(
        "INSERT INTO bookings (guest_email, hotel, check_in) VALUES (?, ?, ?)",
        (data["guest_email"], data["hotel"], data["check_in"]),
    )
    return jsonify(dict(read(db, cursor.lastrowid))), 201


@app.get("/bookings/<int:booking_id>")
def get_booking(booking_id):
    row = read(connect(DSN), booking_id)
    if row is None:
        return jsonify(error="not_found"), 404
    return jsonify(dict(row))


@app.patch("/bookings/<int:booking_id>")
def update_booking(booking_id):
    data = request.get_json()
    db = connect(DSN)
    current = read(db, booking_id)
    if current is None:
        return jsonify(error="not_found"), 404
    db.execute(
        "UPDATE bookings SET hotel = ?, check_in = ? WHERE id = ?",
        (data.get("hotel", current["hotel"]), data.get("check_in", current["check_in"]), booking_id),
    )
    return jsonify(dict(read(db, booking_id)))


if __name__ == "__main__":
    run(app)
