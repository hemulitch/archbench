from itertools import count

from shop.catalog.contracts import price_of
from shop.inventory.contracts import reserve

_ids = count(1)
ORDERS = {}


def place_order(customer_id, sku, qty):
    reserve(sku, qty)
    order = {
        "id": next(_ids),
        "customer_id": customer_id,
        "sku": sku,
        "qty": qty,
        "total": price_of(sku) * qty,
    }
    ORDERS[order["id"]] = order
    return order
