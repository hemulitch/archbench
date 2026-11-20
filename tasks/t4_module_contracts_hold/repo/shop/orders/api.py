from flask import Blueprint, jsonify, request

from shop.inventory.contracts import OutOfStock
from shop.orders.service import ORDERS, place_order

orders_api = Blueprint("orders", __name__)


@orders_api.post("/orders")
def create_order():
    data = request.get_json()
    try:
        order = place_order(data["customer_id"], data["sku"], data["qty"])
    except OutOfStock:
        return jsonify(error="out_of_stock"), 409
    return jsonify(order), 201


@orders_api.get("/orders/<int:order_id>")
def get_order(order_id):
    if order_id not in ORDERS:
        return jsonify(error="not_found"), 404
    return jsonify(ORDERS[order_id])
