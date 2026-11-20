"""Public interface of the catalog module."""
from shop.catalog.internal.prices import PRICES


def price_of(sku: str) -> int:
    return PRICES[sku]
