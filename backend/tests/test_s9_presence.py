"""S9 tests: presence (turnstile + schedule + attendance) and marking attendance.

The four seeded student cases are the whole point of the module, so they are
checked at a *fixed* moment (pair 3 / pair 5) instead of "now":

    aliyev   -> inside since 10:02, schedule says room 214, marked present
    mahmudov -> inside since 08:07 but marked absent ("in the building,
                not in class" — the case the module exists for)
    sodiqova -> entered 08:12, left 13:15 (visible from pair 5 onwards)
    karimov  -> never came today

Domain rule 6 is asserted explicitly: the room always travels with the words
"jadval bo'yicha", and every factual answer carries its sources.
"""

from datetime import date, datetime, time, timedelta

import pytest

from app.agents.registry import execute_tool, tool_names_for_role
from app.models import (
    Attendance,
    AttendanceStatus,
    ClassSession,
    ClassSessionStatus,
    Schedule,
    User,
    UserRole,
)
from app.services import presence as presence_service

DEMO_PASSWORD = "demo123"

TODAY = date.today()
PAIR3 = datetime.combine(TODAY, time(11, 40))  # inside pair 3 (11:30-12:50)
PAIR5 = datetime.combine(TODAY, time(15, 10))  # inside pair 5 (15:00-16:20)

PRESENCE_TOOL = "mavjudlik_tekshir"
ATTENDANCE_TOOL = "davomat_kor"


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
            "mahmudov",
            "umarov",
            "bekmurodov",
            "tursunov",
            "nazarova",
            "qodirova",
            "rashidova",
            "admin",
        )
    }


@pytest.fixture(scope="module")
def hero_class(db_session, users):
    """AT-24-01, pair 3 today: "Ma'lumotlar bazasi", room 214, teacher umarov."""
    row = (
        db_session.query(Schedule)
        .filter(
            Schedule.group_id == users["aliyev"].group_id,
            Schedule.weekday == TODAY.weekday(),
            Schedule.pair_number == 3,
        )
        .one()
    )
    assert row.teacher_id == users["umarov"].id
    return row


@pytest.fixture
def fresh(db_session):
    """Re-read the DB after an endpoint wrote to it (own session snapshot)."""
    db_session.rollback()
    return db_session


def at_param(moment: datetime) -> str:
    return moment.isoformat(timespec="minutes")


def run_tool(db_session, user, name, args=None):
    db_session.rollback()
    return execute_tool(name, args or {}, db_session, user)


# --- 1. the four seeded cases (service level, fixed moment) -----------------


def test_aliyev_is_inside_and_marked_in_the_pinned_class(fresh, users):
    item = presence_service.presence(fresh, users["aliyev"], PAIR3)
    assert item.state == presence_service.INSIDE
    assert item.in_building is True
    assert item.entered_at.strftime("%H:%M") == "10:02"
    assert item.left_at is None
    assert item.current_pair == 3
    assert item.current_class is not None
    assert item.current_class.subject == "Ma'lumotlar bazasi"
    assert item.current_class.room == "214"
    assert item.current_class.teacher_name.startswith("Umarov")
    assert item.attendance_status == AttendanceStatus.present
    assert item.attendance_marked is True
    assert item.day.percent == 100


def test_mahmudov_is_inside_but_not_marked_in_class(fresh, users):
    item = presence_service.presence(fresh, users["mahmudov"], PAIR3)
    assert item.state == presence_service.INSIDE
    assert item.entered_at.strftime("%H:%M") == "08:07"
    assert item.current_class.room == "214"  # same class as aliyev
    assert item.attendance_status == AttendanceStatus.absent
    assert item.attendance_marked is False
    # The whole reason the case exists: the contradiction must be spelled out.
    assert "binoda, lekin darsda belgilanmagan" in item.summary
    assert "binoda, lekin darsda belgilanmagan" in (
        presence_service.format_presence_for_tool(item)
    )


def test_sodiqova_has_left_the_building(fresh, users):
    at_pair3 = presence_service.presence(fresh, users["sodiqova"], PAIR3)
    assert at_pair3.state == presence_service.INSIDE  # she leaves only at 13:15

    item = presence_service.presence(fresh, users["sodiqova"], PAIR5)
    assert item.state == presence_service.LEFT
    assert item.in_building is False
    assert item.left_at.strftime("%H:%M") == "13:15"
    assert item.entered_at.strftime("%H:%M") == "08:12"
    assert "chiqib ketgan" in item.summary


def test_karimov_never_came_today(fresh, users):
    item = presence_service.presence(fresh, users["karimov"], PAIR3)
    assert item.state == presence_service.NOT_ARRIVED
    assert item.entered_at is None and item.left_at is None
    assert item.attendance_status == AttendanceStatus.absent
    assert item.day.percent == 0
    assert "binoga kirmagan" in item.summary


def test_room_is_always_an_inference_with_sources(fresh, users):
    item = presence_service.presence(fresh, users["aliyev"], PAIR3)
    text = presence_service.format_presence_for_tool(item)
    assert "jadval bo'yicha" in text  # domain rule 6
    assert "214-xona" in text
    types = {source["type"] for source in item.sources}
    assert {"turnstile", "schedule", "attendance"} <= types
    assert any("10:02" in source["label"] for source in item.sources)
    assert item.disclaimer


# --- 2. API: scope --------------------------------------------------------


def test_presence_requires_a_token(client):
    assert client.get("/attendance/presence").status_code == 401


def test_student_sees_own_presence(client):
    res = client.get(
        f"/attendance/presence?at={at_param(PAIR3)}", headers=headers(client, "aliyev")
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["username"] == "aliyev"
    assert body["state"] == "inside"
    assert body["current_class"]["room"] == "214"
    assert body["schedule_note"]
    assert body["sources"] and body["disclaimer"]


def test_tutor_sees_a_student_of_their_group(client, users):
    res = client.get(
        f"/attendance/presence/{users['aliyev'].id}?at={at_param(PAIR3)}",
        headers=headers(client, "nazarova"),
    )
    assert res.status_code == 200, res.text
    assert res.json()["entered_at"].endswith("10:02:00")


def test_tutor_of_another_faculty_is_refused(client, users):
    res = client.get(
        f"/attendance/presence/{users['aliyev'].id}",
        headers=headers(client, "qodirova"),
    )
    assert res.status_code == 403


def test_student_cannot_look_up_another_student(client, users):
    res = client.get(
        f"/attendance/presence/{users['karimov'].id}",
        headers=headers(client, "aliyev"),
    )
    assert res.status_code == 403


def test_unknown_user_is_404(client):
    res = client.get("/attendance/presence/999999", headers=headers(client, "nazarova"))
    assert res.status_code == 404


# --- 3. API: the tutor's group list ---------------------------------------


def test_tutor_group_presence_shows_all_four_cases(client):
    res = client.get(
        f"/attendance/group?at={at_param(PAIR3)}", headers=headers(client, "nazarova")
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["group_names"] == ["AT-24-01", "AT-24-02"]
    assert len(body["rows"]) == 16
    by_username = {row["username"]: row for row in body["rows"]}

    assert by_username["aliyev"]["state"] == "inside"
    assert by_username["aliyev"]["attendance_marked"] is True
    assert by_username["aliyev"]["room"] == "214"
    assert by_username["mahmudov"]["state"] == "inside"
    assert by_username["mahmudov"]["attendance_marked"] is False
    assert by_username["karimov"]["state"] == "not_arrived"
    assert body["current_pair"] == 3
    assert body["inside_count"] + body["left_count"] + body["absent_count"] == 16
    assert 0 <= body["attendance_percent"] <= 100
    assert "jadval bo'yicha" in body["schedule_note"]

    left = client.get(
        f"/attendance/group?at={at_param(PAIR5)}", headers=headers(client, "nazarova")
    ).json()
    assert {r["username"]: r for r in left["rows"]}["sodiqova"]["state"] == "left"


def test_tutor_group_is_limited_to_own_groups(client):
    body = client.get("/attendance/group", headers=headers(client, "qodirova")).json()
    assert body["group_names"] == ["IQ-24-01", "IQ-24-02"]
    assert all(row["group_name"].startswith("IQ") for row in body["rows"])


def test_group_presence_is_closed_for_students_and_teachers(client):
    assert (
        client.get("/attendance/group", headers=headers(client, "aliyev")).status_code
        == 403
    )
    assert (
        client.get("/attendance/group", headers=headers(client, "umarov")).status_code
        == 403
    )


def test_group_outside_scope_is_403(client, users):
    res = client.get(
        f"/attendance/group?group_id={users['aliyev'].group_id}",
        headers=headers(client, "qodirova"),
    )
    assert res.status_code == 403


# --- 4. API: attendance summary -------------------------------------------


def test_student_reads_own_attendance_summary(client):
    res = client.get("/attendance/summary", headers=headers(client, "aliyev"))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["username"] == "aliyev"
    assert body["total"] > 0
    assert body["percent"] == 100  # aliyev is present in every seeded class
    assert body["by_subject"]
    assert body["source"]["type"] == "attendance"


def test_karimov_summary_is_weaker_than_aliyev(client, users):
    karimov = client.get(
        f"/attendance/summary?student_id={users['karimov'].id}",
        headers=headers(client, "nazarova"),
    ).json()
    aliyev = client.get(
        f"/attendance/summary?student_id={users['aliyev'].id}",
        headers=headers(client, "nazarova"),
    ).json()
    assert karimov["percent"] < aliyev["percent"]
    assert karimov["absent"] > 0


def test_summary_of_another_student_is_refused(client, users):
    res = client.get(
        f"/attendance/summary?student_id={users['karimov'].id}",
        headers=headers(client, "aliyev"),
    )
    assert res.status_code == 403


# --- 5. API: the teacher's day and the marking sheet ----------------------


def test_teacher_sees_todays_classes(client, users, hero_class):
    res = client.get(
        f"/attendance/my-classes?at={at_param(PAIR3)}",
        headers=headers(client, "umarov"),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["current_pair"] == 3
    ids = [row["schedule_id"] for row in body["classes"]]
    assert hero_class.id in ids
    row = next(r for r in body["classes"] if r["schedule_id"] == hero_class.id)
    assert row["room"] == "214"
    assert row["group_name"] == "AT-24-01"
    assert row["is_current"] is True
    assert row["student_count"] == 8


def test_my_classes_is_teacher_only(client):
    assert (
        client.get(
            "/attendance/my-classes", headers=headers(client, "nazarova")
        ).status_code
        == 403
    )


def test_teacher_opens_own_roster(client, hero_class):
    res = client.get(
        f"/attendance/class/{hero_class.id}?at={at_param(PAIR3)}",
        headers=headers(client, "umarov"),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["can_mark"] is True
    assert body["room"] == "214"
    assert len(body["students"]) == 8
    by_username = {row["username"]: row for row in body["students"]}
    # The turnstile hint: karimov never came, aliyev was inside at 11:30.
    assert by_username["karimov"]["suggested"] == "absent"
    assert by_username["aliyev"]["suggested"] == "present"
    assert by_username["mahmudov"]["status"] == "absent"  # journal, not turnstile
    assert body["source"]["type"] == "attendance"


def test_another_teacher_cannot_open_the_roster(client, hero_class):
    res = client.get(
        f"/attendance/class/{hero_class.id}", headers=headers(client, "bekmurodov")
    )
    assert res.status_code == 403


def test_tutor_may_read_the_roster_but_another_tutor_may_not(client, hero_class):
    assert (
        client.get(
            f"/attendance/class/{hero_class.id}", headers=headers(client, "nazarova")
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/attendance/class/{hero_class.id}", headers=headers(client, "qodirova")
        ).status_code
        == 403
    )


def test_teacher_marks_own_class_and_rows_are_updated_not_duplicated(
    client, fresh, hero_class
):
    before = client.get(
        f"/attendance/class/{hero_class.id}", headers=headers(client, "umarov")
    ).json()
    original = {row["student_id"]: row["status"] for row in before["students"]}
    assert all(status is not None for status in original.values())

    try:
        res = client.post(
            f"/attendance/class/{hero_class.id}/mark",
            json={"marks": [{"student_id": sid, "status": "late"} for sid in original]},
            headers=headers(client, "umarov"),
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["late_count"] == len(original)
        assert body["marked_count"] == len(original)
        assert body["session_status"] == "held"

        fresh.rollback()
        rows = (
            fresh.query(Attendance)
            .filter(Attendance.schedule_id == hero_class.id, Attendance.date == TODAY)
            .all()
        )
        assert len(rows) == len(original)  # updated in place, not duplicated
        assert all(row.status == AttendanceStatus.late for row in rows)
    finally:
        restore = client.post(
            f"/attendance/class/{hero_class.id}/mark",
            json={
                "marks": [
                    {"student_id": sid, "status": status}
                    for sid, status in original.items()
                ]
            },
            headers=headers(client, "umarov"),
        )
        assert restore.status_code == 200, restore.text

    fresh.rollback()
    after = client.get(
        f"/attendance/class/{hero_class.id}", headers=headers(client, "umarov")
    ).json()
    assert {row["student_id"]: row["status"] for row in after["students"]} == original


def test_marking_a_new_day_creates_the_class_session(client, fresh, hero_class, users):
    """A day with no journal yet: rows appear and the session becomes `held`."""
    future = TODAY + timedelta(days=7)
    res = client.post(
        f"/attendance/class/{hero_class.id}/mark?at={at_param(PAIR3)}",
        json={
            "marks": [{"student_id": users["aliyev"].id, "status": "present"}],
            "on_date": future.isoformat(),
        },
        headers=headers(client, "umarov"),
    )
    assert res.status_code == 200, res.text
    assert res.json()["marked_count"] == 1
    assert res.json()["session_status"] == "held"

    fresh.rollback()
    session = (
        fresh.query(ClassSession)
        .filter(
            ClassSession.schedule_id == hero_class.id, ClassSession.date == future
        )
        .one()
    )
    assert session.status == ClassSessionStatus.held
    assert session.teacher_arrived_at is not None


def test_another_teacher_cannot_mark_the_class(client, users, hero_class):
    res = client.post(
        f"/attendance/class/{hero_class.id}/mark",
        json={"marks": [{"student_id": users["aliyev"].id, "status": "absent"}]},
        headers=headers(client, "bekmurodov"),
    )
    assert res.status_code == 403


def test_tutor_cannot_mark_attendance(client, users, hero_class):
    res = client.post(
        f"/attendance/class/{hero_class.id}/mark",
        json={"marks": [{"student_id": users["aliyev"].id, "status": "absent"}]},
        headers=headers(client, "nazarova"),
    )
    assert res.status_code == 403


def test_marking_a_student_of_another_group_is_rejected(client, users, hero_class):
    other = (
        users["admin"]  # any user that is not a student of AT-24-01
    )
    res = client.post(
        f"/attendance/class/{hero_class.id}/mark",
        json={"marks": [{"student_id": other.id, "status": "present"}]},
        headers=headers(client, "umarov"),
    )
    assert res.status_code == 422


# --- 6. tools --------------------------------------------------------------


def test_both_tools_are_registered_for_every_role(client):
    for role in UserRole:
        names = tool_names_for_role(role)
        assert PRESENCE_TOOL in names
        assert ATTENDANCE_TOOL in names


def test_presence_tool_answers_the_dod_question(db_session, users):
    result = run_tool(
        db_session,
        users["nazarova"],
        PRESENCE_TOOL,
        {"talaba": "Aliyev", "vaqt": PAIR3.isoformat()},
    )
    assert result.ok
    assert "binoda" in result.text
    assert "10:02" in result.text
    assert "jadval bo'yicha" in result.text  # domain rule 6
    assert "214-xona" in result.text
    assert "belgilangan" in result.text
    assert result.sources
    assert any(s["type"] == "turnstile" and "10:02" in s["label"] for s in result.sources)


def test_presence_tool_refuses_outside_the_scope(db_session, users):
    result = run_tool(
        db_session, users["qodirova"], PRESENCE_TOOL, {"talaba": "aliyev"}
    )
    assert result.ok is False
    assert "Ruxsat yo'q" in result.text


def test_student_presence_tool_is_self_only(db_session, users):
    own = run_tool(db_session, users["aliyev"], PRESENCE_TOOL, {})
    assert own.ok and "Aliyev" in own.text
    other = run_tool(
        db_session, users["aliyev"], PRESENCE_TOOL, {"talaba": "Karimov"}
    )
    assert other.ok is False


def test_teacher_may_check_their_own_students(db_session, users):
    result = run_tool(
        db_session, users["umarov"], PRESENCE_TOOL, {"talaba": "mahmudov"}
    )
    assert result.ok
    assert "Mahmudov" in result.text


def test_attendance_tool_gives_the_student_their_own_summary(db_session, users):
    result = run_tool(db_session, users["aliyev"], ATTENDANCE_TOOL, {})
    assert result.ok
    assert "davomat svodi" in result.text
    assert "Manba" in result.text


def test_attendance_tool_refuses_another_student(db_session, users):
    result = run_tool(
        db_session, users["aliyev"], ATTENDANCE_TOOL, {"talaba": "karimov"}
    )
    assert result.ok is False


def test_attendance_tool_gives_the_tutor_the_group_picture(db_session, users):
    result = run_tool(db_session, users["nazarova"], ATTENDANCE_TOOL, {})
    assert result.ok
    assert "Mavjudlik svodi" in result.text
    assert "AT-24-01" in result.text
    assert "jadval bo'yicha" in result.text


def test_attendance_tool_refuses_a_student_outside_the_scope(db_session, users):
    result = run_tool(
        db_session, users["qodirova"], ATTENDANCE_TOOL, {"talaba": "karimov"}
    )
    assert result.ok is False


def test_teacher_tool_lists_todays_classes(db_session, users):
    result = run_tool(db_session, users["umarov"], ATTENDANCE_TOOL, {})
    assert result.ok
    assert "Ma'lumotlar bazasi" in result.text
    assert "214-xona" in result.text


# --- 7. the shared pair table --------------------------------------------


def test_pair_times_live_in_one_place():
    from app.agents.tools.schedule_view import PAIR_TIMES as tool_table
    from seed.generate import PAIR_TIMES as seed_table

    assert seed_table is presence_service.PAIR_TIMES
    assert tool_table is presence_service.PAIR_TIME_LABELS
    assert tool_table[3] == ("11:30", "12:50")
    assert presence_service.current_pair(PAIR3) == 3
    assert presence_service.current_pair(datetime.combine(TODAY, time(13, 0))) is None
