from contextlib import closing

from exports import store


def test_cancel_persists_and_notifies_exactly_once(tmp_path):
    path = tmp_path / "exports.db"
    with closing(store.open_store(path)) as db:
        export_id = store.submit(db, "quarterly")
        other = store.submit(db, "inventory")
        assert store.cancel(db, export_id) is True
    with closing(store.open_store(path)) as db:
        assert store.status(db, export_id) == "cancelled"
        assert store.status(db, other) == "queued"
        assert store.cancel(db, export_id) is False
        assert store.events(db) == [
            {"export_id": export_id, "kind": "export.requested"},
            {"export_id": other, "kind": "export.requested"},
            {"export_id": export_id, "kind": "export.cancelled"},
        ]


def test_only_queued_exports_can_be_cancelled(tmp_path):
    with closing(store.open_store(tmp_path / "exports.db")) as db:
        export_id = store.submit(db, "quarterly")
        assert store.complete(db, export_id)
        assert store.cancel(db, export_id) is False
        assert store.cancel(db, export_id + 1) is False
        assert len(store.events(db)) == 1


def test_worker_cannot_complete_cancelled_export(tmp_path):
    with closing(store.open_store(tmp_path / "exports.db")) as db:
        export_id = store.submit(db, "quarterly")
        assert store.cancel(db, export_id)
        assert not store.complete(db, export_id)
        assert store.status(db, export_id) == "cancelled"


def test_batch_preserves_order_and_skips_duplicate_and_ineligible_ids(tmp_path):
    with closing(store.open_store(tmp_path / "exports.db")) as db:
        first, second, third = [store.submit(db, report) for report in ("A", "B", "C")]
        assert store.complete(db, third)
        ids = iter([second, second, third, 999, first])
        assert store.cancel_batch(db, ids) == [second, first]
        assert store.status(db, third) == "completed"
        assert store.events(db)[3:] == [
            {"export_id": second, "kind": "export.cancelled"},
            {"export_id": first, "kind": "export.cancelled"},
        ]
        assert store.cancel_batch(db, [first, second]) == []
        assert store.cancel_batch(db, []) == []
