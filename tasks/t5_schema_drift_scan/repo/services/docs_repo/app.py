import os

from flask import jsonify, request

from shared.db import connect
from shared.server import create_service, run

app = create_service("docs-repo")
DSN = os.environ["DOCS_DB_DSN"]


@app.post("/documents")
def insert_document():
    data = request.get_json()
    db = connect(DSN)
    cursor = db.execute(
        "INSERT INTO documents (filename, text) VALUES (?, ?)",
        (data["filename"], data["text"]),
    )
    row = db.execute("SELECT * FROM documents WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.get("/documents/<int:document_id>")
def read_document(document_id):
    row = connect(DSN).execute(
        "SELECT * FROM documents WHERE id = ?", (document_id,)
    ).fetchone()
    if row is None:
        return jsonify(error="not_found"), 404
    return jsonify(dict(row))


if __name__ == "__main__":
    run(app)
