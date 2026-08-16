"""S11 tests: the document flow and its status chain.

The seed writes four documents and never changes (they are the demo):

    aliyev      -> dekanat (role)     malumotnoma       approved    3 history rows
    abdullayev  -> dekanat (role)     qayta_topshirish  seen        2 history rows
    umarov      -> dekanat (role)     semestr_hisobot   sent        1 history row
    rashidova   -> tursunov (person)  buyruq_topshiriq  in_progress 3 history rows

So this file asserts two different things and keeps them apart:

* the **chain** — a student sends a fresh application, the dean's office sees
  it, marks it seen and approves it; three history rows and a notification at
  every step (nothing seeded is touched);
* the **boundaries** — a stranger's application is a 404 (not a 403: its
  existence is not disclosed), only the recipient may move the status (403),
  a rejection without a reason is refused (422), and an approved document is
  final (409).
"""

from datetime import date, timedelta

import pytest

from app.agents.registry import execute_tool, tool_names_for_role
from app.models import (
    FlowDocument,
    FlowHistory,
    FlowStatus,
    Notification,
    User,
    UserRole,
)
from app.services import docflow as docflow_service

DEMO_PASSWORD = "demo123"
TOOL = "ariza_holati"


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
            "abdullayev",
            "umarov",
            "tursunov",
            "rashidova",
            "yusupov",
            "nazarova",
            "admin",
        )
    }


@pytest.fixture(scope="module")
def seeded_flows(db_session):
    """The four seeded documents, by template id."""

    def by_template(template_id):
        return (
            db_session.query(FlowDocument)
            .filter(FlowDocument.template_id == template_id)
            .order_by(FlowDocument.id)
            .first()
        )

    flows = {t: by_template(t) for t in ("malumotnoma", "qayta_topshirish", "semestr_hisobot", "buyruq_topshiriq")}
    assert all(f is not None for f in flows.values()), flows
    return flows


def history_count(db_session, flow_id):
    db_session.rollback()
    return (
        db_session.query(FlowHistory)
        .filter(FlowHistory.flow_document_id == flow_id)
        .count()
    )


def notifications_for(db_session, user_id, link_id):
    db_session.rollback()
    return (
        db_session.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.link_type == "flow_document",
            Notification.link_id == link_id,
        )
        .all()
    )


# --- templates --------------------------------------------------------------


def test_six_templates_and_the_seeded_four_are_in_the_catalogue():
    assert len(docflow_service.TEMPLATES) == 6
    for template_id in (
        "malumotnoma",
        "qayta_topshirish",
        "semestr_hisobot",
        "buyruq_topshiriq",
        "akademik_tatil",  # the fifth, added by S11 without touching the seed
    ):
        assert docflow_service.get_template(template_id) is not None


def test_templates_are_role_filtered(client):
    student = client.get("/docflow/templates", headers=headers(client, "aliyev"))
    teacher = client.get("/docflow/templates", headers=headers(client, "umarov"))
    staff = client.get("/docflow/templates", headers=headers(client, "rashidova"))
    assert student.status_code == 200

    student_ids = {t["id"] for t in student.json()}
    teacher_ids = {t["id"] for t in teacher.json()}
    staff_ids = {t["id"] for t in staff.json()}

    assert "malumotnoma" in student_ids and "akademik_tatil" in student_ids
    # A student cannot issue an order, a teacher cannot file a student's leave.
    assert "buyruq_topshiriq" not in student_ids
    assert teacher_ids == {"semestr_hisobot"}
    assert staff_ids == {"buyruq_topshiriq"}

    order = next(t for t in staff.json() if t["id"] == "buyruq_topshiriq")
    assert order["needs_recipient_user"] is True
    assert order["needs_due_date"] is True
    assert order["doc_type"] == "order"


def test_templates_need_a_token(client):
    assert client.get("/docflow/templates").status_code == 401


# --- list scope -------------------------------------------------------------


def test_student_outbox_holds_only_their_own(client, seeded_flows):
    res = client.get("/docflow/outbox", headers=headers(client, "aliyev"))
    assert res.status_code == 200
    body = res.json()
    ids = {row["id"] for row in body["rows"]}
    assert seeded_flows["malumotnoma"].id in ids
    # Another student's application is not in the list at all.
    assert seeded_flows["qayta_topshirish"].id not in ids
    row = next(r for r in body["rows"] if r["id"] == seeded_flows["malumotnoma"].id)
    assert row["status"] == "approved"
    assert row["status_label"] == "tasdiqlandi"
    assert row["recipient_label"] == "Dekanat"
    assert row["is_outgoing"] is True and row["is_incoming"] is False
    assert row["can_change_status"] is False  # the sender never decides


def test_student_inbox_is_empty(client):
    res = client.get("/docflow/inbox", headers=headers(client, "aliyev"))
    assert res.status_code == 200
    assert res.json()["rows"] == []


def test_staff_inbox_covers_role_addressed_documents(client, seeded_flows):
    res = client.get("/docflow/inbox", headers=headers(client, "rashidova"))
    assert res.status_code == 200
    ids = {row["id"] for row in res.json()["rows"]}
    for key in ("malumotnoma", "qayta_topshirish", "semestr_hisobot"):
        assert seeded_flows[key].id in ids, key
    # The order she sent herself belongs in the outbox, not the inbox.
    assert seeded_flows["buyruq_topshiriq"].id not in ids


def test_staff_of_another_faculty_sees_nothing_of_ours(client, seeded_flows):
    res = client.get("/docflow/inbox", headers=headers(client, "yusupov"))
    assert res.status_code == 200
    ids = {row["id"] for row in res.json()["rows"]}
    assert ids.isdisjoint({f.id for f in seeded_flows.values()})


def test_person_addressed_document_reaches_that_person(client, seeded_flows):
    res = client.get("/docflow/inbox", headers=headers(client, "tursunov"))
    assert res.status_code == 200
    rows = res.json()["rows"]
    row = next(r for r in rows if r["id"] == seeded_flows["buyruq_topshiriq"].id)
    assert row["is_incoming"] is True
    assert row["status"] == "in_progress"
    assert row["can_change_status"] is True
    assert row["due_in_days"] == 5  # seed: today + 5 days
    assert row["overdue"] is False
    assert row["doc_type_label"] == "Buyruq"


def test_due_sorting_puts_the_deadline_first(client, seeded_flows):
    res = client.get("/docflow/inbox?sort=due", headers=headers(client, "tursunov"))
    assert res.status_code == 200
    body = res.json()
    assert body["sort"] == "due"
    assert body["rows"][0]["id"] == seeded_flows["buyruq_topshiriq"].id
    assert body["due_soon_count"] == 0  # 5 days away is not "soon" (<= 3)


def test_foreign_document_answers_404(client, seeded_flows):
    """Not 403: the existence of a stranger's application is not disclosed."""
    other = seeded_flows["qayta_topshirish"].id
    assert (
        client.get(f"/docflow/{other}", headers=headers(client, "aliyev")).status_code
        == 404
    )
    assert (
        client.get(
            f"/docflow/{seeded_flows['malumotnoma'].id}",
            headers=headers(client, "yusupov"),
        ).status_code
        == 404
    )


def test_detail_carries_history_and_source(client, seeded_flows):
    flow_id = seeded_flows["malumotnoma"].id
    res = client.get(f"/docflow/{flow_id}", headers=headers(client, "aliyev"))
    assert res.status_code == 200
    body = res.json()
    assert [h["status"] for h in body["history"]] == ["sent", "seen", "approved"]
    assert "204-xona" in body["history"][-1]["comment"]
    assert body["history"][-1]["changed_by_name"] == "Rashidova Nilufar"
    assert body["source"]["label"].startswith(f"Ariza №{flow_id}, ")
    assert "holat: tasdiqlandi" in body["source"]["label"]
    assert body["disclaimer"]
    assert body["next_statuses"] == []  # approved is final


# --- the chain --------------------------------------------------------------


def test_full_chain_student_to_approval(client, db_session, users):
    """talaba yuboradi -> dekanat ko'radi -> tasdiqlaydi: 3 history + 3 notif."""
    student = headers(client, "aliyev")
    staff = headers(client, "rashidova")

    created = client.post(
        "/docflow",
        headers=student,
        json={
            "template_id": "akademik_tatil",
            "body_text": (
                "Dekanatga AT-24-01 guruhi talabasi Aliyev Jasurdan.\n\nARIZA\n\n"
                "Sog'lig'im holati sababli menga bir yil muddatga akademik "
                "ta'til berishingizni so'rayman."
            ),
        },
    )
    assert created.status_code == 201, created.text
    flow = created.json()
    flow_id = flow["id"]
    assert flow["status"] == "sent"
    assert flow["recipient_label"] == "Dekanat"
    assert len(flow["history"]) == 1
    assert history_count(db_session, flow_id) == 1

    # the dean's office was notified that something arrived
    incoming = notifications_for(db_session, users["rashidova"].id, flow_id)
    assert len(incoming) == 1
    assert incoming[0].notif_type == "flow_incoming"
    assert "Aliyev Jasur" in incoming[0].text
    # ...and the dean of the *other* faculty was not
    assert notifications_for(db_session, users["yusupov"].id, flow_id) == []

    # it shows up in the dean's inbox as "new"
    inbox = client.get("/docflow/inbox", headers=staff).json()
    row = next(r for r in inbox["rows"] if r["id"] == flow_id)
    assert row["status"] == "sent" and row["can_change_status"] is True
    assert inbox["new_count"] >= 1

    seen = client.post(
        f"/docflow/{flow_id}/status", headers=staff, json={"status": "seen"}
    )
    assert seen.status_code == 200, seen.text
    assert seen.json()["status"] == "seen"
    assert len(seen.json()["history"]) == 2

    approved = client.post(
        f"/docflow/{flow_id}/status",
        headers=staff,
        json={
            "status": "approved",
            "comment": "Buyruq loyihasi tayyorlandi, 204-xonaga murojaat qiling.",
        },
    )
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["status"] == "approved"
    assert [h["status"] for h in body["history"]] == ["sent", "seen", "approved"]
    assert history_count(db_session, flow_id) == 3

    # every status step wrote a notification for the sender
    sender_notes = notifications_for(db_session, users["aliyev"].id, flow_id)
    assert len(sender_notes) == 2
    assert {n.notif_type for n in sender_notes} == {"flow_status"}
    assert any("tasdiqlandi" in n.text for n in sender_notes)
    assert any("204-xona" in n.text for n in sender_notes)

    # the student sees the new state and the comment
    mine = client.get(f"/docflow/{flow_id}", headers=student).json()
    assert mine["status_label"] == "tasdiqlandi"
    assert "204-xona" in mine["history"][-1]["comment"]
    assert mine["can_change_status"] is False


def test_approved_document_is_final(client, db_session, users):
    flow_id = _fresh_flow(client, db_session)
    staff = headers(client, "rashidova")
    assert (
        client.post(
            f"/docflow/{flow_id}/status",
            headers=staff,
            json={"status": "approved", "comment": "Tayyor."},
        ).status_code
        == 200
    )
    again = client.post(
        f"/docflow/{flow_id}/status", headers=staff, json={"status": "seen"}
    )
    assert again.status_code == 409
    assert "mumkin emas" in again.json()["detail"]
    # ...and the chain never goes backwards either
    assert history_count(db_session, flow_id) == 2


def test_only_the_recipient_may_change_the_status(client, db_session):
    """The sender sees their own application but cannot approve it: 403."""
    flow_id = _fresh_flow(client, db_session)
    res = client.post(
        f"/docflow/{flow_id}/status",
        headers=headers(client, "aliyev"),
        json={"status": "approved", "comment": "O'zim tasdiqlayman"},
    )
    assert res.status_code == 403
    # a dean of another faculty does not even see it
    assert (
        client.post(
            f"/docflow/{flow_id}/status",
            headers=headers(client, "yusupov"),
            json={"status": "seen"},
        ).status_code
        == 404
    )
    assert history_count(db_session, flow_id) == 1


def test_rejection_needs_a_reason(client, db_session, users):
    flow_id = _fresh_flow(client, db_session)
    staff = headers(client, "rashidova")

    empty = client.post(
        f"/docflow/{flow_id}/status",
        headers=staff,
        json={"status": "rejected", "comment": "   "},
    )
    assert empty.status_code == 422
    assert "sabab" in empty.json()["detail"]
    assert history_count(db_session, flow_id) == 1

    ok = client.post(
        f"/docflow/{flow_id}/status",
        headers=staff,
        json={"status": "rejected", "comment": "Hujjatlar to'liq emas."},
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "rejected"
    assert ok.json()["history"][-1]["comment"] == "Hujjatlar to'liq emas."
    notes = notifications_for(db_session, users["aliyev"].id, flow_id)
    assert any("rad etildi" in n.text and "to'liq emas" in n.text for n in notes)


def test_short_body_and_unknown_template_are_refused(client):
    student = headers(client, "aliyev")
    short = client.post(
        "/docflow",
        headers=student,
        json={"template_id": "malumotnoma", "body_text": "ariza"},
    )
    assert short.status_code == 422
    unknown = client.post(
        "/docflow",
        headers=student,
        json={"template_id": "yoq_shablon", "body_text": "x" * 40},
    )
    assert unknown.status_code == 404
    forbidden = client.post(
        "/docflow",
        headers=student,
        json={"template_id": "buyruq_topshiriq", "body_text": "x" * 40},
    )
    assert forbidden.status_code == 403


def test_teacher_hands_in_a_report(client, db_session, users):
    """The teacher's path (FUNKSIONALLIK 3.9): a report, not an application."""
    res = client.post(
        "/docflow",
        headers=headers(client, "umarov"),
        json={
            "template_id": "semestr_hisobot",
            "body_text": (
                "Dekanatga o'qituvchi Umarov Sherzoddan.\n\n"
                "Oraliq nazorat natijalari bo'yicha hisobot ilova qilinadi."
            ),
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["doc_type"] == "report"
    assert body["doc_type_label"] == "Hisobot"
    assert body["recipient_label"] == "Dekanat"
    assert len(notifications_for(db_session, users["rashidova"].id, body["id"])) == 1


def test_staff_order_goes_to_one_person_with_a_deadline(client, db_session, users):
    staff = headers(client, "rashidova")
    people = client.get("/docflow/recipients", headers=staff).json()
    ids = {p["id"] for p in people}
    assert users["tursunov"].id in ids  # same faculty
    assert users["yusupov"].id not in ids  # faculty 2

    due = date.today() + timedelta(days=2)
    res = client.post(
        "/docflow",
        headers=staff,
        json={
            "template_id": "buyruq_topshiriq",
            "body_text": "Tursunov Akmalga. Yuklama hisobotini topshiring.",
            "recipient_user_id": users["tursunov"].id,
            "due_date": due.isoformat(),
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["recipient_user_id"] == users["tursunov"].id
    assert body["recipient_label"] == "Tursunov Akmal"
    assert body["due_date"] == due.isoformat()
    assert len(notifications_for(db_session, users["tursunov"].id, body["id"])) == 1

    inbox = client.get(
        "/docflow/inbox?sort=due", headers=headers(client, "tursunov")
    ).json()
    assert inbox["rows"][0]["id"] == body["id"]  # closest deadline first
    assert inbox["due_soon_count"] >= 1

    # the executor moves it along, the sender is notified
    done = client.post(
        f"/docflow/{body['id']}/status",
        headers=headers(client, "tursunov"),
        json={"status": "in_progress", "comment": "Hujjatlar tayyorlanmoqda."},
    )
    assert done.status_code == 200
    notes = notifications_for(db_session, users["rashidova"].id, body["id"])
    assert any(n.notif_type == "flow_status" for n in notes)


def test_recipient_outside_scope_is_refused(client, users):
    res = client.post(
        "/docflow",
        headers=headers(client, "rashidova"),
        json={
            "template_id": "buyruq_topshiriq",
            "body_text": "Boshqa fakultet xodimiga topshiriq.",
            "recipient_user_id": users["yusupov"].id,
            "due_date": date.today().isoformat(),
        },
    )
    assert res.status_code == 422


def test_notification_is_not_written_twice(db_session, users, seeded_flows):
    """Same guard as S10: a repeated write of the same row is swallowed."""
    db_session.rollback()
    flow = db_session.get(FlowDocument, seeded_flows["semestr_hisobot"].id)
    before = len(notifications_for(db_session, users["rashidova"].id, flow.id))
    written = docflow_service.notify_incoming(db_session, flow)
    db_session.commit()
    assert written == 0
    assert len(notifications_for(db_session, users["rashidova"].id, flow.id)) == before


# --- summarizing an incoming document (S6 service reused) -------------------


def test_incoming_document_can_be_summarized(client, seeded_flows):
    flow_id = seeded_flows["semestr_hisobot"].id
    res = client.post(
        f"/docflow/{flow_id}/summary", headers=headers(client, "rashidova")
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["flow_id"] == flow_id
    assert body["summary"].strip()
    assert body["parts"] == 1
    assert body["source"]["label"].startswith(f"Hisobot №{flow_id}, ")
    assert body["disclaimer"]
    # a stranger cannot summarize what they cannot see
    assert (
        client.post(
            f"/docflow/{flow_id}/summary", headers=headers(client, "aliyev")
        ).status_code
        == 404
    )


# --- the `ariza_holati` tool ------------------------------------------------


def test_tool_is_open_to_every_role():
    for role in UserRole:
        assert TOOL in tool_names_for_role(role)


def test_tool_answers_with_the_mandatory_source(db_session, users, seeded_flows):
    db_session.rollback()
    result = execute_tool(
        TOOL, {"ariza": "ma'lumotnoma"}, db_session, users["aliyev"]
    )
    assert result.ok
    flow_id = seeded_flows["malumotnoma"].id
    assert f"Ariza №{flow_id}" in result.text
    assert "holat: tasdiqlandi" in result.text
    assert "204-xona" in result.text  # the last history comment
    assert result.sources
    label = result.sources[0]["label"]
    assert label.startswith(f"Ariza №{flow_id}, ")
    assert "holat: tasdiqlandi" in label
    assert result.sources[0]["type"] == "flow_document"


def test_tool_finds_a_document_by_id(db_session, users, seeded_flows):
    db_session.rollback()
    flow_id = seeded_flows["buyruq_topshiriq"].id
    result = execute_tool(TOOL, {"ariza": str(flow_id)}, db_session, users["tursunov"])
    assert result.ok
    assert f"Buyruq №{flow_id}" in result.text
    assert "Ijro muddati" in result.text


def test_tool_never_discloses_a_foreign_document(db_session, users, seeded_flows):
    """A stranger's id answers exactly like a missing one."""
    db_session.rollback()
    foreign = seeded_flows["qayta_topshirish"].id
    result = execute_tool(TOOL, {"ariza": str(foreign)}, db_session, users["aliyev"])
    assert result.ok is False
    assert "topilmadi" in result.text
    assert "Abdullayev" not in result.text
    assert "qayta topshirish" not in result.text.lower()

    # The same keyword matches aliyev's *own* application (written by the chain
    # tests above), never abdullayev's — the search runs over visible rows only.
    by_word = execute_tool(
        TOOL, {"ariza": "qayta topshirish"}, db_session, users["aliyev"]
    )
    assert f"№{foreign}" not in by_word.text
    assert "Abdullayev" not in by_word.text


def test_tool_without_arguments_summarizes_the_right_box(db_session, users):
    db_session.rollback()
    student = execute_tool(TOOL, {}, db_session, users["aliyev"])
    assert student.ok
    assert student.text.startswith("Yuborilgan hujjatlar")

    staff = execute_tool(TOOL, {}, db_session, users["rashidova"])
    assert staff.ok
    assert staff.text.startswith("Kelgan hujjatlar")
    assert "Umarov Sherzod" in staff.text
    assert "(Manba: hujjat aylanmasi" in staff.text

    # the same tool, the other direction
    sent = execute_tool(TOOL, {"yonalish": "yuborilgan"}, db_session, users["rashidova"])
    assert sent.text.startswith("Yuborilgan hujjatlar")


def test_tool_for_a_teacher_shows_their_own_documents(db_session, users):
    db_session.rollback()
    result = execute_tool(TOOL, {}, db_session, users["umarov"])
    assert result.ok
    assert "Hisobot" in result.text
    assert "Kompyuter tarmoqlari" not in result.text


# --- transition table (unit level) ------------------------------------------


def test_transition_table_only_moves_forward():
    assert FlowStatus.seen in docflow_service.TRANSITIONS[FlowStatus.sent]
    assert docflow_service.TRANSITIONS[FlowStatus.approved] == ()
    assert docflow_service.TRANSITIONS[FlowStatus.rejected] == ()
    # no step ever goes back to `sent`
    for targets in docflow_service.TRANSITIONS.values():
        assert FlowStatus.sent not in targets


# --- shared fixture helper --------------------------------------------------


def _fresh_flow(client, db_session) -> int:
    """A brand-new application from aliyev — the seeded four stay untouched."""
    res = client.post(
        "/docflow",
        headers=headers(client, "aliyev"),
        json={
            "template_id": "qayta_topshirish",
            "body_text": (
                "Dekanatga AT-24-01 guruhi talabasi Aliyev Jasurdan.\n\nARIZA\n\n"
                "'Ma'lumotlar bazasi' fanidan oraliq nazoratni qayta "
                "topshirishga ruxsat berishingizni so'rayman."
            ),
        },
    )
    assert res.status_code == 201, res.text
    db_session.rollback()
    return res.json()["id"]
