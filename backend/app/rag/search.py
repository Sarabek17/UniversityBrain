"""Role-filtered semantic search over the document corpus.

Order matters: the access filter is applied **inside** the vector query
(Chroma metadata filter), not on the results — a chunk the user may not see is
never scored, never returned, never reaches the LLM.

Access rule (PROGRESS.md, S1 corpus tagging):
    - `public` documents      -> every authenticated role
    - role-tagged documents   -> only that role
    - admin                   -> everything (no filter)

Ranking is hybrid: the vector store returns a candidate pool (semantic, works
across languages), then the candidates are re-ranked with an IDF-weighted
keyword overlap. Semantics alone confuse "qaysi haftada oraliq nazorat bor"
with an unrelated document; keywords alone cannot match an Uzbek question to an
English chapter. Measured on the seed corpus (24 queries, top-1 hits):
14/24 plain vectors -> 16/24 with centering -> 19/24 with centering + keywords.

S4 wraps this as the `hujjat_qidir` tool:

    from app.rag.search import search
    results = search("juftlik vaqtlari", user, top_k=5)
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass

from app.config import get_settings
from app.models import AccessLevel, User, UserRole
from app.rag import embeddings
from app.rag.store import get_collection

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_MIN_TOKEN_LEN = 3


@dataclass
class SearchResult:
    """One retrieved chunk with everything a citation needs."""

    document_id: int
    title: str
    text: str
    order_index: int  # position of the chunk inside the document
    score: float  # blended relevance, higher is better
    heading: str  # section(s) of the document the chunk covers
    language: str
    doc_type: str
    access_level: str
    chunk_id: int | None

    def as_dict(self) -> dict:
        return asdict(self)


# --- access filter ----------------------------------------------------------


def allowed_access_levels(user: User) -> list[str] | None:
    """Access levels visible to this user. None = unrestricted (admin)."""
    if user.role == UserRole.admin:
        return None
    levels = {AccessLevel.public.value}
    if user.role.value in AccessLevel.__members__:
        levels.add(user.role.value)
    return sorted(levels)


def _where_filter(user: User) -> dict | None:
    levels = allowed_access_levels(user)
    if levels is None:
        return None
    return {"access_level": {"$in": levels}}


# --- lexical re-ranking -----------------------------------------------------


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if len(t) >= _MIN_TOKEN_LEN]


def _lexical_scores(query: str, texts: list[str]) -> list[float]:
    """Share of the query's IDF mass that each candidate text covers (0..1)."""
    query_tokens = set(_tokens(query))
    if not query_tokens or not texts:
        return [0.0] * len(texts)

    token_sets = [set(_tokens(t)) for t in texts]
    n = len(texts)
    default_idf = math.log(1 + n)
    idf = {}
    for token in query_tokens:
        hits = sum(1 for s in token_sets if token in s)
        idf[token] = math.log(1 + n / hits) if hits else default_idf

    total = sum(idf.values())
    if total <= 0:
        return [0.0] * len(texts)
    return [
        sum(idf[t] for t in query_tokens if t in s) / total for s in token_sets
    ]


def _clipped(values: list[float]) -> list[float]:
    """Keep the raw cosine, only clip to [0, 1].

    Deliberately *not* min-max normalized over the candidate pool: that would
    stretch the best candidate to 1.0 even when it is a weak match, and a weak
    off-topic hit would then outrank a decent on-topic one.
    """
    return [min(max(v, 0.0), 1.0) for v in values]


# --- search -----------------------------------------------------------------


def search(query: str, user: User, top_k: int = 5) -> list[SearchResult]:
    """Semantic search restricted to what `user` is allowed to see."""
    if not query or not query.strip():
        return []

    settings = get_settings()
    collection = get_collection()
    total = collection.count()
    if total == 0:
        return []

    n_candidates = min(
        total,
        max(top_k * settings.search_candidate_factor, settings.search_min_candidates),
    )
    kwargs = {
        "query_embeddings": [embeddings.embed_query(query)],
        "n_results": n_candidates,
        "include": ["documents", "metadatas", "distances"],
    }
    where = _where_filter(user)
    if where is not None:
        kwargs["where"] = where

    raw = collection.query(**kwargs)
    texts = (raw.get("documents") or [[]])[0]
    metadatas = (raw.get("metadatas") or [[]])[0]
    distances = (raw.get("distances") or [[]])[0]
    if not texts:
        return []

    similarities = [1.0 - float(d) for d in distances]  # cosine distance -> cosine
    semantic = _clipped(similarities)
    lexical = _lexical_scores(query, list(texts))
    weight = settings.search_lexical_weight

    scored = []
    for i, (text, meta) in enumerate(zip(texts, metadatas)):
        meta = meta or {}
        blended = (1.0 - weight) * semantic[i] + weight * lexical[i]
        scored.append(
            (
                blended,
                SearchResult(
                    document_id=int(meta.get("document_id", 0)),
                    title=str(meta.get("title", "")),
                    text=text or "",
                    order_index=int(meta.get("order_index", 0)),
                    score=round(blended, 4),
                    heading=str(meta.get("heading", "")),
                    language=str(meta.get("language", "")),
                    doc_type=str(meta.get("doc_type", "")),
                    access_level=str(meta.get("access_level", "")),
                    chunk_id=int(meta["chunk_id"]) if meta.get("chunk_id") else None,
                ),
            )
        )

    scored.sort(key=lambda pair: -pair[0])
    return [result for _score, result in scored[:top_k]]
