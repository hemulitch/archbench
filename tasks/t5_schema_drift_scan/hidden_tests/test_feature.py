import requests

OCRCLOUD = "api.ocrcloud.example"
AVSCAN = "api.avscan.example"


def system(make_cluster, make_fake, verdict):
    ocr, scanner = make_fake(), make_fake()
    ocr.route("POST", "/v1/ocr", lambda b: (200, {"result": {"plain": "договор"}}))
    scanner.route("POST", "/v2/scans", lambda b: (200, verdict))
    return make_cluster({OCRCLOUD: ocr, AVSCAN: scanner}), ocr, scanner


def upload(cluster):
    return requests.post(
        f"{cluster.url('ingest-api')}/documents",
        json={"filename": "a.pdf", "content": "QUJD"},
    )


def test_clean_document_is_scanned_then_processed(make_cluster, make_fake):
    cluster, ocr, scanner = system(make_cluster, make_fake, {"verdict": "CLEAN"})
    assert upload(cluster).status_code == 201
    assert scanner.calls[0]["body"] == {"payload": "QUJD"}
    assert len(ocr.calls) == 1


def test_infected_document_is_rejected(make_cluster, make_fake):
    verdict = {"verdict": "MALICIOUS", "signature": "Trojan.Generic"}
    cluster, ocr, _ = system(make_cluster, make_fake, verdict)
    response = upload(cluster)
    assert response.status_code == 422
    assert response.json() == {"error": "infected", "threat": "Trojan.Generic"}
    assert ocr.calls == []
    assert requests.get(f"{cluster.url('ingest-api')}/documents/1").status_code == 404
