"""Presence + attendance service (S9 students, S10 teachers use the same code).

Three sources, one conclusion:

    turnstile log  -> fact:      "binoda, 10:02 da kirgan"
    schedule       -> inference: "jadval bo'yicha 3-para, 214-xona"
    attendance     -> fact:      "davomatda belgilangan (kelgan)"

Domain rule 6 is enforced here, not in the UI: the room a person *should* be in
is a schedule-based inference and is always labelled `jadval bo'yicha`
(`SCHEDULE_HINT` / `ROOM_NOTE`), never presented as a measured fact. Every
answer carries its citations (`sources`), turnstile times included.

Scope is never re-implemented: it comes from `auth/rbac.py`
(`visible_group_ids`, `ensure_can_access_user`). Marking attendance is narrower
still — a teacher may only touch **their own** class (`Schedule.teacher_id`).

`now` is injectable everywhere so tests can look at the day from any moment
(the seed writes the whole day in advance, so the demo works at any hour).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.agents.orchestrator import DISCLAIMER
from app.auth.rbac import can_access_user, ensure_can_access_user, visible_group_ids
from app.models import (
    Attendance,
    AttendanceStatus,
    ClassSession,
    ClassSessionStatus,
    Group,
    Schedule,
    TurnstileDirection,
    TurnstileLog,
    User,
    UserRole,
)
from app.services import notifications

# --- pair times: THE single table --------------------------------------------
# `seed/generate.py` and `agents/tools/schedule_view.py` import it from here, so
# the class hours exist in exactly one place (internal regulations, art. 3.1).

PAIR_TIMES: dict[int, tuple[time, time]] = {
    1: (time(8, 30), time(9, 50)),
    2: (time(10, 0), time(11, 20)),
    3: (time(11, 30), time(12, 50)),
    4: (time(13, 30), time(14, 50)),
    5: (time(15, 0), time(16, 20)),
    6: (time(16, 30), time(17, 50)),
}

# Same table as strings ("08:30", "09:50") for text output.
PAIR_TIME_LABELS: dict[int, tuple[str, str]] = {
    number: (start.strftime("%H:%M"), end.strftime("%H:%M"))
    for number, (start, end) in PAIR_TIMES.items()
}

# --- vocabulary --------------------------------------------------------------

INSIDE = "inside"  # last turnstile event today is an entry
LEFT = "left"  # entered and left again
NOT_ARRIVED = "not_arrived"  # no turnstile event today at all

BUILDING_LABELS = {
    INSIDE: "binoda",
    LEFT: "binodan chiqib ketgan",
    NOT_ARRIVED: "bugun binoga kirmagan",
}

ATTENDANCE_LABELS = {
    AttendanceStatus.present: "kelgan",
    AttendanceStatus.absent: "kelmagan",
    AttendanceStatus.late: "kechikkan",
}

SESSION_LABELS = {
    ClassSessionStatus.held: "o'tildi",
    ClassSessionStatus.cancelled: "qoldirildi",
    ClassSessionStatus.needs_clarification: "aniqlashtirish kerak",
}

# --- S10: derived state of one scheduled class (the dean's traffic light) -----
# The DB enum (`ClassSessionStatus`) stays untouched: "xavf ostida" and
# "kechikkan" are *conclusions* drawn from three sources at a given moment
# (schedule window + teacher turnstile + whether attendance was marked), not new
# stored statuses. So the same row reads "xavf ostida" at 11:35 and
# "aniqlashtirish kerak" at 13:00 — that is the point.

CLASS_HELD = "held"  # o'tildi: attendance marked / session held
CLASS_LATE = "late"  # kechikkan: held, but the teacher entered after the bell
CLASS_AT_RISK = "at_risk"  # xavf ostida: class time, teacher not in the building
CLASS_UNCLEAR = "needs_clarification"  # aniqlashtirish kerak
CLASS_UPCOMING = "upcoming"  # scheduled, not started yet
CLASS_CANCELLED = "cancelled"  # qoldirildi (explicitly recorded)

CLASS_STATE_LABELS = {
    CLASS_HELD: "o'tildi",
    CLASS_LATE: "kechikkan",
    CLASS_AT_RISK: "dars xavf ostida",
    CLASS_UNCLEAR: "aniqlashtirish kerak",
    CLASS_UPCOMING: "hali boshlanmagan",
    CLASS_CANCELLED: "qoldirildi",
}

# States the dean's office has to act on.
CLASS_ALERT_STATES = (CLASS_AT_RISK, CLASS_UNCLEAR, CLASS_LATE)

# A class counts as "at risk" from this many minutes before the bell.
RISK_LEAD_MINUTES = 10
# Entering later than this after the bell is a late arrival.
LATE_GRACE_MINUTES = 5

DEFAULT_MONTH_DAYS = 30
MAX_MONTH_DAYS = 180

TEACHER_ABSENCE_NOTIF = "teacher_absence"

# Domain rule 6: the room is an inference drawn from the schedule.
SCHEDULE_HINT = "jadval bo'yicha"
ROOM_NOTE = (
    "Xona va dars ma'lumoti dars jadvaliga asoslangan xulosa (jadval bo'yicha), "
    "qat'iy fakt emas — turniket vaqti va davomat belgisi esa yozuvdan olingan."
)

TURNSTILE_SOURCE = "turnstile"
SCHEDULE_SOURCE = "schedule"
ATTENDANCE_SOURCE = "attendance"

# `late` still counts as attended when the daily percentage is computed.
ATTENDED_STATUSES = (AttendanceStatus.present, AttendanceStatus.late)

DEFAULT_SUMMARY_DAYS = 7
MAX_SUMMARY_DAYS = 60
MAX_RECENT_ROWS = 20


class PresenceError(RuntimeError):
    """Base class: routers map these onto HTTP codes, tools onto tool errors."""


class OutOfScopeError(PresenceError):
    """The requested group is outside the caller's RBAC scope."""


class NotOwnClassError(PresenceError):
    """Attendance may only be marked by the teacher of that very class."""


class UnknownStudentError(PresenceError):
    """A marked student does not belong to the class group."""


# --- data shapes -------------------------------------------------------------


@dataclass
class BuildingState:
    state: str  # INSIDE | LEFT | NOT_ARRIVED
    entered_at: datetime | None
    left_at: datetime | None
    last_event_at: datetime | None

    @property
    def in_building(self) -> bool:
        return self.state == INSIDE

    @property
    def label(self) -> str:
        return BUILDING_LABELS[self.state]


@dataclass
class ClassSlot:
    """One scheduled class — always an inference about *where someone should be*."""

    schedule_id: int
    pair_number: int
    subject: str
    room: str
    group_id: int
    group_name: str | None
    teacher_id: int
    teacher_name: str | None
    starts_at: datetime
    ends_at: datetime
    session_status: ClassSessionStatus | None = None
    attendance_status: AttendanceStatus | None = None


@dataclass
class DayAttendance:
    """Today's attendance of one student, over the pairs that already started."""

    total: int
    present: int
    late: int
    absent: int
    percent: int | None  # None: no pair has started yet


@dataclass
class Presence:
    user_id: int
    username: str
    full_name: str
    role: UserRole
    group_id: int | None
    group_name: str | None
    at: datetime
    state: str
    state_label: str
    in_building: bool
    entered_at: datetime | None
    left_at: datetime | None
    last_event_at: datetime | None
    current_pair: int | None
    current_class: ClassSlot | None
    next_class: ClassSlot | None
    attendance_status: AttendanceStatus | None
    attendance_marked: bool
    day: DayAttendance
    summary: str
    schedule_note: str = ROOM_NOTE
    sources: list[dict] = field(default_factory=list)
    disclaimer: str = DISCLAIMER


@dataclass
class GroupPresenceRow:
    student_id: int
    username: str
    full_name: str
    group_id: int | None
    group_name: str | None
    state: str
    state_label: str
    entered_at: datetime | None
    left_at: datetime | None
    pair_number: int | None
    subject: str | None
    room: str | None
    attendance_status: AttendanceStatus | None
    attendance_marked: bool
    attendance_percent: int | None
    attended_count: int
    marked_count: int
    summary: str


@dataclass
class GroupPresence:
    group_ids: list[int]
    group_names: list[str]
    at: datetime
    current_pair: int | None
    pair_label: str | None
    rows: list[GroupPresenceRow]
    inside_count: int
    left_count: int
    absent_count: int
    in_class_count: int  # marked present/late in the class running right now
    attendance_percent: int | None
    schedule_note: str = ROOM_NOTE
    source: dict = field(default_factory=dict)
    disclaimer: str = DISCLAIMER


@dataclass
class TeacherClass:
    schedule_id: int
    pair_number: int
    subject: str
    room: str
    group_id: int
    group_name: str | None
    starts_at: datetime
    ends_at: datetime
    session_status: ClassSessionStatus | None
    session_label: str | None
    student_count: int
    marked_count: int
    present_count: int
    is_current: bool
    is_past: bool


@dataclass
class RosterStudent:
    student_id: int
    username: str
    full_name: str
    status: AttendanceStatus | None  # what the journal says right now
    suggested: AttendanceStatus  # turnstile-based hint for one-click marking
    state: str
    state_label: str
    entered_at: datetime | None
    left_at: datetime | None


@dataclass
class ClassRoster:
    schedule_id: int
    date: date
    pair_number: int
    pair_label: str
    subject: str
    room: str
    group_id: int
    group_name: str | None
    teacher_id: int
    teacher_name: str | None
    starts_at: datetime
    ends_at: datetime
    session_status: ClassSessionStatus | None
    session_label: str | None
    can_mark: bool
    students: list[RosterStudent]
    marked_count: int
    present_count: int
    late_count: int
    absent_count: int
    schedule_note: str = ROOM_NOTE
    source: dict = field(default_factory=dict)
    disclaimer: str = DISCLAIMER


@dataclass
class SubjectAttendance:
    subject: str
    total: int
    attended: int
    absent: int
    percent: int


@dataclass
class AttendanceRow:
    date: date
    pair_number: int
    subject: str
    room: str
    status: AttendanceStatus
    status_label: str


@dataclass
class AttendanceSummary:
    student_id: int
    username: str
    full_name: str
    group_id: int | None
    group_name: str | None
    days: int
    date_from: date
    date_to: date
    total: int
    present: int
    late: int
    absent: int
    percent: int | None
    by_subject: list[SubjectAttendance]
    recent: list[AttendanceRow]
    today: DayAttendance
    source: dict = field(default_factory=dict)
    disclaimer: str = DISCLAIMER


# --- small helpers -----------------------------------------------------------


def current_pair(moment: datetime) -> int | None:
    """Which pair is running at `moment` (None between pairs / after classes)."""
    clock = moment.time()
    for number, (start, end) in PAIR_TIMES.items():
        if start <= clock <= end:
            return number
    return None

def pair_bounds(day: date, pair_number: int) -> tuple[datetime, datetime]:
    start, end = PAIR_TIMES[pair_number]
    return datetime.combine(day, start), datetime.combine(day, end)


def pair_label(pair_number: int) -> str:
    start, end = PAIR_TIME_LABELS.get(pair_number, ("?", "?"))
    return f"{pair_number}-para ({start}-{end})"


def _hhmm(moment: datetime | None) -> str:
    return moment.strftime("%H:%M") if moment else "—"


def _group_names(db: Session, group_ids: set[int]) -> dict[int, str]:
    ids = {gid for gid in group_ids if gid is not None}
    if not ids:
        return {}
    rows = db.query(Group.id, Group.name).filter(Group.id.in_(ids)).all()
    return {gid: name for gid, name in rows}


def _user_names(db: Session, user_ids: set[int]) -> dict[int, str]:
    ids = {uid for uid in user_ids if uid is not None}
    if not ids:
        return {}
    rows = db.query(User.id, User.full_name).filter(User.id.in_(ids)).all()
    return {uid: name for uid, name in rows}


def _logs_by_user(
    db: Session, user_ids: list[int], day: date, until: datetime
) -> dict[int, list[TurnstileLog]]:
    """Today's turnstile events, only those that already happened (`<= until`)."""
    grouped: dict[int, list[TurnstileLog]] = {uid: [] for uid in user_ids}
    if not user_ids:
        return grouped
    rows = (
        db.query(TurnstileLog)
        .filter(
            TurnstileLog.user_id.in_(user_ids),
            TurnstileLog.timestamp >= datetime.combine(day, time.min),
            TurnstileLog.timestamp <= until,
        )
        .order_by(TurnstileLog.timestamp, TurnstileLog.id)
        .all()
    )
    for row in rows:
        grouped.setdefault(row.user_id, []).append(row)
    return grouped


def building_state(logs: list[TurnstileLog]) -> BuildingState:
    """Fact layer: where the turnstile last saw this person today."""
    if not logs:
        return BuildingState(NOT_ARRIVED, None, None, None)
    entered_at: datetime | None = None
    left_at: datetime | None = None
    for row in logs:
        if row.direction == TurnstileDirection.entry:
            entered_at = row.timestamp
        else:
            left_at = row.timestamp
    last = logs[-1]
    state = INSIDE if last.direction == TurnstileDirection.entry else LEFT
    return BuildingState(
        state=state,
        entered_at=entered_at,
        # An earlier exit is irrelevant once the person came back in.
        left_at=left_at if state == LEFT else None,
        last_event_at=last.timestamp,
    )


def _schedule_rows(
    db: Session, weekday: int, group_ids: list[int] | None = None,
    teacher_id: int | None = None,
) -> list[Schedule]:
    query = db.query(Schedule).filter(Schedule.weekday == weekday)
    if group_ids is not None:
        if not group_ids:
            return []
        query = query.filter(Schedule.group_id.in_(group_ids))
    if teacher_id is not None:
        query = query.filter(Schedule.teacher_id == teacher_id)
    return query.order_by(Schedule.pair_number, Schedule.group_id).all()


def _sessions_by_schedule(
    db: Session, schedule_ids: list[int], day: date
) -> dict[int, ClassSession]:
    if not schedule_ids:
        return {}
    rows = (
        db.query(ClassSession)
        .filter(ClassSession.schedule_id.in_(schedule_ids), ClassSession.date == day)
        .all()
    )
    return {row.schedule_id: row for row in rows}


def _attendance_by_student(
    db: Session, student_ids: list[int], day: date
) -> dict[int, list[Attendance]]:
    grouped: dict[int, list[Attendance]] = {sid: [] for sid in student_ids}
    if not student_ids:
        return grouped
    rows = (
        db.query(Attendance)
        .filter(Attendance.student_id.in_(student_ids), Attendance.date == day)
        .all()
    )
    for row in rows:
        grouped.setdefault(row.student_id, []).append(row)
    return grouped


def _day_attendance(
    rows: list[Attendance], schedules: dict[int, Schedule], day: date, now: datetime
) -> DayAttendance:
    """Only pairs that have already started count — the seed writes the whole day."""
    present = late = absent = 0
    for row in rows:
        schedule = schedules.get(row.schedule_id)
        if schedule is None:
            continue
        start, _end = pair_bounds(day, schedule.pair_number)
        if start > now:
            continue
        if row.status == AttendanceStatus.present:
            present += 1
        elif row.status == AttendanceStatus.late:
            late += 1
        else:
            absent += 1
    total = present + late + absent
    percent = round((present + late) * 100 / total) if total else None
    return DayAttendance(
        total=total, present=present, late=late, absent=absent, percent=percent
    )


def _slot(
    schedule: Schedule,
    day: date,
    group_names: dict[int, str],
    teacher_names: dict[int, str],
    session: ClassSession | None = None,
    attendance: Attendance | None = None,
) -> ClassSlot:
    starts_at, ends_at = pair_bounds(day, schedule.pair_number)
    return ClassSlot(
        schedule_id=schedule.id,
        pair_number=schedule.pair_number,
        subject=schedule.subject,
        room=schedule.room,
        group_id=schedule.group_id,
        group_name=group_names.get(schedule.group_id),
        teacher_id=schedule.teacher_id,
        teacher_name=teacher_names.get(schedule.teacher_id),
        starts_at=starts_at,
        ends_at=ends_at,
        session_status=session.status if session else None,
        attendance_status=attendance.status if attendance else None,
    )


# --- citations (domain rule 5) ----------------------------------------------


def turnstile_source(state: BuildingState, day: date) -> dict:
    if state.state == NOT_ARRIVED:
        text = f"bugun ({day.strftime('%d.%m.%Y')}) yozuv yo'q"
    elif state.state == INSIDE:
        text = f"{_hhmm(state.entered_at)} kirish"
    else:
        text = f"{_hhmm(state.entered_at)} kirish, {_hhmm(state.left_at)} chiqish"
    return {"type": TURNSTILE_SOURCE, "label": f"Turniket logi — {text}"}


def schedule_source(slot: ClassSlot) -> dict:
    return {
        "type": SCHEDULE_SOURCE,
        "label": (
            f"Dars jadvali ({SCHEDULE_HINT}) — {pair_label(slot.pair_number)}, "
            f"{slot.subject}, {slot.room}-xona"
        ),
    }


def attendance_source(day: date, detail: str) -> dict:
    return {
        "type": ATTENDANCE_SOURCE,
        "label": f"Davomat jurnali — {day.strftime('%d.%m.%Y')}, {detail}",
    }


# --- the flow: one person's presence ----------------------------------------


def presence(db: Session, user: User, now: datetime | None = None) -> Presence:
    """Turnstile + schedule + attendance -> one structured conclusion.

    The caller must already have checked access (`ensure_can_access_user`);
    `student_presence()` does that for the API and the tools.
    """
    moment = now or datetime.now()
    day = moment.date()

    logs = _logs_by_user(db, [user.id], day, moment).get(user.id, [])
    state = building_state(logs)

    group_names = _group_names(db, {user.group_id} if user.group_id else set())
    group_name = group_names.get(user.group_id) if user.group_id else None

    # Which classes are this person's today? Student -> own group, teacher ->
    # own classes; tutor/staff/admin have none of their own.
    if user.role == UserRole.teacher:
        rows = _schedule_rows(db, moment.weekday(), teacher_id=user.id)
    elif user.group_id is not None:
        rows = _schedule_rows(db, moment.weekday(), group_ids=[user.group_id])
    else:
        rows = []

    schedules = {row.id: row for row in rows}
    sessions = _sessions_by_schedule(db, list(schedules), day)
    attendance_rows = _attendance_by_student(db, [user.id], day).get(user.id, [])
    attendance_by_schedule = {row.schedule_id: row for row in attendance_rows}

    slot_names = _group_names(db, {row.group_id for row in rows})
    teacher_names = _user_names(db, {row.teacher_id for row in rows})

    pair = current_pair(moment)
    current_row = next((r for r in rows if r.pair_number == pair), None)
    next_row = next(
        (r for r in rows if pair_bounds(day, r.pair_number)[0] > moment), None
    )

    current_class = (
        _slot(
            current_row,
            day,
            slot_names,
            teacher_names,
            sessions.get(current_row.id),
            attendance_by_schedule.get(current_row.id),
        )
        if current_row is not None
        else None
    )
    next_class = (
        _slot(next_row, day, slot_names, teacher_names, sessions.get(next_row.id))
        if next_row is not None
        else None
    )

    attendance_status = current_class.attendance_status if current_class else None
    day_attendance = _day_attendance(attendance_rows, schedules, day, moment)

    sources = [turnstile_source(state, day)]
    if current_class is not None:
        sources.append(schedule_source(current_class))
        if attendance_status is not None:
            sources.append(
                attendance_source(
                    day,
                    f"{current_class.pair_number}-para: "
                    f"{ATTENDANCE_LABELS[attendance_status]}",
                )
            )
    if day_attendance.total:
        sources.append(
            attendance_source(
                day,
                f"kunlik svod {day_attendance.present + day_attendance.late}/"
                f"{day_attendance.total}",
            )
        )

    result = Presence(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        group_id=user.group_id,
        group_name=group_name,
        at=moment,
        state=state.state,
        state_label=state.label,
        in_building=state.in_building,
        entered_at=state.entered_at,
        left_at=state.left_at,
        last_event_at=state.last_event_at,
        current_pair=pair,
        current_class=current_class,
        next_class=next_class,
        attendance_status=attendance_status,
        attendance_marked=attendance_status in ATTENDED_STATUSES,
        day=day_attendance,
        summary="",
        sources=sources,
    )
    result.summary = presence_sentence(result)
    return result


def student_presence(
    db: Session, actor: User, target: User, now: datetime | None = None
) -> Presence:
    """Presence of another person — 403 unless the actor's scope covers them."""
    ensure_can_access_user(db, actor, target)
    return presence(db, target, now)


def _attendance_phrase(item: Presence) -> str:
    """The journal in words. "inside but not marked" is spelled out on purpose."""
    if item.attendance_status is None:
        return "davomatda hali belgilanmagan"
    if item.attendance_status in ATTENDED_STATUSES:
        return (
            "davomatda belgilangan "
            f"({ATTENDANCE_LABELS[item.attendance_status]})"
        )
    phrase = "davomatda \"kelmagan\" deb belgilangan"
    if item.in_building:
        phrase += " — binoda, lekin darsda belgilanmagan"
    return phrase


def presence_sentence(item: Presence) -> str:
    """One human line: fact, then the schedule-based inference, then the journal."""
    parts: list[str] = []
    if item.state == INSIDE:
        parts.append(f"Binoda — {_hhmm(item.entered_at)} da kirgan")
    elif item.state == LEFT:
        parts.append(
            f"Binodan chiqib ketgan — {_hhmm(item.left_at)} da chiqqan"
            + (f" ({_hhmm(item.entered_at)} da kirgan edi)" if item.entered_at else "")
        )
    else:
        parts.append("Bugun binoga kirmagan (turniketda yozuv yo'q)")

    if item.current_class is not None:
        slot = item.current_class
        parts.append(
            f"{SCHEDULE_HINT} hozir {pair_label(slot.pair_number)}: "
            f"\"{slot.subject}\", {slot.room}-xona"
            + (f", o'qituvchi {slot.teacher_name}" if slot.teacher_name else "")
        )
        parts.append(_attendance_phrase(item))
    elif item.next_class is not None:
        slot = item.next_class
        parts.append(
            f"hozir dars vaqti emas; {SCHEDULE_HINT} keyingi dars "
            f"{_hhmm(slot.starts_at)} da — \"{slot.subject}\", {slot.room}-xona"
        )
    else:
        parts.append("hozir jadval bo'yicha darsi yo'q")

    if item.day.percent is not None:
        parts.append(
            f"bugungi davomat {item.day.present + item.day.late}/{item.day.total} "
            f"({item.day.percent}%)"
        )
    return "; ".join(parts) + "."


def format_presence_for_tool(item: Presence) -> str:
    """Agent-facing text: the answer plus the sources it must cite."""
    lines = [
        f"{item.full_name}"
        + (f" ({item.group_name})" if item.group_name else "")
        + f" — {_hhmm(item.at)} holatiga ko'ra:",
        f"  Bino: {item.state_label}"
        + (
            f", {_hhmm(item.entered_at)} da kirgan"
            if item.entered_at and item.state == INSIDE
            else (
                f", {_hhmm(item.left_at)} da chiqqan"
                if item.state == LEFT
                else ""
            )
        ),
    ]
    if item.current_class is not None:
        slot = item.current_class
        lines.append(
            f"  Joriy dars ({SCHEDULE_HINT}): {pair_label(slot.pair_number)}, "
            f"\"{slot.subject}\", {slot.room}-xona"
            + (f", o'qituvchi {slot.teacher_name}" if slot.teacher_name else "")
        )
        lines.append(f"  Davomat: {_attendance_phrase(item)}")
    elif item.next_class is not None:
        slot = item.next_class
        lines.append(
            f"  Hozir dars vaqti emas. Keyingi dars ({SCHEDULE_HINT}): "
            f"{_hhmm(slot.starts_at)}, \"{slot.subject}\", {slot.room}-xona"
        )
    else:
        lines.append(f"  Hozir {SCHEDULE_HINT} darsi yo'q.")

    if item.day.percent is not None:
        lines.append(
            f"  Bugungi davomat: {item.day.present + item.day.late}/{item.day.total} "
            f"dars ({item.day.percent}%), belgilanmagan kelmagan: {item.day.absent}"
        )
    lines.append(f"  Eslatma: {ROOM_NOTE}")
    lines.append("(Manba: " + "; ".join(s["label"] for s in item.sources) + ".)")
    return "\n".join(lines)


# --- the flow: a whole group (tutor / dean's office) -------------------------


def resolve_scope(db: Session, user: User, group_id: int | None) -> list[int]:
    """Group ids this user may look at, optionally narrowed to one group."""
    visible = visible_group_ids(db, user)
    if group_id is not None:
        if visible is not None and group_id not in visible:
            raise OutOfScopeError(group_id)
        return [group_id]
    if visible is None:
        return [gid for (gid,) in db.query(Group.id).order_by(Group.id).all()]
    return sorted(visible)


def group_presence(
    db: Session,
    user: User,
    group_id: int | None = None,
    now: datetime | None = None,
) -> GroupPresence:
    """Who is inside, who is in class (confirmed), who never came — per group."""
    moment = now or datetime.now()
    day = moment.date()
    group_ids = resolve_scope(db, user, group_id)
    names = _group_names(db, set(group_ids))

    students = (
        db.query(User)
        .filter(User.role == UserRole.student, User.group_id.in_(group_ids))
        .order_by(User.group_id, User.full_name)
        .all()
        if group_ids
        else []
    )
    student_ids = [s.id for s in students]

    logs = _logs_by_user(db, student_ids, day, moment)
    attendance = _attendance_by_student(db, student_ids, day)
    schedule_rows = _schedule_rows(db, moment.weekday(), group_ids=group_ids)
    schedules = {row.id: row for row in schedule_rows}

    pair = current_pair(moment)
    current_by_group = {
        row.group_id: row for row in schedule_rows if row.pair_number == pair
    }

    rows: list[GroupPresenceRow] = []
    for student in students:
        state = building_state(logs.get(student.id, []))
        day_attendance = _day_attendance(
            attendance.get(student.id, []), schedules, day, moment
        )
        current_row = current_by_group.get(student.group_id or -1)
        status = None
        if current_row is not None:
            marked = next(
                (
                    a
                    for a in attendance.get(student.id, [])
                    if a.schedule_id == current_row.id
                ),
                None,
            )
            status = marked.status if marked else None

        summary = state.label
        if state.state == INSIDE and state.entered_at:
            summary += f" ({_hhmm(state.entered_at)} da kirgan)"
        elif state.state == LEFT and state.left_at:
            summary += f" ({_hhmm(state.left_at)} da chiqqan)"
        if current_row is not None:
            summary += (
                f", {SCHEDULE_HINT} {current_row.room}-xona"
                + (
                    f" — davomatda {ATTENDANCE_LABELS[status]}"
                    if status is not None
                    else " — davomatda belgilanmagan"
                )
            )

        rows.append(
            GroupPresenceRow(
                student_id=student.id,
                username=student.username,
                full_name=student.full_name,
                group_id=student.group_id,
                group_name=names.get(student.group_id or -1),
                state=state.state,
                state_label=state.label,
                entered_at=state.entered_at,
                left_at=state.left_at,
                pair_number=current_row.pair_number if current_row else None,
                subject=current_row.subject if current_row else None,
                room=current_row.room if current_row else None,
                attendance_status=status,
                attendance_marked=status in ATTENDED_STATUSES,
                attendance_percent=day_attendance.percent,
                attended_count=day_attendance.present + day_attendance.late,
                marked_count=day_attendance.total,
                summary=summary,
            )
        )

    attended = sum(r.attended_count for r in rows)
    marked = sum(r.marked_count for r in rows)
    group_names = [names[gid] for gid in group_ids if gid in names]
    summary = GroupPresence(
        group_ids=group_ids,
        group_names=group_names,
        at=moment,
        current_pair=pair,
        pair_label=pair_label(pair) if pair else None,
        rows=rows,
        inside_count=sum(1 for r in rows if r.state == INSIDE),
        left_count=sum(1 for r in rows if r.state == LEFT),
        absent_count=sum(1 for r in rows if r.state == NOT_ARRIVED),
        in_class_count=sum(1 for r in rows if r.attendance_marked),
        attendance_percent=round(attended * 100 / marked) if marked else None,
        source={
            "type": TURNSTILE_SOURCE,
            "label": (
                "Turniket logi + dars jadvali + davomat jurnali — "
                + (", ".join(group_names) if group_names else "doirangiz")
                + f", {moment.strftime('%d.%m.%Y %H:%M')} holati"
            ),
        },
    )
    return summary


# --- the flow: a teacher's classes and the marking sheet ---------------------


def can_mark_class(actor: User, schedule: Schedule) -> bool:
    """Only the teacher of that very class (admin is superuser everywhere)."""
    return actor.role == UserRole.admin or schedule.teacher_id == actor.id


def can_view_class(db: Session, actor: User, schedule: Schedule) -> bool:
    if can_mark_class(actor, schedule):
        return True
    if actor.role == UserRole.teacher:
        return False  # a teacher sees their own classes only
    visible = visible_group_ids(db, actor)
    return visible is None or schedule.group_id in visible


def teacher_classes(
    db: Session, teacher: User, day: date | None = None, now: datetime | None = None
) -> list[TeacherClass]:
    """The teacher's classes for one day + how far the marking got."""
    moment = now or datetime.now()
    on_date = day or moment.date()
    rows = _schedule_rows(db, on_date.weekday(), teacher_id=teacher.id)
    names = _group_names(db, {row.group_id for row in rows})
    sessions = _sessions_by_schedule(db, [row.id for row in rows], on_date)

    counts: dict[int, int] = {}
    for group_id in {row.group_id for row in rows}:
        counts[group_id] = (
            db.query(User)
            .filter(User.role == UserRole.student, User.group_id == group_id)
            .count()
        )

    marks = (
        db.query(Attendance)
        .filter(
            Attendance.schedule_id.in_([row.id for row in rows]),
            Attendance.date == on_date,
        )
        .all()
        if rows
        else []
    )
    marked: dict[int, int] = {}
    present: dict[int, int] = {}
    for mark in marks:
        marked[mark.schedule_id] = marked.get(mark.schedule_id, 0) + 1
        if mark.status in ATTENDED_STATUSES:
            present[mark.schedule_id] = present.get(mark.schedule_id, 0) + 1

    pair = current_pair(moment) if on_date == moment.date() else None
    result: list[TeacherClass] = []
    for row in rows:
        starts_at, ends_at = pair_bounds(on_date, row.pair_number)
        session = sessions.get(row.id)
        result.append(
            TeacherClass(
                schedule_id=row.id,
                pair_number=row.pair_number,
                subject=row.subject,
                room=row.room,
                group_id=row.group_id,
                group_name=names.get(row.group_id),
                starts_at=starts_at,
                ends_at=ends_at,
                session_status=session.status if session else None,
                session_label=SESSION_LABELS[session.status] if session else None,
                student_count=counts.get(row.group_id, 0),
                marked_count=marked.get(row.id, 0),
                present_count=present.get(row.id, 0),
                is_current=row.pair_number == pair,
                is_past=ends_at < moment,
            )
        )
    return result


def get_schedule(db: Session, schedule_id: int) -> Schedule | None:
    return db.get(Schedule, schedule_id)


def _suggested_status(
    logs: list[TurnstileLog], starts_at: datetime
) -> AttendanceStatus:
    """Turnstile-based hint (the same rule the seed used): inside at the start
    of the pair -> present, entered after it -> late, otherwise absent."""
    inside = False
    last_entry: datetime | None = None
    for row in logs:
        if row.timestamp > starts_at + timedelta(minutes=15):
            break
        inside = row.direction == TurnstileDirection.entry
        if inside:
            last_entry = row.timestamp
    if not inside:
        return AttendanceStatus.absent
    if last_entry and last_entry > starts_at + timedelta(minutes=5):
        return AttendanceStatus.late
    return AttendanceStatus.present


def class_roster(
    db: Session,
    actor: User,
    schedule: Schedule,
    day: date | None = None,
    now: datetime | None = None,
) -> ClassRoster:
    """The marking sheet: every student of the group + journal + turnstile hint."""
    moment = now or datetime.now()
    on_date = day or moment.date()
    starts_at, ends_at = pair_bounds(on_date, schedule.pair_number)

    students = (
        db.query(User)
        .filter(User.role == UserRole.student, User.group_id == schedule.group_id)
        .order_by(User.full_name)
        .all()
    )
    student_ids = [s.id for s in students]
    logs = _logs_by_user(db, student_ids, on_date, max(moment, ends_at))
    existing = {
        row.student_id: row
        for row in (
            db.query(Attendance)
            .filter(
                Attendance.schedule_id == schedule.id, Attendance.date == on_date
            )
            .all()
        )
    }
    session = _sessions_by_schedule(db, [schedule.id], on_date).get(schedule.id)
    names = _group_names(db, {schedule.group_id})
    teachers = _user_names(db, {schedule.teacher_id})

    rows: list[RosterStudent] = []
    for student in students:
        state = building_state(logs.get(student.id, []))
        mark = existing.get(student.id)
        rows.append(
            RosterStudent(
                student_id=student.id,
                username=student.username,
                full_name=student.full_name,
                status=mark.status if mark else None,
                suggested=_suggested_status(logs.get(student.id, []), starts_at),
                state=state.state,
                state_label=state.label,
                entered_at=state.entered_at,
                left_at=state.left_at,
            )
        )

    return ClassRoster(
        schedule_id=schedule.id,
        date=on_date,
        pair_number=schedule.pair_number,
        pair_label=pair_label(schedule.pair_number),
        subject=schedule.subject,
        room=schedule.room,
        group_id=schedule.group_id,
        group_name=names.get(schedule.group_id),
        teacher_id=schedule.teacher_id,
        teacher_name=teachers.get(schedule.teacher_id),
        starts_at=starts_at,
        ends_at=ends_at,
        session_status=session.status if session else None,
        session_label=SESSION_LABELS[session.status] if session else None,
        can_mark=can_mark_class(actor, schedule),
        students=rows,
        marked_count=sum(1 for r in rows if r.status is not None),
        present_count=sum(1 for r in rows if r.status == AttendanceStatus.present),
        late_count=sum(1 for r in rows if r.status == AttendanceStatus.late),
        absent_count=sum(1 for r in rows if r.status == AttendanceStatus.absent),
        source=attendance_source(
            on_date,
            f"{pair_label(schedule.pair_number)}, {schedule.subject}, "
            f"{schedule.room}-xona",
        ),
    )


def mark_attendance(
    db: Session,
    actor: User,
    schedule: Schedule,
    marks: dict[int, AttendanceStatus],
    day: date | None = None,
    now: datetime | None = None,
) -> ClassRoster:
    """One click from the teacher: attendance rows + the class session status.

    Today's rows may already exist (the seed pre-writes the whole day), so this
    updates in place instead of adding duplicates. The `ClassSession` becomes
    `held` — that is what turns "the schedule says so" into "it happened".
    """
    moment = now or datetime.now()
    on_date = day or moment.date()
    if not can_mark_class(actor, schedule):
        raise NotOwnClassError(schedule.id)

    student_ids = {
        sid
        for (sid,) in db.query(User.id).filter(
            User.role == UserRole.student, User.group_id == schedule.group_id
        )
    }
    unknown = set(marks) - student_ids
    if unknown:
        raise UnknownStudentError(", ".join(str(i) for i in sorted(unknown)))

    existing = {
        row.student_id: row
        for row in db.query(Attendance).filter(
            Attendance.schedule_id == schedule.id, Attendance.date == on_date
        )
    }
    for student_id, status in marks.items():
        row = existing.get(student_id)
        if row is None:
            db.add(
                Attendance(
                    student_id=student_id,
                    schedule_id=schedule.id,
                    date=on_date,
                    status=status,
                    marked_by_teacher_id=schedule.teacher_id,
                )
            )
        else:
            row.status = status
            row.marked_by_teacher_id = schedule.teacher_id

    session = _sessions_by_schedule(db, [schedule.id], on_date).get(schedule.id)
    arrived = _teacher_arrival(db, schedule.teacher_id, on_date, moment)
    if session is None:
        db.add(
            ClassSession(
                schedule_id=schedule.id,
                date=on_date,
                status=ClassSessionStatus.held,
                teacher_arrived_at=arrived,
            )
        )
    else:
        session.status = ClassSessionStatus.held
        if session.teacher_arrived_at is None:
            session.teacher_arrived_at = arrived
    db.commit()
    # S12 trigger (FUNKSIONALLIK 3.10): whoever was marked absent hears about
    # it. Duplicate-safe, so re-saving the same class writes nothing new.
    notifications.notify_absent(
        db,
        schedule,
        on_date,
        [
            student_id
            for student_id, status in marks.items()
            if status == AttendanceStatus.absent
        ],
    )
    return class_roster(db, actor, schedule, on_date, moment)


def _teacher_arrival(
    db: Session, teacher_id: int, day: date, moment: datetime
) -> datetime:
    """When the turnstile first saw the teacher today (fallback: right now)."""
    row = (
        db.query(TurnstileLog)
        .filter(
            TurnstileLog.user_id == teacher_id,
            TurnstileLog.timestamp >= datetime.combine(day, time.min),
            TurnstileLog.timestamp <= moment,
            TurnstileLog.direction == TurnstileDirection.entry,
        )
        .order_by(TurnstileLog.timestamp)
        .first()
    )
    return row.timestamp if row else moment


# --- the flow: attendance history of one student ----------------------------


def attendance_summary(
    db: Session,
    student: User,
    days: int = DEFAULT_SUMMARY_DAYS,
    now: datetime | None = None,
) -> AttendanceSummary:
    """`davomat_kor`: how many classes were attended over the last N days."""
    moment = now or datetime.now()
    day = moment.date()
    window = max(1, min(int(days or DEFAULT_SUMMARY_DAYS), MAX_SUMMARY_DAYS))
    date_from = day - timedelta(days=window - 1)

    rows = (
        db.query(Attendance)
        .filter(
            Attendance.student_id == student.id,
            Attendance.date >= date_from,
            Attendance.date <= day,
        )
        .order_by(Attendance.date, Attendance.id)
        .all()
    )
    schedules = {
        row.id: row
        for row in (
            db.query(Schedule)
            .filter(Schedule.id.in_({r.schedule_id for r in rows}))
            .all()
            if rows
            else []
        )
    }

    present = late = absent = 0
    by_subject: dict[str, list[int]] = {}
    detailed: list[AttendanceRow] = []
    for row in rows:
        schedule = schedules.get(row.schedule_id)
        if schedule is None:
            continue
        starts_at, _end = pair_bounds(row.date, schedule.pair_number)
        if starts_at > moment:
            continue  # the seed writes the whole day ahead of time
        if row.status == AttendanceStatus.present:
            present += 1
        elif row.status == AttendanceStatus.late:
            late += 1
        else:
            absent += 1
        bucket = by_subject.setdefault(schedule.subject, [0, 0])
        bucket[0] += 1
        if row.status in ATTENDED_STATUSES:
            bucket[1] += 1
        detailed.append(
            AttendanceRow(
                date=row.date,
                pair_number=schedule.pair_number,
                subject=schedule.subject,
                room=schedule.room,
                status=row.status,
                status_label=ATTENDANCE_LABELS[row.status],
            )
        )

    total = present + late + absent
    today_rows = [r for r in rows if r.date == day]
    subjects = [
        SubjectAttendance(
            subject=name,
            total=counts[0],
            attended=counts[1],
            absent=counts[0] - counts[1],
            percent=round(counts[1] * 100 / counts[0]) if counts[0] else 0,
        )
        for name, counts in sorted(by_subject.items())
    ]
    subjects.sort(key=lambda s: (s.percent, s.subject))

    names = _group_names(db, {student.group_id} if student.group_id else set())
    detailed.reverse()
    summary = AttendanceSummary(
        student_id=student.id,
        username=student.username,
        full_name=student.full_name,
        group_id=student.group_id,
        group_name=names.get(student.group_id or -1),
        days=window,
        date_from=date_from,
        date_to=day,
        total=total,
        present=present,
        late=late,
        absent=absent,
        percent=round((present + late) * 100 / total) if total else None,
        by_subject=subjects,
        recent=detailed[:MAX_RECENT_ROWS],
        today=_day_attendance(today_rows, schedules, day, moment),
        source=attendance_source(
            day,
            f"{date_from.strftime('%d.%m.%Y')}–{day.strftime('%d.%m.%Y')} oralig'i, "
            f"{total} dars",
        ),
    )
    return summary


def student_attendance_summary(
    db: Session,
    actor: User,
    target: User,
    days: int = DEFAULT_SUMMARY_DAYS,
    now: datetime | None = None,
) -> AttendanceSummary:
    """Someone else's attendance — 403 unless the actor's scope covers them."""
    ensure_can_access_user(db, actor, target)
    return attendance_summary(db, target, days, now)


def format_attendance_for_tool(summary: AttendanceSummary) -> str:
    lines = [
        f"{summary.full_name}"
        + (f" ({summary.group_name})" if summary.group_name else "")
        + f" — davomat svodi ({summary.date_from.strftime('%d.%m.%Y')}–"
        f"{summary.date_to.strftime('%d.%m.%Y')}):",
    ]
    if summary.total == 0:
        lines.append("  Bu oraliqda davomat yozuvi yo'q.")
    else:
        lines.append(
            f"  Jami {summary.total} dars: kelgan {summary.present}, "
            f"kechikkan {summary.late}, kelmagan {summary.absent} "
            f"({summary.percent}%)"
        )
        for row in summary.by_subject[:6]:
            lines.append(
                f"  {row.subject}: {row.attended}/{row.total} ({row.percent}%)"
            )
    if summary.today.total:
        lines.append(
            f"  Bugun: {summary.today.present + summary.today.late}/"
            f"{summary.today.total} ({summary.today.percent}%)"
        )
    lines.append(f"(Manba: {summary.source['label']}.)")
    return "\n".join(lines)


def format_teacher_day_for_tool(
    classes: list[TeacherClass], teacher: User, day: date
) -> str:
    """The teacher's own day: which class is marked, which one still waits."""
    if not classes:
        return (
            f"{teacher.full_name} — {day.strftime('%d.%m.%Y')} kuni jadvalda "
            "darsingiz yo'q."
        )
    lines = [
        f"{teacher.full_name} — {day.strftime('%d.%m.%Y')} kungi darslar "
        f"({len(classes)} ta):"
    ]
    for row in classes:
        marking = (
            f"davomat belgilangan: {row.marked_count}/{row.student_count} "
            f"(kelgan {row.present_count})"
            if row.marked_count
            else "davomat hali belgilanmagan"
        )
        lines.append(
            f"  {pair_label(row.pair_number)} — {row.subject}, "
            f"{row.group_name or '?'}, {row.room}-xona ({SCHEDULE_HINT}); "
            f"{marking}"
            + (f"; dars holati: {row.session_label}" if row.session_label else "")
            + (" [hozir]" if row.is_current else "")
        )
    lines.append(
        "(Manba: dars jadvali + davomat jurnali, "
        f"{day.strftime('%d.%m.%Y')}.)"
    )
    return "\n".join(lines)


MAX_FLAGGED_ROWS = 15
LOW_ATTENDANCE_PERCENT = 75


def _needs_attention(row: GroupPresenceRow, class_running: bool) -> bool:
    """Rows worth naming in a chat answer: not inside, unmarked, or low today."""
    if row.state != INSIDE:
        return True
    if class_running and not row.attendance_marked:
        return True
    return (
        row.attendance_percent is not None
        and row.attendance_percent < LOW_ATTENDANCE_PERCENT
    )


def format_group_presence_for_tool(summary: GroupPresence) -> str:
    if not summary.rows:
        return "Doirangizda talaba topilmadi — mavjudlik svodi bo'sh."
    where = ", ".join(summary.group_names) if summary.group_names else "guruhlar"
    lines = [
        f"Mavjudlik svodi ({where}), {summary.at.strftime('%H:%M')} holati: "
        f"{len(summary.rows)} talaba — binoda {summary.inside_count}, "
        f"chiqib ketgan {summary.left_count}, kelmagan {summary.absent_count}."
    ]
    if summary.pair_label:
        lines.append(
            f"Hozir {SCHEDULE_HINT} {summary.pair_label}; davomatda belgilangan: "
            f"{summary.in_class_count} talaba."
        )
    if summary.attendance_percent is not None:
        lines.append(f"Bugungi davomat: {summary.attendance_percent}%.")
    flagged = [
        row
        for row in summary.rows
        if _needs_attention(row, summary.current_pair is not None)
    ]
    for row in flagged[:MAX_FLAGGED_ROWS]:
        lines.append(f"  {row.full_name} — {row.summary}")
    if len(flagged) > MAX_FLAGGED_ROWS:
        lines.append(f"  … va yana {len(flagged) - MAX_FLAGGED_ROWS} talaba.")
    if not flagged:
        lines.append("  Diqqat talab qiladigan holat yo'q.")
    lines.append(f"({ROOM_NOTE})")
    lines.append(f"(Manba: {summary.source['label']}.)")
    return "\n".join(lines)


# =============================================================================
# S10 — teacher attendance (dean's office view)
#
# Same three sources as everywhere else, one more question: was the class
# actually held? The answer is *derived* at a given moment, never stored:
#
#     attendance marked / session held      -> o'tildi (late if the teacher
#                                              entered after the bell)
#     class time, teacher not in building   -> xavf ostida
#     class time over, nothing marked       -> aniqlashtirish kerak
#     in the building, nothing marked       -> aniqlashtirish kerak
#
# Scope comes from `auth/rbac.can_access_user` — staff see their own faculty,
# admin everyone. Teachers are not group members, so `visible_group_ids` is the
# wrong tool here (a teacher belongs to a faculty, not to a group).
# =============================================================================


@dataclass
class TeacherClassState:
    """One scheduled class of one teacher, with the conclusion drawn about it."""

    schedule_id: int
    pair_number: int
    subject: str
    room: str
    group_id: int
    group_name: str | None
    starts_at: datetime
    ends_at: datetime
    session_status: ClassSessionStatus | None
    session_label: str | None
    state: str  # CLASS_HELD | CLASS_LATE | CLASS_AT_RISK | ...
    state_label: str
    teacher_arrived_at: datetime | None
    student_count: int
    marked_count: int
    present_count: int
    is_current: bool
    is_past: bool
    summary: str


@dataclass
class TeacherPresenceRow:
    """One teacher on the dean's daily list."""

    teacher_id: int
    username: str
    full_name: str
    faculty_id: int | None
    state: str  # INSIDE | LEFT | NOT_ARRIVED
    state_label: str
    in_building: bool
    entered_at: datetime | None
    left_at: datetime | None
    classes: list[TeacherClassState]
    class_count: int
    held_count: int
    late_count: int
    at_risk_count: int
    unclear_count: int
    summary: str


@dataclass
class TeacherDayOverview:
    """GET /attendance/teachers — today's teacher roll-call for the dean."""

    date: date
    at: datetime
    current_pair: int | None
    pair_label: str | None
    faculty_ids: list[int]
    rows: list[TeacherPresenceRow]
    teacher_count: int
    inside_count: int
    left_count: int
    absent_count: int
    class_count: int
    held_count: int
    late_count: int
    at_risk_count: int
    unclear_count: int
    schedule_note: str = ROOM_NOTE
    source: dict = field(default_factory=dict)
    disclaimer: str = DISCLAIMER


@dataclass
class TeacherMonthRow:
    teacher_id: int
    username: str
    full_name: str
    total: int
    held: int
    late: int
    cancelled: int
    unclear: int
    percent: int | None


@dataclass
class TeacherMonthSummary:
    """GET /attendance/teachers/monthly — held/missed percentages per teacher."""

    date_from: date
    date_to: date
    days: int
    rows: list[TeacherMonthRow]
    total: int
    held: int
    late: int
    cancelled: int
    unclear: int
    percent: int | None
    source: dict = field(default_factory=dict)
    disclaimer: str = DISCLAIMER


# --- scope -------------------------------------------------------------------


def teachers_in_scope(db: Session, actor: User) -> list[User]:
    """Teachers this user may look at — decided by `rbac.can_access_user` only.

    staff -> own faculty, admin -> everybody. Nothing is re-implemented here.
    """
    rows = (
        db.query(User)
        .filter(User.role == UserRole.teacher)
        .order_by(User.full_name)
        .all()
    )
    return [row for row in rows if can_access_user(db, actor, row)]


def _room_text(room: str) -> str:
    """`214` -> `214-xona`; `103-lab` already carries its own name."""
    return f"{room}-xona" if room and room[-1].isdigit() else room


# --- the conclusion ----------------------------------------------------------


def class_state(
    session: ClassSession | None,
    building: BuildingState,
    starts_at: datetime,
    ends_at: datetime,
    marked_count: int,
    now: datetime,
) -> str:
    """Derived state of one class. The stored `ClassSessionStatus` is an input."""
    if session is not None and session.status == ClassSessionStatus.cancelled:
        return CLASS_CANCELLED

    held = marked_count > 0 or (
        session is not None and session.status == ClassSessionStatus.held
    )
    if held:
        arrived = (
            session.teacher_arrived_at if session else None
        ) or building.entered_at
        if arrived and arrived > starts_at + timedelta(minutes=LATE_GRACE_MINUTES):
            return CLASS_LATE
        return CLASS_HELD

    if now < starts_at - timedelta(minutes=RISK_LEAD_MINUTES):
        return CLASS_UPCOMING
    if not building.in_building:
        # The bell is about to ring (or already did) and the turnstile has not
        # seen the teacher: this is the alert the dean's office needs.
        return CLASS_AT_RISK if now <= ends_at else CLASS_UNCLEAR
    if now < starts_at:
        return CLASS_UPCOMING
    return CLASS_UNCLEAR


def _class_sentence(state: str, room: str, marked: int, total: int) -> str:
    """Why the class is in that state — the label itself is never repeated here."""
    if state == CLASS_AT_RISK:
        return "dars vaqti keldi, o'qituvchi turniketdan o'tmagan"
    if state == CLASS_LATE:
        return f"o'qituvchi qo'ng'iroqdan keyin kirgan, davomat {marked}/{total}"
    if state == CLASS_HELD:
        return f"davomat belgilangan ({marked}/{total})"
    if state == CLASS_CANCELLED:
        return "dars qoldirildi deb yozilgan"
    if state == CLASS_UPCOMING:
        return f"dars hali boshlanmagan ({SCHEDULE_HINT} {_room_text(room)})"
    return "davomat belgilanmagan"


def _teacher_sentence(building: BuildingState, states: list[str]) -> str:
    parts: list[str] = []
    if building.state == INSIDE:
        parts.append(f"Binoda — {_hhmm(building.entered_at)} da kirgan")
    elif building.state == LEFT:
        parts.append(f"Binodan chiqib ketgan — {_hhmm(building.left_at)} da chiqqan")
    else:
        parts.append("Bugun binoga kirmagan (turniketda yozuv yo'q)")

    if not states:
        parts.append("bugun jadvalda darsi yo'q")
    else:
        at_risk = states.count(CLASS_AT_RISK)
        unclear = states.count(CLASS_UNCLEAR)
        late = states.count(CLASS_LATE)
        held = states.count(CLASS_HELD) + late
        detail = [f"{len(states)} ta dars"]
        if held:
            detail.append(f"o'tilgan {held}")
        if late:
            detail.append(f"kechikkan {late}")
        if at_risk:
            detail.append(f"xavf ostida {at_risk}")
        if unclear:
            detail.append(f"aniqlashtirish kerak {unclear}")
        parts.append(", ".join(detail))
    return "; ".join(parts) + "."


# --- the flow: today's teacher roll-call --------------------------------------


def teacher_day_overview(
    db: Session,
    actor: User,
    day: date | None = None,
    now: datetime | None = None,
    notify: bool = True,
) -> TeacherDayOverview:
    """Every teacher in scope: in the building or not, and how their classes go.

    `notify=True` writes a `Notification` for each class that is at risk right
    now (S12 renders them; duplicates are never written).
    """
    moment = now or datetime.now()
    on_date = day or moment.date()
    teachers = teachers_in_scope(db, actor)
    teacher_ids = [t.id for t in teachers]

    logs = _logs_by_user(db, teacher_ids, on_date, moment)
    schedule_rows = (
        db.query(Schedule)
        .filter(
            Schedule.weekday == on_date.weekday(),
            Schedule.teacher_id.in_(teacher_ids),
        )
        .order_by(Schedule.pair_number, Schedule.group_id)
        .all()
        if teacher_ids
        else []
    )
    sessions = _sessions_by_schedule(db, [row.id for row in schedule_rows], on_date)
    names = _group_names(db, {row.group_id for row in schedule_rows})

    student_counts: dict[int, int] = {}
    for group_id in {row.group_id for row in schedule_rows}:
        student_counts[group_id] = (
            db.query(User)
            .filter(User.role == UserRole.student, User.group_id == group_id)
            .count()
        )

    marks = (
        db.query(Attendance)
        .filter(
            Attendance.schedule_id.in_([row.id for row in schedule_rows]),
            Attendance.date == on_date,
        )
        .all()
        if schedule_rows
        else []
    )
    marked: dict[int, int] = {}
    present: dict[int, int] = {}
    for mark in marks:
        marked[mark.schedule_id] = marked.get(mark.schedule_id, 0) + 1
        if mark.status in ATTENDED_STATUSES:
            present[mark.schedule_id] = present.get(mark.schedule_id, 0) + 1

    by_teacher: dict[int, list[Schedule]] = {}
    for row in schedule_rows:
        by_teacher.setdefault(row.teacher_id, []).append(row)

    pair = current_pair(moment) if on_date == moment.date() else None
    rows: list[TeacherPresenceRow] = []
    for teacher in teachers:
        building = building_state(logs.get(teacher.id, []))
        classes: list[TeacherClassState] = []
        for schedule in by_teacher.get(teacher.id, []):
            starts_at, ends_at = pair_bounds(on_date, schedule.pair_number)
            session = sessions.get(schedule.id)
            marked_count = marked.get(schedule.id, 0)
            state = class_state(
                session, building, starts_at, ends_at, marked_count, moment
            )
            total = student_counts.get(schedule.group_id, 0)
            classes.append(
                TeacherClassState(
                    schedule_id=schedule.id,
                    pair_number=schedule.pair_number,
                    subject=schedule.subject,
                    room=schedule.room,
                    group_id=schedule.group_id,
                    group_name=names.get(schedule.group_id),
                    starts_at=starts_at,
                    ends_at=ends_at,
                    session_status=session.status if session else None,
                    session_label=SESSION_LABELS[session.status] if session else None,
                    state=state,
                    state_label=CLASS_STATE_LABELS[state],
                    teacher_arrived_at=session.teacher_arrived_at if session else None,
                    student_count=total,
                    marked_count=marked_count,
                    present_count=present.get(schedule.id, 0),
                    is_current=schedule.pair_number == pair,
                    is_past=ends_at < moment,
                    summary=_class_sentence(state, schedule.room, marked_count, total),
                )
            )
        states = [c.state for c in classes]
        rows.append(
            TeacherPresenceRow(
                teacher_id=teacher.id,
                username=teacher.username,
                full_name=teacher.full_name,
                faculty_id=teacher.faculty_id,
                state=building.state,
                state_label=building.label,
                in_building=building.in_building,
                entered_at=building.entered_at,
                left_at=building.left_at,
                classes=classes,
                class_count=len(classes),
                held_count=states.count(CLASS_HELD) + states.count(CLASS_LATE),
                late_count=states.count(CLASS_LATE),
                at_risk_count=states.count(CLASS_AT_RISK),
                unclear_count=states.count(CLASS_UNCLEAR),
                summary=_teacher_sentence(building, states),
            )
        )

    # Problems first: the demo has to open on the teacher who never came.
    rows.sort(
        key=lambda r: (
            0 if r.at_risk_count else 1,
            0 if r.unclear_count or r.late_count else 1,
            0 if r.state == NOT_ARRIVED else 1,
            r.full_name,
        )
    )

    faculty_ids = sorted({t.faculty_id for t in teachers if t.faculty_id is not None})
    where = (
        ", ".join(f"{fid}-fakultet" for fid in faculty_ids)
        if faculty_ids
        else "doirangiz"
    )
    overview = TeacherDayOverview(
        date=on_date,
        at=moment,
        current_pair=pair,
        pair_label=pair_label(pair) if pair else None,
        faculty_ids=faculty_ids,
        rows=rows,
        teacher_count=len(rows),
        inside_count=sum(1 for r in rows if r.state == INSIDE),
        left_count=sum(1 for r in rows if r.state == LEFT),
        absent_count=sum(1 for r in rows if r.state == NOT_ARRIVED),
        class_count=sum(r.class_count for r in rows),
        held_count=sum(r.held_count for r in rows),
        late_count=sum(r.late_count for r in rows),
        at_risk_count=sum(r.at_risk_count for r in rows),
        unclear_count=sum(r.unclear_count for r in rows),
        source={
            "type": TURNSTILE_SOURCE,
            "label": (
                "Turniket logi + dars jadvali + davomat jurnali — "
                f"{where} o'qituvchilari, "
                f"{moment.strftime('%d.%m.%Y %H:%M')} holati"
            ),
        },
    )
    if notify:
        record_risk_notifications(db, overview)
    return overview


# --- "dars xavf ostida" -> Notification (S12 renders them) --------------------


def risk_notification_text(row: TeacherPresenceRow, item: TeacherClassState) -> str:
    """The seed's wording, so demo rows and runtime rows read alike."""
    return (
        f"Dars xavf ostida: {row.full_name} bugun {item.pair_number}-paradagi "
        f"darsiga ({item.group_name or '?'}, {item.subject}, {item.room}) "
        "hali binoga kirmagan."
    )


def record_risk_notifications(db: Session, overview: TeacherDayOverview) -> int:
    """One notification per (dean, class) per day — never a duplicate.

    Recipients are the staff of the teacher's own faculty. The seed already
    wrote today's row for the pinned class; it is recognised and kept. The row
    itself is written by `services/notifications.py` (S12) — this function only
    decides *who* hears about *which* class.
    """
    risky = [
        (row, item)
        for row in overview.rows
        for item in row.classes
        if item.state == CLASS_AT_RISK
    ]
    if not risky:
        return 0

    by_faculty: dict[int | None, list[User]] = {}
    for person in db.query(User).filter(User.role == UserRole.staff):
        by_faculty.setdefault(person.faculty_id, []).append(person)

    # `Notification.created_at` is written by SQLite's CURRENT_TIMESTAMP (UTC)
    # while everything else here reasons in local time, so the "already
    # notified" window starts at the *previous* midnight. A schedule row recurs
    # weekly, so a window this wide can never hide a genuinely new alert.
    window_start = datetime.combine(overview.date, time.min) - timedelta(days=1)
    day_end = datetime.combine(overview.date, time.max)

    written = 0
    for row, item in risky:
        for recipient in by_faculty.get(row.faculty_id, []):
            written += notifications.write_notification(
                db,
                recipient.id,
                TEACHER_ABSENCE_NOTIF,
                risk_notification_text(row, item),
                notifications.LINK_SCHEDULE,
                item.schedule_id,
                match_text=False,
                since=window_start,
                until=day_end,
            )
    if written:
        db.commit()
    return written


# --- the flow: monthly percentages -------------------------------------------


def teacher_month_summary(
    db: Session,
    actor: User,
    days: int = DEFAULT_MONTH_DAYS,
    now: datetime | None = None,
) -> TeacherMonthSummary:
    """Held / missed classes per teacher over the last N days (report view)."""
    moment = now or datetime.now()
    day = moment.date()
    window = max(1, min(int(days or DEFAULT_MONTH_DAYS), MAX_MONTH_DAYS))
    date_from = day - timedelta(days=window - 1)

    teachers = teachers_in_scope(db, actor)
    teacher_ids = [t.id for t in teachers]
    rows = (
        db.query(ClassSession, Schedule)
        .join(Schedule, Schedule.id == ClassSession.schedule_id)
        .filter(
            Schedule.teacher_id.in_(teacher_ids),
            ClassSession.date >= date_from,
            ClassSession.date <= day,
        )
        .all()
        if teacher_ids
        else []
    )

    buckets: dict[int, dict[str, int]] = {
        t.id: {"total": 0, "held": 0, "late": 0, "cancelled": 0, "unclear": 0}
        for t in teachers
    }
    for session, schedule in rows:
        starts_at, _ends_at = pair_bounds(session.date, schedule.pair_number)
        if starts_at > moment:
            continue  # the seed writes the whole day ahead of time
        bucket = buckets[schedule.teacher_id]
        bucket["total"] += 1
        if session.status == ClassSessionStatus.held:
            bucket["held"] += 1
            arrived = session.teacher_arrived_at
            if arrived and arrived > starts_at + timedelta(minutes=LATE_GRACE_MINUTES):
                bucket["late"] += 1
        elif session.status == ClassSessionStatus.cancelled:
            bucket["cancelled"] += 1
        else:
            bucket["unclear"] += 1

    result = [
        TeacherMonthRow(
            teacher_id=t.id,
            username=t.username,
            full_name=t.full_name,
            total=buckets[t.id]["total"],
            held=buckets[t.id]["held"],
            late=buckets[t.id]["late"],
            cancelled=buckets[t.id]["cancelled"],
            unclear=buckets[t.id]["unclear"],
            percent=(
                round(buckets[t.id]["held"] * 100 / buckets[t.id]["total"])
                if buckets[t.id]["total"]
                else None
            ),
        )
        for t in teachers
    ]
    # Worst first — that is the row a dean opens the report for.
    result.sort(
        key=lambda r: (r.percent if r.percent is not None else 101, r.full_name)
    )

    total = sum(r.total for r in result)
    held = sum(r.held for r in result)
    return TeacherMonthSummary(
        date_from=date_from,
        date_to=day,
        days=window,
        rows=result,
        total=total,
        held=held,
        late=sum(r.late for r in result),
        cancelled=sum(r.cancelled for r in result),
        unclear=sum(r.unclear for r in result),
        percent=round(held * 100 / total) if total else None,
        source=attendance_source(
            day,
            f"{date_from.strftime('%d.%m.%Y')}-{day.strftime('%d.%m.%Y')} oralig'i, "
            f"{len(result)} o'qituvchi, {total} dars",
        ),
    )


# --- agent-facing text (`oqituvchi_davomat`) ---------------------------------


def class_state_source(item: TeacherClassState) -> dict:
    return {
        "type": SCHEDULE_SOURCE,
        "label": (
            f"Dars jadvali ({SCHEDULE_HINT}) — {pair_label(item.pair_number)}, "
            f"{item.subject}, {item.room}, {item.group_name or '?'}"
        ),
    }


def teacher_row_sources(row: TeacherPresenceRow, day: date) -> list[dict]:
    """Citations for one teacher: the turnstile fact + the schedule inference."""
    building = BuildingState(row.state, row.entered_at, row.left_at, None)
    sources = [turnstile_source(building, day)]
    for item in row.classes:
        if item.state in CLASS_ALERT_STATES:
            sources.append(class_state_source(item))
    return sources


def _class_line(item: TeacherClassState) -> str:
    return (
        f"    {pair_label(item.pair_number)} — \"{item.subject}\", "
        f"{item.group_name or '?'}, {item.room} ({SCHEDULE_HINT}): "
        f"{item.state_label} — {item.summary}"
    )


def _is_flagged(row: TeacherPresenceRow) -> bool:
    return bool(
        row.at_risk_count
        or row.unclear_count
        or row.late_count
        or row.state == NOT_ARRIVED
    )


def format_teacher_overview_for_tool(overview: TeacherDayOverview) -> str:
    """The dean's answer: who is missing, in which class, and from which source."""
    if not overview.rows:
        return "Doirangizda o'qituvchi topilmadi — svod bo'sh."

    lines = [
        f"O'qituvchilar davomati — {overview.date.strftime('%d.%m.%Y')}, "
        f"{overview.at.strftime('%H:%M')} holati: {overview.teacher_count} "
        f"o'qituvchi — binoda {overview.inside_count}, chiqib ketgan "
        f"{overview.left_count}, kelmagan {overview.absent_count}.",
        f"Bugungi darslar: {overview.class_count} ta — o'tilgan "
        f"{overview.held_count}, xavf ostida {overview.at_risk_count}, "
        f"aniqlashtirish kerak {overview.unclear_count}, kechikkan "
        f"{overview.late_count}.",
    ]
    if overview.pair_label:
        lines.append(f"Hozir {SCHEDULE_HINT} {overview.pair_label}.")

    flagged = [row for row in overview.rows if _is_flagged(row)]
    if not flagged:
        lines.append("Diqqat talab qiladigan o'qituvchi yo'q.")
    for row in flagged[:MAX_FLAGGED_ROWS]:
        lines.append(f"  {row.full_name} — {row.summary}")
        for item in row.classes:
            if item.state in CLASS_ALERT_STATES:
                lines.append(_class_line(item))
    if len(flagged) > MAX_FLAGGED_ROWS:
        lines.append(f"  … va yana {len(flagged) - MAX_FLAGGED_ROWS} o'qituvchi.")

    lines.append(f"({ROOM_NOTE})")
    labels = [overview.source["label"]]
    for row in flagged[:MAX_FLAGGED_ROWS]:
        if row.state == NOT_ARRIVED or row.at_risk_count:
            building = BuildingState(row.state, row.entered_at, row.left_at, None)
            labels.append(
                f"{turnstile_source(building, overview.date)['label']} "
                f"({row.full_name})"
            )
    lines.append("(Manba: " + "; ".join(labels) + ".)")
    return "\n".join(lines)


def format_teacher_row_for_tool(
    row: TeacherPresenceRow, overview: TeacherDayOverview
) -> str:
    """One named teacher ("Tursunov bugun darsga keldimi?")."""
    lines = [
        f"{row.full_name} — {overview.date.strftime('%d.%m.%Y')}, "
        f"{overview.at.strftime('%H:%M')} holatiga ko'ra: {row.summary}"
    ]
    if not row.classes:
        lines.append(f"    Bugun {SCHEDULE_HINT} darsi yo'q.")
    for item in row.classes:
        lines.append(_class_line(item))
    lines.append(f"  Eslatma: {ROOM_NOTE}")
    lines.append(
        "(Manba: "
        + "; ".join(s["label"] for s in teacher_row_sources(row, overview.date))
        + ".)"
    )
    return "\n".join(lines)


def format_teacher_month_for_tool(summary: TeacherMonthSummary) -> str:
    lines = [
        "O'qituvchilar bo'yicha svod "
        f"({summary.date_from.strftime('%d.%m.%Y')}-"
        f"{summary.date_to.strftime('%d.%m.%Y')}): {summary.total} dars, "
        f"o'tilgan {summary.held}"
        + (f" ({summary.percent}%)" if summary.percent is not None else "")
        + "."
    ]
    for row in summary.rows[:MAX_FLAGGED_ROWS]:
        lines.append(
            f"  {row.full_name}: {row.held}/{row.total}"
            + (f" ({row.percent}%)" if row.percent is not None else "")
            + (f", kechikkan {row.late}" if row.late else "")
            + (f", qoldirilgan {row.cancelled}" if row.cancelled else "")
            + (f", aniqlashtirish kerak {row.unclear}" if row.unclear else "")
        )
    lines.append(f"(Manba: {summary.source['label']}.)")
    return "\n".join(lines)
