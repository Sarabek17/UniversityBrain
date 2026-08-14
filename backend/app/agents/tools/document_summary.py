"""`hujjat_rezyume` — summarize one document through the LLM client.

Simple version (S6 strengthens it with role-specific angles and map-reduce for
long documents). Access is checked against `Document.access_level` with the
same rule the RAG search uses (`rag.search.allowed_access_levels`), so the
confidential order stays invisible to students even when asked by name.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.registry import ALL_ROLES, Tool, ToolResult, register
from app.llm.client import get_llm_client
from app.models import Chunk, Document, User, UserRole
from app.rag.ingest import document_path, extract_text
from app.rag.search import allowed_access_levels

NAME = "hujjat_rezyume"

MAX_INPUT_CHARS = 6000  # enough for the demo corpus; S6 adds map-reduce

SYSTEM = (
    "Sen universitet hujjatlarini qisqartiruvchi yordamchisan. Faqat berilgan "
    "matnga tayan, yangi fakt qo'shma. Javob o'zbek tilida, 5-7 qatorlik "
    "aniq ro'yxat ko'rinishida bo'lsin."
)

ROLE_FOCUS = {
    UserRole.student: "talaba nima qilishi va qaysi muddatgacha ulgurishi kerakligiga",
    UserRole.teacher: "asosiy bandlar va o'quv jarayoniga ta'siriga",
    UserRole.tutor: "guruh va talabalarga tegishli majburiyatlarga",
    UserRole.staff: "hujjat raqami, sanalar, ijrochilar va muddatlarga",
    UserRole.admin: "tashkiliy va texnik tafsilotlarga",
}


def _visible_documents(db: Session, user: User):
    query = db.query(Document)
    levels = allowed_access_levels(user)  # None = admin
    if levels is not None:
        query = query.filter(Document.access_level.in_(levels))
    return query


def _find_document(db: Session, user: User, args: dict) -> tuple[Document | None, str | None]:
    """Locate the document. Returns (document, error_text)."""
    raw_id = args.get("hujjat_id")
    if raw_id not in (None, ""):
        try:
            doc_id = int(raw_id)
        except (TypeError, ValueError):
            return None, f"'hujjat_id' butun son bo'lishi kerak, kelgani: {raw_id!r}."
        document = db.get(Document, doc_id)
        if document is None:
            return None, f"{doc_id}-raqamli hujjat topilmadi."
        levels = allowed_access_levels(user)
        if levels is not None and document.access_level.value not in levels:
            return None, (
                "Ruxsat yo'q: bu hujjat sizning rolingiz uchun yopiq. "
                "Foydalanuvchiga hujjat mazmunini aytma."
            )
        return document, None

    name = str(args.get("nom") or "").strip()
    if not name:
        return None, "Hujjatni aniqlash uchun 'nom' yoki 'hujjat_id' bering."

    # Title search runs over visible documents only: a document the user may
    # not open simply does not exist for them.
    document = (
        _visible_documents(db, user)
        .filter(Document.title.ilike(f"%{name}%"))
        .order_by(Document.id)
        .first()
    )
    if document is None:
        return None, f"'{name}' bo'yicha sizga ochiq hujjatlardan mos hujjat topilmadi."
    return document, None


def _document_text(db: Session, document: Document) -> str:
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


def handler(db: Session, user: User, args: dict) -> ToolResult:
    document, error = _find_document(db, user, args)
    if error:
        return ToolResult(text=error, ok=False)

    text = _document_text(db, document)
    if not text.strip():
        return ToolResult(
            text=f"'{document.title}' hujjatining matni topilmadi.", ok=False
        )
    truncated = len(text) > MAX_INPUT_CHARS
    body = text[:MAX_INPUT_CHARS]

    focus = ROLE_FOCUS.get(user.role, ROLE_FOCUS[UserRole.student])
    prompt = (
        f"Quyidagi hujjatni qisqartir. Rakurs: {focus} urg'u ber.\n"
        f"Hujjat nomi: {document.title}\n"
        f"Turi: {document.doc_type.value}, tili: {document.language}\n"
        + ("(Matn qisqartirilgan holda berilmoqda.)\n" if truncated else "")
        + f"\n--- HUJJAT MATNI ---\n{body}\n--- MATN OXIRI ---"
    )

    response = get_llm_client().chat(
        messages=[{"role": "user", "content": prompt}], system=SYSTEM
    )
    summary = (response.text or "").strip() or "Rezyume tayyorlanmadi."

    return ToolResult(
        text=f"'{document.title}' hujjati rezyumesi:\n{summary}",
        sources=[
            {
                "type": "document",
                "label": f"{document.title} (to'liq hujjat)",
                "document_id": document.id,
                "title": document.title,
            }
        ],
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
