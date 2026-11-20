import requests


def order(cluster, sku, qty, **extra):
    return requests.post(
        f"{cluster.url('shop')}/orders",
        json={"customer_id": "c1", "sku": sku, "qty": qty, **extra},
    )


def stock(cluster, sku):
    return requests.get(f"{cluster.url('shop')}/stock/{sku}").json()


def test_hold_picks_warehouse_with_most_stock(make_cluster):
    cluster = make_cluster()
    created = order(cluster, "SKU-1", 3, hold_minutes=30)
    assert created.status_code == 201
    reservation = created.json()["reservation"]
    assert (reservation["warehouse"], reservation["minutes"]) == ("spb", 30)
    assert isinstance(reservation["id"], int)


def test_stock_reflects_the_hold(make_cluster):
    cluster = make_cluster()
    order(cluster, "SKU-1", 3, hold_minutes=30)
    assert stock(cluster, "SKU-1")["by_warehouse"] == {"msk": 5, "spb": 9}


def test_reservation_is_returned_by_get(make_cluster):
    cluster = make_cluster()
    created = order(cluster, "SKU-1", 3, hold_minutes=15).json()
    fetched = requests.get(f"{cluster.url('shop')}/orders/{created['id']}").json()
    assert fetched["reservation"] == created["reservation"]


def test_no_single_warehouse_rejected_without_side_effects(make_cluster):
    cluster = make_cluster()
    response = order(cluster, "SKU-3", 3, hold_minutes=30)
    assert response.status_code == 409
    assert response.json() == {"error": "no_single_warehouse"}
    assert stock(cluster, "SKU-3")["by_warehouse"] == {"msk": 2, "spb": 2}
