"""`hujjat_rezyume` — summarize one document from the caller's role angle.

This file is only the *tool wrapper*: it resolves which document is meant and
turns the result into a `ToolResult`. The summarization itself (role angle,
map-reduce, LLM call) lives in `services/summarization.py`, the exact same code
path the "Rezyume" button uses via `POST /documents/{id}/summary`.

Access rules (unchanged since S4, `services/documents.py` owns them):
    * by title  -> only visible documents are searched, so a confidential order
      is not even reported as existing,
    * by id     -> a document the user may not open answers a plain
      "Ruxsat yo'q" (the id came from somewhere, hiding it helps nobody).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.registry import ALL_ROLES, Tool, ToolResult, register
from app.models import Document, User
from app.services import documents as documents_service
from app.services import summarization

NAME = "hujjat_rezyume"


def _find_document(db: Session, user: User, args: dict) -> tuple[Document | None, str | None]:
    """Locate the document. Returns (document, error_text)."""
    raw_id = args.get("hujjat_id")
    if raw_id not in (None, ""):
        try:
            doc_id = int(raw_id)
        except (TypeError, ValueError):
            return None, f"'hujjat_id' butun son bo'lishi kerak, kelgani: {raw_id!r}."
        if db.get(Document, doc_id) is None:
            return None, f"{doc_id}-raqamli hujjat topilmadi."
        document = documents_service.get_visible_document(db, user, doc_id)
        if document is None:
            return None, (
                "Ruxsat yo'q: bu hujjat sizning rolingiz uchun yopiq. "
                "Foydalanuvchiga hujjat mazmunini aytma."
            )
        return document, None

    name = str(args.get("nom") or "").strip()
    if not name:
        return None, "Hujjatni aniqlash uchun 'nom' yoki 'hujjat_id' bering."

    document = documents_service.find_visible_document_by_title(db, user, name)
    if document is None:
        return None, f"'{name}' bo'yicha sizga ochiq hujjatlardan mos hujjat topilmadi."
    return document, None


def handler(db: Session, user: User, args: dict) -> ToolResult:
    document, error = _find_document(db, user, args)
    if error or document is None:
        return ToolResult(text=error or "Hujjat topilmadi.", ok=False)

    try:
        result = summarization.summarize_document(db, document, user)
    except summarization.EmptyDocumentError:
        return ToolResult(
            text=f"'{document.title}' hujjatining matni topilmadi.", ok=False
        )

    note = (
        "\n(Hujjat juda uzun — rezyume uning boshidagi qismlar bo'yicha.)"
        if result.truncated
        else ""
    )
    return ToolResult(
        text=f"'{result.title}' hujjati rezyumesi:\n{result.summary}{note}",
        sources=[result.source],
    )


register(
    Tool(
        name=NAME,
        description=(
            "Bitta hujjatni qisqartirib beradi (rezyume). Hujjat nomi yoki id "
            "raqami bo'yicha topadi. 'Shu buyruqni qisqartir', 'hujjatning "
            "mazmuni nima?' kabi so'rovlarda ishlat."
        ),
        parameters={
            "type": "object",
            "properties": {
                "nom": {
                    "type": "string",
                    "description": "Hujjat nomi yoki uning bir qismi.",
                },
                "hujjat_id": {
                    "type": "integer",
                    "description": "Hujjatning id raqami (qidiruv natijasidan olinadi).",
                },
            },
            "required": [],
        },
        handler=handler,
        roles=ALL_ROLES,
    )
)
