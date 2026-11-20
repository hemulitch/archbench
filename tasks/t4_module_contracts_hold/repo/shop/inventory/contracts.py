"""Public interface of the inventory module."""
from shop.inventory.internal.stock import LEDGER


class OutOfStock(Exception):
    pass


def reserve(sku: str, qty: int) -> None:
    """Takes ``qty`` units, spreading them across warehouses if needed."""
    with LEDGER.lock:
        levels = LEDGER.by_warehouse(sku)
        if sum(levels.values()) < qty:
            raise OutOfStock(sku)
        for warehouse, available in levels.items():
            taken = min(available, qty)
            if taken:
                LEDGER.take(sku, taken, warehouse)
            qty -= taken
