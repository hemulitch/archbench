import requests

PAYGATE = "api.paygate.example"
FASTSHIP = "api.fastship.example"
ITEMS = [{"sku": "A", "price": 100, "qty": 2}]
DELIVERY = {"to_zip": "420111", "weight_g": 1500}


def system(make_cluster, make_fake, quote):
    paygate, fastship = make_fake(), make_fake()
    paygate.route("POST", "/v1/charges", lambda b: (200, {"id": "ch_7", "status": "succeeded"}))
    fastship.route("POST", "/v2/quotes", lambda b: (200, quote))
    cluster = make_cluster({PAYGATE: paygate, FASTSHIP: fastship})
    return cluster, paygate, fastship


PRICED = {"state": "PRICED", "offer": {"amount_minor": 35000, "currency": "RUB", "transit_days": 3}}


def order(cluster, **extra):
    return requests.post(
        f"{cluster.url('orders-api')}/orders",
        json={"customer_id": "c1", "items": ITEMS, **extra},
    )


def test_delivery_is_added_to_total_and_charge(make_cluster, make_fake):
    cluster, paygate, _ = system(make_cluster, make_fake, PRICED)
    created = order(cluster, delivery=DELIVERY)
    assert created.status_code == 201
    body = created.json()
    assert (body["total"], body["delivery_cost"], body["delivery_days"]) == (550, 350, 3)
    assert paygate.calls[0]["body"] == {"customer": "c1", "amount_minor": 55000}


def test_quote_request_follows_carrier_format(make_cluster, make_fake):
    cluster, _, fastship = system(make_cluster, make_fake, PRICED)
    order(cluster, delivery=DELIVERY)
    assert fastship.calls[0]["body"] == {
        "route": {"src": "190000", "dst": "420111"},
        "parcel": {"grams": 1500},
    }


def test_delivery_is_persisted(make_cluster, make_fake):
    cluster, _, _ = system(make_cluster, make_fake, PRICED)
    order_id = order(cluster, delivery=DELIVERY).json()["id"]
    fetched = requests.get(f"{cluster.url('orders-api')}/orders/{order_id}").json()
    assert (fetched["total"], fetched["delivery_cost"], fetched["delivery_days"]) == (550, 350, 3)


def test_no_route_rejects_without_charge(make_cluster, make_fake):
    cluster, paygate, _ = system(make_cluster, make_fake, {"state": "NO_ROUTE"})
    created = order(cluster, delivery=DELIVERY)
    assert created.status_code == 422
    assert created.json() == {"error": "delivery_unavailable"}
    assert paygate.calls == []
    assert requests.get(f"{cluster.url('orders-api')}/orders/1").status_code == 404
