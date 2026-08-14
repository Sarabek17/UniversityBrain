"""Document summarization (FUNKSIONALLIK 3.4) — ONE code path.

Both entry points go through `summarize_document`:
    * the `hujjat_rezyume` tool (chat: "shu buyruqni qisqartir"),
    * `POST /documents/{id}/summary` (the "Rezyume" button in the viewer).

Two things make a summary useful here:

1. **Role angle.** The same order reads differently for a student ("what do I
   have to do, by when") and for the registrar ("number, date, who executes").
   `ROLE_FOCUS` + `ROLE_POINTS` go into the system prompt *and* the user prompt,
   so the angle survives whichever provider is behind `llm/client.py`.
2. **Map-reduce.** A document longer than `PART_CHARS` is split on paragraph
   boundaries; every part gets its own LLM call (map), then the part summaries
   are merged by one final call (reduce). Short documents stay a single call.

The LLM is reached ONLY through `llm/client.py`, and access is never decided
here — callers pass a `Document` they already proved the user may open
(`services/documents.get_visible_document` / the tool's own lookup).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.agents.orchestrator import DISCLAIMER
from app.llm.client import get_llm_client
from app.models import Document, User, UserRole
from app.services import documents as documents_service

# Characters handed to one LLM call. Not a model limit (Gemini takes far more)
# but a quality/latency budget: ~1000-1300 tokens summarize well in one pass.
# It is also chosen so the corpus really exercises map-reduce — the longest demo
# documents (~4.4-4.9k characters) split into two parts, while a two-page order
# (~2k) stays a single call.
PART_CHARS = 4000
MAX_PARTS = 12  # safety cap: 12 * PART_CHARS is far beyond any demo document

SYSTEM_BASE = (
    "Sen universitet hujjatlarini qisqartiruvchi yordamchisan. Faqat berilgan "
    "matnga tayan: matnda yo'q sana, raqam yoki ismni o'ylab topma. Javob "
    "o'zbek tilida, 5-7 qatorlik aniq ro'yxat ko'rinishida bo'lsin."
)

# The angle each role reads a document from (FUNKSIONALLIK 3.4).
ROLE_FOCUS: dict[UserRole, str] = {
    UserRole.student: "talaba nima qilishi va qaysi muddatgacha ulgurishi kerakligiga",
    UserRole.teacher: "asosiy bandlar va o'quv jarayoniga ta'siriga",
    UserRole.tutor: "guruh va talabalarga tegishli majburiyatlarga",
    UserRole.staff: "hujjat raqami, sanalar, ijrochilar va muddatlarga",
    UserRole.admin: "tashkiliy va texnik tafsilotlarga",
}

# What the summary must answer for that role — concrete, so the model cannot
# fall back to a generic retelling.
ROLE_POINTS: dict[UserRole, tuple[str, ...]] = {
    UserRole.student: (
        "mendan nima talab qilinadi",
        "qachongacha (muddat, sana)",
        "bajarmaslik oqibati yoki baho ta'siri",
    ),
    UserRole.teacher: (
        "hujjatning asosiy bandlari",
        "o'quv jarayoniga ta'siri (dars, baholash, topshiriq)",
        "o'qituvchidan talab qilinadigan ish va uning muddati",
    ),
    UserRole.tutor: (
        "guruh va talabalarga tushadigan majburiyatlar",
        "tyutor nazorat qilishi kerak bo'lgan muddatlar",
        "talabalarga yetkazilishi kerak bo'lgan ma'lumot",
    ),
    UserRole.staff: (
        "hujjat raqami va sanasi",
        "ijrochilar (kim, qaysi bo'lim)",
        "muddatlar va nazorat qiluvchi shaxs",
    ),
    UserRole.admin: (
        "hujjatning tashkiliy mazmuni",
        "kimga taalluqli (rol, bo'lim, guruh)",
        "sana, raqam va muddatlar",
    ),
}

DEFAULT_ROLE = UserRole.student


class EmptyDocumentError(RuntimeError):
    """The document exists but has no readable text (file and chunks empty)."""


@dataclass
class DocumentSummary:
    document_id: int
    title: str
    summary: str
    parts: int  # map steps; 1 = single-shot, >1 = map-reduce
    llm_calls: int  # parts (+1 for the reduce step)
    truncated: bool  # document longer than MAX_PARTS * PART_CHARS
    source: dict = field(default_factory=dict)
    disclaimer: str = DISCLAIMER


# --- role angle -------------------------------------------------------------


def role_focus(role: UserRole) -> str:
    return ROLE_FOCUS.get(role, ROLE_FOCUS[DEFAULT_ROLE])


def role_points(role: UserRole) -> tuple[str, ...]:
    return ROLE_POINTS.get(role, ROLE_POINTS[DEFAULT_ROLE])


def system_prompt(role: UserRole) -> str:
    """Shared rules + the reader's angle. Differs per role by construction."""
    points = "; ".join(role_points(role))
    return (
        f"{SYSTEM_BASE}\n"
        f"O'quvchining roli: {role.value}. Rezyume {role_focus(role)} urg'u bersin.\n"
        f"Javobda quyidagilar yoritilsin: {points}."
    )


# --- prompts ----------------------------------------------------------------


def _document_header(title: str, doc_type: str, language: str) -> str:
    return f"Hujjat nomi: {title}\nTuri: {doc_type}, tili: {language}"


def build_summary_prompt(
    *, title: str, doc_type: str, language: str, role: UserRole, body: str
) -> str:
    """Single-shot summary (document fits into one LLM call)."""
    points = "\n".join(f"- {p}" for p in role_points(role))
    return (
        f"Quyidagi hujjatni qisqartir. Rakurs: {role_focus(role)} urg'u ber.\n"
        f"{_document_header(title, doc_type, language)}\n"
        f"Rezyume shu savollarga javob bersin:\n{points}\n"
        f"\n--- HUJJAT MATNI ---\n{body}\n--- MATN OXIRI ---"
    )


def build_part_prompt(
    *, title: str, role: UserRole, body: str, index: int, total: int
) -> str:
    """MAP step: one part of a long document."""
    return (
        f"Bu uzun hujjatning {index}/{total}-qismi. Faqat shu qismdagi muhim "
        f"faktlarni qisqa bandlar bilan yozib ol (bu oraliq qayd, yakuniy "
        f"rezyume emas). Rakurs: {role_focus(role)} e'tibor ber. Sana, raqam "
        f"va muddatlarni aynan ko'chir.\n"
        f"Hujjat nomi: {title}\n"
        f"\n--- QISM MATNI ---\n{body}\n--- QISM OXIRI ---"
    )


def build_reduce_prompt(
    *,
    title: str,
    doc_type: str,
    language: str,
    role: UserRole,
    part_summaries: list[str],
    truncated: bool = False,
) -> str:
    """REDUCE step: merge the part summaries into the final answer."""
    points = "\n".join(f"- {p}" for p in role_points(role))
    joined = "\n\n".join(
        f"[{i}-qism]\n{s}" for i, s in enumerate(part_summaries, start=1)
    )
    note = (
        "(Hujjat juda uzun — oxirgi qismlar qamrab olinmagan, buni rezyume "
        "oxirida bir qatorda eslatib qo'y.)\n"
        if truncated
        else ""
    )
    return (
        f"Quyida bitta hujjatning qismlari bo'yicha oraliq qaydlar berilgan. "
        f"Ularni takrorlarsiz, yagona rezyumega birlashtir. Rakurs: "
        f"{role_focus(role)} urg'u ber.\n"
        f"{_document_header(title, doc_type, language)}\n"
        f"{note}"
        f"Rezyume shu savollarga javob bersin:\n{points}\n"
        f"\n--- ORALIQ QAYDLAR ---\n{joined}\n--- QAYDLAR OXIRI ---"
    )


# --- splitting --------------------------------------------------------------


def split_parts(
    text: str, part_chars: int = PART_CHARS, max_parts: int = MAX_PARTS
) -> tuple[list[str], bool]:
    """Split on paragraph boundaries. Returns (parts, truncated).

    A single oversized paragraph is cut at the hard limit — a last resort that
    the demo corpus never reaches.
    """
    text = text.strip()
    if not text:
        return [], False
    if len(text) <= part_chars:
        return [text], False

    parts: list[str] = []
    current = ""
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if current and len(current) + len(block) + 2 > part_chars:
            parts.append(current)
            current = block
        else:
            current = f"{current}\n\n{block}" if current else block
        while len(current) > part_chars:
            parts.append(current[:part_chars])
            current = current[part_chars:].strip()
    if current:
        parts.append(current)

    truncated = len(parts) > max_parts
    return parts[:max_parts], truncated


# --- the flow ---------------------------------------------------------------


def _ask(prompt: str, system: str) -> str:
    response = get_llm_client().chat(
        messages=[{"role": "user", "content": prompt}], system=system
    )
    return (response.text or "").strip()


def summarize_text(
    text: str,
    *,
    title: str,
    doc_type: str,
    language: str,
    role: UserRole,
) -> tuple[str, int, int, bool]:
    """Summarize raw text. Returns (summary, parts, llm_calls, truncated)."""
    parts, truncated = split_parts(text)
    if not parts:
        raise EmptyDocumentError(title)

    system = system_prompt(role)

    if len(parts) == 1:
        summary = _ask(
            build_summary_prompt(
                title=title,
                doc_type=doc_type,
                language=language,
                role=role,
                body=parts[0],
            ),
            system,
        )
        return summary, 1, 1, truncated

    part_summaries = [
        _ask(
            build_part_prompt(
                title=title, role=role, body=body, index=i, total=len(parts)
            ),
            system,
        )
        for i, body in enumerate(parts, start=1)
    ]
    summary = _ask(
        build_reduce_prompt(
            title=title,
            doc_type=doc_type,
            language=language,
            role=role,
            part_summaries=part_summaries,
            truncated=truncated,
        ),
        system,
    )
    return summary, len(parts), len(parts) + 1, truncated


def document_source(document: Document) -> dict:
    """Citation for the summary (same shape as a chat source)."""
    return {
        "type": "document",
        "label": f"{document.title} (to'liq hujjat)",
        "document_id": document.id,
        "title": document.title,
    }


def summarize_document(db: Session, document: Document, user: User) -> DocumentSummary:
    """Summarize one document from `user`'s role angle.

    The caller must already have checked that this user may open the document.
    """
    text = documents_service.document_text(db, document)
    summary, parts, calls, truncated = summarize_text(
        text,
        title=document.title,
        doc_type=document.doc_type.value,
        language=document.language,
        role=user.role,
    )
    return DocumentSummary(
        document_id=document.id,
        title=document.title,
        summary=summary or "Rezyume tayyorlanmadi.",
        parts=parts,
        llm_calls=calls,
        truncated=truncated,
        source=document_source(document),
    )
