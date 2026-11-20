import requests

PAYGATE = "api.paygate.example"
ITEMS = [{"sku": "A", "price": 100, "qty": 2}]


def system(make_cluster, make_fake, status="succeeded"):
    paygate = make_fake()
    paygate.route("POST", "/v1/charges", lambda b: (200, {"id": "ch_1", "status": status}))
    return make_cluster({PAYGATE: paygate}), paygate


def test_order_is_paid_and_saved(make_cluster, make_fake):
    cluster, paygate = system(make_cluster, make_fake)
    created = requests.post(
        f"{cluster.url('orders-api')}/orders",
        json={"customer_id": "c1", "items": ITEMS},
    )
    assert created.status_code == 201
    assert created.json()["total"] == 200
    assert paygate.calls[0]["body"] == {"customer": "c1", "amount_minor": 20000}
    fetched = requests.get(f"{cluster.url('orders-api')}/orders/{created.json()['id']}")
    assert fetched.json()["charge_id"] == "ch_1"


def test_declined_payment_creates_no_order(make_cluster, make_fake):
    cluster, _ = system(make_cluster, make_fake, status="declined")
    created = requests.post(
        f"{cluster.url('orders-api')}/orders",
        json={"customer_id": "c1", "items": ITEMS},
    )
    assert created.status_code == 402
    assert requests.get(f"{cluster.url('orders-api')}/orders/1").status_code == 404
