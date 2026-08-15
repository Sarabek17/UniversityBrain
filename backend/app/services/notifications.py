"""Notifications service (S12): one bell for every module event.

Every module writes through the single helper below, so a notification is
written in exactly one way in the whole project:

    write_notification(db, user_id, notif_type, text, link_type, link_id)

It is duplicate-safe by construction. The key is
`(user_id, notif_type, link_type, link_id[, text])` and the text is part of it
by default:

    match_text=True   a genuine *second step* of the same object is a new row
                      (an application goes "ko'rildi" and later "tasdiqlandi")
    match_text=False  the event happens once per object, so any wording wins —
                      this is how the rows the seed already wrote are
                      recognised and never doubled (S10/S11 pattern)

`since`/`until` narrow the guard to a time window: a weekly schedule row may
legitimately raise the same alert again next week (S10's "dars xavf ostida").

**UTC trap (S10, still in force):** `Notification.created_at` is filled by
SQLite's `CURRENT_TIMESTAMP`, which is **UTC**, while everything else in this
project reasons in local time (Uzbekistan, UTC+5). Rows leaving this service
are therefore converted with `to_local()` — the UI and the agent print the same
clock as the rest of the app — and duplicate windows start at the *previous*
midnight.

Triggers (FUNKSIONALLIK 3.10). Two kinds, deliberately:

    written by the action        upload_receipt / confirm_payment (S8),
                                 mark_attendance (S9), teacher risk (S10),
                                 flow created / flow status (S11)
    computed when the bell is
    opened (no cron, hackathon)  contract debt, flow execution deadline
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import (
    AccessLevel,
    Document,
    DocumentType,
    Group,
    Notification,
    Payment,
    Schedule,
    User,
    UserRole,
)

# --- vocabulary --------------------------------------------------------------

# `notif_type` values. The first six already exist in the seed; S12 adds the
# last three (FUNKSIONALLIK 3.10 rows that had no trigger yet).
FLOW_STATUS = "flow_status"  # your application moved            -> sender
FLOW_INCOMING = "flow_incoming"  # a new document arrived        -> recipient
TEACHER_ABSENCE = "teacher_absence"  # "dars xavf ostida"        -> dean office
PAYMENT_UPLOADED = "payment_uploaded"  # receipt needs confirming -> tutor
PAYMENT_DEBT = "payment_debt"  # contract debt                   -> student/tutor
NEW_ASSIGNMENT = "new_assignment"  # new task/material           -> student
PAYMENT_CONFIRMED = "payment_confirmed"  # receipt accepted      -> student
CLASS_ABSENT = "class_absent"  # marked absent in a class        -> student
FLOW_DUE = "flow_due"  # execution deadline near/passed  -> executor + sender
NEW_ORDER = "new_order"  # a document was published       -> the roles that see it

TYPE_LABELS: dict[str, str] = {
    FLOW_STATUS: "Ariza holati",
    FLOW_INCOMING: "Yangi hujjat",
    FLOW_DUE: "Ijro muddati",
    TEACHER_ABSENCE: "Dars xavf ostida",
    PAYMENT_UPLOADED: "To'lov cheki",
    PAYMENT_CONFIRMED: "To'lov tasdiqlandi",
    PAYMENT_DEBT: "Kontrakt qarzdorligi",
    CLASS_ABSENT: "Davomat",
    NEW_ASSIGNMENT: "Yangi topshiriq",
    NEW_ORDER: "Yangi hujjat e'loni",
}

# `link_type` -> the page the UI opens (the frontend mirrors this table).
#   flow_document -> /docflow      link_id = FlowDocument.id
#   schedule      -> /attendance   link_id = Schedule.id
#   payment       -> /contract (student) | /group (tutor, staff)
#   contract      -> same as payment, link_id = None
#   assignment    -> /documents    link_id = None (seed rows)
#   document      -> /documents    link_id = Document.id
LINK_FLOW = "flow_document"
LINK_SCHEDULE = "schedule"
LINK_PAYMENT = "payment"
LINK_CONTRACT = "contract"
LINK_ASSIGNMENT = "assignment"
LINK_DOCUMENT = "document"

DEFAULT_LIMIT = 30
MAX_LIMIT = 100

SOURCE_TYPE = "notification"

# Debt reminders are one per person: a contract does not change hourly.
DEBT_ROLES = (UserRole.student, UserRole.tutor)


# --- local time --------------------------------------------------------------


def utc_offset() -> timedelta:
    """This machine's offset from UTC (UTC+5 in the demo)."""
    return datetime.now().astimezone().utcoffset() or timedelta(0)


def to_local(moment: datetime) -> datetime:
    """`created_at` is stored in UTC; everything the user sees is local."""
    return moment + utc_offset()


# --- view models -------------------------------------------------------------


@dataclass
class NotificationItem:
    id: int
    user_id: int
    notif_type: str
    type_label: str
    text: str
    link_type: str | None
    link_id: int | None
    is_read: bool
    created_at: datetime  # already local


@dataclass
class NotificationFeed:
    rows: list[NotificationItem] = field(default_factory=list)
    total: int = 0  # everything the user has, not just this page
    unread_count: int = 0
    unread_only: bool = False
    limit: int = DEFAULT_LIMIT
    source: dict = field(default_factory=dict)


def item_of(row: Notification) -> NotificationItem:
    return NotificationItem(
        id=row.id,
        user_id=row.user_id,
        notif_type=row.notif_type,
        type_label=TYPE_LABELS.get(row.notif_type, "Bildirishnoma"),
        text=row.text,
        link_type=row.link_type,
        link_id=row.link_id,
        is_read=bool(row.is_read),
        created_at=to_local(row.created_at),
    )


def feed_source(count: int, on_day: date | None = None) -> dict:
    """Mandatory citation (domain rule 5): where the answer came from."""
    day = on_day or date.today()
    return {
        "type": SOURCE_TYPE,
        "label": f"Bildirishnomalar ro'yxati, {day.strftime('%d.%m.%Y')} "
        f"({count} ta o'qilmagan)",
    }


# --- the single writer -------------------------------------------------------


def write_notification(
    db: Session,
    user_id: int,
    notif_type: str,
    text: str,
    link_type: str | None,
    link_id: int | None,
    *,
    match_text: bool = True,
    since: datetime | None = None,
    until: datetime | None = None,
) -> bool:
    """Add one notification unless an equivalent row already exists.

    Returns True when a row was added. The caller commits (several triggers
    write a batch and commit once).
    """
    query = db.query(Notification.id).filter(
        Notification.user_id == user_id,
        Notification.notif_type == notif_type,
    )
    query = (
        query.filter(Notification.link_type.is_(None))
        if link_type is None
        else query.filter(Notification.link_type == link_type)
    )
    query = (
        query.filter(Notification.link_id.is_(None))
        if link_id is None
        else query.filter(Notification.link_id == link_id)
    )
    if match_text:
        query = query.filter(Notification.text == text)
    if since is not None:
        query = query.filter(Notification.created_at >= since)
    if until is not None:
        query = query.filter(Notification.created_at <= until)
    if query.first() is not None:
        return False
    db.add(
        Notification(
            user_id=user_id,
            notif_type=notif_type,
            text=text,
            link_type=link_type,
            link_id=link_id,
        )
    )
    return True


# --- reading the bell --------------------------------------------------------


def unread_count(db: Session, user: User) -> int:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.is_read.is_(False))
        .count()
    )


def feed(
    db: Session,
    user: User,
    *,
    unread_only: bool = False,
    limit: int | None = None,
    refresh: bool = True,
) -> NotificationFeed:
    """The bell: newest first, with the unread counter in the same answer.

    `refresh=True` runs the "computed" triggers first (debt, execution
    deadlines) — the hackathon's substitute for a cron job: the check happens
    when somebody opens the bell.
    """
    if refresh:
        refresh_triggers(db, user)

    size = DEFAULT_LIMIT if limit is None else max(1, min(int(limit), MAX_LIMIT))
    query = db.query(Notification).filter(Notification.user_id == user.id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    rows = (
        query.order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(size)
        .all()
    )
    total = db.query(Notification).filter(Notification.user_id == user.id).count()
    unread = unread_count(db, user)
    return NotificationFeed(
        rows=[item_of(row) for row in rows],
        total=total,
        unread_count=unread,
        unread_only=unread_only,
        limit=size,
        source=feed_source(unread),
    )


def get_own(db: Session, user: User, notification_id: int) -> Notification | None:
    """Somebody else's notification does not exist for this caller (404)."""
    return (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user.id)
        .first()
    )


def mark_read(db: Session, user: User, notification_id: int) -> Notification | None:
    row = get_own(db, user, notification_id)
    if row is None:
        return None
    if not row.is_read:
        row.is_read = True
        db.commit()
    return row


def mark_all_read(db: Session, user: User) -> int:
    rows = (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.is_read.is_(False))
        .all()
    )
    for row in rows:
        row.is_read = True
    if rows:
        db.commit()
    return len(rows)


# --- triggers written by the action (S8, S9) ---------------------------------


def _group_name(db: Session, group_id: int | None) -> str | None:
    if group_id is None:
        return None
    group = db.get(Group, group_id)
    return group.name if group else None


def _tutors_of(db: Session, student: User) -> list[User]:
    """Who confirms this student's receipt: the tutor of their group."""
    if student.group_id is None:
        return []
    group = db.get(Group, student.group_id)
    if group is None or group.tutor_id is None:
        return []
    tutor = db.get(User, group.tutor_id)
    return [tutor] if tutor is not None else []


def notify_receipt_uploaded(db: Session, student: User, payment: Payment) -> int:
    """A receipt is waiting for confirmation -> the group's tutor (3.10)."""
    from app.services.payments import format_amount

    group_name = _group_name(db, student.group_id)
    text = (
        f"{student.full_name}"
        + (f" ({group_name})" if group_name else "")
        + f" to'lov chekini yukladi — {format_amount(float(payment.amount))}, "
        f"tasdiqlash kutilmoqda."
    )
    written = 0
    for tutor in _tutors_of(db, student):
        # One receipt is uploaded once: any wording of the same (tutor,
        # payment) pair counts, so the seeded row is recognised.
        written += write_notification(
            db,
            tutor.id,
            PAYMENT_UPLOADED,
            text,
            LINK_PAYMENT,
            payment.id,
            match_text=False,
        )
    if written:
        db.commit()
    return written


def notify_payment_confirmed(db: Session, student: User, payment: Payment) -> int:
    """The tutor accepted the receipt -> the student (3.10)."""
    from app.services.payments import format_amount

    text = (
        f"To'lovingiz tasdiqlandi: {format_amount(float(payment.amount))}"
        + (f", chek {payment.receipt_number}" if payment.receipt_number else "")
        + f" ({payment.paid_at.strftime('%d.%m.%Y')})."
    )
    written = write_notification(
        db,
        student.id,
        PAYMENT_CONFIRMED,
        text,
        LINK_PAYMENT,
        payment.id,
        match_text=False,
    )
    if written:
        db.commit()
    return int(written)


def notify_absent(
    db: Session, schedule: Schedule, day: date, student_ids: list[int]
) -> int:
    """Marked "kelmagan" in a class -> that student (3.10).

    The date is part of the text, so the same weekly class writes a new row on
    a new day but never twice for the same one.
    """
    if not student_ids:
        return 0
    # Local import: `services/presence.py` imports this module, so the pair
    # table is fetched at call time instead of at import time.
    from app.services.presence import PAIR_TIME_LABELS

    hours = PAIR_TIME_LABELS.get(schedule.pair_number)
    when = f"{hours[0]}-{hours[1]}" if hours else ""
    text = (
        f"{day.strftime('%d.%m.%Y')} kuni {schedule.pair_number}-juftlik"
        + (f" ({when})" if when else "")
        + f" '{schedule.subject}' darsida davomatda 'kelmagan' deb "
        "belgilandingiz."
    )
    written = 0
    for student_id in student_ids:
        written += write_notification(
            db, student_id, CLASS_ABSENT, text, LINK_SCHEDULE, schedule.id
        )
    if written:
        db.commit()
    return written


def roles_for_access(level: AccessLevel) -> tuple[UserRole, ...]:
    """Which roles may see a document at this access level (S14).

    Mirrors `rag.search.allowed_access_levels` read the other way round: a role
    sees `public` plus documents tagged with its own name, and admin sees
    everything. No second permission rule is introduced.
    """
    if level == AccessLevel.public:
        return tuple(UserRole)
    return tuple(
        role
        for role in UserRole
        if role == UserRole.admin or role.value == level.value
    )


def notify_new_document(
    db: Session, document: Document, *, exclude_user_id: int | None = None
) -> int:
    """A document was published -> everyone whose role may read it (3.10).

    `match_text=False` with `link_id=document.id`: one announcement per person
    per document, whatever the wording.
    """
    label = (
        "Yangi buyruq e'lon qilindi"
        if document.doc_type == DocumentType.order
        else "Yangi hujjat e'lon qilindi"
    )
    text = (
        f"{label}: «{document.title}». "
        "Hujjatlar bo'limida o'qishingiz mumkin."
    )
    roles = roles_for_access(document.access_level)
    recipients = db.query(User.id).filter(User.role.in_(roles))
    if exclude_user_id is not None:
        recipients = recipients.filter(User.id != exclude_user_id)
    written = 0
    for (user_id,) in recipients.all():
        written += write_notification(
            db,
            user_id,
            NEW_ORDER,
            text,
            LINK_DOCUMENT,
            document.id,
            match_text=False,
        )
    if written:
        db.commit()
    return written


# --- triggers computed when the bell is opened (no cron) ---------------------


def record_debt_notifications(db: Session, user: User) -> int:
    """Contract debt -> the student themselves and their tutor (3.10).

    `match_text=False` with `link_id=None`: the reminder exists once per
    person, so the seeded row (karimov) is recognised and the amount in the
    text never produces a second one.
    """
    if user.role not in DEBT_ROLES:
        return 0
    from app.services import payments as payments_service

    written = 0
    if user.role == UserRole.student:
        try:
            summary = payments_service.contract_summary(db, user)
        except payments_service.NoContractError:
            return 0
        if summary.remaining_amount > payments_service.EPSILON:
            text = (
                "Kontrakt bo'yicha qarzdorlik: "
                f"{payments_service.format_amount(summary.remaining_amount)} "
                "to'lanmagan. To'lov jadvali bilan tanishing "
                "(ichki tartib nizomi, 5-bo'lim)."
            )
            written += write_notification(
                db, user.id, PAYMENT_DEBT, text, LINK_CONTRACT, None, match_text=False
            )
    else:
        summary = payments_service.group_payment_summary(db, user)
        debtors = [row for row in summary.rows if row.remaining_amount > 0]
        if debtors:
            text = (
                f"Guruhingizda {len(debtors)} ta talaba kontrakt bo'yicha "
                "qarzdor — jami "
                f"{payments_service.format_amount(summary.remaining_amount)}. "
                "Ro'yxatni guruh sahifasida ko'ring."
            )
            written += write_notification(
                db, user.id, PAYMENT_DEBT, text, LINK_CONTRACT, None, match_text=False
            )
    if written:
        db.commit()
    return written


def record_flow_due_notifications(db: Session, user: User) -> int:
    """Execution deadline near or passed -> executor **and** sender (3.10).

    No new query is written: `services/docflow` already computes `overdue` and
    `due_in_days` for both boxes (S11). The wording deliberately carries no
    "N kun qoldi" counter — otherwise every day would produce a new row; this
    way one document yields at most one "yaqin" and one "o'tdi" notification.
    """
    from app.services import docflow as docflow_service

    written = 0
    for listing in (docflow_service.inbox(db, user), docflow_service.outbox(db, user)):
        for row in listing.rows:
            if row.due_date is None or row.status in docflow_service.TERMINAL_STATUSES:
                continue
            due = row.due_date.strftime("%d.%m.%Y")
            if row.overdue:
                text = (
                    f"Ijro muddati o'tdi: {row.title} (№{row.id}) — "
                    f"muddat {due} edi."
                )
            elif (
                row.due_in_days is not None
                and 0 <= row.due_in_days <= docflow_service.DUE_SOON_DAYS
            ):
                text = f"Ijro muddati yaqin: {row.title} (№{row.id}) — {due} gacha."
            else:
                continue
            written += write_notification(
                db, user.id, FLOW_DUE, text, LINK_FLOW, row.id
            )
    if written:
        db.commit()
    return written


def refresh_triggers(db: Session, user: User) -> int:
    """Everything that is computed rather than pushed (see module docstring)."""
    return record_debt_notifications(db, user) + record_flow_due_notifications(db, user)


# --- chat formatting (used by the `bildirishnomalar` tool) -------------------


def format_feed_for_tool(view: NotificationFeed) -> str:
    """Source line first (domain rule 5), then the unread digest."""
    lines = [
        view.source.get("label", "Bildirishnomalar ro'yxati"),
        f"O'qilmagan: {view.unread_count} ta (jami {view.total} ta).",
    ]
    if not view.rows:
        lines.append(
            "Yangi bildirishnoma yo'q."
            if view.unread_only
            else "Bildirishnomalar yo'q."
        )
        return "\n".join(lines)

    for row in view.rows:
        mark = "•" if not row.is_read else " "
        lines.append(
            f"{mark} [{row.type_label}] {row.text} "
            f"({row.created_at.strftime('%d.%m.%Y %H:%M')})"
        )
    if view.unread_only and view.unread_count > len(view.rows):
        lines.append(f"... yana {view.unread_count - len(view.rows)} ta o'qilmagan.")
    return "\n".join(lines)
