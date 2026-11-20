import os

import requests
from flask import jsonify, request

from shared.server import create_service, run

app = create_service("notifications-api")
REPO_URL = os.environ["NOTIFICATIONS_REPO_URL"]
MAIL_URL = os.environ["MAIL_URL"]
TIMEOUT = 5


@app.post("/reminders")
def create_reminder():
    saved = requests.post(f"{REPO_URL}/reminders", json=request.get_json(), timeout=TIMEOUT)
    saved.raise_for_status()
    return jsonify(saved.json()), 201


@app.post("/reminders/run-due")
def run_due():
    today = request.get_json()["today"]
    due = requests.get(f"{REPO_URL}/reminders", params={"due_by": today}, timeout=TIMEOUT)
    due.raise_for_status()
    for reminder in due.json():
        requests.post(
            f"{MAIL_URL}/messages",
            json={
                "to": reminder["email"],
                "subject": "Напоминание о бронировании",
                "body": f"Бронирование №{reminder['booking_id']} скоро начнётся.",
            },
            timeout=TIMEOUT,
        ).raise_for_status()
        requests.post(
            f"{REPO_URL}/reminders/{reminder['booking_id']}/sent", timeout=TIMEOUT
        ).raise_for_status()
    return jsonify(sent=len(due.json()))


if __name__ == "__main__":
    run(app)
