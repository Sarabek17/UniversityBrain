"""Document reading service: what a user may list and open.

The access rule is NOT re-implemented here — it is the same one the RAG search
uses (`rag.search.allowed_access_levels`), so a document that is invisible in
search is invisible in the list and in the viewer too.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Chunk, Document, User
from app.rag.ingest import document_path, extract_text
from app.rag.search import allowed_access_levels


def visible_documents(db: Session, user: User) -> list[Document]:
    """Documents this user is allowed to see, newest title order by id."""
    query = db.query(Document)
    levels = allowed_access_levels(user)  # None = admin, no restriction
    if levels is not None:
        query = query.filter(Document.access_level.in_(levels))
    return query.order_by(Document.id).all()


def get_visible_document(db: Session, user: User, document_id: int) -> Document | None:
    """One document, or None when it does not exist / is not visible.

    Callers turn None into 404 (never 403): a document the user may not open
    must not be probeable by id either.
    """
    document = db.get(Document, document_id)
    if document is None:
        return None
    levels = allowed_access_levels(user)
    if levels is not None and document.access_level.value not in levels:
        return None
    return document


def document_text(db: Session, document: Document) -> str:
    """Full text: the source file, falling back to the indexed chunks."""
    try:
        text = extract_text(document_path(document))
    except (OSError, ValueError):
        text = ""
    if text.strip():
        return text
    chunks = (
        db.query(Chunk)
        .filter(Chunk.document_id == document.id)
        .order_by(Chunk.order_index)
        .all()
    )
    return "\n\n".join(c.text for c in chunks)
