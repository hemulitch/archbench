from concurrent.futures import ThreadPoolExecutor

import pytest
import requests


def accrue(cluster, customer, amount, day="2026-03-05"):
    return requests.post(
        f"{cluster.url('loyalty-api')}/accruals",
        json={"customer_id": customer, "purchase_amount": amount, "occurred_at": day},
    )


def balance(cluster, customer):
    return requests.get(f"{cluster.url('loyalty-api')}/balance/{customer}").json()["points"]


def test_within_cap_reports_zero_rejected(make_cluster):
    body = accrue(make_cluster(), "c1", 1500).json()
    assert (body["accepted_points"], body["rejected_points"]) == (150, 0)


@pytest.mark.parametrize(
    "customer,cap", [("c1", 1000), ("c2", 3000), ("c3", 10000)]
)
def test_accrual_is_truncated_to_tier_cap(make_cluster, customer, cap):
    cluster = make_cluster()
    response = accrue(cluster, customer, (cap + 40) * 10)
    assert response.status_code == 201
    assert (response.json()["accepted_points"], response.json()["rejected_points"]) == (cap, 40)
    assert balance(cluster, customer) == cap


def test_exhausted_cap_accepts_zero(make_cluster):
    cluster = make_cluster()
    accrue(cluster, "c1", 10000)
    response = accrue(cluster, "c1", 500)
    assert response.status_code == 201
    assert (response.json()["accepted_points"], response.json()["rejected_points"]) == (0, 50)


def test_cap_is_per_calendar_month(make_cluster):
    cluster = make_cluster()
    assert accrue(cluster, "c1", 20000, "2026-03-31").json()["accepted_points"] == 1000
    assert accrue(cluster, "c1", 500, "2026-04-01").json()["accepted_points"] == 50


def test_concurrent_accruals_never_exceed_cap(make_cluster):
    cluster = make_cluster()
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda _: accrue(cluster, "c1", 1000).json(), range(32)))
    assert sum(r["accepted_points"] for r in results) == 1000
    assert balance(cluster, "c1") == 1000
