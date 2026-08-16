"""S10 tests: teacher attendance as the dean's office sees it.

The seeded hero is `tursunov`: classes today in AT-24-02 ("Kompyuter
tarmoqlari", 103-lab) and **no turnstile record at all**. The seed pins his
pair 3 for whatever weekday the demo runs on, so that class is the anchor here
— and the same row must read differently depending on the clock:

    11:40 (pair 3 running)  -> teacher not in the building
                               -> "dars xavf ostida" (+ a Notification)
    after the last pair     -> class time over, nothing marked
                               -> "aniqlashtirish kerak"

`umarov` is the counter-example (in the building since 07:55, pinned pair 3
held), and a late arrival is produced by moving one `teacher_arrived_at` past
the bell. Nothing is hardcoded to a weekday: the moments come from
`pair_bounds()` and the rows from the seeded schedule.

Permissions are asserted, not assumed: a teacher may not open the dean's view
(403) and the registry refuses `oqituvchi_davomat` for them *before* the
handler runs.
"""

from datetime import date, datetime, time, timedelta

import pytest

from app.agents.registry import execute_tool, tool_names_for_role
from app.models import ClassSession, Notification, Schedule, User, UserRole
from app.services import presence as presence_service

DEMO_PASSWORD = "demo123"

TODAY = date.today()
# Pair 3 (11:30-12:50) is the pinned demo class of both heroes, every weekday.
PAIR3_START, PAIR3_END = presence_service.pair_bounds(TODAY, 3)
PAIR3 = PAIR3_START + timedelta(minutes=10)  # 11:40, the class is running
AFTER = datetime.combine(TODAY, time(23, 55))  # every pair of the day is over

TOOL = "oqituvchi_davomat"


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
            "tursunov",
            "umarov",
            "rashidova",
            "yusupov",
            "nazarova",
            "aliyev",
            "admin",
        )
    }


def teacher_row(overview, username):
    return next((r for r in overview.rows if r.username == username), None)


def class_by_pair(row, pair_number):
    return next(c for c in row.classes if c.pair_number == pair_number)


# --- the derived class state ------------------------------------------------


def test_tursunov_class_is_at_risk_during_the_pair(db_session, users):
    """Class time + no turnstile record -> "dars xavf ostida"."""
    overview = presence_service.teacher_day_overview(
        db_session, users["rashidova"], now=PAIR3, notify=False
    )
    row = teacher_row(overview, "tursunov")
    assert row is not None
    assert row.state == presence_service.NOT_ARRIVED
    assert row.in_building is False
    assert row.entered_at is None

    running = class_by_pair(row, 3)
    assert running.state == presence_service.CLASS_AT_RISK
    assert running.state_label == "dars xavf ostida"
    assert running.subject == "Kompyuter tarmoqlari"
    assert running.room == "103-lab"
    assert running.group_name == "AT-24-02"
    # The stored enum is untouched — the alert is a conclusion, not a status.
    assert running.session_status.value == "needs_clarification"

    assert overview.at_risk_count >= 1
    # Problems first: the demo opens on the teacher who never came.
    assert overview.rows[0].username == "tursunov"


def test_tursunov_needs_clarification_after_the_pair(db_session, users):
    """Same rows, later clock: the risk turns into "aniqlashtirish kerak"."""
    overview = presence_service.teacher_day_overview(
        db_session, users["rashidova"], now=AFTER, notify=False
    )
    row = teacher_row(overview, "tursunov")
    assert row.class_count >= 1
    assert {c.state for c in row.classes} == {presence_service.CLASS_UNCLEAR}
    assert class_by_pair(row, 3).state == presence_service.CLASS_UNCLEAR
    assert row.at_risk_count == 0
    assert row.unclear_count == row.class_count


def test_umarov_class_is_held(db_session, users):
    """The counter-example: in the building since 07:55, attendance marked."""
    overview = presence_service.teacher_day_overview(
        db_session, users["rashidova"], now=PAIR3, notify=False
    )
    row = teacher_row(overview, "umarov")
    assert row.state == presence_service.INSIDE
    assert row.entered_at.strftime("%H:%M") == "07:55"
    assert row.at_risk_count == 0
    assert row.class_count >= 1
    held = class_by_pair(row, 3)
    assert held.state == presence_service.CLASS_HELD
    assert held.state_label == "o'tildi"
    assert held.marked_count > 0


def test_late_arrival_is_reported_as_kechikkan(db_session, users):
    """Entering after the bell -> "kechikkan" (both in the day and the month)."""
    schedule = (
        db_session.query(Schedule)
        .filter_by(
            teacher_id=users["umarov"].id, weekday=TODAY.weekday(), pair_number=3
        )
        .one()
    )
    session = (
        db_session.query(ClassSession)
        .filter_by(schedule_id=schedule.id, date=TODAY)
        .one()
    )
    backup = session.teacher_arrived_at
    try:
        session.teacher_arrived_at = PAIR3_START + timedelta(minutes=12)
        db_session.commit()

        overview = presence_service.teacher_day_overview(
            db_session, users["rashidova"], now=AFTER, notify=False
        )
        row = teacher_row(overview, "umarov")
        late = class_by_pair(row, 3)
        assert late.state == presence_service.CLASS_LATE
        assert late.state_label == "kechikkan"
        assert row.late_count == 1
        assert row.held_count >= 1  # a late class is still a held class
        assert overview.late_count >= 1

        month = presence_service.teacher_month_summary(
            db_session, users["rashidova"], now=AFTER
        )
        umarov_row = next(r for r in month.rows if r.username == "umarov")
        assert umarov_row.late >= 1
    finally:
        session.teacher_arrived_at = backup
        db_session.commit()


def test_class_state_rules_are_explicit():
    """The four rules, in isolation (no DB): only the clock and the facts."""
    starts_at = datetime.combine(TODAY, time(11, 30))
    ends_at = datetime.combine(TODAY, time(12, 50))
    outside = presence_service.BuildingState(
        presence_service.NOT_ARRIVED, None, None, None
    )
    inside = presence_service.BuildingState(
        presence_service.INSIDE, starts_at - timedelta(minutes=30), None, None
    )

    call = presence_service.class_state
    assert call(None, outside, starts_at, ends_at, 0, starts_at) == (
        presence_service.CLASS_AT_RISK
    )
    assert call(None, outside, starts_at, ends_at, 0, ends_at + timedelta(hours=1)) == (
        presence_service.CLASS_UNCLEAR
    )
    assert call(None, inside, starts_at, ends_at, 0, starts_at + timedelta(minutes=5)) == (
        presence_service.CLASS_UNCLEAR
    )
    assert call(None, inside, starts_at, ends_at, 12, ends_at) == (
        presence_service.CLASS_HELD
    )
    # Same held class, but the turnstile saw the teacher after the bell.
    late = presence_service.BuildingState(
        presence_service.INSIDE, starts_at + timedelta(minutes=20), None, None
    )
    assert call(None, late, starts_at, ends_at, 12, ends_at) == (
        presence_service.CLASS_LATE
    )
    # Nothing is "at risk" long before the bell.
    assert call(None, outside, starts_at, ends_at, 0, starts_at - timedelta(hours=2)) == (
        presence_service.CLASS_UPCOMING
    )


# --- the "dars xavf ostida" event -> Notification -----------------------------


def test_risk_writes_one_notification_and_never_a_duplicate(db_session, users):
    """The event is recorded for the faculty's dean's office, exactly once."""
    overview = presence_service.teacher_day_overview(
        db_session, users["rashidova"], now=PAIR3, notify=False
    )
    row = teacher_row(overview, "tursunov")
    risky = class_by_pair(row, 3)
    assert risky.state == presence_service.CLASS_AT_RISK

    # Start from a clean slate for this one (dean, class) pair.
    db_session.query(Notification).filter(
        Notification.user_id == users["rashidova"].id,
        Notification.notif_type == presence_service.TEACHER_ABSENCE_NOTIF,
        Notification.link_id == risky.schedule_id,
    ).delete()
    db_session.commit()

    def count():
        db_session.rollback()
        return (
            db_session.query(Notification)
            .filter_by(notif_type=presence_service.TEACHER_ABSENCE_NOTIF)
            .count()
        )

    before = count()
    presence_service.teacher_day_overview(db_session, users["rashidova"], now=PAIR3)
    after_first = count()
    assert after_first == before + 1

    presence_service.teacher_day_overview(db_session, users["rashidova"], now=PAIR3)
    assert count() == after_first  # asked again -> no duplicate

    written = (
        db_session.query(Notification)
        .filter_by(
            user_id=users["rashidova"].id,
            notif_type=presence_service.TEACHER_ABSENCE_NOTIF,
            link_id=risky.schedule_id,
        )
        .one()
    )
    assert "Dars xavf ostida" in written.text
    assert "Tursunov Akmal" in written.text
    assert "103-lab" in written.text
    assert written.link_type == "schedule"


def test_notifications_go_to_the_teachers_own_faculty(db_session, users):
    """A dean of another faculty is not notified about someone else's teacher."""
    presence_service.teacher_day_overview(db_session, users["rashidova"], now=PAIR3)
    db_session.rollback()
    rows = (
        db_session.query(Notification)
        .filter_by(
            user_id=users["yusupov"].id,
            notif_type=presence_service.TEACHER_ABSENCE_NOTIF,
        )
        .all()
    )
    # Only the pre-seeded demo row (pinned class) — nothing new was added for
    # the faculty-2 dean by faculty-1 risks.
    assert len(rows) <= 1


# --- scope (rbac only) --------------------------------------------------------


def test_staff_sees_only_the_own_faculty(client, users):
    res = client.get("/attendance/teachers", headers=headers(client, "rashidova"))
    assert res.status_code == 200, res.text
    body = res.json()
    names = {row["username"] for row in body["rows"]}
    assert "tursunov" in names and "umarov" in names
    assert names == {"umarov", "tursunov", "bekmurodov", "ismoilova", "xolmatov"}
    assert body["faculty_ids"] == [1]
    assert body["teacher_count"] == 5
    assert body["schedule_note"] and body["disclaimer"]
    assert body["source"]["label"].startswith("Turniket logi")


def test_other_faculty_dean_does_not_see_tursunov(client):
    res = client.get("/attendance/teachers", headers=headers(client, "yusupov"))
    assert res.status_code == 200, res.text
    names = {row["username"] for row in res.json()["rows"]}
    assert names == {"saidova", "ergashev", "muminova"}
    assert "tursunov" not in names


def test_admin_sees_every_teacher(client):
    res = client.get("/attendance/teachers", headers=headers(client, "admin"))
    assert res.status_code == 200
    assert res.json()["teacher_count"] == 8


@pytest.mark.parametrize("username", ["umarov", "tursunov", "nazarova", "aliyev"])
def test_dean_view_is_closed_to_everyone_else(client, username):
    """Teacher (even the one being watched), tutor and student -> 403."""
    assert (
        client.get("/attendance/teachers", headers=headers(client, username)).status_code
        == 403
    )
    assert (
        client.get(
            "/attendance/teachers/monthly", headers=headers(client, username)
        ).status_code
        == 403
    )


def test_dean_view_requires_a_token(client):
    assert client.get("/attendance/teachers").status_code == 401


def test_overview_endpoint_shows_the_risk_at_a_given_moment(client):
    res = client.get(
        f"/attendance/teachers?at={PAIR3.isoformat()}",
        headers=headers(client, "rashidova"),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    row = next(r for r in body["rows"] if r["username"] == "tursunov")
    assert row["state"] == "not_arrived"
    running = next(c for c in row["classes"] if c["pair_number"] == 3)
    assert running["state"] == "at_risk"
    assert running["state_label"] == "dars xavf ostida"
    assert running["room"] == "103-lab"
    assert body["at_risk_count"] >= 1


# --- monthly report -----------------------------------------------------------


def test_monthly_percentages(client):
    # `at` = end of the day, so today's (unstarted-at-midnight) pairs count too.
    res = client.get(
        f"/attendance/teachers/monthly?at={AFTER.isoformat()}",
        headers=headers(client, "rashidova"),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["rows"]) == 5
    assert body["total"] > 0
    assert body["percent"] is not None
    rows = {row["username"]: row for row in body["rows"]}
    tursunov = rows["tursunov"]
    assert tursunov["unclear"] >= 1  # today's unmarked classes
    assert tursunov["percent"] < 100
    assert tursunov["held"] + tursunov["cancelled"] + tursunov["unclear"] == (
        tursunov["total"]
    )
    # Worst first: the row a dean opens the report for.
    percents = [row["percent"] for row in body["rows"]]
    assert percents == sorted(percents)
    assert body["source"]["label"].startswith("Davomat jurnali")


# --- the tool -----------------------------------------------------------------


def test_tool_is_registered_for_the_dean_only():
    assert TOOL in tool_names_for_role(UserRole.staff)
    assert TOOL in tool_names_for_role(UserRole.admin)
    for role in (UserRole.teacher, UserRole.tutor, UserRole.student):
        assert TOOL not in tool_names_for_role(role)


def test_tool_is_blocked_for_a_teacher_before_the_handler_runs(
    db_session, users, monkeypatch
):
    """The registry refuses it: the service is never touched (domain rule 2)."""
    calls = []

    def spy(*args, **kwargs):
        calls.append(args)
        raise AssertionError("handler must not run for a teacher")

    monkeypatch.setattr(presence_service, "teacher_day_overview", spy)
    result = execute_tool(TOOL, {}, db_session, users["umarov"])
    assert result.ok is False
    assert "Ruxsat yo'q" in result.text
    assert calls == []


def test_tool_answers_the_deans_question_with_sources(db_session, users):
    """"Bugun kim darsga kelmadi?" -> tursunov, pair 3, 103-lab, + citations."""
    result = execute_tool(
        TOOL, {"vaqt": "11:40"}, db_session, users["rashidova"]
    )
    assert result.ok is True
    text = result.text
    assert "Tursunov Akmal" in text
    assert "3-para" in text
    assert "Kompyuter tarmoqlari" in text
    assert "103-lab" in text
    assert "dars xavf ostida" in text
    # Domain rules 5 and 6: the citation and the "inference" wording.
    assert presence_service.SCHEDULE_HINT in text
    assert "Turniket logi" in text
    assert result.sources and result.sources[0]["label"]


def test_tool_answers_about_one_named_teacher(db_session, users):
    result = execute_tool(
        TOOL, {"oqituvchi": "Tursunov", "vaqt": "11:40"}, db_session, users["rashidova"]
    )
    assert result.ok is True
    assert "Tursunov Akmal" in result.text
    assert presence_service.SCHEDULE_HINT in result.text
    types = {source["type"] for source in result.sources}
    assert presence_service.TURNSTILE_SOURCE in types
    assert presence_service.SCHEDULE_SOURCE in types


def test_tool_refuses_a_teacher_of_another_faculty(db_session, users):
    result = execute_tool(TOOL, {"oqituvchi": "Tursunov"}, db_session, users["yusupov"])
    assert result.ok is False
    assert "Ruxsat yo'q" in result.text


def test_tool_monthly_period(db_session, users):
    result = execute_tool(TOOL, {"davr": "oy"}, db_session, users["rashidova"])
    assert result.ok is True
    assert "Tursunov Akmal" in result.text
    assert "Manba" in result.text


def test_tool_unknown_teacher(db_session, users):
    result = execute_tool(
        TOOL, {"oqituvchi": "Petrov Ivan"}, db_session, users["rashidova"]
    )
    assert result.ok is False
    assert "topilmadi" in result.text
