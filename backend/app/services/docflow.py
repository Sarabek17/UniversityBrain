"""Document flow service (S11): applications, reports and orders.

The problem in one sentence: the student walks to the dean's office to ask
where their application is, the teacher hands the report over on paper, and the
registrar does not know who is holding which document. Here every document has
a **status chain** and a history, and both sides read the same rows:

    yuborildi -> ko'rildi -> ijroda -> tasdiqlandi / rad etildi (sabab bilan)

Three rules keep the module honest:

1. **Templates are code, not a table.** `TEMPLATES` below is the whole catalogue
   (`FlowDocument.template_id` is just that string). The seed uses four of them;
   `akademik_tatil` is the fifth, added here without touching the seed.
2. **Scope is never re-invented.** Visibility comes from `auth/rbac.py`
   (`can_access_user`): the sender always sees their own document, a named
   recipient always sees theirs, and a role-addressed document (e.g. "to the
   dean's office") is visible to that role *inside the sender's faculty*.
   Anything else does not exist for the caller — the router answers **404**, so
   the existence of a stranger's application is not disclosed either.
3. **Every status change writes both a `FlowHistory` row and a
   `Notification`** (`flow_status` to the sender, `flow_incoming` to the
   recipients on creation), with the same duplicate guard S10 uses.

Transitions are checked, not trusted: an approved/rejected document is final,
and a rejection without a reason is refused (422).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.agents.orchestrator import DISCLAIMER
from app.auth.rbac import can_access_user
from app.models import (
    FlowDocument,
    FlowDocumentType,
    FlowHistory,
    FlowStatus,
    Notification,
    User,
    UserRole,
)
from app.services import summarization

FLOW_SOURCE_TYPE = "flow_document"

STATUS_NOTIF = "flow_status"  # sender: "your application moved"
INCOMING_NOTIF = "flow_incoming"  # recipient: "a new document arrived"

DOC_TYPE_LABELS: dict[FlowDocumentType, str] = {
    FlowDocumentType.application: "Ariza",
    FlowDocumentType.report: "Hisobot",
    FlowDocumentType.order: "Buyruq",
    FlowDocumentType.letter: "Xat",
}

STATUS_LABELS: dict[FlowStatus, str] = {
    FlowStatus.sent: "yuborildi",
    FlowStatus.seen: "ko'rildi",
    FlowStatus.in_progress: "ijroda",
    FlowStatus.approved: "tasdiqlandi",
    FlowStatus.rejected: "rad etildi",
}

ROLE_LABELS: dict[UserRole, str] = {
    UserRole.student: "Talaba",
    UserRole.teacher: "O'qituvchi",
    UserRole.tutor: "Tyutor",
    UserRole.staff: "Dekanat",
    UserRole.admin: "Admin",
}

# The chain only moves forward: an approved or rejected document is closed.
TRANSITIONS: dict[FlowStatus, tuple[FlowStatus, ...]] = {
    FlowStatus.sent: (
        FlowStatus.seen,
        FlowStatus.in_progress,
        FlowStatus.approved,
        FlowStatus.rejected,
    ),
    FlowStatus.seen: (
        FlowStatus.in_progress,
        FlowStatus.approved,
        FlowStatus.rejected,
    ),
    FlowStatus.in_progress: (FlowStatus.approved, FlowStatus.rejected),
    FlowStatus.approved: (),
    FlowStatus.rejected: (),
}

TERMINAL_STATUSES = (FlowStatus.approved, FlowStatus.rejected)
# A refusal a person cannot read is worse than no answer at all.
REASON_REQUIRED = (FlowStatus.rejected,)

OPEN_STATUSES = (FlowStatus.sent, FlowStatus.seen, FlowStatus.in_progress)

MIN_BODY_CHARS = 10
PREVIEW_CHARS = 180
DUE_SOON_DAYS = 3  # "muddati yaqin" threshold used by the staff sorting

SORT_NEW = "new"  # newest first (default)
SORT_DUE = "due"  # closest execution deadline first
SORTS = (SORT_NEW, SORT_DUE)

BOX_INBOX = "inbox"
BOX_OUTBOX = "outbox"


# --- templates (the whole catalogue; no separate table) ----------------------


@dataclass(frozen=True)
class FlowTemplate:
    id: str
    title: str
    description: str
    doc_type: FlowDocumentType
    roles: tuple[UserRole, ...]  # who may send it
    recipient_role: UserRole | None = UserRole.staff
    needs_recipient_user: bool = False  # addressed to a person, not a role
    needs_due_date: bool = False
    body_hint: str = ""

    def is_allowed_for(self, role: UserRole) -> bool:
        return role == UserRole.admin or role in self.roles


TEMPLATES: tuple[FlowTemplate, ...] = (
    FlowTemplate(
        id="malumotnoma",
        title="O'qish joyidan ma'lumotnoma",
        description="Ma'lumotnoma so'rovi — dekanatga.",
        doc_type=FlowDocumentType.application,
        roles=(UserRole.student,),
        body_hint=(
            "Dekanatga [guruh] guruhi talabasidan.\n\nARIZA\n\n"
            "Menga o'qish joyimdan ma'lumotnoma berishingizni so'rayman. "
            "Ma'lumotnoma [qayerga taqdim etish uchun] kerak."
        ),
    ),
    FlowTemplate(
        id="akademik_tatil",
        title="Akademik ta'til so'rovi",
        description="Akademik ta'til berish to'g'risida ariza — dekanatga.",
        doc_type=FlowDocumentType.application,
        roles=(UserRole.student,),
        body_hint=(
            "Dekanatga [guruh] guruhi talabasidan.\n\nARIZA\n\n"
            "Sog'lig'im holati sababli (tibbiy ma'lumotnoma ilova qilinadi) "
            "menga [muddat] muddatga akademik ta'til berishingizni so'rayman."
        ),
    ),
    FlowTemplate(
        id="qayta_topshirish",
        title="Qayta topshirishga ruxsat",
        description="Nazoratni qayta topshirish uchun ariza — dekanatga.",
        doc_type=FlowDocumentType.application,
        roles=(UserRole.student,),
        body_hint=(
            "Dekanatga [guruh] guruhi talabasidan.\n\nARIZA\n\n"
            "'[fan]' fanidan oraliq nazoratni [sabab] sababli qayta "
            "topshirishga ruxsat berishingizni so'rayman."
        ),
    ),
    FlowTemplate(
        id="semestr_hisobot",
        title="Semestr yakuniy hisoboti",
        description="O'qituvchining semestr hisoboti — dekanatga.",
        doc_type=FlowDocumentType.report,
        roles=(UserRole.teacher,),
        body_hint=(
            "Dekanatga o'qituvchidan.\n\n"
            "[o'quv yili] o'quv yili [semestr] semestri bo'yicha '[fan]' "
            "fanidan yakuniy hisobot: o'zlashtirish [foiz]%, qayta "
            "topshirishga qolganlar [son] nafar."
        ),
    ),
    FlowTemplate(
        id="buyruq_topshiriq",
        title="Buyruq asosidagi topshiriq",
        description="Dekanatdan aniq shaxsga topshiriq — ijro muddati bilan.",
        doc_type=FlowDocumentType.order,
        roles=(UserRole.staff,),
        recipient_role=None,
        needs_recipient_user=True,
        needs_due_date=True,
        body_hint=(
            "[Ism]ga.\n\nRektorning [raqam]-son buyrug'iga asosan "
            "[nima qilish kerak] dekanatga topshirishingiz so'raladi."
        ),
    ),
)

TEMPLATES_BY_ID: dict[str, FlowTemplate] = {t.id: t for t in TEMPLATES}


class DocflowError(RuntimeError):
    """Base class: the router maps these onto HTTP codes, the tool onto text."""


class UnknownTemplateError(DocflowError):
    """No such template id in `TEMPLATES`."""


class TemplateNotAllowedError(DocflowError):
    """This role may not send that template (a student cannot issue an order)."""


class EmptyBodyError(DocflowError):
    """The document body is empty or too short to be a real application."""


class InvalidRecipientError(DocflowError):
    """The named recipient does not exist or is outside the sender's scope."""


class NotRecipientError(DocflowError):
    """Only the recipient may move the status (403)."""


class InvalidTransitionError(DocflowError):
    """The status chain does not allow this step (e.g. approved -> seen)."""


class ReasonRequiredError(DocflowError):
    """A rejection must carry a reason."""


# --- data shapes ------------------------------------------------------------


@dataclass
class FlowHistoryItem:
    id: int
    status: FlowStatus
    status_label: str
    comment: str | None
    timestamp: datetime
    changed_by_id: int
    changed_by_name: str


@dataclass
class FlowItem:
    """One row of an inbox/outbox list."""

    id: int
    doc_type: FlowDocumentType
    doc_type_label: str
    template_id: str | None
    title: str
    sender_id: int
    sender_name: str
    sender_role: UserRole
    recipient_role: UserRole | None
    recipient_user_id: int | None
    recipient_label: str
    status: FlowStatus
    status_label: str
    created_at: datetime
    updated_at: datetime
    due_date: date | None
    due_in_days: int | None
    overdue: bool
    is_incoming: bool
    is_outgoing: bool
    can_change_status: bool
    last_comment: str | None
    preview: str


@dataclass
class FlowDetail(FlowItem):
    """One document with its whole history — what both sides see."""

    body_text: str = ""
    history: list[FlowHistoryItem] = field(default_factory=list)
    next_statuses: list[FlowStatus] = field(default_factory=list)
    source: dict = field(default_factory=dict)
    disclaimer: str = DISCLAIMER


@dataclass
class FlowList:
    box: str
    sort: str
    rows: list[FlowItem] = field(default_factory=list)
    total: int = 0
    new_count: int = 0  # incoming and still `sent` (nobody opened it)
    open_count: int = 0  # not approved/rejected yet
    overdue_count: int = 0
    due_soon_count: int = 0
    source: dict = field(default_factory=dict)
    disclaimer: str = DISCLAIMER


@dataclass
class FlowSummary:
    flow_id: int
    title: str
    summary: str
    parts: int
    llm_calls: int
    truncated: bool
    source: dict = field(default_factory=dict)
    disclaimer: str = DISCLAIMER


# --- helpers ----------------------------------------------------------------


def get_template(template_id: str | None) -> FlowTemplate | None:
    return TEMPLATES_BY_ID.get((template_id or "").strip())


def templates_for(user: User) -> list[FlowTemplate]:
    return [t for t in TEMPLATES if t.is_allowed_for(user.role)]


def template_title(flow: FlowDocument) -> str:
    template = get_template(flow.template_id)
    if template is not None:
        return template.title
    return DOC_TYPE_LABELS.get(flow.doc_type, "Hujjat")


def doc_type_label(flow: FlowDocument) -> str:
    return DOC_TYPE_LABELS.get(flow.doc_type, "Hujjat")


def status_label(status: FlowStatus) -> str:
    return STATUS_LABELS.get(status, status.value)


def _preview(text: str) -> str:
    body = " ".join((text or "").split())
    if len(body) <= PREVIEW_CHARS:
        return body
    return body[:PREVIEW_CHARS].rstrip() + "…"


def get_flow(db: Session, flow_id: int) -> FlowDocument | None:
    return db.get(FlowDocument, flow_id)


def history_of(db: Session, flow: FlowDocument) -> list[FlowHistory]:
    return (
        db.query(FlowHistory)
        .filter(FlowHistory.flow_document_id == flow.id)
        .order_by(FlowHistory.timestamp, FlowHistory.id)
        .all()
    )


def _user_names(db: Session, user_ids: set[int]) -> dict[int, User]:
    if not user_ids:
        return {}
    rows = db.query(User).filter(User.id.in_(user_ids)).all()
    return {row.id: row for row in rows}


# --- who may see / act ------------------------------------------------------


def is_recipient(db: Session, user: User, flow: FlowDocument) -> bool:
    """Is this document addressed to `user` — personally or through their role?"""
    if user.role == UserRole.admin:
        return True
    if flow.recipient_user_id is not None:
        return flow.recipient_user_id == user.id
    if flow.recipient_role is None or flow.recipient_role != user.role:
        return False
    sender = db.get(User, flow.sender_id)
    # Role-addressed documents stay inside the sender's faculty: the dean of
    # faculty 2 never sees an application written in faculty 1.
    return sender is not None and can_access_user(db, user, sender)


def can_view(db: Session, user: User, flow: FlowDocument) -> bool:
    return flow.sender_id == user.id or is_recipient(db, user, flow)


def get_visible_flow(db: Session, user: User, flow_id: int) -> FlowDocument | None:
    """The document if the caller may see it, else None (router -> 404)."""
    flow = get_flow(db, flow_id)
    if flow is None or not can_view(db, user, flow):
        return None
    return flow


def can_change_status(db: Session, user: User, flow: FlowDocument) -> bool:
    return flow.status not in TERMINAL_STATUSES and is_recipient(db, user, flow)


def next_statuses(db: Session, user: User, flow: FlowDocument) -> list[FlowStatus]:
    if not can_change_status(db, user, flow):
        return []
    return list(TRANSITIONS.get(flow.status, ()))


def recipients_of(db: Session, flow: FlowDocument) -> list[User]:
    """Everyone who will find this document in their inbox."""
    if flow.recipient_user_id is not None:
        person = db.get(User, flow.recipient_user_id)
        return [person] if person is not None else []
    if flow.recipient_role is None:
        return []
    sender = db.get(User, flow.sender_id)
    if sender is None:
        return []
    people = db.query(User).filter(User.role == flow.recipient_role).all()
    return [p for p in people if can_access_user(db, p, sender)]


def recipient_label(db: Session, flow: FlowDocument) -> str:
    if flow.recipient_user_id is not None:
        person = db.get(User, flow.recipient_user_id)
        return person.full_name if person is not None else "Noma'lum"
    if flow.recipient_role is not None:
        return ROLE_LABELS.get(flow.recipient_role, flow.recipient_role.value)
    return "Noma'lum"


# --- sources ----------------------------------------------------------------


def flow_source(flow: FlowDocument) -> dict:
    """The mandatory citation: "Ariza №5, 12.08.2026, holat: tasdiqlandi"."""
    label = (
        f"{doc_type_label(flow)} №{flow.id}, "
        f"{flow.created_at.strftime('%d.%m.%Y')}, "
        f"holat: {status_label(flow.status)}"
    )
    return {"type": FLOW_SOURCE_TYPE, "label": label}


def list_source(box: str, count: int) -> dict:
    where = "kelgan hujjatlar" if box == BOX_INBOX else "yuborilgan hujjatlar"
    return {
        "type": FLOW_SOURCE_TYPE,
        "label": f"Hujjat aylanmasi — {where} ({count} ta)",
    }


# --- building the view models ----------------------------------------------


def build_item(
    db: Session,
    user: User,
    flow: FlowDocument,
    *,
    history: list[FlowHistory] | None = None,
    people: dict[int, User] | None = None,
    today: date | None = None,
) -> FlowItem:
    rows = history if history is not None else history_of(db, flow)
    known = people or {}
    sender = known.get(flow.sender_id) or db.get(User, flow.sender_id)
    last = rows[-1] if rows else None
    day = today or date.today()

    due_in = (flow.due_date - day).days if flow.due_date is not None else None
    overdue = (
        due_in is not None and due_in < 0 and flow.status not in TERMINAL_STATUSES
    )
    return FlowItem(
        id=flow.id,
        doc_type=flow.doc_type,
        doc_type_label=doc_type_label(flow),
        template_id=flow.template_id,
        title=template_title(flow),
        sender_id=flow.sender_id,
        sender_name=sender.full_name if sender else "Noma'lum",
        sender_role=sender.role if sender else UserRole.student,
        recipient_role=flow.recipient_role,
        recipient_user_id=flow.recipient_user_id,
        recipient_label=recipient_label(db, flow),
        status=flow.status,
        status_label=status_label(flow.status),
        created_at=flow.created_at,
        updated_at=last.timestamp if last else flow.created_at,
        due_date=flow.due_date,
        due_in_days=due_in,
        overdue=overdue,
        is_incoming=is_recipient(db, user, flow),
        is_outgoing=flow.sender_id == user.id,
        can_change_status=can_change_status(db, user, flow),
        last_comment=last.comment if last else None,
        preview=_preview(flow.body_text),
    )


def flow_detail(db: Session, user: User, flow: FlowDocument) -> FlowDetail:
    rows = history_of(db, flow)
    people = _user_names(db, {flow.sender_id} | {r.changed_by_id for r in rows})
    item = build_item(db, user, flow, history=rows, people=people)
    detail = FlowDetail(**item.__dict__)
    detail.body_text = flow.body_text
    detail.history = [
        FlowHistoryItem(
            id=row.id,
            status=row.status,
            status_label=status_label(row.status),
            comment=row.comment,
            timestamp=row.timestamp,
            changed_by_id=row.changed_by_id,
            changed_by_name=(
                people[row.changed_by_id].full_name
                if row.changed_by_id in people
                else "Noma'lum"
            ),
        )
        for row in rows
    ]
    detail.next_statuses = next_statuses(db, user, flow)
    detail.source = flow_source(flow)
    return detail


def sort_rows(rows: list[FlowItem], sort: str) -> list[FlowItem]:
    """`new` — newest first; `due` — closest execution deadline first."""
    if sort == SORT_DUE:
        # No deadline goes last; among equals the newest first.
        return sorted(
            rows,
            key=lambda r: (
                r.due_date is None,
                r.due_date or date.max,
                -r.created_at.timestamp(),
            ),
        )
    return sorted(rows, key=lambda r: (r.created_at, r.id), reverse=True)


def _listing(
    db: Session, user: User, flows: list[FlowDocument], box: str, sort: str
) -> FlowList:
    people = _user_names(db, {f.sender_id for f in flows})
    today = date.today()
    rows = [build_item(db, user, f, people=people, today=today) for f in flows]
    rows = sort_rows(rows, sort if sort in SORTS else SORT_NEW)
    listing = FlowList(
        box=box,
        sort=sort if sort in SORTS else SORT_NEW,
        rows=rows,
        total=len(rows),
        new_count=sum(1 for r in rows if r.is_incoming and r.status == FlowStatus.sent),
        open_count=sum(1 for r in rows if r.status in OPEN_STATUSES),
        overdue_count=sum(1 for r in rows if r.overdue),
        due_soon_count=sum(
            1
            for r in rows
            if r.due_in_days is not None
            and 0 <= r.due_in_days <= DUE_SOON_DAYS
            and r.status not in TERMINAL_STATUSES
        ),
    )
    listing.source = list_source(box, len(rows))
    return listing


def inbox(db: Session, user: User, sort: str = SORT_NEW) -> FlowList:
    """Documents addressed to the caller — personally or through their role."""
    query = db.query(FlowDocument)
    if user.role != UserRole.admin:
        query = query.filter(
            or_(
                FlowDocument.recipient_user_id == user.id,
                FlowDocument.recipient_role == user.role,
            )
        )
    flows = [f for f in query.all() if is_recipient(db, user, f)]
    return _listing(db, user, flows, BOX_INBOX, sort)


def outbox(db: Session, user: User, sort: str = SORT_NEW) -> FlowList:
    """Documents the caller sent — "Arizalarim" for a student."""
    flows = db.query(FlowDocument).filter(FlowDocument.sender_id == user.id).all()
    return _listing(db, user, flows, BOX_OUTBOX, sort)


def recipient_candidates(db: Session, user: User) -> list[User]:
    """Who a staff order may be addressed to: staff of the caller's scope."""
    people = (
        db.query(User)
        .filter(User.role.in_((UserRole.teacher, UserRole.tutor, UserRole.staff)))
        .order_by(User.full_name)
        .all()
    )
    return [p for p in people if p.id != user.id and can_access_user(db, user, p)]


# --- notifications ----------------------------------------------------------


def _write_notification(
    db: Session,
    user_id: int,
    notif_type: str,
    text: str,
    link_id: int,
    *,
    match_text: bool = True,
) -> bool:
    """Write one notification unless an equivalent row already exists.

    Same guard as S10's `record_risk_notifications`, with one twist: a document
    *arrives* exactly once, so `flow_incoming` is keyed on (user, type, link)
    alone — that is how the rows the seed already wrote are recognised even
    though their wording differs. A *status* step is keyed on the text too, so
    a genuine second step is never swallowed.
    """
    query = db.query(Notification.id).filter(
        Notification.user_id == user_id,
        Notification.notif_type == notif_type,
        Notification.link_type == FLOW_SOURCE_TYPE,
        Notification.link_id == link_id,
    )
    if match_text:
        query = query.filter(Notification.text == text)
    exists = query.first()
    if exists is not None:
        return False
    db.add(
        Notification(
            user_id=user_id,
            notif_type=notif_type,
            text=text,
            link_type=FLOW_SOURCE_TYPE,
            link_id=link_id,
        )
    )
    return True


def incoming_text(db: Session, flow: FlowDocument) -> str:
    sender = db.get(User, flow.sender_id)
    who = sender.full_name if sender else "Noma'lum"
    text = (
        f"Yangi {doc_type_label(flow).lower()} keldi: {who} — "
        f"{template_title(flow)}."
    )
    if flow.due_date is not None:
        text += f" Ijro muddati: {flow.due_date.strftime('%d.%m.%Y')}."
    return text


def status_text(flow: FlowDocument, comment: str | None) -> str:
    text = (
        f"{doc_type_label(flow)} №{flow.id} holati: {status_label(flow.status)} — "
        f"{template_title(flow)}."
    )
    if comment:
        text += f" Izoh: {comment}"
    return text


def notify_incoming(db: Session, flow: FlowDocument) -> int:
    """Recipients learn that a document arrived (FUNKSIONALLIK 3.10)."""
    written = 0
    for person in recipients_of(db, flow):
        if person.id == flow.sender_id:
            continue
        written += _write_notification(
            db,
            person.id,
            INCOMING_NOTIF,
            incoming_text(db, flow),
            flow.id,
            match_text=False,
        )
    return written


def notify_status(db: Session, flow: FlowDocument, actor: User, comment: str | None) -> int:
    """The sender learns that their document moved."""
    if flow.sender_id == actor.id:
        return 0
    return int(
        _write_notification(
            db, flow.sender_id, STATUS_NOTIF, status_text(flow, comment), flow.id
        )
    )


# --- the flow ---------------------------------------------------------------


def create_flow(
    db: Session,
    sender: User,
    *,
    template_id: str,
    body_text: str,
    recipient_user_id: int | None = None,
    due_date: date | None = None,
) -> FlowDocument:
    """Send a document built from a template. Writes history + notifications."""
    template = get_template(template_id)
    if template is None:
        raise UnknownTemplateError(template_id)
    if not template.is_allowed_for(sender.role):
        raise TemplateNotAllowedError(template.title)

    body = (body_text or "").strip()
    if len(body) < MIN_BODY_CHARS:
        raise EmptyBodyError(f"matn juda qisqa (kamida {MIN_BODY_CHARS} belgi)")

    recipient: User | None = None
    if template.needs_recipient_user:
        if recipient_user_id is None:
            raise InvalidRecipientError("qabul qiluvchi tanlanmagan")
        recipient = db.get(User, recipient_user_id)
        if recipient is None or not can_access_user(db, sender, recipient):
            raise InvalidRecipientError("qabul qiluvchi doirangizga kirmaydi")

    now = datetime.now()
    flow = FlowDocument(
        doc_type=template.doc_type,
        template_id=template.id,
        sender_id=sender.id,
        recipient_role=None if recipient else template.recipient_role,
        recipient_user_id=recipient.id if recipient else None,
        body_text=body,
        due_date=due_date if template.needs_due_date else None,
        status=FlowStatus.sent,
        created_at=now,
    )
    db.add(flow)
    db.flush()
    db.add(
        FlowHistory(
            flow_document_id=flow.id,
            status=FlowStatus.sent,
            comment=None,
            timestamp=now,
            changed_by_id=sender.id,
        )
    )
    notify_incoming(db, flow)
    db.commit()
    db.refresh(flow)
    return flow


def change_status(
    db: Session,
    actor: User,
    flow: FlowDocument,
    new_status: FlowStatus,
    comment: str | None = None,
) -> FlowDocument:
    """Move the document along the chain: history + notification, always."""
    if not is_recipient(db, actor, flow):
        raise NotRecipientError(flow.id)
    allowed = TRANSITIONS.get(flow.status, ())
    if new_status not in allowed:
        raise InvalidTransitionError(
            f"{status_label(flow.status)} -> {status_label(new_status)}"
        )
    text = (comment or "").strip() or None
    if new_status in REASON_REQUIRED and not text:
        raise ReasonRequiredError("rad etish sababi ko'rsatilmagan")

    flow.status = new_status
    db.add(
        FlowHistory(
            flow_document_id=flow.id,
            status=new_status,
            comment=text,
            timestamp=datetime.now(),
            changed_by_id=actor.id,
        )
    )
    notify_status(db, flow, actor, text)
    db.commit()
    db.refresh(flow)
    return flow


def summarize_flow(db: Session, user: User, flow: FlowDocument) -> FlowSummary:
    """Role-angled summary of an incoming document — S6 service, no new prompts.

    `summarize_text` is the same code path `POST /documents/{id}/summary` uses;
    only the body of the flow document is handed to it instead of a file.
    """
    title = f"{doc_type_label(flow)} №{flow.id} — {template_title(flow)}"
    summary, parts, calls, truncated = summarization.summarize_text(
        flow.body_text,
        title=title,
        doc_type=flow.doc_type.value,
        language=user.language or "uz",
        role=user.role,
    )
    return FlowSummary(
        flow_id=flow.id,
        title=title,
        summary=summary or "Rezyume tayyorlanmadi.",
        parts=parts,
        llm_calls=calls,
        truncated=truncated,
        source=flow_source(flow),
    )


# --- chat formatting (used by the `ariza_holati` tool) ----------------------


def find_flow(db: Session, user: User, query: str) -> FlowDocument | None:
    """Find one visible document by id or by keyword. Invisible -> None.

    A stranger's application is never disclosed: an id the caller may not see
    answers exactly like an id that does not exist.
    """
    asked = (query or "").strip()
    if not asked:
        return None
    if asked.isdigit():
        return get_visible_flow(db, user, int(asked))

    needle = asked.lower()
    candidates = [
        f
        for f in db.query(FlowDocument).order_by(FlowDocument.created_at.desc()).all()
        if can_view(db, user, f)
    ]
    for flow in candidates:
        haystack = " ".join(
            filter(
                None,
                (
                    template_title(flow).lower(),
                    (flow.template_id or "").lower(),
                    doc_type_label(flow).lower(),
                ),
            )
        )
        if needle in haystack:
            return flow
    for flow in candidates:
        if needle in (flow.body_text or "").lower():
            return flow
    return None


def default_box(user: User) -> str:
    """A student asks "where is my application", a dean "what came in"."""
    if user.role in (UserRole.student, UserRole.teacher):
        return BOX_OUTBOX
    return BOX_INBOX


def overview(db: Session, user: User, box: str | None = None) -> FlowList:
    chosen = (box or "").strip().lower() or default_box(user)
    if chosen not in (BOX_INBOX, BOX_OUTBOX):
        chosen = default_box(user)
    return inbox(db, user) if chosen == BOX_INBOX else outbox(db, user)


def format_flow_for_tool(detail: FlowDetail) -> str:
    """Exact status + source, the way the agent must report it."""
    lines = [
        f"{detail.doc_type_label} №{detail.id}, "
        f"{detail.created_at.strftime('%d.%m.%Y')}, "
        f"holat: {detail.status_label}",
        f"  Mavzu: {detail.title}",
        f"  Yuboruvchi: {detail.sender_name} "
        f"({ROLE_LABELS.get(detail.sender_role, detail.sender_role.value)}) "
        f"-> {detail.recipient_label}",
    ]
    if detail.due_date is not None:
        due = detail.due_date.strftime("%d.%m.%Y")
        if detail.overdue:
            lines.append(f"  Ijro muddati: {due} — muddat o'tgan!")
        else:
            lines.append(
                f"  Ijro muddati: {due}"
                + (
                    f" ({detail.due_in_days} kun qoldi)"
                    if detail.due_in_days is not None
                    else ""
                )
            )
    if detail.history:
        chain = " -> ".join(
            f"{h.status_label} ({h.timestamp.strftime('%d.%m')})"
            for h in detail.history
        )
        lines.append(f"  Tarix: {chain}")
        last = detail.history[-1]
        lines.append(
            f"  Oxirgi o'zgarish: {last.timestamp.strftime('%d.%m.%Y %H:%M')}, "
            f"{last.changed_by_name}"
            + (f" — izoh: {last.comment}" if last.comment else "")
        )
    lines.append(f"(Manba: hujjat aylanmasi — {flow_label(detail)}.)")
    return "\n".join(lines)


def flow_label(detail: FlowDetail) -> str:
    return (
        f"{detail.doc_type_label} №{detail.id}, "
        f"{detail.created_at.strftime('%d.%m.%Y')}, "
        f"holat: {detail.status_label}"
    )


MAX_TOOL_ROWS = 15


def format_flow_list_for_tool(listing: FlowList) -> str:
    where = "Kelgan hujjatlar" if listing.box == BOX_INBOX else "Yuborilgan hujjatlar"
    if not listing.rows:
        return (
            f"{where}: yozuv yo'q — hujjat aylanmasida sizga tegishli hujjat "
            "topilmadi."
        )
    lines = [
        f"{where}: {listing.total} ta (ochiq {listing.open_count}, "
        f"yangi {listing.new_count})."
    ]
    if listing.overdue_count:
        lines.append(f"Muddati o'tgan: {listing.overdue_count} ta.")
    if listing.due_soon_count:
        lines.append(
            f"Muddati yaqin ({DUE_SOON_DAYS} kun ichida): {listing.due_soon_count} ta."
        )
    for row in listing.rows[:MAX_TOOL_ROWS]:
        line = (
            f"  {row.doc_type_label} №{row.id}, "
            f"{row.created_at.strftime('%d.%m.%Y')}, holat: {row.status_label} "
            f"— {row.title}"
        )
        if listing.box == BOX_INBOX:
            line += f" (yuboruvchi: {row.sender_name})"
        else:
            line += f" (qabul qiluvchi: {row.recipient_label})"
        if row.due_date is not None:
            line += f", muddat {row.due_date.strftime('%d.%m.%Y')}"
            if row.overdue:
                line += " — o'tgan!"
        if row.last_comment:
            line += f", izoh: {row.last_comment}"
        lines.append(line)
    lines.append(f"(Manba: hujjat aylanmasi — {listing.source['label']}.)")
    return "\n".join(lines)
