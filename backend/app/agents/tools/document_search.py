"""`hujjat_qidir` — RAG search over the document corpus (S3 pipeline).

Open to every role: the role filter lives *inside* `rag.search` (Chroma
metadata filter), so a chunk the user may not see is never scored and never
reaches the model. Nothing extra to check here.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.registry import ALL_ROLES, Tool, ToolResult, register
from app.models import User
from app.rag.search import SearchResult, search

NAME = "hujjat_qidir"

DEFAULT_TOP_K = 5
MAX_TOP_K = 8
SNIPPET_CHARS = 700  # per hit, so several hits still fit the model's context


def _snippet(text: str) -> str:
    text = (text or "").strip()
    if len(text) <= SNIPPET_CHARS:
        return text
    return text[:SNIPPET_CHARS].rstrip() + " […]"


def citation(result: SearchResult) -> dict:
    """Source entry for the answer (document + section + chunk position)."""
    where = result.title
    if result.heading:
        where = f"{where} — {result.heading}"
    return {
        "type": "document",
        "label": f"{where} ({result.order_index + 1}-bo'lak)",
        "document_id": result.document_id,
        "title": result.title,
        "heading": result.heading or None,
        "order_index": result.order_index,
        "chunk_id": result.chunk_id,
    }


def handler(db: Session, user: User, args: dict) -> ToolResult:
    query = str(args.get("query") or "").strip()
    if not query:
        return ToolResult(text="Qidiruv so'rovi bo'sh — 'query' berilishi kerak.", ok=False)

    try:
        top_k = int(args.get("top_k") or DEFAULT_TOP_K)
    except (TypeError, ValueError):
        top_k = DEFAULT_TOP_K
    top_k = max(1, min(top_k, MAX_TOP_K))

    results = search(query, user, top_k=top_k)
    if not results:
        return ToolResult(
            text=(
                f"'{query}' bo'yicha sizga ochiq hujjatlardan hech narsa topilmadi. "
                "Foydalanuvchiga ma'lumot topilmaganini ayting, o'ylab topmang."
            )
        )

    blocks = []
    for i, result in enumerate(results, start=1):
        head = result.title
        if result.heading:
            head = f"{head} — {result.heading}"
        blocks.append(
            f"[{i}] {head} ({result.order_index + 1}-bo'lak, "
            f"moslik {result.score:.2f})\n{_snippet(result.text)}"
        )

    return ToolResult(
        text="Topilgan hujjat bo'laklari:\n\n" + "\n\n".join(blocks),
        sources=[citation(r) for r in results],
    )


register(
    Tool(
        name=NAME,
        description=(
            "Universitet hujjatlari bazasidan (sillabus, topshiriqlar, nizom, "
            "buyruqlar, adabiyot) semantik qidiruv. Foydalanuvchining hujjatga "
            "oid har qanday savolida shu vositani ishlat. Natija — hujjat "
            "bo'laklari, nomi va bo'limi bilan."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Qidiruv so'rovi (foydalanuvchi savoli yoki kalit so'zlar).",
                },
                "top_k": {
                    "type": "integer",
                    "description": f"Nechta bo'lak qaytarilsin (1-{MAX_TOP_K}, default {DEFAULT_TOP_K}).",
                    "minimum": 1,
                    "maximum": MAX_TOP_K,
                },
            },
            "required": ["query"],
        },
        handler=handler,
        roles=ALL_ROLES,
    )
)
