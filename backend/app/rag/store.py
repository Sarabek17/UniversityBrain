"""Chroma vector store access — the only module that talks to chromadb.

Collection name and persist directory come from `config.py`
(`CHROMA_COLLECTION`, `CHROMA_PATH`, relative paths resolve against backend/).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

_client: Any = None


def chroma_dir() -> Path:
    raw = Path(get_settings().chroma_path)
    return raw if raw.is_absolute() else (BACKEND_DIR / raw).resolve()


def get_client() -> Any:
    """Persistent Chroma client (cached per process)."""
    global _client
    if _client is None:
        import chromadb

        path = chroma_dir()
        path.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(path))
    return _client


def get_collection() -> Any:
    """The document-chunk collection (cosine space, embeddings supplied by us)."""
    return get_client().get_or_create_collection(
        name=get_settings().chroma_collection,
        metadata={"hnsw:space": "cosine"},
        embedding_function=None,
    )


def reset_collection() -> Any:
    """Drop and recreate the collection (used by ingest --reset)."""
    client = get_client()
    try:
        client.delete_collection(name=get_settings().chroma_collection)
    except Exception:  # collection did not exist yet
        pass
    return get_collection()


def collection_count() -> int:
    return int(get_collection().count())
