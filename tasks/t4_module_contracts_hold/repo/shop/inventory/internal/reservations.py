from itertools import count

from shop.inventory.internal.stock import LEDGER


class ReservationBook:
    """Time-limited holds of stock at a particular warehouse."""

    def __init__(self, ledger):
        self._ledger = ledger
        self._ids = count(1)
        self.active = {}

    def hold(self, sku, qty, warehouse, minutes):
        self._ledger.take(sku, qty, warehouse)
        reservation = {"id": next(self._ids), "warehouse": warehouse, "minutes": minutes}
        self.active[reservation["id"]] = {**reservation, "sku": sku, "qty": qty}
        return reservation


BOOK = ReservationBook(LEDGER)
