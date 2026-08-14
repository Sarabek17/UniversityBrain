"""S8 tests: contract state, tutor group summary, receipt upload/confirm.

What is verified here is the money arithmetic against the *seed* numbers
(aliyev fully paid, karimov debtor, sodiqova exactly 50%), the scope rules
(a student may not read another student's contract, a tutor sees only their own
groups) and the receipt flow (sharipova's uploaded receipt becomes confirmed
only through her own tutor).
"""

import pytest

from app.agents.registry import execute_tool, tool_names_for_role
from app.models import Payment, PaymentStatus, User, UserRole
from app.services import payments as payments_service

DEMO_PASSWORD = "demo123"

FACULTY1_TOTAL = 12_000_000.0
FACULTY2_TOTAL = 10_500_000.0

TOOL = "tolov_holati"


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
            "sodiqova",
            "sharipova",
            "nazarova",
            "qodirova",
            "umarov",
            "rashidova",
            "admin",
        )
    }


@pytest.fixture
def fresh(db_session):
    """Re-read the DB after an endpoint wrote to it (own session snapshot)."""
    db_session.rollback()
    return db_session


def contract(client, username, student_id=None):
    path = "/payments/contract" if student_id is None else f"/payments/contract/{student_id}"
    return client.get(path, headers=headers(client, username))


def uploaded_payment(db_session, student_id):
    db_session.rollback()
    return (
        db_session.query(Payment)
        .filter(
            Payment.student_id == student_id,
            Payment.status == PaymentStatus.uploaded,
        )
        .order_by(Payment.id.desc())
        .first()
    )


def run_tool(db_session, user, args=None):
    db_session.rollback()
    return execute_tool(TOOL, args or {}, db_session, user)


# --- 1. the numbers match the seed ------------------------------------------


def test_aliyev_is_fully_paid(client):
    res = contract(client, "aliyev")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["total_amount"] == FACULTY1_TOTAL
    assert body["paid_amount"] == FACULTY1_TOTAL
    assert body["remaining_amount"] == 0.0
    assert body["paid_percent"] == 100
    assert body["state"] == "paid"
    assert len(body["payments"]) == 3  # 40% + 30% + 30%
    assert body["source"]["type"] == "payment"
    assert body["disclaimer"]


def test_karimov_is_a_full_debtor(client):
    body = contract(client, "karimov").json()
    assert body["total_amount"] == FACULTY1_TOTAL
    assert body["paid_amount"] == 0.0
    assert body["remaining_amount"] == FACULTY1_TOTAL
    assert body["paid_percent"] == 0
    assert body["state"] == "debtor"
    assert body["payments"] == []


def test_sodiqova_paid_exactly_half(client):
    body = contract(client, "sodiqova").json()
    assert body["paid_amount"] == FACULTY1_TOTAL * 0.5 == 6_000_000.0
    assert body["remaining_amount"] == 6_000_000.0
    assert body["paid_percent"] == 50
    assert body["state"] == "partial"
    assert body["pending_amount"] == 0.0


def test_uploaded_receipt_is_pending_not_paid(client):
    """sharipova: 50% confirmed + 10% waiting for the tutor (S8 demo node)."""
    body = contract(client, "sharipova").json()
    assert body["paid_amount"] == 6_000_000.0
    assert body["pending_amount"] == 1_200_000.0
    assert body["remaining_amount"] == 6_000_000.0  # pending does not reduce it
    assert body["state"] == "partial"


# --- 2. scope: a student sees only themselves -------------------------------


def test_student_asking_for_another_student_gets_403(client, users):
    res = contract(client, "aliyev", users["karimov"].id)
    assert res.status_code == 403, res.text


def test_student_may_read_their_own_contract_by_id(client, users):
    res = contract(client, "aliyev", users["aliyev"].id)
    assert res.status_code == 200
    assert res.json()["username"] == "aliyev"


def test_without_a_token_everything_is_401(client, users):
    assert client.get("/payments/contract").status_code == 401
    assert client.get("/payments/group").status_code == 401
    assert client.get(f"/payments/contract/{users['aliyev'].id}").status_code == 401
    assert client.post("/payments/receipts", json={"amount": 1}).status_code == 401


# --- 3. scope: the tutor dashboard ------------------------------------------


def test_tutor_sees_only_their_own_groups(client, users):
    res = client.get("/payments/group", headers=headers(client, "nazarova"))
    assert res.status_code == 200, res.text
    body = res.json()
    assert sorted(body["group_names"]) == ["AT-24-01", "AT-24-02"]
    usernames = {row["username"] for row in body["rows"]}
    assert "aliyev" in usernames and "sharipova" in usernames
    assert not usernames & {"ismatov", "roziyeva", "boboyev"}  # IQ students
    assert len(body["rows"]) == 16
    assert body["debtor_count"] == 2  # karimov + olimov
    assert body["pending_count"] == 1  # sharipova's receipt
    # biggest debt first — that is what the tutor is looking for
    remaining = [row["remaining_amount"] for row in body["rows"]]
    assert remaining == sorted(remaining, reverse=True)
    assert remaining[0] == FACULTY1_TOTAL


def test_other_faculty_tutor_cannot_reach_an_at_student(client, users):
    res = contract(client, "qodirova", users["aliyev"].id)
    assert res.status_code == 403, res.text
    body = client.get("/payments/group", headers=headers(client, "qodirova")).json()
    assert sorted(body["group_names"]) == ["IQ-24-01", "IQ-24-02"]
    assert all(row["total_amount"] == FACULTY2_TOTAL for row in body["rows"])


def test_staff_sees_their_faculty_and_admin_sees_everything(client):
    staff = client.get("/payments/group", headers=headers(client, "rashidova")).json()
    assert sorted(staff["group_names"]) == ["AT-24-01", "AT-24-02"]
    everything = client.get("/payments/group", headers=headers(client, "admin")).json()
    assert len(everything["group_names"]) == 4
    assert len(everything["rows"]) == 30


def test_teacher_has_no_payment_access(client):
    assert client.get(
        "/payments/group", headers=headers(client, "umarov")
    ).status_code == 403


def test_group_id_outside_the_scope_is_403(client, db_session):
    db_session.rollback()
    iq_group = db_session.query(User).filter_by(username="ismatov").one().group_id
    res = client.get(
        f"/payments/group?group_id={iq_group}", headers=headers(client, "nazarova")
    )
    assert res.status_code == 403, res.text


# --- 4. receipts ------------------------------------------------------------


def test_receipt_view_survives_the_missing_file(client, users, db_session):
    """Seed receipt paths point at files that do not exist — no 404 for that."""
    payment = uploaded_payment(db_session, users["sharipova"].id)
    assert payment is not None and payment.receipt_file  # seed placeholder path
    res = client.get(
        f"/payments/{payment.id}/receipt", headers=headers(client, "sharipova")
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["receipt_number"] == payment.receipt_number
    assert body["file_available"] is False
    assert body["note"]
    assert body["status"] == "uploaded"
    assert body["source"]["type"] == "payment"


def test_another_students_receipt_is_403(client, users, db_session):
    payment = uploaded_payment(db_session, users["sharipova"].id)
    res = client.get(
        f"/payments/{payment.id}/receipt", headers=headers(client, "aliyev")
    )
    assert res.status_code == 403, res.text


def test_tutor_confirms_the_uploaded_receipt(client, users, db_session):
    payment = uploaded_payment(db_session, users["sharipova"].id)
    assert payment is not None
    payment_id = payment.id
    try:
        # the wrong faculty's tutor is refused before anything is written
        assert client.post(
            f"/payments/{payment_id}/confirm", headers=headers(client, "qodirova")
        ).status_code == 403
        db_session.rollback()
        assert db_session.get(Payment, payment_id).status == PaymentStatus.uploaded

        res = client.post(
            f"/payments/{payment_id}/confirm", headers=headers(client, "nazarova")
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["username"] == "sharipova"
        assert body["paid_amount"] == 7_200_000.0
        assert body["pending_amount"] == 0.0
        assert body["remaining_amount"] == 4_800_000.0
        db_session.rollback()
        assert db_session.get(Payment, payment_id).status == PaymentStatus.confirmed

        # confirming twice is a conflict, not a silent no-op
        assert client.post(
            f"/payments/{payment_id}/confirm", headers=headers(client, "nazarova")
        ).status_code == 409
    finally:
        db_session.rollback()
        row = db_session.get(Payment, payment_id)
        row.status = PaymentStatus.uploaded
        db_session.commit()


def test_student_uploads_a_receipt(client, users, db_session):
    before = contract(client, "karimov").json()
    assert before["pending_amount"] == 0.0

    res = client.post(
        "/payments/receipts",
        json={"amount": 1_000_000, "receipt_number": "CHK-TEST01"},
        headers=headers(client, "karimov"),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    created = uploaded_payment(db_session, users["karimov"].id)
    try:
        assert body["pending_amount"] == 1_000_000.0
        assert body["paid_amount"] == 0.0  # still not paid: awaiting confirmation
        assert body["state"] == "debtor"
        assert created is not None and created.receipt_number == "CHK-TEST01"
        assert created.receipt_file is None
    finally:
        db_session.rollback()
        db_session.delete(db_session.get(Payment, created.id))
        db_session.commit()


def test_upload_rejects_bad_amounts(client):
    bad = client.post(
        "/payments/receipts", json={"amount": 0}, headers=headers(client, "karimov")
    )
    assert bad.status_code == 422, bad.text
    too_much = client.post(
        "/payments/receipts",
        json={"amount": FACULTY1_TOTAL + 1},
        headers=headers(client, "karimov"),
    )
    assert too_much.status_code == 422, too_much.text
    paid_up = client.post(
        "/payments/receipts",
        json={"amount": 100},
        headers=headers(client, "aliyev"),  # nothing left to pay
    )
    assert paid_up.status_code == 422


def test_tutor_may_not_upload_a_receipt(client):
    res = client.post(
        "/payments/receipts", json={"amount": 100}, headers=headers(client, "nazarova")
    )
    assert res.status_code == 403, res.text


# --- 5. the `tolov_holati` tool ---------------------------------------------


def test_tool_is_closed_for_teachers(users):
    assert TOOL in tool_names_for_role(UserRole.student)
    assert TOOL in tool_names_for_role(UserRole.tutor)
    assert TOOL in tool_names_for_role(UserRole.staff)
    assert TOOL in tool_names_for_role(UserRole.admin)
    assert TOOL not in tool_names_for_role(UserRole.teacher)


def test_tool_refuses_a_teacher_before_the_handler(db_session, users):
    result = run_tool(db_session, users["umarov"])
    assert result.ok is False
    assert "Ruxsat yo'q" in result.text


def test_tool_gives_the_student_their_own_exact_numbers(db_session, users):
    result = run_tool(db_session, users["aliyev"])
    assert result.ok is True
    assert "12 000 000 so'm" in result.text  # total
    assert "Qoldiq: 0 so'm" in result.text
    assert "CLK-" in result.text or "CHK-" in result.text  # last receipt number
    assert result.sources and result.sources[0]["type"] == "payment"
    assert "to'lov jadvali" in result.text.lower()


def test_tool_refuses_a_student_asking_about_someone_else(db_session, users):
    result = run_tool(db_session, users["aliyev"], {"talaba": "karimov"})
    assert result.ok is False
    assert "Ruxsat yo'q" in result.text
    assert "12 000 000" not in result.text


def test_tool_lets_a_student_name_themselves(db_session, users):
    result = run_tool(db_session, users["karimov"], {"talaba": "Karimov Diyor"})
    assert result.ok is True
    assert "Qoldiq: 12 000 000 so'm" in result.text


def test_tool_tutor_reads_a_student_of_their_group(db_session, users):
    result = run_tool(db_session, users["nazarova"], {"talaba": "karimov"})
    assert result.ok is True
    assert "Karimov Diyor" in result.text
    assert "Qoldiq: 12 000 000 so'm" in result.text


def test_tool_tutor_cannot_reach_another_faculty(db_session, users):
    result = run_tool(db_session, users["qodirova"], {"talaba": "karimov"})
    assert result.ok is False
    assert "Ruxsat yo'q" in result.text


def test_tool_without_a_name_gives_the_tutor_the_group_summary(db_session, users):
    result = run_tool(db_session, users["nazarova"])
    assert result.ok is True
    assert "qarzdor" in result.text
    assert "Karimov Diyor" in result.text
    assert "Sharipova Gulnora" in result.text  # pending receipt shows up
    assert "Ismatov" not in result.text  # IQ faculty stays out


def test_tool_unknown_student(db_session, users):
    result = run_tool(db_session, users["nazarova"], {"talaba": "Petrov"})
    assert result.ok is False
    assert "topilmadi" in result.text


# --- 6. the chat path (the DoD question) ------------------------------------


def test_chat_answers_the_contract_question_with_numbers_and_a_source(client):
    res = client.post(
        "/chat",
        json={"message": f"use_tool:{TOOL}:{{}} Kontraktimdan qancha qoldi?"},
        headers=headers(client, "aliyev"),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert "12 000 000 so'm" in body["text"]
    assert body["sources"] and body["sources"][0]["type"] == "payment"
    assert body["disclaimer"]


# --- 7. service-level details -----------------------------------------------


def test_format_amount_and_state():
    assert payments_service.format_amount(12_000_000) == "12 000 000 so'm"
    assert payments_service.state_of(100.0, 0.0) == payments_service.DEBTOR
    assert payments_service.state_of(100.0, 50.0) == payments_service.PARTIAL
    assert payments_service.state_of(100.0, 100.0) == payments_service.PAID
