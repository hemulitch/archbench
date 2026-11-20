import os
from datetime import date, timedelta

import requests
from flask import jsonify, request

from shared.server import create_service, run

app = create_service("bookings-api")
REPO_URL = os.environ["BOOKINGS_REPO_URL"]
NOTIFICATIONS_URL = os.environ["NOTIFICATIONS_URL"]
TIMEOUT = 5


def reminder_date(check_in):
    return (date.fromisoformat(check_in) - timedelta(days=1)).isoformat()


@app.post("/bookings")
def create_booking():
    saved = requests.post(f"{REPO_URL}/bookings", json=request.get_json(), timeout=TIMEOUT)
    saved.raise_for_status()
    booking = saved.json()
    reminder = requests.post(
        f"{NOTIFICATIONS_URL}/reminders",
        json={
            "booking_id": booking["id"],
            "email": booking["guest_email"],
            "due_date": reminder_date(booking["check_in"]),
        },
        timeout=TIMEOUT,
    )
    reminder.raise_for_status()
    return jsonify(booking), 201


@app.get("/bookings/<int:booking_id>")
def get_booking(booking_id):
    found = requests.get(f"{REPO_URL}/bookings/{booking_id}", timeout=TIMEOUT)
    if found.status_code == 404:
        return jsonify(error="not_found"), 404
    found.raise_for_status()
    return jsonify(found.json())


@app.patch("/bookings/<int:booking_id>")
def change_booking(booking_id):
    changed = requests.patch(
        f"{REPO_URL}/bookings/{booking_id}", json=request.get_json(), timeout=TIMEOUT
    )
    if changed.status_code == 404:
        return jsonify(error="not_found"), 404
    changed.raise_for_status()
    return jsonify(changed.json())


if __name__ == "__main__":
    run(app)
