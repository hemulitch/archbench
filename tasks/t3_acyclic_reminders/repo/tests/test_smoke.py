import requests

MAILER = "api.mailer.example"
BOOKING = {"guest_email": "g@example.org", "hotel": "Астория", "check_in": "2026-07-10"}


def system(make_cluster, make_fake):
    mailer = make_fake()
    mailer.route("POST", "/v3/send", lambda b: (202, {"queued": True}))
    return make_cluster({MAILER: mailer}), mailer


def run_due(cluster, today):
    return requests.post(
        f"{cluster.url('notifications-api')}/reminders/run-due", json={"today": today}
    ).json()


def test_booking_is_created_and_readable(make_cluster, make_fake):
    cluster, _ = system(make_cluster, make_fake)
    created = requests.post(f"{cluster.url('bookings-api')}/bookings", json=BOOKING)
    assert created.status_code == 201
    fetched = requests.get(f"{cluster.url('bookings-api')}/bookings/{created.json()['id']}")
    assert fetched.json()["hotel"] == "Астория"


def test_reminder_goes_out_once_the_day_before(make_cluster, make_fake):
    cluster, mailer = system(make_cluster, make_fake)
    requests.post(f"{cluster.url('bookings-api')}/bookings", json=BOOKING)
    assert run_due(cluster, "2026-07-08") == {"sent": 0}
    assert run_due(cluster, "2026-07-09") == {"sent": 1}
    assert run_due(cluster, "2026-07-09") == {"sent": 0}
    assert mailer.calls[0]["body"]["recipient"] == "g@example.org"
