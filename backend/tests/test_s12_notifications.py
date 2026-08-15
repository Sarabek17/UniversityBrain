"""S12 tests: the notification centre — one bell for every module event.

The seed writes 15 demo rows and they are the demo, so this file never counts
"all notifications of a user": it filters by `(notif_type, link_id)` and
asserts two things instead.

* the **bell** — own rows only (a stranger's id is a 404, not a 403), the
  unread counter travels with the page, read / read-all move it;
* every **trigger** of FUNKSIONALLIK 3.10 that S12 added: a receipt uploaded
  and confirmed (S8), a student marked absent (S9), an execution deadline
  (S11) and the contract debt reminder — each written exactly once, and never
  on top of a row the seed already wrote.

Anything this file creates (payments, flows, attendance rows) is removed
again: pytest runs the session files in one shared demo database.
"""

from datetime import date, timedelta

import pytest

from app.agents.registry import execute_tool, tool_names_for_role
from app.models import (
    Attendance,
    ClassSession,
    FlowDocument,
    FlowHistory,
    Notification,
    Payment,
    PaymentStatus,
    Schedule,
    User,
    UserRole,
)
from app.services import notifications as notif_service

DEMO_PASSWORD = "demo123"
TODAY = date.today()
TOOL = "bildirishnomalar"


# --- helpers ----------------------------------------------------------------


def headers(client, username):
    res = client.post(
        "/auth/login", json={"username": username, "password": DEMO_PASSWORD}
    )
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture(scope="module")
def users(db_session):
    def get(username):
        return db_session.query(User).filter_by(username=username).one()

    return {
        n: get(n)
        for n in (
            "aliyev",
            "karimov",
            "mahmudov",
            "sharipova",
            "abdullayev",
            "umarov",
            "tursunov",
            "nazarova",
            "rashidova",
            "admin",
        )
    }


@pytest.fixture
def fresh(db_session):
    """Re-read the DB after an endpoint wrote to it (own session snapshot)."""
    db_session.rollback()
    return db_session


@pytest.fixture(scope="module")
def hero_class(db_session, users):
    """AT-24-01, pair 3 today: "Ma'lumotlar bazasi", room 214, teacher umarov."""
    return (
        db_session.query(Schedule)
        .filter(
            Schedule.group_id == users["aliyev"].group_id,
            Schedule.weekday == TODAY.weekday(),
            Schedule.pair_number == 3,
        )
        .one()
    )


def rows_of(db, user_id, notif_type, link_id=None):
    db.rollback()
    query = db.query(Notification).filter(
        Notification.user_id == user_id, Notification.notif_type == notif_type
    )
    if link_id is not None:
        query = query.filter(Notification.link_id == link_id)
    return query.all()


def bell(client, username, suffix=""):
    res = client.get(f"/notifications{suffix}", headers=headers(client, username))
    assert res.status_code == 200, res.text
    return res.json()


# --- the bell ---------------------------------------------------------------


def test_bell_returns_own_rows_with_the_unread_counter(client, users):
    body = bell(client, "aliyev")
    assert body["rows"], "aliyev has seeded notifications"
    assert all(row["user_id"] == users["aliyev"].id for row in body["rows"])
    assert body["total"] >= len(body["rows"])
    # one request is enough for the bell: the counter comes with the page
    assert body["unread_count"] == sum(1 for r in body["rows"] if not r["is_read"])
    assert {"id", "notif_type", "text", "link_type", "link_id", "created_at"} <= set(
        body["rows"][0]
    )


def test_rows_are_newest_first_and_carry_a_link(client):
    body = bell(client, "aliyev")
    stamps = [row["created_at"] for row in body["rows"]]
    assert stamps == sorted(stamps, reverse=True)
    flow_rows = [r for r in body["rows"] if r["notif_type"] == "flow_status"]
    assert flow_rows and flow_rows[0]["link_type"] == "flow_document"
    assert flow_rows[0]["link_id"] is not None


def test_unread_filter_and_limit_do_not_shrink_the_counter(client):
    body = bell(client, "aliyev", "?unread=true&limit=1")
    assert body["unread_only"] is True
    assert len(body["rows"]) <= 1
    assert all(row["is_read"] is False for row in body["rows"])
    # the page is limited, the counter is not
    assert body["unread_count"] >= len(body["rows"])


def test_another_persons_notification_is_a_404(client, users, fresh):
    debt = rows_of(fresh, users["karimov"].id, notif_service.PAYMENT_DEBT)
    assert debt, "the seed writes karimov's debt reminder"
    stranger_id = debt[0].id

    body = bell(client, "aliyev")
    assert stranger_id not in {row["id"] for row in body["rows"]}
    res = client.post(
        f"/notifications/{stranger_id}/read", headers=headers(client, "aliyev")
    )
    assert res.status_code == 404


def test_read_one_then_read_all(client, users, fresh):
    """abdullayev has a single seeded row, so the counter is easy to follow."""
    own = fresh.query(Notification).filter(
        Notification.user_id == users["abdullayev"].id
    ).all()
    assert own
    ids = [row.id for row in own]
    try:
        before = bell(client, "abdullayev")
        assert before["unread_count"] >= 1
        first = before["rows"][0]["id"]

        after = client.post(
            f"/notifications/{first}/read", headers=headers(client, "abdullayev")
        )
        assert after.status_code == 200, after.text
        body = after.json()
        assert body["unread_count"] == before["unread_count"] - 1
        assert next(r for r in body["rows"] if r["id"] == first)["is_read"] is True

        cleared = client.post(
            "/notifications/read-all", headers=headers(client, "abdullayev")
        )
        assert cleared.status_code == 200
        assert cleared.json()["unread_count"] == 0
        assert bell(client, "abdullayev")["unread_count"] == 0
    finally:
        fresh.rollback()
        for row in fresh.query(Notification).filter(Notification.id.in_(ids)):
            row.is_read = False
        fresh.commit()


# --- trigger: a receipt is uploaded / confirmed (S8) -------------------------


def test_uploading_a_receipt_notifies_the_tutor(client, users, fresh):
    tutor_id = users["nazarova"].id
    before = len(rows_of(fresh, tutor_id, notif_service.PAYMENT_UPLOADED))

    res = client.post(
        "/payments/receipts",
        json={"amount": 1_000_000, "receipt_number": "CHK-S12-TEST"},
        headers=headers(client, "karimov"),
    )
    assert res.status_code == 200, res.text
    fresh.rollback()
    payment = (
        fresh.query(Payment)
        .filter(Payment.receipt_number == "CHK-S12-TEST")
        .one()
    )
    try:
        written = rows_of(
            fresh, tutor_id, notif_service.PAYMENT_UPLOADED, payment.id
        )
        assert len(written) == 1
        assert "Karimov" in written[0].text
        assert written[0].link_type == notif_service.LINK_PAYMENT
        assert len(rows_of(fresh, tutor_id, notif_service.PAYMENT_UPLOADED)) == (
            before + 1
        )
        # the same event a second time writes nothing
        assert (
            notif_service.notify_receipt_uploaded(fresh, users["karimov"], payment)
            == 0
        )
    finally:
        fresh.rollback()
        fresh.query(Notification).filter(
            Notification.notif_type.in_(
                (notif_service.PAYMENT_UPLOADED, notif_service.PAYMENT_CONFIRMED)
            ),
            Notification.link_id == payment.id,
        ).delete(synchronize_session=False)
        fresh.query(Payment).filter(Payment.id == payment.id).delete()
        fresh.commit()


def test_seeded_receipt_row_is_never_doubled(fresh, users):
    """sharipova's pending receipt already has its row — the seed wrote it."""
    payment = (
        fresh.query(Payment)
        .filter(
            Payment.student_id == users["sharipova"].id,
            Payment.status == PaymentStatus.uploaded,
        )
        .first()
    )
    assert payment is not None
    before = rows_of(
        fresh, users["nazarova"].id, notif_service.PAYMENT_UPLOADED, payment.id
    )
    assert len(before) == 1
    assert (
        notif_service.notify_receipt_uploaded(fresh, users["sharipova"], payment) == 0
    )
    assert (
        len(
            rows_of(
                fresh,
                users["nazarova"].id,
                notif_service.PAYMENT_UPLOADED,
                payment.id,
            )
        )
        == 1
    )


def test_confirming_a_receipt_notifies_the_student(client, users, fresh):
    payment = (
        fresh.query(Payment)
        .filter(
            Payment.student_id == users["sharipova"].id,
            Payment.status == PaymentStatus.uploaded,
        )
        .first()
    )
    assert payment is not None
    payment_id = payment.id
    try:
        res = client.post(
            f"/payments/{payment_id}/confirm", headers=headers(client, "nazarova")
        )
        assert res.status_code == 200, res.text
        written = rows_of(
            fresh,
            users["sharipova"].id,
            notif_service.PAYMENT_CONFIRMED,
            payment_id,
        )
        assert len(written) == 1
        assert "tasdiqlandi" in written[0].text
        assert written[0].link_type == notif_service.LINK_PAYMENT
        assert (
            notif_service.notify_payment_confirmed(
                fresh, users["sharipova"], fresh.get(Payment, payment_id)
            )
            == 0
        )
    finally:
        fresh.rollback()
        fresh.query(Notification).filter(
            Notification.notif_type == notif_service.PAYMENT_CONFIRMED,
            Notification.link_id == payment_id,
        ).delete(synchronize_session=False)
        fresh.get(Payment, payment_id).status = PaymentStatus.uploaded
        fresh.commit()


# --- trigger: marked absent in a class (S9) ---------------------------------


def test_being_marked_absent_notifies_the_student(client, users, fresh, hero_class):
    """A future date, so nothing the other sessions assert on is touched."""
    day = TODAY + timedelta(days=9)
    student = users["mahmudov"]
    payload = {
        "marks": [{"student_id": student.id, "status": "absent"}],
        "on_date": day.isoformat(),
    }
    try:
        res = client.post(
            f"/attendance/class/{hero_class.id}/mark",
            json=payload,
            headers=headers(client, "umarov"),
        )
        assert res.status_code == 200, res.text
        written = rows_of(
            fresh, student.id, notif_service.CLASS_ABSENT, hero_class.id
        )
        assert len(written) == 1
        assert day.strftime("%d.%m.%Y") in written[0].text
        assert "kelmagan" in written[0].text
        assert written[0].link_type == notif_service.LINK_SCHEDULE

        # saving the same class again must not write a second row
        again = client.post(
            f"/attendance/class/{hero_class.id}/mark",
            json=payload,
            headers=headers(client, "umarov"),
        )
        assert again.status_code == 200
        assert (
            len(rows_of(fresh, student.id, notif_service.CLASS_ABSENT, hero_class.id))
            == 1
        )
        # a student who was present hears nothing
        assert rows_of(fresh, users["aliyev"].id, notif_service.CLASS_ABSENT) == []
    finally:
        fresh.rollback()
        fresh.query(Notification).filter(
            Notification.notif_type == notif_service.CLASS_ABSENT,
            Notification.link_id == hero_class.id,
        ).delete(synchronize_session=False)
        fresh.query(Attendance).filter(
            Attendance.schedule_id == hero_class.id, Attendance.date == day
        ).delete(synchronize_session=False)
        fresh.query(ClassSession).filter(
            ClassSession.schedule_id == hero_class.id, ClassSession.date == day
        ).delete(synchronize_session=False)
        fresh.commit()


# --- trigger: execution deadline (S11 counters, no new query) ---------------


def test_deadline_notifies_the_executor_and_the_sender(client, users, fresh):
    due = TODAY + timedelta(days=1)
    created = client.post(
        "/docflow",
        headers=headers(client, "rashidova"),
        json={
            "template_id": "buyruq_topshiriq",
            "body_text": "Tursunov Akmalga. S12 muddat sinovi uchun topshiriq.",
            "recipient_user_id": users["tursunov"].id,
            "due_date": due.isoformat(),
        },
    )
    assert created.status_code == 201, created.text
    flow_id = created.json()["id"]
    try:
        for username, user_id in (
            ("tursunov", users["tursunov"].id),
            ("rashidova", users["rashidova"].id),
        ):
            body = bell(client, username)
            written = rows_of(fresh, user_id, notif_service.FLOW_DUE, flow_id)
            assert len(written) == 1, username
            assert "Ijro muddati yaqin" in written[0].text
            assert due.strftime("%d.%m.%Y") in written[0].text
            assert written[0].link_type == notif_service.LINK_FLOW
            assert flow_id in {
                row["link_id"]
                for row in body["rows"]
                if row["notif_type"] == notif_service.FLOW_DUE
            }
            # opening the bell again recomputes but writes nothing new
            bell(client, username)
            assert (
                len(rows_of(fresh, user_id, notif_service.FLOW_DUE, flow_id)) == 1
            )
    finally:
        fresh.rollback()
        fresh.query(Notification).filter(
            Notification.link_type == notif_service.LINK_FLOW,
            Notification.link_id == flow_id,
        ).delete(synchronize_session=False)
        fresh.query(FlowHistory).filter(
            FlowHistory.flow_document_id == flow_id
        ).delete(synchronize_session=False)
        fresh.query(FlowDocument).filter(FlowDocument.id == flow_id).delete()
        fresh.commit()


def test_closed_documents_never_raise_a_deadline(client, users, fresh):
    """aliyev's approved application has no deadline row and never gets one."""
    bell(client, "aliyev")
    assert rows_of(fresh, users["aliyev"].id, notif_service.FLOW_DUE) == []


# --- trigger: contract debt (computed when the bell is opened) --------------


def test_debt_reminder_reuses_the_seeded_row(client, users, fresh):
    before = rows_of(fresh, users["karimov"].id, notif_service.PAYMENT_DEBT)
    assert len(before) == 1  # the seed's row
    bell(client, "karimov")
    bell(client, "karimov")
    after = rows_of(fresh, users["karimov"].id, notif_service.PAYMENT_DEBT)
    assert len(after) == 1
    assert after[0].id == before[0].id
    assert after[0].link_type == notif_service.LINK_CONTRACT


def test_tutor_gets_one_debt_summary(client, users, fresh):
    bell(client, "nazarova")
    bell(client, "nazarova")
    written = rows_of(fresh, users["nazarova"].id, notif_service.PAYMENT_DEBT)
    assert len(written) == 1
    assert "qarzdor" in written[0].text


def test_a_paid_student_gets_no_debt_reminder(client, users, fresh):
    bell(client, "aliyev")
    assert rows_of(fresh, users["aliyev"].id, notif_service.PAYMENT_DEBT) == []


# --- the agent tool ---------------------------------------------------------


def test_tool_is_open_to_every_role(db_session):
    for role in UserRole:
        assert TOOL in tool_names_for_role(role), role


def test_tool_answers_with_a_source_and_only_own_rows(db_session, users, fresh):
    stranger = rows_of(fresh, users["karimov"].id, notif_service.PAYMENT_DEBT)[0].text
    fresh.rollback()
    result = execute_tool(TOOL, {}, fresh, users["aliyev"])
    assert result.ok
    first_line = result.text.splitlines()[0]
    assert first_line.startswith("Bildirishnomalar ro'yxati, ")
    assert "o'qilmagan" in first_line
    assert result.sources and result.sources[0]["type"] == notif_service.SOURCE_TYPE
    assert result.sources[0]["label"] == first_line
    assert stranger not in result.text  # another person's debt never leaks


def test_tool_can_include_already_read_rows(db_session, users, fresh):
    fresh.rollback()
    unread = execute_tool(TOOL, {}, fresh, users["karimov"])
    fresh.rollback()
    everything = execute_tool(TOOL, {"holat": "hammasi"}, fresh, users["karimov"])
    assert everything.ok
    assert len(everything.text.splitlines()) >= len(unread.text.splitlines())
    assert "[Kontrakt qarzdorligi]" in everything.text
