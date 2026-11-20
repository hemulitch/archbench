import requests

OCRCLOUD = "api.ocrcloud.example"
AVSCAN = "api.avscan.example"


def test_document_is_recognized_and_stored(make_cluster, make_fake):
    ocr = make_fake()
    ocr.route("POST", "/v1/ocr", lambda b: (200, {"result": {"plain": "договор"}}))
    scanner = make_fake()
    scanner.route("POST", "/v2/scans", lambda b: (200, {"verdict": "CLEAN"}))
    cluster = make_cluster({OCRCLOUD: ocr, AVSCAN: scanner})
    created = requests.post(
        f"{cluster.url('ingest-api')}/documents",
        json={"filename": "a.pdf", "content": "QUJD"},
    )
    assert created.status_code == 201
    fetched = requests.get(f"{cluster.url('ingest-api')}/documents/{created.json()['id']}")
    assert fetched.json()["text"] == "договор"
