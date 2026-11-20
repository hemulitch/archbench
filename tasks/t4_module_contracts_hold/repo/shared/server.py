"""Common bootstrap for every deployable: Flask app + /health + run()."""
import os

from flask import Flask, jsonify


def create_service(name: str) -> Flask:
    app = Flask(name)

    @app.get("/health")
    def health():
        return jsonify(status="ok", service=name)

    return app


def run(app: Flask) -> None:
    app.run(
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8080")),
        threaded=True,
    )
