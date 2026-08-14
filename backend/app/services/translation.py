"""Document translation (FUNKSIONALLIK 3.5) — ONE code path.

Both entry points go through `translate_document`:
    * the `tarjima_qil` tool (chat: "shu maqolani o'zbekchaga o'gir"),
    * `POST /documents/{id}/translate` (the "Tarjima" button in the viewer).

Three properties the domain rules demand (CLAUDE.md #4):

1. **The original is never replaced.** The result is a list of paragraph pairs
   (original, translation); the caller renders them side by side. Nothing here
   ever rewrites `Document` or its chunks.
2. **Paragraph structure survives.** The translated paragraph count always
   equals the original one — that is what makes the two columns line up. It is
   guaranteed structurally, not by trusting the model: paragraphs are sent in
   batches with `[[n]]` markers, and if a response does not come back with
   exactly those markers, that batch is retranslated one paragraph per call.
3. **Terms keep their original in brackets** — "mashinaviy o'qitish (machine
   learning)". That is a prompt rule (`TERM_RULE`), present in both prompts.

The result is cached in the `Translation` table keyed by
`(document_id, language)`, so the second request costs **zero** LLM calls.

The LLM is reached ONLY through `llm/client.py`, and access is never decided
here — callers pass a `Document` they already proved the user may open
(`services/documents.get_visible_document` / the tool's own lookup).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.agents.orchestrator import DISCLAIMER
from app.llm.client import get_llm_client
from app.models import Document, Translation, User
from app.services import documents as documents_service

DEFAULT_LANGUAGE = "uz"
LANGUAGE_NAMES = {"uz": "o'zbek", "ru": "rus", "en": "ingliz"}
SUPPORTED_LANGUAGES = tuple(LANGUAGE_NAMES)

# Characters handed to one batched LLM call. Small enough that a batch stays
# reliable, large enough that a demo document costs ~2 calls instead of ~30
# (the corpus paragraphs are 100-400 characters each).
BATCH_CHARS = 3000
MAX_PARAGRAPHS = 80  # safety cap; the longest demo document has 38

MARKER_RE = re.compile(r"^[ \t]*\[\[(\d+)\]\][ \t]*$", re.MULTILINE)

TERM_RULE = (
    "Muhim atama va terminlarni tarjima qil, lekin originalini darhol qavs "
    "ichida qoldir — masalan: mashinaviy o'qitish (machine learning). "
    "Ism, sana, raqam, hujjat raqami va kod bo'laklarini o'zgartirmasdan ko'chir. "
    "Markdown belgilarini (# sarlavha, - ro'yxat, | jadval, `kod`) saqlab qol."
)


class UnsupportedLanguageError(ValueError):
    """Target language outside SUPPORTED_LANGUAGES."""


class EmptyDocumentError(RuntimeError):
    """The document exists but has no readable text (file and chunks empty)."""


@dataclass
class ParagraphPair:
    index: int  # 1-based, matches the order in the document
    original: str
    translated: str


@dataclass
class DocumentTranslation:
    document_id: int
    title: str
    source_language: str
    target_language: str
    paragraphs: list[ParagraphPair]
    cached: bool  # served from the Translation table (0 LLM calls)
    llm_calls: int
    truncated: bool  # document longer than MAX_PARAGRAPHS paragraphs
    same_language: bool  # document is already in the target language
    source: dict = field(default_factory=dict)
    disclaimer: str = DISCLAIMER


# --- language helpers -------------------------------------------------------


def normalize_language(language: str | None) -> str:
    """Validate + canonicalise a target language code."""
    code = (language or DEFAULT_LANGUAGE).strip().lower()
    if code not in LANGUAGE_NAMES:
        raise UnsupportedLanguageError(code)
    return code


def language_name(code: str) -> str:
    return LANGUAGE_NAMES.get((code or "").strip().lower(), code or "noma'lum")


# --- paragraphs -------------------------------------------------------------


def split_paragraphs(text: str) -> list[str]:
    """Blank-line separated blocks. The unit of alignment for the two columns."""
    return [block.strip() for block in (text or "").split("\n\n") if block.strip()]


def normalize_paragraph(text: str) -> str:
    """Collapse blank lines inside one paragraph.

    The cache stores paragraphs joined by a blank line, so a translated
    paragraph must not contain one itself — otherwise the cached text would
    split back into more paragraphs than the original has.
    """
    return re.sub(r"\n\s*\n+", "\n", (text or "").strip())


def batch_paragraphs(
    paragraphs: list[str], batch_chars: int = BATCH_CHARS
) -> list[list[int]]:
    """Group paragraph indices into batches of at most `batch_chars`."""
    batches: list[list[int]] = []
    current: list[int] = []
    size = 0
    for index, paragraph in enumerate(paragraphs):
        length = len(paragraph)
        if current and size + length > batch_chars:
            batches.append(current)
            current, size = [], 0
        current.append(index)
        size += length
    if current:
        batches.append(current)
    return batches


# --- prompts ----------------------------------------------------------------


def system_prompt(target_language: str) -> str:
    return (
        f"Sen universitet hujjatlarini {language_name(target_language)} tiliga "
        "tarjima qiluvchi yordamchisan. Faqat tarjima qil: matnga yangi ma'lumot "
        "qo'shma, hech narsani tushirib qoldirma, o'zingdan izoh yozma. Original "
        "matn o'zgarmasdan saqlanadi — tarjima unga qo'shiladigan alohida qatlam.\n"
        f"{TERM_RULE}"
    )


def build_batch_prompt(
    *, title: str, source_language: str, target_language: str, paragraphs: list[str]
) -> str:
    """Several paragraphs in one call, held together by `[[n]]` markers."""
    body = "\n\n".join(
        f"[[{i}]]\n{p}" for i, p in enumerate(paragraphs, start=1)
    )
    return (
        f"Quyidagi matnni {language_name(source_language)} tilidan "
        f"{language_name(target_language)} tiliga tarjima qil.\n"
        f"Matn {len(paragraphs)} ta paragrafga bo'lingan, har biri [[N]] belgisi "
        "bilan boshlanadi. Javobda AYNAN shu belgilarni va AYNAN shu tartibni "
        "saqla: har [[N]] belgisidan keyin faqat o'sha paragrafning tarjimasi "
        "tursin. Paragraflarni birlashtirma, bo'lakka bo'lma, tushirib qoldirma.\n"
        f"{TERM_RULE}\n"
        f"Hujjat nomi: {title}\n"
        f"\n--- MATN ---\n{body}\n--- MATN OXIRI ---"
    )


def build_paragraph_prompt(
    *, title: str, source_language: str, target_language: str, paragraph: str
) -> str:
    """One paragraph, one call — the fallback that keeps the counts equal."""
    return (
        f"Quyidagi bitta paragrafni {language_name(source_language)} tilidan "
        f"{language_name(target_language)} tiliga tarjima qil.\n"
        "Javobda faqat tarjima matni bo'lsin: izoh, sarlavha yoki qo'shimcha "
        "belgi yozma. Paragrafning ichki tuzilishini saqla.\n"
        f"{TERM_RULE}\n"
        f"Hujjat nomi: {title}\n"
        f"\n--- PARAGRAF ---\n{paragraph}\n--- PARAGRAF OXIRI ---"
    )


# --- LLM plumbing -----------------------------------------------------------


def _ask(prompt: str, system: str) -> str:
    response = get_llm_client().chat(
        messages=[{"role": "user", "content": prompt}], system=system
    )
    return (response.text or "").strip()


def parse_batch_response(text: str, expected: int) -> list[str] | None:
    """Split a marked response back into paragraphs, or None if it is off.

    Strict on purpose: a partially obeyed format would silently misalign the
    columns, so anything unexpected sends the batch down the fallback path.
    """
    matches = list(MARKER_RE.finditer(text or ""))
    if len(matches) != expected:
        return None
    parts: list[str] = []
    for position, match in enumerate(matches):
        if int(match.group(1)) != position + 1:
            return None
        start = match.end()
        end = matches[position + 1].start() if position + 1 < len(matches) else len(text)
        piece = normalize_paragraph(text[start:end])
        if not piece:
            return None
        parts.append(piece)
    return parts


def translate_paragraphs(
    paragraphs: list[str],
    *,
    title: str,
    source_language: str,
    target_language: str,
) -> tuple[list[str], int]:
    """Translate every paragraph. Returns (translations, llm_calls).

    `len(translations) == len(paragraphs)` always holds.
    """
    if not paragraphs:
        return [], 0

    system = system_prompt(target_language)
    translations: list[str] = []
    calls = 0

    def one(paragraph: str) -> str:
        nonlocal calls
        calls += 1
        answer = _ask(
            build_paragraph_prompt(
                title=title,
                source_language=source_language,
                target_language=target_language,
                paragraph=paragraph,
            ),
            system,
        )
        return normalize_paragraph(answer) or paragraph

    for indices in batch_paragraphs(paragraphs):
        block = [paragraphs[i] for i in indices]
        if len(block) == 1:
            translations.append(one(block[0]))
            continue

        calls += 1
        answer = _ask(
            build_batch_prompt(
                title=title,
                source_language=source_language,
                target_language=target_language,
                paragraphs=block,
            ),
            system,
        )
        parsed = parse_batch_response(answer, len(block))
        if parsed is not None:
            translations.extend(parsed)
        else:
            # The model did not keep the markers: fall back to one call per
            # paragraph, which cannot misalign.
            translations.extend(one(paragraph) for paragraph in block)

    return translations, calls


# --- cache ------------------------------------------------------------------


def cached_row(db: Session, document_id: int, language: str) -> Translation | None:
    return (
        db.query(Translation)
        .filter(
            Translation.document_id == document_id,
            Translation.chunk_id.is_(None),
            Translation.language == language,
        )
        .order_by(Translation.id.desc())
        .first()
    )


def store_translation(
    db: Session, document_id: int, language: str, translated: list[str]
) -> Translation:
    """Upsert the cached translation for one document+language."""
    text = "\n\n".join(normalize_paragraph(p) for p in translated)
    row = cached_row(db, document_id, language)
    if row is None:
        row = Translation(
            document_id=document_id,
            chunk_id=None,
            language=language,
            translated_text=text,
        )
        db.add(row)
    else:
        row.translated_text = text
    db.commit()
    return row


# --- the flow ---------------------------------------------------------------


def document_source(document: Document) -> dict:
    """Citation for the translation (same shape as a chat source)."""
    return {
        "type": "document",
        "label": f"{document.title} (original {language_name(document.language)} tilida)",
        "document_id": document.id,
        "title": document.title,
    }


def _pairs(originals: list[str], translations: list[str]) -> list[ParagraphPair]:
    return [
        ParagraphPair(index=i, original=o, translated=t)
        for i, (o, t) in enumerate(zip(originals, translations), start=1)
    ]


def translate_document(
    db: Session,
    document: Document,
    user: User,
    target_language: str | None = None,
) -> DocumentTranslation:
    """Translate one document into `target_language`, cache-first.

    The caller must already have checked that this user may open the document.
    `user` is accepted for symmetry with the other services (and so a future
    per-role glossary has somewhere to hook in); the translation itself is
    role-independent, which is exactly why it can be cached and shared.
    """
    language = normalize_language(target_language)
    originals = split_paragraphs(documents_service.document_text(db, document))
    if not originals:
        raise EmptyDocumentError(document.title)

    truncated = len(originals) > MAX_PARAGRAPHS
    originals = originals[:MAX_PARAGRAPHS]

    result = DocumentTranslation(
        document_id=document.id,
        title=document.title,
        source_language=document.language,
        target_language=language,
        paragraphs=[],
        cached=False,
        llm_calls=0,
        truncated=truncated,
        same_language=(document.language or "").strip().lower() == language,
        source=document_source(document),
    )

    if result.same_language:
        # Nothing to translate: the columns would be identical. Costs no LLM
        # call and stores nothing — the UI says so instead.
        result.paragraphs = _pairs(originals, list(originals))
        return result

    row = cached_row(db, document.id, language)
    if row is not None:
        cached_paragraphs = split_paragraphs(row.translated_text)
        if len(cached_paragraphs) == len(originals):
            result.paragraphs = _pairs(originals, cached_paragraphs)
            result.cached = True
            return result
        # Stale cache (the document text changed): fall through and rebuild.

    translations, calls = translate_paragraphs(
        originals,
        title=document.title,
        source_language=document.language,
        target_language=language,
    )
    store_translation(db, document.id, language, translations)
    result.paragraphs = _pairs(originals, translations)
    result.llm_calls = calls
    return result


# --- chat formatting --------------------------------------------------------

TOOL_TEXT_CHARS = 2200
TOOL_PARAGRAPH_CHARS = 320


def _clip(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[:limit].rstrip() + " […]"


def format_pairs_for_tool(result: DocumentTranslation) -> str:
    """Tool answer: original AND translation, paragraph by paragraph.

    Capped, because a whole document would flood the model's context — the
    viewer shows the full pairing.
    """
    header = (
        f"'{result.title}' hujjati tarjimasi "
        f"({language_name(result.source_language)} → "
        f"{language_name(result.target_language)}). "
        "Original o'zgartirilmadi, quyida har paragrafning asli va tarjimasi:"
    )
    if result.same_language:
        header = (
            f"'{result.title}' hujjati allaqachon "
            f"{language_name(result.target_language)} tilida — tarjima kerak emas. "
            "Matnning boshi:"
        )

    lines: list[str] = []
    used = 0
    shown = 0
    for pair in result.paragraphs:
        original = _clip(pair.original, TOOL_PARAGRAPH_CHARS)
        block = (
            f"{pair.index}. [asl] {original}"
            if result.same_language
            else f"{pair.index}. [asl] {original}\n"
            f"   [tarjima] {_clip(pair.translated, TOOL_PARAGRAPH_CHARS)}"
        )
        if used + len(block) > TOOL_TEXT_CHARS and shown:
            break
        lines.append(block)
        used += len(block)
        shown += 1

    total = len(result.paragraphs)
    note = ""
    if shown < total:
        note = (
            f"\n\n(Jami {total} paragraf, shu yerda {shown} tasi ko'rsatildi — "
            "to'liq yonma-yon ko'rinish hujjat panelida.)"
        )
    if result.truncated:
        note += "\n(Hujjat juda uzun — tarjima uning boshidagi paragraflar bo'yicha.)"
    return f"{header}\n\n" + "\n\n".join(lines) + note
