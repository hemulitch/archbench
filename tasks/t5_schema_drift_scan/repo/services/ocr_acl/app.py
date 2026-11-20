"""Translates between our recognition model and OCRCloud's."""
import os

import requests
from flask import jsonify, request

from shared.server import create_service, run

app = create_service("ocr-acl")
OCRCLOUD_URL = os.environ["OCRCLOUD_URL"]


@app.post("/recognize")
def recognize():
    response = requests.post(
        f"{OCRCLOUD_URL}/ocr", json={"blob": request.get_json()["content"]}, timeout=5
    )
    response.raise_for_status()
    return jsonify(text=response.json()["result"]["plain"])


if __name__ == "__main__":
    run(app)
