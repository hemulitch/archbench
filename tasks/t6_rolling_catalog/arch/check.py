import importlib.util
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory


def load_legacy():
    path = Path(__file__).resolve().parents[1] / "repo" / "catalog" / "catalog.py"
    spec = importlib.util.spec_from_file_location("legacy_catalog", path)
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    return legacy


def check(current, legacy, path):
    with closing(legacy.open_catalog(path)) as old, closing(current.open_catalog(path)) as new:
        current.put(new, "A", "Tea")
        has_receipts = callable(getattr(current, "receipt_row", None))
        if has_receipts:
            current.set_receipt_caption(new, "A", "fr", "Thé vert")
        try:
            if legacy.get(old, "A") != {"sku": "A", "title": "Tea"}:
                return ["the already running client cannot read the new client's product"]
            legacy.put(old, "A", "Green tea")
            with closing(legacy.open_catalog(path)) as rollback:
                legacy.put(rollback, "B", "Coffee")
        except sqlite3.DatabaseError as error:
            return [f"the previous client cannot use the migrated schema: {error}"]

        if current.get(new, "B") != {"sku": "B", "title": "Coffee"}:
            return ["the new client cannot read a product inserted after rollback"]
        if current.get(new, "A") != {"sku": "A", "title": "Green tea"}:
            return ["the new client did not observe the previous client's update"]
        if has_receipts and current.receipt_row(new, "A", "fr-CA")["caption"] != "Thé vert":
            return ["the previous client's update overwrote the new receipt caption"]
        return []


if __name__ == "__main__":
    sys.path.insert(0, sys.argv[1])
    from catalog import catalog

    with TemporaryDirectory() as directory:
        print(json.dumps(check(catalog, load_legacy(), Path(directory) / "catalog.db")))
