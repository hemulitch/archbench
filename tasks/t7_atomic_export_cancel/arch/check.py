import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory


def reject_write(db, operation_sql, operation, retry, inspect):
    before = inspect()
    db.execute(f"CREATE TRIGGER simulate_failure {operation_sql} "
               "BEGIN SELECT RAISE(ABORT, 'simulated write failure'); END")
    try:
        operation()
    except sqlite3.DatabaseError as error:
        if str(error) != "simulated write failure":
            raise
    finally:
        db.execute("DROP TRIGGER simulate_failure")
    if inspect() != before:
        return "a failed write left a partial commit"
    if not retry():
        return "the operation did not recover after the storage error"
    return None


def check_submit(store, path):
    with closing(store.open_store(path)) as db, closing(store.open_store(path)) as reader:
        def snapshot():
            return reader.execute("SELECT COUNT(*) FROM exports").fetchone()[0], store.events(reader)

        def retry():
            export_id = store.submit(db, "quarterly")
            return store.status(reader, export_id) == "queued" and store.events(reader) == [
                {"export_id": export_id, "kind": "export.requested"},
            ]

        return reject_write(db, "BEFORE INSERT ON outbox", lambda: store.submit(db, "quarterly"),
                            retry, snapshot)


def check_cancel(store, path, operation_sql):
    with closing(store.open_store(path)) as db, closing(store.open_store(path)) as reader:
        export_id = store.submit(db, "quarterly")

        def snapshot():
            return store.status(reader, export_id), store.events(reader)

        def retry():
            return store.cancel(db, export_id) is True and snapshot() == (
                "cancelled",
                [{"export_id": export_id, "kind": "export.requested"},
                 {"export_id": export_id, "kind": "export.cancelled"}],
            )

        return reject_write(db, operation_sql, lambda: store.cancel(db, export_id), retry, snapshot)


def check_batch(store, path):
    with closing(store.open_store(path)) as db, closing(store.open_store(path)) as reader:
        first = store.submit(db, "quarterly")
        second = store.submit(db, "inventory")

        def snapshot():
            states = [store.status(reader, export_id) for export_id in (first, second)]
            return states, store.events(reader)

        def retry():
            if store.cancel_batch(db, [first, second]) != [first, second]:
                return False
            states, events = snapshot()
            return states == ["cancelled", "cancelled"] and events[2:] == [
                {"export_id": first, "kind": "export.cancelled"},
                {"export_id": second, "kind": "export.cancelled"},
            ]

        return reject_write(
            db,
            f"BEFORE INSERT ON outbox WHEN NEW.export_id = {second}",
            lambda: store.cancel_batch(db, [first, second]),
            retry,
            snapshot,
        )


def check(store, directory):
    violations = []
    result = check_submit(store, directory / "submit.db")
    if result:
        violations.append(f"submit when outbox insert fails: {result}")
    if callable(getattr(store, "cancel", None)):
        for operation, label in (
            ("BEFORE INSERT ON outbox", "outbox insert"),
            ("BEFORE UPDATE ON exports", "status update"),
        ):
            result = check_cancel(store, directory / f"{label}.db", operation)
            if result:
                violations.append(f"cancel when {label} fails: {result}")
    if callable(getattr(store, "cancel_batch", None)):
        result = check_batch(store, directory / "batch.db")
        if result:
            violations.append(f"batch when the second write fails: {result}")
    return violations


if __name__ == "__main__":
    sys.path.insert(0, sys.argv[1])
    from exports import store

    with TemporaryDirectory() as directory:
        print(json.dumps(check(store, Path(directory))))
