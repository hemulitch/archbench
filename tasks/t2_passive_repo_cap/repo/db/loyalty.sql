CREATE TABLE ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    month TEXT NOT NULL,
    points INTEGER NOT NULL
);
CREATE INDEX ledger_customer_month ON ledger (customer_id, month);
