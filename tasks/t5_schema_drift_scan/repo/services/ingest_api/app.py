import os

import requests
from flask import jsonify, request

from shared.server import create_service, run

app = create_service("ingest-api")
DOCS_REPO_URL = os.environ["DOCS_REPO_URL"]
OCR_URL = os.environ["OCR_URL"]
TIMEOUT = 5


@app.post("/documents")
def upload():
    data = request.get_json()
    recognized = requests.post(
        f"{OCR_URL}/recognize", json={"content": data["content"]}, timeout=TIMEOUT
    )
    recognized.raise_for_status()
    saved = requests.post(
        f"{DOCS_REPO_URL}/documents",
        json={"filename": data["filename"], "text": recognized.json()["text"]},
        timeout=TIMEOUT,
    )
    saved.raise_for_status()
    return jsonify(saved.json()), 201


@app.get("/documents/<int:document_id>")
def get_document(document_id):
    found = requests.get(f"{DOCS_REPO_URL}/documents/{document_id}", timeout=TIMEOUT)
    if found.status_code == 404:
        return jsonify(error="not_found"), 404
    found.raise_for_status()
    return jsonify(found.json())


if __name__ == "__main__":
    run(app)
