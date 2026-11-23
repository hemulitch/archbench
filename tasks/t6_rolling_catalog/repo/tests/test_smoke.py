from contextlib import closing

from catalog.catalog import get, open_catalog, put


def test_update_keeps_public_shape(tmp_path):
    with closing(open_catalog(tmp_path / "catalog.db")) as db:
        put(db, "A", "Tea")
        put(db, "A", "Green tea")
        assert get(db, "A") == {"sku": "A", "title": "Green tea"}
        assert get(db, "missing") is None


def test_reopen_keeps_products(tmp_path):
    path = tmp_path / "catalog.db"
    with closing(open_catalog(path)) as db:
        put(db, "A", "Tea")
    with closing(open_catalog(path)) as db:
        assert get(db, "A")["title"] == "Tea"
