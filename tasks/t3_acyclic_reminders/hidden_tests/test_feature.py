import requests

MAILER = "api.mailer.example"
BOOKING = {"guest_email": "g@example.org", "hotel": "Астория", "check_in": "2026-07-10"}


def system(make_cluster, make_fake):
    mailer = make_fake()
    mailer.route("POST", "/v3/send", lambda b: (202, {"queued": True}))
    cluster = make_cluster({MAILER: mailer})
    booking = requests.post(f"{cluster.url('bookings-api')}/bookings", json=BOOKING).json()
    return cluster, mailer, booking["id"]


def run_due(cluster, today):
    return requests.post(
        f"{cluster.url('notifications-api')}/reminders/run-due", json={"today": today}
    ).json()


def patch(cluster, booking_id, **fields):
    response = requests.patch(f"{cluster.url('bookings-api')}/bookings/{booking_id}", json=fields)
    assert response.status_code == 200


def test_body_names_hotel_and_check_in(make_cluster, make_fake):
    cluster, mailer, _ = system(make_cluster, make_fake)
    assert run_due(cluster, "2026-07-09") == {"sent": 1}
    text = mailer.calls[0]["body"]["text"]
    assert "Астория" in text and "2026-07-10" in text


def test_body_uses_data_changed_after_booking(make_cluster, make_fake):
    cluster, mailer, booking_id = system(make_cluster, make_fake)
    patch(cluster, booking_id, hotel="Метрополь")
    assert run_due(cluster, "2026-07-09") == {"sent": 1}
    text = mailer.calls[0]["body"]["text"]
    assert "Метрополь" in text and "Астория" not in text


def test_reminder_follows_postponed_check_in(make_cluster, make_fake):
    cluster, mailer, booking_id = system(make_cluster, make_fake)
    patch(cluster, booking_id, check_in="2026-08-20")
    assert run_due(cluster, "2026-07-09") == {"sent": 0}
    assert mailer.calls == []
    assert run_due(cluster, "2026-08-19") == {"sent": 1}
    assert "2026-08-20" in mailer.calls[0]["body"]["text"]


def test_reminder_follows_earlier_check_in(make_cluster, make_fake):
    cluster, mailer, booking_id = system(make_cluster, make_fake)
    patch(cluster, booking_id, check_in="2026-07-01")
    assert run_due(cluster, "2026-06-30") == {"sent": 1}
    assert "2026-07-01" in mailer.calls[0]["body"]["text"]
