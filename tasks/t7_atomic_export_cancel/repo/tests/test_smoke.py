from contextlib import closing

from exports import store


def test_submitting_records_request(tmp_path):
    with closing(store.open_store(tmp_path / "exports.db")) as db:
        export_id = store.submit(db, "quarterly")
        assert store.status(db, export_id) == "queued"
        assert store.events(db) == [{"export_id": export_id, "kind": "export.requested"}]


def test_worker_completes_only_queued_jobs(tmp_path):
    with closing(store.open_store(tmp_path / "exports.db")) as db:
        export_id = store.submit(db, "quarterly")
        assert store.complete(db, export_id)
        assert store.status(db, export_id) == "completed"
        assert not store.complete(db, export_id)
        assert store.status(db, 999) is None
