"""Document flow endpoints. Thin layer: all logic lives in services/docflow.py.

    GET  /docflow/templates            -> templates this role may send
    GET  /docflow/recipients           -> people a staff order may go to
    GET  /docflow/inbox[?sort=new|due] -> documents addressed to me
    GET  /docflow/outbox[?sort=]       -> documents I sent ("Arizalarim")
    GET  /docflow/{id}                 -> one document + its whole history
    POST /docflow                      -> send a document built from a template
    POST /docflow/{id}/status          -> move the status chain (+ history)
    POST /docflow/{id}/summary         -> role-angled summary of the body (S6)

Two error codes carry the RBAC decision, and the difference is deliberate:
a document outside the caller's scope answers **404** (its existence is not
disclosed — the documents/conversations rule), while a visible document the
caller may not *decide* on answers **403** (the sender sees their own
application but cannot approve it).
"""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.rbac import get_current_user
from app.db import get_db
from app.models import FlowDocument, User
from app.schemas import (
    FlowCreateRequest,
    FlowDetailOut,
    FlowListOut,
    FlowRecipientOut,
    FlowStatusRequest,
    FlowSummaryOut,
    FlowTemplateOut,
)
from app.services import docflow as docflow_service
from app.services import summarization

router = APIRouter(prefix="/docflow", tags=["docflow"])

_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Hujjat topilmadi"
)
_NOT_RECIPIENT = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Hujjat holatini faqat qabul qiluvchi o'zgartira oladi",
)


def _flow_or_404(db: Session, user: User, flow_id: int) -> FlowDocument:
    flow = docflow_service.get_visible_flow(db, user, flow_id)
    if flow is None:
        raise _NOT_FOUND
    return flow


def _detail_out(db: Session, user: User, flow: FlowDocument) -> FlowDetailOut:
    return FlowDetailOut.model_validate(asdict(docflow_service.flow_detail(db, user, flow)))


@router.get("/templates", response_model=list[FlowTemplateOut])
def templates(
    user: User = Depends(get_current_user),
) -> list[FlowTemplateOut]:
    """The catalogue this role may send from (a student cannot issue an order)."""
    return [
        FlowTemplateOut(
            id=t.id,
            title=t.title,
            description=t.description,
            doc_type=t.doc_type,
            doc_type_label=docflow_service.DOC_TYPE_LABELS[t.doc_type],
            recipient_role=t.recipient_role,
            recipient_label=(
                docflow_service.ROLE_LABELS[t.recipient_role]
                if t.recipient_role is not None
                else ""
            ),
            needs_recipient_user=t.needs_recipient_user,
            needs_due_date=t.needs_due_date,
            body_hint=t.body_hint,
        )
        for t in docflow_service.templates_for(user)
    ]


@router.get("/recipients", response_model=list[FlowRecipientOut])
def recipients(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FlowRecipientOut]:
    """Who an order may be addressed to — the caller's own scope only."""
    return [
        FlowRecipientOut(
            id=person.id,
            full_name=person.full_name,
            role=person.role,
            role_label=docflow_service.ROLE_LABELS.get(person.role, person.role.value),
        )
        for person in docflow_service.recipient_candidates(db, user)
    ]


@router.get("/inbox", response_model=FlowListOut)
def inbox(
    sort: str = docflow_service.SORT_NEW,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FlowListOut:
    """Documents addressed to me: personally or through my role (own faculty)."""
    return FlowListOut.model_validate(asdict(docflow_service.inbox(db, user, sort)))


@router.get("/outbox", response_model=FlowListOut)
def outbox(
    sort: str = docflow_service.SORT_NEW,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FlowListOut:
    """Documents I sent — the student's "Arizalarim" list."""
    return FlowListOut.model_validate(asdict(docflow_service.outbox(db, user, sort)))


@router.post("", response_model=FlowDetailOut, status_code=status.HTTP_201_CREATED)
def create_flow(
    payload: FlowCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FlowDetailOut:
    """Send a document from a template: history row + recipient notifications."""
    try:
        flow = docflow_service.create_flow(
            db,
            user,
            template_id=payload.template_id,
            body_text=payload.body_text,
            recipient_user_id=payload.recipient_user_id,
            due_date=payload.due_date,
        )
    except docflow_service.UnknownTemplateError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Shablon topilmadi"
        ) from None
    except docflow_service.TemplateNotAllowedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu shablon sizning rolingiz uchun ochiq emas",
        ) from None
    except docflow_service.EmptyBodyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Hujjat matni qabul qilinmadi: {exc}",
        ) from None
    except docflow_service.InvalidRecipientError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Qabul qiluvchi qabul qilinmadi: {exc}",
        ) from None
    return _detail_out(db, user, flow)


@router.get("/{flow_id}", response_model=FlowDetailOut)
def flow_detail(
    flow_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FlowDetailOut:
    """One document + history. Outside the caller's scope -> 404, never 403."""
    return _detail_out(db, user, _flow_or_404(db, user, flow_id))


@router.post("/{flow_id}/status", response_model=FlowDetailOut)
def change_status(
    flow_id: int,
    payload: FlowStatusRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FlowDetailOut:
    """ko'rildi / ijroda / tasdiqlandi / rad etildi (+ mandatory reason).

    Answers with the refreshed document, so the page needs no second request.
    """
    flow = _flow_or_404(db, user, flow_id)
    try:
        docflow_service.change_status(db, user, flow, payload.status, payload.comment)
    except docflow_service.NotRecipientError:
        raise _NOT_RECIPIENT from None
    except docflow_service.InvalidTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Bu holat o'zgarishi mumkin emas: {exc}",
        ) from None
    except docflow_service.ReasonRequiredError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rad etish uchun sabab yozilishi shart",
        ) from None
    return _detail_out(db, user, flow)


@router.post("/{flow_id}/summary", response_model=FlowSummaryOut)
def summarize(
    flow_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FlowSummaryOut:
    """Summarize an incoming document with the S6 service (no new prompts)."""
    flow = _flow_or_404(db, user, flow_id)
    try:
        summary = docflow_service.summarize_flow(db, user, flow)
    except summarization.EmptyDocumentError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Hujjat matni bo'sh — rezyume tayyorlab bo'lmaydi",
        ) from None
    return FlowSummaryOut.model_validate(asdict(summary))
