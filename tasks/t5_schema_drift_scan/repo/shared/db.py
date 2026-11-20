"""Team wrapper over the storage driver.

A DSN looks like ``sqlite://<database-instance>/<database-name>``. The instance
is the name of a ``kind: database`` entry in ``deploy/``.
"""
import os
import sqlite3
from urllib.parse import urlparse


def connect(dsn: str) -> sqlite3.Connection:
    parsed = urlparse(dsn)
    path = os.path.join(
        os.environ.get("DATA_DIR", "/var/lib/app"),
        parsed.hostname,
        f"{parsed.path.lstrip('/')}.sqlite3",
    )
    connection = sqlite3.connect(path, timeout=10, isolation_level=None)
    connection.row_factory = sqlite3.Row
    return connection
