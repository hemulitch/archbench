CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    items TEXT NOT NULL,
    total INTEGER NOT NULL,
    charge_id TEXT NOT NULL
);
