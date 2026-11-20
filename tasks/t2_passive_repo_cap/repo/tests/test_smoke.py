import requests


def accrue(cluster, customer, amount, day="2026-03-05"):
    return requests.post(
        f"{cluster.url('loyalty-api')}/accruals",
        json={"customer_id": customer, "purchase_amount": amount, "occurred_at": day},
    )


def test_points_are_accrued(make_cluster):
    cluster = make_cluster()
    response = accrue(cluster, "c1", 1500)
    assert response.status_code == 201
    assert response.json()["accepted_points"] == 150
    balance = requests.get(f"{cluster.url('loyalty-api')}/balance/c1").json()
    assert balance["points"] == 150


def test_blocked_customer_is_rejected(make_cluster):
    assert accrue(make_cluster(), "c4", 1500).status_code == 403


def test_unknown_customer_is_rejected(make_cluster):
    assert accrue(make_cluster(), "nobody", 1500).status_code == 404
