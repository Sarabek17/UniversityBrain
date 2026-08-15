"""Payments service (S8): contract state, group summary, receipts.

The "receipt problem" in one place: a student sees their own contract without
digging through a bank app, a tutor sees the whole group without asking anyone
for a photo of a receipt.

Scope is never re-implemented here — it comes from `auth/rbac.py`
(`visible_group_ids`, `ensure_can_access_user`), so payments obey exactly the
same visibility rules as the rest of the project:

    student -> only themselves (another student's contract answers 403)
    tutor   -> their groups (Group.tutor_id)
    staff   -> their faculty
    admin   -> everything

Money rule (the only piece of arithmetic that matters): an `uploaded` payment
is *pending*, not paid — it counts towards `pending_amount` until a tutor
confirms it. `paid_amount` therefore only ever sums `automatic` + `confirmed`,
and `remaining_amount = total - paid`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from app.agents.orchestrator import DISCLAIMER
from app.auth.rbac import ensure_can_access_user, visible_group_ids
from app.models import Contract, Group, Payment, PaymentStatus, User, UserRole
from app.services import notifications

# --- payment state of one student -------------------------------------------

PAID = "paid"  # nothing left to pay
PARTIAL = "partial"  # something paid, something left
DEBTOR = "debtor"  # nothing paid at all

STATE_LABELS = {PAID: "to'langan", PARTIAL: "qisman to'langan", DEBTOR: "qarzdor"}

# Statuses that count as money actually received.
COUNTED_STATUSES = (PaymentStatus.automatic, PaymentStatus.confirmed)

# Rounding tolerance: contract totals are whole so'm, never fractions.
EPSILON = 0.5

RECEIPT_SOURCE_TYPE = "payment"

METHOD_LABELS = {
    PaymentStatus.automatic: "To'lov tizimi (Click/Payme) orqali avtomatik",
    PaymentStatus.uploaded: "Talaba yuklagan chek — tasdiq kutilmoqda",
    PaymentStatus.confirmed: "Talaba yuklagan chek — tyutor tasdiqlagan",
}

# Demo data carries receipt *paths* (`uploads/receipts/...`) but no real files,
# so the receipt view is structured data, never a file download (S8 decision).
RECEIPT_NOTE = (
    "Chek fayli demo ma'lumotda saqlanmagan — quyidagi ma'lumotlar to'lov "
    "yozuvidan olindi (chek raqami, sana, summa, holat)."
)


class PaymentsError(RuntimeError):
    """Base class: routers map these onto HTTP codes, tools onto tool errors."""


class NoContractError(PaymentsError):
    """The student has no contract row for any academic year."""


class OutOfScopeError(PaymentsError):
    """The requested group is outside the caller's RBAC scope."""


class InvalidAmountError(PaymentsError):
    """Receipt amount is not a positive number / exceeds what is left."""


class NotPendingError(PaymentsError):
    """Only an `uploaded` payment can be confirmed."""


# --- data shapes ------------------------------------------------------------


@dataclass
class PaymentRow:
    id: int
    amount: float
    paid_at: datetime
    receipt_number: str | None
    status: PaymentStatus
    has_receipt_file: bool


@dataclass
class ContractSummary:
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
    payments: list[PaymentRow] = field(default_factory=list)
    source: dict = field(default_factory=dict)
    disclaimer: str = DISCLAIMER


@dataclass
class GroupPaymentRow:
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


@dataclass
class GroupPaymentSummary:
    group_ids: list[int]
    group_names: list[str]
    rows: list[GroupPaymentRow]
    total_amount: float
    paid_amount: float
    pending_amount: float
    remaining_amount: float
    debtor_count: int
    partial_count: int
    paid_count: int
    pending_count: int
    source: dict = field(default_factory=dict)
    disclaimer: str = DISCLAIMER


@dataclass
class Receipt:
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
    source: dict = field(default_factory=dict)
    disclaimer: str = DISCLAIMER


# --- helpers ----------------------------------------------------------------


def format_amount(value: float) -> str:
    """`12000000` -> `"12 000 000 so'm"` (the exact numbers the demo shows)."""
    return f"{int(round(value)):,}".replace(",", " ") + " so'm"


def state_of(total: float, paid: float) -> str:
    if paid <= EPSILON:
        return DEBTOR
    if total - paid <= EPSILON:
        return PAID
    return PARTIAL


def _percent(total: float, paid: float) -> int:
    if total <= 0:
        return 100 if paid > 0 else 0
    return max(0, min(100, int(round(paid * 100 / total))))


def get_contract(db: Session, student: User) -> Contract | None:
    """The student's contract (latest academic year wins)."""
    return (
        db.query(Contract)
        .filter(Contract.student_id == student.id)
        .order_by(Contract.academic_year.desc(), Contract.id.desc())
        .first()
    )


def _payments_of(db: Session, student_ids: list[int]) -> dict[int, list[Payment]]:
    if not student_ids:
        return {}
    rows = (
        db.query(Payment)
        .filter(Payment.student_id.in_(student_ids))
        .order_by(Payment.paid_at, Payment.id)
        .all()
    )
    grouped: dict[int, list[Payment]] = {sid: [] for sid in student_ids}
    for row in rows:
        grouped.setdefault(row.student_id, []).append(row)
    return grouped


def _totals(payments: list[Payment]) -> tuple[float, float, datetime | None, int]:
    """(paid, pending, last counted payment time, pending count)."""
    paid = pending = 0.0
    last: datetime | None = None
    pending_count = 0
    for row in payments:
        amount = float(row.amount)
        if row.status in COUNTED_STATUSES:
            paid += amount
            if last is None or row.paid_at > last:
                last = row.paid_at
        else:
            pending += amount
            pending_count += 1
    return round(paid, 2), round(pending, 2), last, pending_count


def _group_names(db: Session, group_ids: set[int]) -> dict[int, str]:
    if not group_ids:
        return {}
    rows = db.query(Group.id, Group.name).filter(Group.id.in_(group_ids)).all()
    return {gid: name for gid, name in rows}


# --- citations (domain rule 5: every factual answer names its source) --------


def contract_source(summary: ContractSummary) -> dict:
    label = f"To'lov jadvali — kontrakt {summary.academic_year}"
    if summary.payments:
        last = summary.payments[-1]
        if last.receipt_number:
            label += f", oxirgi chek {last.receipt_number}"
        label += f", {last.paid_at.strftime('%d.%m.%Y')}"
    return {"type": RECEIPT_SOURCE_TYPE, "label": label}


def group_source(group_names: list[str]) -> dict:
    where = ", ".join(group_names) if group_names else "doirangizdagi guruhlar"
    return {"type": RECEIPT_SOURCE_TYPE, "label": f"To'lov jadvali — {where}"}


def receipt_source(payment: Payment) -> dict:
    parts = [f"To'lov jadvali — {payment.paid_at.strftime('%d.%m.%Y %H:%M')}"]
    if payment.receipt_number:
        parts.append(f"chek {payment.receipt_number}")
    return {"type": RECEIPT_SOURCE_TYPE, "label": ", ".join(parts)}


# --- the flow ---------------------------------------------------------------


def contract_summary(db: Session, student: User) -> ContractSummary:
    """One student's contract: total / paid / pending / remaining + history.

    The caller must already have checked access (`ensure_can_access_user`).
    """
    contract = get_contract(db, student)
    if contract is None:
        raise NoContractError(student.username)

    payments = _payments_of(db, [student.id]).get(student.id, [])
    total = round(float(contract.total_amount), 2)
    paid, pending, last, _pending_count = _totals(payments)
    remaining = round(max(0.0, total - paid), 2)
    group_name = None
    if student.group_id is not None:
        group_name = _group_names(db, {student.group_id}).get(student.group_id)

    summary = ContractSummary(
        student_id=student.id,
        username=student.username,
        student_name=student.full_name,
        group_id=student.group_id,
        group_name=group_name,
        academic_year=contract.academic_year,
        total_amount=total,
        paid_amount=paid,
        pending_amount=pending,
        remaining_amount=remaining,
        paid_percent=_percent(total, paid),
        state=state_of(total, paid),
        last_payment_at=last,
        payments=[
            PaymentRow(
                id=p.id,
                amount=round(float(p.amount), 2),
                paid_at=p.paid_at,
                receipt_number=p.receipt_number,
                status=p.status,
                has_receipt_file=bool(p.receipt_file),
            )
            for p in payments
        ],
    )
    summary.source = contract_source(summary)
    return summary


def resolve_scope(db: Session, user: User, group_id: int | None) -> list[int]:
    """Group ids this user may look at, optionally narrowed to one group.

    `visible_group_ids` returning None means admin (no restriction) — then the
    scope is every group that exists.
    """
    visible = visible_group_ids(db, user)
    if group_id is not None:
        if visible is not None and group_id not in visible:
            raise OutOfScopeError(group_id)
        return [group_id]
    if visible is None:
        return [gid for (gid,) in db.query(Group.id).order_by(Group.id).all()]
    return sorted(visible)


def group_payment_summary(
    db: Session, user: User, group_id: int | None = None
) -> GroupPaymentSummary:
    """Payment state of every student in the caller's groups (tutor dashboard)."""
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
    payments = _payments_of(db, student_ids)
    contracts = {
        c.student_id: c
        for c in (
            db.query(Contract).filter(Contract.student_id.in_(student_ids)).all()
            if student_ids
            else []
        )
    }

    rows: list[GroupPaymentRow] = []
    for student in students:
        contract = contracts.get(student.id)
        total = round(float(contract.total_amount), 2) if contract else 0.0
        paid, pending, last, pending_count = _totals(payments.get(student.id, []))
        rows.append(
            GroupPaymentRow(
                student_id=student.id,
                username=student.username,
                full_name=student.full_name,
                group_id=student.group_id,
                group_name=names.get(student.group_id or -1),
                total_amount=total,
                paid_amount=paid,
                pending_amount=pending,
                remaining_amount=round(max(0.0, total - paid), 2),
                paid_percent=_percent(total, paid),
                state=state_of(total, paid),
                last_payment_at=last,
                pending_count=pending_count,
            )
        )

    # Default order = the one the tutor actually needs: biggest debt first.
    rows.sort(key=lambda r: (-r.remaining_amount, r.full_name))
    group_names = [names[gid] for gid in group_ids if gid in names]
    summary = GroupPaymentSummary(
        group_ids=group_ids,
        group_names=group_names,
        rows=rows,
        total_amount=round(sum(r.total_amount for r in rows), 2),
        paid_amount=round(sum(r.paid_amount for r in rows), 2),
        pending_amount=round(sum(r.pending_amount for r in rows), 2),
        remaining_amount=round(sum(r.remaining_amount for r in rows), 2),
        debtor_count=sum(1 for r in rows if r.state == DEBTOR),
        partial_count=sum(1 for r in rows if r.state == PARTIAL),
        paid_count=sum(1 for r in rows if r.state == PAID),
        pending_count=sum(r.pending_count for r in rows),
    )
    summary.source = group_source(group_names)
    return summary


def get_payment(db: Session, payment_id: int) -> Payment | None:
    return db.get(Payment, payment_id)


def receipt_view(db: Session, payment: Payment) -> Receipt:
    """Structured receipt. Never 404s over a missing image (demo must not fall)."""
    student = db.get(User, payment.student_id)
    return Receipt(
        payment_id=payment.id,
        student_id=payment.student_id,
        student_name=student.full_name if student else "",
        receipt_number=payment.receipt_number,
        amount=round(float(payment.amount), 2),
        paid_at=payment.paid_at,
        status=payment.status,
        academic_year=payment.academic_year,
        method=METHOD_LABELS.get(payment.status, ""),
        file_available=False,
        note=RECEIPT_NOTE,
        source=receipt_source(payment),
    )


def generate_receipt_number() -> str:
    """`CHK-…` — the same shape the seed uses for hand-uploaded receipts."""
    return f"CHK-{random.randrange(10**5, 10**6)}"


def upload_receipt(
    db: Session,
    student: User,
    amount: float,
    receipt_number: str | None = None,
    paid_at: datetime | None = None,
) -> Payment:
    """Student uploads a receipt: a payment with status=uploaded (pending).

    It does not move `paid_amount` — a tutor has to confirm it first.
    """
    contract = get_contract(db, student)
    if contract is None:
        raise NoContractError(student.username)
    try:
        value = round(float(amount), 2)
    except (TypeError, ValueError):
        raise InvalidAmountError("summa son bo'lishi kerak") from None
    if value <= 0:
        raise InvalidAmountError("summa musbat bo'lishi kerak")

    summary = contract_summary(db, student)
    if value > summary.remaining_amount + EPSILON:
        raise InvalidAmountError(
            "summa kontrakt qoldig'idan ko'p: qoldiq "
            f"{format_amount(summary.remaining_amount)}"
        )

    payment = Payment(
        student_id=student.id,
        amount=value,
        paid_at=paid_at or datetime.now(),
        receipt_number=(receipt_number or "").strip() or generate_receipt_number(),
        receipt_file=None,  # no file storage in the demo (see RECEIPT_NOTE)
        status=PaymentStatus.uploaded,
        academic_year=contract.academic_year,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    # S12 trigger (FUNKSIONALLIK 3.10): the tutor has something to confirm.
    notifications.notify_receipt_uploaded(db, student, payment)
    return payment


def confirm_payment(db: Session, actor: User, payment: Payment) -> Payment:
    """Tutor accepts an uploaded receipt: uploaded -> confirmed.

    Access is the RBAC helper, not a hand-rolled role check: the payment's
    student must be inside the actor's scope (403 otherwise).
    """
    student = db.get(User, payment.student_id)
    if student is None:
        raise NoContractError(str(payment.student_id))
    ensure_can_access_user(db, actor, student)
    if payment.status != PaymentStatus.uploaded:
        raise NotPendingError(payment.status.value)
    payment.status = PaymentStatus.confirmed
    db.commit()
    db.refresh(payment)
    # S12 trigger: the student learns the money is now counted as paid.
    notifications.notify_payment_confirmed(db, student, payment)
    return payment


# --- chat formatting (used by the `tolov_holati` tool) ----------------------


def format_contract_for_tool(summary: ContractSummary) -> str:
    """Exact numbers + the source, the way the agent must report them."""
    lines = [
        f"{summary.student_name}"
        + (f" ({summary.group_name})" if summary.group_name else "")
        + f" — kontrakt {summary.academic_year}:",
        f"  Jami: {format_amount(summary.total_amount)}",
        f"  To'langan: {format_amount(summary.paid_amount)} "
        f"({summary.paid_percent}%)",
        f"  Qoldiq: {format_amount(summary.remaining_amount)}",
        f"  Holat: {STATE_LABELS[summary.state]}",
    ]
    if summary.pending_amount > 0:
        lines.append(
            f"  Tasdiq kutilmoqda: {format_amount(summary.pending_amount)} "
            "(talaba chek yuklagan, tyutor tasdig'i kerak)"
        )
    if summary.payments:
        last = summary.payments[-1]
        lines.append(
            f"  Oxirgi to'lov: {last.paid_at.strftime('%d.%m.%Y')}, "
            f"{format_amount(last.amount)}, chek "
            f"{last.receipt_number or 'raqamsiz'} ({last.status.value})"
        )
    else:
        lines.append("  To'lov yozuvi yo'q — hali hech qanday to'lov tushmagan.")
    lines.append("(Manba: to'lov jadvali — universitet moliya tizimi yozuvlari.)")
    return "\n".join(lines)


MAX_TOOL_ROWS = 30


def format_group_for_tool(summary: GroupPaymentSummary) -> str:
    if not summary.rows:
        return "Doirangizda talaba topilmadi — to'lov svodi bo'sh."
    where = ", ".join(summary.group_names) if summary.group_names else "guruhlar"
    lines = [
        f"To'lov svodi ({where}): {len(summary.rows)} talaba — "
        f"to'langan {summary.paid_count}, qisman {summary.partial_count}, "
        f"qarzdor {summary.debtor_count}."
    ]
    if summary.pending_count:
        lines.append(
            f"Tasdiq kutayotgan chek: {summary.pending_count} ta "
            f"({format_amount(summary.pending_amount)})."
        )
    lines.append(f"Umumiy qarz: {format_amount(summary.remaining_amount)}.")
    for row in summary.rows[:MAX_TOOL_ROWS]:
        if row.state == PAID:
            continue
        lines.append(
            f"  {row.full_name} ({row.group_name or '-'}) — "
            f"{STATE_LABELS[row.state]}, qoldiq "
            f"{format_amount(row.remaining_amount)}, to'langan "
            f"{format_amount(row.paid_amount)} ({row.paid_percent}%)"
            + (
                f", {row.pending_count} ta chek tasdiq kutmoqda"
                if row.pending_count
                else ""
            )
        )
    lines.append("(Manba: to'lov jadvali — universitet moliya tizimi yozuvlari.)")
    return "\n".join(lines)
