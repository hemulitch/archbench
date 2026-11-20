import requests


def order(cluster, sku, qty):
    return requests.post(
        f"{cluster.url('shop')}/orders", json={"customer_id": "c1", "sku": sku, "qty": qty}
    )


def stock(cluster, sku):
    return requests.get(f"{cluster.url('shop')}/stock/{sku}").json()


def test_order_is_priced_and_stored(make_cluster):
    cluster = make_cluster()
    created = order(cluster, "SKU-2", 2)
    assert created.status_code == 201
    assert created.json()["total"] == 900
    assert requests.get(f"{cluster.url('shop')}/orders/1").json()["sku"] == "SKU-2"


def test_order_can_span_warehouses(make_cluster):
    cluster = make_cluster()
    assert order(cluster, "SKU-3", 3).status_code == 201
    assert stock(cluster, "SKU-3")["total"] == 1


def test_out_of_stock_is_rejected(make_cluster):
    cluster = make_cluster()
    response = order(cluster, "SKU-2", 4)
    assert response.status_code == 409
    assert response.json() == {"error": "out_of_stock"}
    assert stock(cluster, "SKU-2")["total"] == 3
