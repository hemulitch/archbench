CREATE TABLE bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_email TEXT NOT NULL,
    hotel TEXT NOT NULL,
    check_in TEXT NOT NULL
);
