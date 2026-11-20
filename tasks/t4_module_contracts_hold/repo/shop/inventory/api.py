from flask import Blueprint, jsonify

from shop.inventory.internal.stock import LEDGER

inventory_api = Blueprint("inventory", __name__)


@inventory_api.get("/stock/<sku>")
def stock(sku):
    return jsonify(sku=sku, total=LEDGER.total(sku), by_warehouse=LEDGER.by_warehouse(sku))
