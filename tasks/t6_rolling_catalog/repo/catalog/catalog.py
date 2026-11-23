import sqlite3


def open_catalog(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    try:
        with db:
            db.execute("BEGIN IMMEDIATE")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version == 0:
                db.execute("CREATE TABLE products (sku TEXT PRIMARY KEY, title TEXT NOT NULL)")
                db.execute("PRAGMA user_version = 1")
    except Exception:
        db.close()
        raise
    return db


def put(db, sku, title):
    with db:
        db.execute(
            """INSERT INTO products (sku, title) VALUES (?, ?)
               ON CONFLICT(sku) DO UPDATE SET title = excluded.title""",
            (sku, title),
        )


def get(db, sku):
    row = db.execute("SELECT sku, title FROM products WHERE sku = ?", (sku,)).fetchone()
    return dict(row) if row else None
