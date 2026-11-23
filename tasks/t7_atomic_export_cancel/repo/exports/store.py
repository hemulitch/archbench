import sqlite3


def open_store(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS exports (
            id INTEGER PRIMARY KEY,
            report TEXT NOT NULL,
            status TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS outbox (
            id INTEGER PRIMARY KEY,
            export_id INTEGER NOT NULL,
            kind TEXT NOT NULL
        );
    """)
    return db


def submit(db, report):
    with db:
        cursor = db.execute("INSERT INTO exports (report, status) VALUES (?, 'queued')", (report,))
        export_id = cursor.lastrowid
        db.execute(
            "INSERT INTO outbox (export_id, kind) VALUES (?, 'export.requested')",
            (export_id,),
        )
    return export_id


def status(db, export_id):
    row = db.execute("SELECT status FROM exports WHERE id = ?", (export_id,)).fetchone()
    return row["status"] if row else None


def complete(db, export_id):
    with db:
        cursor = db.execute(
            "UPDATE exports SET status = 'completed' WHERE id = ? AND status = 'queued'",
            (export_id,),
        )
        return cursor.rowcount == 1


def events(db):
    return [
        dict(row) for row in db.execute("SELECT export_id, kind FROM outbox ORDER BY id")
    ]
