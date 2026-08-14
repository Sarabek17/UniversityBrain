"""Payment endpoints. Thin layer: all logic lives in services/payments.py.

    GET  /payments/contract               -> own contract (student view)
    GET  /payments/contract/{student_id}  -> one student's contract (scope!)
    GET  /payments/group                  -> group summary (tutor dashboard)
    GET  /payments/{payment_id}/receipt   -> structured receipt
    POST /payments/receipts               -> student uploads a receipt
    POST /payments/{payment_id}/confirm   -> tutor confirms an uploaded receipt

RBAC: scope comes from `auth/rbac.py` only. Personal data of *another user*
answers **403** (`ensure_can_access_user`) — unlike documents/conversations,
where an invisible object answers 404. The difference is deliberate: a group
mate's existence is not a secret, their contract is.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.rbac import ensure_can_access_user, get_current_user
from app.auth.rbac import require_role
from app.db import get_db
from app.models import User, UserRole
from app.schemas import (
    ChatSource,
    ContractSummaryOut,
    GroupPaymentRowOut,
    GroupPaymentSummaryOut,
    PaymentRowOut,
    ReceiptOut,
    ReceiptUploadIn,
)
from app.services import payments as payments_service

router = APIRouter(prefix="/payments", tags=["payments"])

_NO_CONTRACT = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Kontrakt topilmadi"
)
_NO_PAYMENT = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="To'lov yozuvi topilmadi"
)


def _contract_out(summary: payments_service.ContractSummary) -> ContractSummaryOut:
    return ContractSummaryOut(
        student_id=summary.student_id,
        username=summary.username,
        student_name=summary.student_name,
        group_id=summary.group_id,
        group_name=summary.group_name,
        academic_year=summary.academic_year,
        total_amount=summary.total_amount,
        paid_amount=summary.paid_amount,
        pending_amount=summary.pending_amount,
        remaining_amount=summary.remaining_amount,
        paid_percent=summary.paid_percent,
        state=summary.state,
        last_payment_at=summary.last_payment_at,
        payments=[PaymentRowOut.model_validate(p) for p in summary.payments],
        source=ChatSource(**summary.source),
        disclaimer=summary.disclaimer,
    )


def _student_or_404(db: Session, student_id: int) -> User:
    student = db.get(User, student_id)
    if student is None:
        raise _NO_CONTRACT
    return student


@router.get("/contract", response_model=ContractSummaryOut)
def own_contract(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ContractSummaryOut:
    """The caller's own contract: total / paid / pending / remaining + history."""
    try:
        return _contract_out(payments_service.contract_summary(db, user))
    except payments_service.NoContractError:
        raise _NO_CONTRACT from None


@router.get("/contract/{student_id}", response_model=ContractSummaryOut)
def student_contract(
    student_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ContractSummaryOut:
    """One student's contract. Outside the caller's scope -> 403."""
    student = _student_or_404(db, student_id)
    ensure_can_access_user(db, user, student)
    try:
        return _contract_out(payments_service.contract_summary(db, student))
    except payments_service.NoContractError:
        raise _NO_CONTRACT from None


@router.get("/group", response_model=GroupPaymentSummaryOut)
def group_summary(
    group_id: int | None = None,
    user: User = Depends(require_role(UserRole.tutor, UserRole.staff)),
    db: Session = Depends(get_db),
) -> GroupPaymentSummaryOut:
    """Payment state of every student in scope, biggest debt first.

    Teachers are not on the list on purpose: contract money is the tutor's and
    the dean office's business (FUNKSIONALLIK 3.6 "maxfiylik").
    """
    try:
        summary = payments_service.group_payment_summary(db, user, group_id)
    except payments_service.OutOfScopeError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu guruh sizning doirangizga kirmaydi",
        ) from None
    return GroupPaymentSummaryOut(
        group_ids=summary.group_ids,
        group_names=summary.group_names,
        rows=[GroupPaymentRowOut(**row.__dict__) for row in summary.rows],
        total_amount=summary.total_amount,
        paid_amount=summary.paid_amount,
        pending_amount=summary.pending_amount,
        remaining_amount=summary.remaining_amount,
        debtor_count=summary.debtor_count,
        partial_count=summary.partial_count,
        paid_count=summary.paid_count,
        pending_count=summary.pending_count,
        source=ChatSource(**summary.source),
        disclaimer=summary.disclaimer,
    )


@router.get("/{payment_id}/receipt", response_model=ReceiptOut)
def payment_receipt(
    payment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReceiptOut:
    """The receipt behind one payment — structured data, never a file 404."""
    payment = payments_service.get_payment(db, payment_id)
    if payment is None:
        raise _NO_PAYMENT
    ensure_can_access_user(db, user, _student_or_404(db, payment.student_id))
    receipt = payments_service.receipt_view(db, payment)
    return ReceiptOut(
        payment_id=receipt.payment_id,
        student_id=receipt.student_id,
        student_name=receipt.student_name,
        receipt_number=receipt.receipt_number,
        amount=receipt.amount,
        paid_at=receipt.paid_at,
        status=receipt.status,
        academic_year=receipt.academic_year,
        method=receipt.method,
        file_available=receipt.file_available,
        note=receipt.note,
        source=ChatSource(**receipt.source),
        disclaimer=receipt.disclaimer,
    )


@router.post("/receipts", response_model=ContractSummaryOut)
def upload_receipt(
    payload: ReceiptUploadIn,
    user: User = Depends(require_role(UserRole.student)),
    db: Session = Depends(get_db),
) -> ContractSummaryOut:
    """Student hands in a receipt: a pending (`uploaded`) payment is created.

    Answers with the refreshed contract summary, so the page needs one call.
    """
    try:
        payments_service.upload_receipt(
            db, user, payload.amount, payload.receipt_number
        )
    except payments_service.NoContractError:
        raise _NO_CONTRACT from None
    except payments_service.InvalidAmountError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Chek qabul qilinmadi: {exc}",
        ) from None
    return _contract_out(payments_service.contract_summary(db, user))


@router.post("/{payment_id}/confirm", response_model=ContractSummaryOut)
def confirm_receipt(
    payment_id: int,
    user: User = Depends(require_role(UserRole.tutor, UserRole.staff)),
    db: Session = Depends(get_db),
) -> ContractSummaryOut:
    """Tutor accepts an uploaded receipt (uploaded -> confirmed).

    `confirm_payment` runs the scope check itself, so a tutor from another
    faculty gets 403 before anything is written.
    """
    payment = payments_service.get_payment(db, payment_id)
    if payment is None:
        raise _NO_PAYMENT
    try:
        payments_service.confirm_payment(db, user, payment)
    except payments_service.NotPendingError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu to'lov tasdiqlashni kutmayapti",
        ) from None
    student = _student_or_404(db, payment.student_id)
    return _contract_out(payments_service.contract_summary(db, student))
