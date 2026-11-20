from shared.server import create_service, run
from shop.inventory.api import inventory_api
from shop.orders.api import orders_api

app = create_service("shop")
app.register_blueprint(orders_api)
app.register_blueprint(inventory_api)

if __name__ == "__main__":
    run(app)
