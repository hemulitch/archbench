from threading import RLock


class StockLedger:
    def __init__(self, levels):
        self._levels = levels
        self.lock = RLock()

    def by_warehouse(self, sku):
        return dict(self._levels.get(sku, {}))

    def total(self, sku):
        return sum(self.by_warehouse(sku).values())

    def take(self, sku, qty, warehouse):
        with self.lock:
            if self._levels[sku][warehouse] < qty:
                raise ValueError("not enough stock")
            self._levels[sku][warehouse] -= qty


LEDGER = StockLedger(
    {
        "SKU-1": {"msk": 5, "spb": 12},
        "SKU-2": {"msk": 3},
        "SKU-3": {"msk": 2, "spb": 2},
    }
)
