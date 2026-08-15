"""Pydantic schemas for the core objects. Response format source of truth."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.agents.orchestrator import DISCLAIMER as AGENT_DISCLAIMER
from app.models import (
    AccessLevel,
    AttendanceStatus,
    ChatRole,
    ClassSessionStatus,
    DocumentType,
    FlowDocumentType,
    FlowStatus,
    PaymentStatus,
    TurnstileDirection,
    UserRole,
)


class ORMSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HealthOut(BaseModel):
    status: str
    app: str


class UserOut(ORMSchema):
    id: int
    username: str
    full_name: str
    role: UserRole
    group_id: int | None
    faculty_id: int | None
    language: str


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class OkOut(BaseModel):
    status: str = "ok"


class GroupOut(ORMSchema):
    id: int
    name: str
    tutor_id: int | None
    faculty_id: int | None


class DocumentOut(ORMSchema):
    id: int
    title: str
    doc_type: DocumentType
    language: str
    access_level: AccessLevel
    file_path: str | None
    uploaded_at: datetime


class DocumentListItemOut(ORMSchema):
    """One row of GET /documents. `file_path` is internal and never exposed."""

    id: int
    title: str
    doc_type: DocumentType
    language: str
    access_level: AccessLevel
    uploaded_at: datetime


class DocumentDetailOut(DocumentListItemOut):
    """GET /documents/{id}: the same metadata plus the full text."""

    text: str


class ChunkOut(ORMSchema):
    id: int
    document_id: int
    text: str
    order_index: int


class TranslationOut(ORMSchema):
    id: int
    document_id: int | None
    chunk_id: int | None
    language: str
    translated_text: str
    created_at: datetime


class AssignmentOut(ORMSchema):
    id: int
    subject: str
    group_id: int
    description: str
    deadline: datetime
    teacher_id: int
    created_at: datetime


class ScheduleOut(ORMSchema):
    id: int
    group_id: int
    subject: str
    room: str
    weekday: int
    pair_number: int
    teacher_id: int


class ContractOut(ORMSchema):
    id: int
    student_id: int
    total_amount: float
    academic_year: str


class PaymentOut(ORMSchema):
    id: int
    student_id: int
    amount: float
    paid_at: datetime
    receipt_number: str | None
    receipt_file: str | None
    status: PaymentStatus
    academic_year: str


class TurnstileLogOut(ORMSchema):
    id: int
    user_id: int
    timestamp: datetime
    direction: TurnstileDirection


class AttendanceOut(ORMSchema):
    id: int
    student_id: int
    schedule_id: int
    date: date
    status: AttendanceStatus
    marked_by_teacher_id: int


class ClassSessionOut(ORMSchema):
    id: int
    schedule_id: int
    date: date
    status: ClassSessionStatus
    teacher_arrived_at: datetime | None


class FlowDocumentOut(ORMSchema):
    id: int
    doc_type: FlowDocumentType
    template_id: str | None
    sender_id: int
    recipient_role: UserRole | None
    recipient_user_id: int | None
    body_text: str
    file_path: str | None
    due_date: date | None
    status: FlowStatus
    created_at: datetime


class FlowHistoryOut(ORMSchema):
    id: int
    flow_document_id: int
    status: FlowStatus
    comment: str | None
    timestamp: datetime
    changed_by_id: int


# --- chat / agent (S4) ------------------------------------------------------


class ChatSource(BaseModel):
    """One citation. `type` says where it came from: document, schedule, ..."""

    type: str
    label: str
    document_id: int | None = None
    title: str | None = None
    heading: str | None = None
    order_index: int | None = None
    chunk_id: int | None = None


class DocumentSummaryOut(BaseModel):
    """POST /documents/{id}/summary (S6) — role-angled summary of one document.

    Defined here, next to `ChatSource`: a summary is a factual answer, so the
    domain rules require it to carry its citation and the "not an official
    document" notice, exactly like a chat answer does.
    """

    document_id: int
    title: str
    summary: str
    parts: int  # 1 = single LLM call, >1 = map-reduce over that many parts
    truncated: bool
    source: ChatSource
    disclaimer: str = AGENT_DISCLAIMER


class TranslationParagraph(BaseModel):
    """One aligned row of the side-by-side view (S7).

    The original travels with the translation, never instead of it — that is
    what lets the UI put them in the same row (domain rule 4).
    """

    index: int  # 1-based position in the document
    original: str
    translated: str


class DocumentTranslationOut(BaseModel):
    """POST /documents/{id}/translate (S7) — original + translation, aligned.

    `paragraphs` always has exactly as many rows as the document has
    paragraphs. `cached` is True when the answer came from the `translations`
    table (no LLM call was made).
    """

    document_id: int
    title: str
    source_language: str
    target_language: str
    paragraph_count: int
    paragraphs: list[TranslationParagraph]
    cached: bool
    truncated: bool
    same_language: bool  # document already in the target language
    source: ChatSource
    disclaimer: str = AGENT_DISCLAIMER


class ChatIn(BaseModel):
    message: str
    conversation_id: int | None = None


class ChatOut(BaseModel):
    conversation_id: int
    text: str
    sources: list[ChatSource] = []
    disclaimer: str


class ConversationOut(ORMSchema):
    id: int
    user_id: int
    title: str | None
    created_at: datetime


class ChatMessageOut(ORMSchema):
    id: int
    conversation_id: int
    role: ChatRole
    content: str
    tool_name: str | None
    sources: list[ChatSource] | None
    created_at: datetime


class ConversationDetailOut(ConversationOut):
    messages: list[ChatMessageOut] = []
    # Answers replayed from history must carry the same "not an official
    # document" notice as fresh ones, and the UI must never hardcode it.
    disclaimer: str = AGENT_DISCLAIMER


class NotificationOut(ORMSchema):
    id: int
    user_id: int
    notif_type: str
    text: str
    link_type: str | None
    link_id: int | None
    is_read: bool
    # Local time already: the row is stored in UTC, `services/notifications`
    # converts it so the bell shows the same clock as the rest of the app.
    created_at: datetime


class NotificationListOut(BaseModel):
    """The bell in one request (S12): the page **and** the unread counter.

    `type_label` is not sent — the UI names the types in `i18n/uz.json`, the
    same way it labels every other backend enum.
    """

    rows: list[NotificationOut] = []
    total: int = 0
    unread_count: int = 0
    unread_only: bool = False
    limit: int = 30


# --- payments (S8) ----------------------------------------------------------

# `state` is one of "paid" | "partial" | "debtor" (services/payments.py).
# An `uploaded` payment is pending, not paid: it sits in `pending_amount`
# until a tutor confirms it, so `remaining_amount = total - paid`.


class PaymentRowOut(ORMSchema):
    """One line of the payment history. The file path itself is never exposed."""

    id: int
    amount: float
    paid_at: datetime
    receipt_number: str | None
    status: PaymentStatus
    has_receipt_file: bool


class ContractSummaryOut(BaseModel):
    """GET /payments/contract[/{student_id}] — one student's contract state."""

    student_id: int
    username: str
    student_name: str
    group_id: int | None
    group_name: str | None
    academic_year: str
    total_amount: float
    paid_amount: float
    pending_amount: float
    remaining_amount: float
    paid_percent: int
    state: str
    last_payment_at: datetime | None
    payments: list[PaymentRowOut] = []
    source: ChatSource
    disclaimer: str = AGENT_DISCLAIMER


class GroupPaymentRowOut(BaseModel):
    """One student row of the tutor's group summary."""

    student_id: int
    username: str
    full_name: str
    group_id: int | None
    group_name: str | None
    total_amount: float
    paid_amount: float
    pending_amount: float
    remaining_amount: float
    paid_percent: int
    state: str
    last_payment_at: datetime | None
    pending_count: int


class GroupPaymentSummaryOut(BaseModel):
    """GET /payments/group — every student of the caller's groups, debts first."""

    group_ids: list[int]
    group_names: list[str]
    rows: list[GroupPaymentRowOut] = []
    total_amount: float
    paid_amount: float
    pending_amount: float
    remaining_amount: float
    debtor_count: int
    partial_count: int
    paid_count: int
    pending_count: int
    source: ChatSource
    disclaimer: str = AGENT_DISCLAIMER


class ReceiptOut(BaseModel):
    """GET /payments/{id}/receipt — structured receipt, not a file download.

    The demo data carries receipt paths but no image files, so this answers
    with the payment record itself and says so (`file_available=false`); it
    never 404s over a missing file.
    """

    payment_id: int
    student_id: int
    student_name: str
    receipt_number: str | None
    amount: float
    paid_at: datetime
    status: PaymentStatus
    academic_year: str
    method: str
    file_available: bool
    note: str
    source: ChatSource
    disclaimer: str = AGENT_DISCLAIMER


class ReceiptUploadIn(BaseModel):
    """POST /payments/receipts — student hands in a receipt (status=uploaded)."""

    amount: float
    receipt_number: str | None = None


# --- presence / attendance (S9) ---------------------------------------------

# `state` is one of "inside" | "left" | "not_arrived" (services/presence.py).
# Everything schedule-derived (`current_class.room`, `room`, `subject`) is an
# INFERENCE, never a measured fact: the UI shows it with "jadval bo'yicha"
# (domain rule 6) and `schedule_note` carries that sentence from the backend.


class PresenceClassOut(BaseModel):
    """The class someone is *supposed* to be in — read with `schedule_note`."""

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


class DayAttendanceOut(BaseModel):
    """Today's attendance over the pairs that already started."""

    total: int
    present: int
    late: int
    absent: int
    percent: int | None


class PresenceOut(BaseModel):
    """GET /attendance/presence[/{user_id}] — turnstile + schedule + journal."""

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
    current_class: PresenceClassOut | None
    next_class: PresenceClassOut | None
    attendance_status: AttendanceStatus | None
    attendance_marked: bool
    day: DayAttendanceOut
    summary: str
    schedule_note: str
    sources: list[ChatSource] = []
    disclaimer: str = AGENT_DISCLAIMER


class GroupPresenceRowOut(BaseModel):
    """One student row of the tutor's presence list."""

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


class GroupPresenceOut(BaseModel):
    """GET /attendance/group — who is inside, who is in class, who never came."""

    group_ids: list[int]
    group_names: list[str]
    at: datetime
    current_pair: int | None
    pair_label: str | None
    rows: list[GroupPresenceRowOut] = []
    inside_count: int
    left_count: int
    absent_count: int
    in_class_count: int
    attendance_percent: int | None
    schedule_note: str
    source: ChatSource
    disclaimer: str = AGENT_DISCLAIMER


class TeacherClassOut(BaseModel):
    """One row of the teacher's day: the class plus how far marking got."""

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


class TeacherDayOut(BaseModel):
    """GET /attendance/my-classes — the teacher's classes for one day."""

    date: date
    teacher_id: int
    teacher_name: str
    current_pair: int | None
    classes: list[TeacherClassOut] = []
    disclaimer: str = AGENT_DISCLAIMER


class RosterStudentOut(BaseModel):
    """One student on the marking sheet. `suggested` is the turnstile hint."""

    student_id: int
    username: str
    full_name: str
    status: AttendanceStatus | None
    suggested: AttendanceStatus
    state: str
    state_label: str
    entered_at: datetime | None
    left_at: datetime | None


class ClassRosterOut(BaseModel):
    """GET/POST /attendance/class/{schedule_id}[/mark] — the marking sheet."""

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
    students: list[RosterStudentOut] = []
    marked_count: int
    present_count: int
    late_count: int
    absent_count: int
    schedule_note: str
    source: ChatSource
    disclaimer: str = AGENT_DISCLAIMER


class AttendanceMarkIn(BaseModel):
    student_id: int
    status: AttendanceStatus


class AttendanceMarkRequest(BaseModel):
    """POST /attendance/class/{schedule_id}/mark — one click from the teacher."""

    marks: list[AttendanceMarkIn]
    # Named `on_date` (not `date`): a field called `date` would shadow the
    # `date` type in this class body.
    on_date: date | None = None  # default: today


class SubjectAttendanceOut(BaseModel):
    subject: str
    total: int
    attended: int
    absent: int
    percent: int


class AttendanceRowOut(BaseModel):
    date: date
    pair_number: int
    subject: str
    room: str
    status: AttendanceStatus
    status_label: str


class AttendanceSummaryOut(BaseModel):
    """GET /attendance/summary — one student's attendance over the last N days."""

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
    by_subject: list[SubjectAttendanceOut] = []
    recent: list[AttendanceRowOut] = []
    today: DayAttendanceOut
    source: ChatSource
    disclaimer: str = AGENT_DISCLAIMER


# --- S10: teacher attendance (dean's office) --------------------------------
# `state` here is a *derived* class state (held / late / at_risk /
# needs_clarification / upcoming / cancelled), not the stored DB enum — that one
# still travels as `session_status`.


class TeacherClassStateOut(BaseModel):
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
    state: str
    state_label: str
    teacher_arrived_at: datetime | None
    student_count: int
    marked_count: int
    present_count: int
    is_current: bool
    is_past: bool
    summary: str


class TeacherPresenceRowOut(BaseModel):
    teacher_id: int
    username: str
    full_name: str
    faculty_id: int | None
    state: str
    state_label: str
    in_building: bool
    entered_at: datetime | None
    left_at: datetime | None
    classes: list[TeacherClassStateOut] = []
    class_count: int
    held_count: int
    late_count: int
    at_risk_count: int
    unclear_count: int
    summary: str


class TeacherDayOverviewOut(BaseModel):
    """GET /attendance/teachers — today's teacher roll-call for the dean."""

    date: date
    at: datetime
    current_pair: int | None
    pair_label: str | None
    faculty_ids: list[int] = []
    rows: list[TeacherPresenceRowOut] = []
    teacher_count: int
    inside_count: int
    left_count: int
    absent_count: int
    class_count: int
    held_count: int
    late_count: int
    at_risk_count: int
    unclear_count: int
    schedule_note: str
    source: ChatSource
    disclaimer: str = AGENT_DISCLAIMER


class TeacherMonthRowOut(BaseModel):
    teacher_id: int
    username: str
    full_name: str
    total: int
    held: int
    late: int
    cancelled: int
    unclear: int
    percent: int | None


class TeacherMonthOut(BaseModel):
    """GET /attendance/teachers/monthly — held classes per teacher, in percent."""

    date_from: date
    date_to: date
    days: int
    rows: list[TeacherMonthRowOut] = []
    total: int
    held: int
    late: int
    cancelled: int
    unclear: int
    percent: int | None
    source: ChatSource
    disclaimer: str = AGENT_DISCLAIMER


# --- S11: document flow (ariza / hujjat aylanmasi) ---------------------------
# Templates are a code constant (`services/docflow.TEMPLATES`), not a table:
# `FlowDocument.template_id` is just that string.


class FlowTemplateOut(BaseModel):
    """One entry of the template catalogue, already filtered by role."""

    id: str
    title: str
    description: str
    doc_type: FlowDocumentType
    doc_type_label: str
    recipient_role: UserRole | None
    recipient_label: str
    needs_recipient_user: bool
    needs_due_date: bool
    body_hint: str


class FlowRecipientOut(BaseModel):
    """A person a staff order may be addressed to (inside the caller's scope)."""

    id: int
    full_name: str
    role: UserRole
    role_label: str


class FlowHistoryItemOut(BaseModel):
    id: int
    status: FlowStatus
    status_label: str
    comment: str | None
    timestamp: datetime
    changed_by_id: int
    changed_by_name: str


class FlowItemOut(BaseModel):
    """One row of an inbox / outbox list."""

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


class FlowDetailOut(FlowItemOut):
    """GET /docflow/{id} — the document with its whole status history."""

    body_text: str
    history: list[FlowHistoryItemOut] = []
    next_statuses: list[FlowStatus] = []
    source: ChatSource
    disclaimer: str = AGENT_DISCLAIMER


class FlowListOut(BaseModel):
    """GET /docflow/inbox | /docflow/outbox."""

    box: str  # "inbox" | "outbox"
    sort: str  # "new" | "due"
    rows: list[FlowItemOut] = []
    total: int
    new_count: int  # incoming and still `sent` — nobody opened it yet
    open_count: int  # not approved/rejected
    overdue_count: int
    due_soon_count: int
    source: ChatSource
    disclaimer: str = AGENT_DISCLAIMER


class FlowCreateRequest(BaseModel):
    template_id: str
    body_text: str
    recipient_user_id: int | None = None  # only for person-addressed templates
    due_date: date | None = None  # only for templates with an execution deadline


class FlowStatusRequest(BaseModel):
    status: FlowStatus
    comment: str | None = None  # mandatory when rejecting


class FlowSummaryOut(BaseModel):
    """POST /docflow/{id}/summary — S6 summarizer over the document body."""

    flow_id: int
    title: str
    summary: str
    parts: int
    truncated: bool
    source: ChatSource
    disclaimer: str = AGENT_DISCLAIMER


# --- S13: admin panel (users, uploads, stats, demo reset) --------------------


class AdminUserOut(ORMSchema):
    """One account in the admin user table."""

    id: int
    username: str
    full_name: str
    role: UserRole
    role_label: str
    group_id: int | None
    group_name: str | None
    faculty_id: int | None
    language: str
    created_at: datetime


class AdminUserCreateIn(BaseModel):
    """New account. Synthetic/demo data only (domain rule 1)."""

    username: str
    full_name: str
    role: UserRole
    password: str
    group_id: int | None = None
    faculty_id: int | None = None
    language: str = "uz"


class AdminUserUpdateIn(BaseModel):
    """Role change (the main use) and the other editable fields."""

    role: UserRole | None = None
    full_name: str | None = None
    group_id: int | None = None
    faculty_id: int | None = None
    language: str | None = None
    password: str | None = None


class AdminGroupOut(ORMSchema):
    """Group picker for the user form."""

    id: int
    name: str
    faculty_id: int | None


class AdminDocumentOut(ORMSchema):
    """A document plus its indexing state (`indexed` = found by search)."""

    id: int
    title: str
    doc_type: DocumentType
    language: str
    access_level: AccessLevel
    file_path: str | None
    uploaded_at: datetime
    chunk_count: int
    indexed: bool
    uploaded: bool  # admin upload (uploads/) vs. seed corpus


class AdminUploadOut(BaseModel):
    """POST /admin/documents — the document and how many chunks it produced."""

    document: AdminDocumentOut
    chunks: int
    message: str


class AdminRoleCountOut(ORMSchema):
    role: UserRole
    label: str
    count: int


class AdminUserStatsOut(ORMSchema):
    total: int
    by_role: list[AdminRoleCountOut]
    group_count: int
    faculty_count: int


class AdminCorpusStatsOut(ORMSchema):
    document_count: int
    indexed_count: int
    chunk_count: int
    uploaded_count: int


class AdminPaymentStatsOut(ORMSchema):
    student_count: int
    total_amount: float
    paid_amount: float
    pending_amount: float
    remaining_amount: float
    debtor_count: int
    partial_count: int
    paid_count: int
    pending_count: int


class AdminPresenceStatsOut(ORMSchema):
    at: datetime
    current_pair: int | None
    pair_label: str | None
    student_count: int
    inside_count: int
    left_count: int
    absent_count: int
    attendance_percent: int | None


class AdminTeacherStatsOut(ORMSchema):
    teacher_count: int
    inside_count: int
    absent_count: int
    class_count: int
    held_count: int
    at_risk_count: int
    unclear_count: int


class AdminDocflowStatsOut(ORMSchema):
    total: int
    new_count: int
    open_count: int
    overdue_count: int
    due_soon_count: int


class AdminNotificationStatsOut(ORMSchema):
    total: int
    unread_count: int


class AdminStatsOut(ORMSchema):
    """GET /admin/stats — every figure collected from the existing services."""

    generated_at: datetime
    users: AdminUserStatsOut
    corpus: AdminCorpusStatsOut
    payments: AdminPaymentStatsOut
    presence: AdminPresenceStatsOut
    teachers: AdminTeacherStatsOut
    docflow: AdminDocflowStatsOut
    notifications: AdminNotificationStatsOut
    source: ChatSource
    disclaimer: str = AGENT_DISCLAIMER


class AdminResetOut(ORMSchema):
    """State of the demo reset (POST /admin/reset, GET /admin/reset/status)."""

    running: bool
    started_at: datetime | None
    finished_at: datetime | None
    ok: bool | None
    message: str
    documents: int
    chunks: int
