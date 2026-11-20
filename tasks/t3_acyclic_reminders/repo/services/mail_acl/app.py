"""Translates between our message model and Mailer's."""
import os

import requests
from flask import jsonify, request

from shared.server import create_service, run

app = create_service("mail-acl")
MAILER_URL = os.environ["MAILER_URL"]


@app.post("/messages")
def send():
    data = request.get_json()
    response = requests.post(
        f"{MAILER_URL}/send",
        json={"recipient": data["to"], "title": data["subject"], "text": data["body"]},
        timeout=5,
    )
    response.raise_for_status()
    return jsonify(accepted=True), 202


if __name__ == "__main__":
    run(app)
