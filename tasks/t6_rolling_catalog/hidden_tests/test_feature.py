import sqlite3
from contextlib import closing

from catalog import catalog


def test_precedence_persistence_and_case_fold(tmp_path):
    path = tmp_path / "catalog.db"
    with closing(catalog.open_catalog(path)) as db:
        catalog.put(db, "A", "Mountain green tea")
        assert catalog.set_receipt_caption(db, "A", "fr", "Thé vert") is True
        assert catalog.set_receipt_caption(db, "A", "FR-CA", "Thé vert local") is True
    with closing(catalog.open_catalog(path)) as db:
        assert catalog.receipt_row(db, "A", "fr-ca") == {"sku": "A", "caption": "Thé vert local"}
        assert catalog.receipt_row(db, "A", "fr-FR")["caption"] == "Thé vert"
        assert catalog.receipt_row(db, "A", "en")["caption"] == "Mountain green tea"
        assert catalog.get(db, "A")["title"] == "Mountain green tea"


def test_deleting_override_exposes_fallback(tmp_path):
    with closing(catalog.open_catalog(tmp_path / "catalog.db")) as db:
        catalog.put(db, "A", "Tea")
        catalog.set_receipt_caption(db, "A", "fr", "Thé")
        catalog.set_receipt_caption(db, "A", "fr-ca", "Thé local")
        catalog.put(db, "A", "New title")
        assert catalog.receipt_row(db, "A", "fr-ca")["caption"] == "Thé local"
        catalog.set_receipt_caption(db, "A", "fr-ca", None)
        assert catalog.receipt_row(db, "A", "fr-ca")["caption"] == "Thé"
        catalog.set_receipt_caption(db, "A", "fr", None)
        assert catalog.receipt_row(db, "A", "fr-ca")["caption"] == "New title"
        assert catalog.set_receipt_caption(db, "missing", "fr", "Thé") is False
        assert catalog.receipt_row(db, "missing", "fr") is None


def test_existing_database_is_migrated(tmp_path):
    path = tmp_path / "old.db"
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("CREATE TABLE products (sku TEXT PRIMARY KEY, title TEXT NOT NULL)")
        db.execute("INSERT INTO products VALUES ('P', 'Chocolate')")
        db.execute("PRAGMA user_version = 1")
    with closing(catalog.open_catalog(path)) as db:
        assert catalog.receipt_row(db, "P", "fr") == {"sku": "P", "caption": "Chocolate"}
        catalog.set_receipt_caption(db, "P", "fr", "Chocolat")
        assert catalog.receipt_row(db, "P", "fr")["caption"] == "Chocolat"
