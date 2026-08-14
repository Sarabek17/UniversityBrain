"""Document endpoints. Thin layer: access logic lives in services/documents.py.

    GET /documents          -> documents this user may see
    GET /documents/{id}     -> metadata + full text (404 when not visible)

RBAC: every authenticated role may list documents; *which* documents is decided
by `rag.search.allowed_access_levels` — the same rule the RAG search applies, so
the chat and the viewer can never disagree. An invisible document answers 404,
not 403: its very existence stays hidden (same rule as the chat API).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.rbac import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import DocumentDetailOut, DocumentListItemOut
from app.services import documents as documents_service

router = APIRouter(prefix="/documents", tags=["documents"])

_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Hujjat topilmadi"
)


@router.get("", response_model=list[DocumentListItemOut])
def list_documents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DocumentListItemOut]:
    return documents_service.visible_documents(db, user)


@router.get("/{document_id}", response_model=DocumentDetailOut)
def get_document(
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentDetailOut:
    document = documents_service.get_visible_document(db, user, document_id)
    if document is None:
        raise _NOT_FOUND
    return DocumentDetailOut(
        id=document.id,
        title=document.title,
        doc_type=document.doc_type,
        language=document.language,
        access_level=document.access_level,
        uploaded_at=document.uploaded_at,
        text=documents_service.document_text(db, document),
    )
