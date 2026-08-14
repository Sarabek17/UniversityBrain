"""Document indexing: file text -> chunks -> embeddings -> Chroma + SQLite.

Pipeline (FUNKSIONALLIK 3.3):
    file -> text -> language (Document.language, set at upload/seed time)
         -> paragraph-aware chunking -> embeddings -> Chroma + Chunk rows.

The vector lives in Chroma; SQLite keeps the chunk text and the Chroma record
id (`Chunk.embedding_id`), so the two stores can always be re-linked.

Entry point for the whole seed corpus: `python -m seed.ingest_documents`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Chunk, Document
from app.rag import embeddings
from app.rag.store import get_collection, reset_collection

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

SUPPORTED_SUFFIXES = {".md", ".txt", ".markdown"}

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_SENTENCE_END_RE = re.compile(r"(?<=[.!?;:])\s+")


@dataclass
class TextChunk:
    """One chunk before it is persisted."""

    order_index: int
    heading: str  # markdown section(s) the chunk covers, " · " separated
    body: str  # raw text as it appears in the file
    text: str  # what actually gets embedded (title + heading + body)


# --- text extraction --------------------------------------------------------


def document_path(document: Document) -> Path:
    """Absolute path of a Document.file_path (stored relative to backend/)."""
    raw = Path(document.file_path or "")
    return raw if raw.is_absolute() else (BACKEND_DIR / raw)


def extract_text(path: Path) -> str:
    """Plain text of a document file. Only text formats for now."""
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Qo'llab-quvvatlanmaydigan fayl turi: {path.suffix}")
    return path.read_text(encoding="utf-8").lstrip("﻿")


# --- chunking ---------------------------------------------------------------


def _split_blocks(text: str) -> list[tuple[str, str]]:
    """Split into (heading, block) pairs on blank lines, tracking headings.

    Markdown tables and lists survive intact: they contain no blank lines, so
    they stay inside a single block.
    """
    blocks: list[tuple[str, str]] = []
    heading = ""
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            block = "\n".join(buffer).strip()
            if block:
                blocks.append((heading, block))
            buffer.clear()

    for line in text.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            flush()
            heading = match.group(2)
            continue
        if not line.strip():
            flush()
            continue
        buffer.append(line.rstrip())
    flush()
    return blocks


def _split_long_block(block: str, max_chars: int) -> list[str]:
    """Break an oversized paragraph on sentence boundaries (last resort: lines)."""
    pieces = [p for p in _SENTENCE_END_RE.split(block) if p.strip()]
    if len(pieces) == 1:
        pieces = [line for line in block.splitlines() if line.strip()]
    out: list[str] = []
    current = ""
    for piece in pieces:
        candidate = f"{current} {piece}".strip() if current else piece
        if current and len(candidate) > max_chars:
            out.append(current)
            current = piece
        else:
            current = candidate
    if current:
        out.append(current)
    return out or [block[:max_chars]]


def chunk_text(
    text: str,
    title: str = "",
    target_chars: int | None = None,
    max_chars: int | None = None,
) -> list[TextChunk]:
    """Paragraph-aware chunking (~500 tokens), never cutting mid-paragraph.

    Each chunk is prefixed with the document title and its section heading
    before embedding — short chunks ("| 3-juftlik | 11:30 - 12:50 |") are
    meaningless without that context.
    """
    settings = get_settings()
    target = target_chars or settings.chunk_target_chars
    hard_max = max_chars or settings.chunk_max_chars

    chunks: list[TextChunk] = []
    current: list[str] = []
    current_headings: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len, current_headings
        if not current:
            return
        # A chunk may span several sections — cite all of them, not just the first.
        heading = " · ".join(current_headings)
        body = "\n\n".join(current)
        prefix = " — ".join(p for p in (title, heading) if p)
        chunks.append(
            TextChunk(
                order_index=len(chunks),
                heading=heading,
                body=body,
                text=f"{prefix}\n\n{body}" if prefix else body,
            )
        )
        current = []
        current_headings = []
        current_len = 0

    for heading, block in _split_blocks(text):
        parts = (
            _split_long_block(block, hard_max) if len(block) > hard_max else [block]
        )
        for part in parts:
            new_section = heading not in current_headings
            if current and (
                current_len + len(part) > hard_max
                or (new_section and current_len >= target // 2)
                or current_len >= target
            ):
                flush()
            if heading and heading not in current_headings:
                current_headings.append(heading)
            current.append(part)
            current_len += len(part) + 2
    flush()

    # A short tail ("## Итоги главы") is useless on its own — fold it back.
    if len(chunks) > 1 and len(chunks[-1].body) < 300:
        tail = chunks.pop()
        prev = chunks[-1]
        if len(prev.body) + len(tail.body) <= hard_max:
            prev.body = f"{prev.body}\n\n{tail.body}"
            prev.text = f"{prev.text}\n\n{tail.body}"
        else:
            chunks.append(tail)
    return chunks


# --- indexing ---------------------------------------------------------------


def chroma_id(document_id: int, order_index: int) -> str:
    return f"doc{document_id}_c{order_index}"


def _metadata(document: Document, chunk: TextChunk, chunk_row_id: int) -> dict:
    return {
        "document_id": document.id,
        "chunk_id": chunk_row_id,
        "title": document.title,
        "doc_type": document.doc_type.value,
        "language": document.language,
        "access_level": document.access_level.value,
        "order_index": chunk.order_index,
        "heading": chunk.heading,
    }


def delete_document_index(db: Session, document: Document) -> None:
    """Remove a document's chunks from both stores (re-index safety)."""
    get_collection().delete(where={"document_id": document.id})
    db.query(Chunk).filter(Chunk.document_id == document.id).delete(
        synchronize_session=False
    )
    db.flush()


def read_chunks(document: Document) -> list[TextChunk]:
    """File -> text -> chunks. Raises if the file is missing/unsupported."""
    path = document_path(document)
    if not path.exists():
        raise FileNotFoundError(f"Hujjat fayli topilmadi: {path}")
    return chunk_text(extract_text(path), title=document.title)


def _write(
    db: Session,
    document: Document,
    pieces: list[TextChunk],
    vectors: list[list[float]],
) -> int:
    """Persist chunks to SQLite and their vectors to Chroma."""
    delete_document_index(db, document)

    rows = [
        Chunk(document_id=document.id, text=p.body, order_index=p.order_index)
        for p in pieces
    ]
    db.add_all(rows)
    db.flush()  # assigns Chunk.id

    ids = [chroma_id(document.id, p.order_index) for p in pieces]
    for row, cid in zip(rows, ids):
        row.embedding_id = cid

    get_collection().add(
        ids=ids,
        embeddings=vectors,
        documents=[p.body for p in pieces],
        metadatas=[_metadata(document, p, r.id) for p, r in zip(pieces, rows)],
    )
    db.flush()
    return len(pieces)


def ingest_document(db: Session, document: Document) -> int:
    """Index one document (upload / incremental path). Returns chunk count."""
    pieces = read_chunks(document)
    if not pieces:
        return 0
    vectors = embeddings.embed_passages([p.text for p in pieces])
    return _write(db, document, pieces, vectors)


def ingest_all(db: Session, reset: bool = False) -> dict:
    """Index the whole Document table.

    reset=False -> only documents that have no chunks yet (incremental);
    reset=True  -> drop the collection and all Chunk rows, then rebuild. Only
    the full rebuild refits the centering vector, because that needs the whole
    corpus in one batch (see embeddings.py).
    """
    if reset:
        reset_collection()
        embeddings.clear_bias()
        db.query(Chunk).delete(synchronize_session=False)
        db.flush()

    report: dict = {"documents": 0, "chunks": 0, "skipped": [], "missing": []}
    pending: list[tuple[Document, list[TextChunk]]] = []

    for document in db.query(Document).order_by(Document.id).all():
        if not reset:
            has_chunks = (
                db.query(Chunk.id).filter(Chunk.document_id == document.id).first()
            )
            if has_chunks:
                report["skipped"].append(document.title)
                continue
        try:
            pieces = read_chunks(document)
        except (FileNotFoundError, ValueError) as exc:
            report["missing"].append(f"{document.title}: {exc}")
            continue
        if pieces:
            pending.append((document, pieces))

    if pending:
        flat = [p.text for _doc, pieces in pending for p in pieces]
        vectors = embeddings.embed_passages(flat, fit_bias=reset)
        offset = 0
        for document, pieces in pending:
            slice_ = vectors[offset : offset + len(pieces)]
            offset += len(pieces)
            report["chunks"] += _write(db, document, pieces, slice_)
            report["documents"] += 1

    db.commit()
    return report
