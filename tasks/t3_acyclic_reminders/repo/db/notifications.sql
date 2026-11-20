CREATE TABLE reminders (
    booking_id INTEGER PRIMARY KEY,
    email TEXT NOT NULL,
    due_date TEXT NOT NULL,
    sent INTEGER NOT NULL DEFAULT 0
);
