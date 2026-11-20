# Учитывать стоимость доставки при оформлении заказа

Сейчас заказ оплачивается только за товары. Нужно считать доставку через
перевозчика FastShip и включать её в сумму оплаты.

## Что должно измениться в `POST /orders` (orders-api)

В запросе появляется необязательное поле:

    "delivery": {"to_zip": "420111", "weight_g": 1500}

Если поле передано:

- запросить у FastShip тариф, индекс склада отправления всегда `190000`;
- в ответе и в `GET /orders/<id>` вернуть `delivery_cost` (рубли, целое число) и
  `delivery_days`;
- `total` и сумма списания = товары + доставка;
- если FastShip не нашёл маршрут — ответить `422 {"error": "delivery_unavailable"}`,
  не списывать деньги и не создавать заказ.

Без поля `delivery` всё работает как раньше.

## API FastShip

Адрес: `https://api.fastship.example/v2`

    POST /quotes
    {"route": {"src": "190000", "dst": "420111"}, "parcel": {"grams": 1500}}

Ответ:

    {"state": "PRICED", "offer": {"amount_minor": 35000, "currency": "RUB", "transit_days": 3}}

или, если маршрута нет:

    {"state": "NO_ROUTE"}

`amount_minor` — копейки.
