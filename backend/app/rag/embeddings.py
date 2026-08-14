"""THE single place where text is turned into vectors (CLAUDE.md rule).

No other module imports sentence-transformers / any embedding SDK directly, so
swapping the model (or moving to a hosted embedding API) is a one-file change.

Model is chosen in `config.py` (`EMBEDDING_MODEL`). It must be multilingual:
an Uzbek question has to retrieve English and Russian documents as well.
Loading is lazy and cached — the first call downloads/loads the model (slow),
every later call reuses it.

Mean centering (`EMBEDDING_CENTER`)
-----------------------------------
Multilingual embedding spaces are anisotropic: every vector shares one big
common direction, so *all* cosine similarities sit in a narrow band (0.79-0.87
on our corpus) and the language of the text dominates the little variance that
is left. The practical effect: the Uzbek question "mashinaviy o'qitish nima?"
ranked 12th against the English ML chapter, behind unrelated Uzbek documents.

Subtracting the corpus mean before comparing removes that direction. Measured
on the seed corpus (16 queries, top-1 hits): e5-small 12/16 -> 15/16,
e5-base 12/16 -> 15/16. e5-small is therefore enough, and 3x faster.

The mean ("bias") is computed over all chunks during a full re-index and
stored next to the vector store; queries are centered with the same vector.
Without a stored bias the module falls back to plain embeddings.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from app.config import get_settings

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sentence_transformers import SentenceTransformer

BIAS_FILENAME = "embedding_bias.json"

_model: "SentenceTransformer | None" = None
_lock = threading.Lock()
_bias: np.ndarray | None = None
_bias_loaded = False


def model_name() -> str:
    return get_settings().embedding_model


def get_model() -> "SentenceTransformer":
    """Load (once) and return the sentence-transformers model."""
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(model_name())
    return _model


def embedding_dimension() -> int:
    model = get_model()
    # renamed in sentence-transformers 5.x; keep working on older versions too
    getter = getattr(model, "get_embedding_dimension", None) or (
        model.get_sentence_embedding_dimension
    )
    return int(getter())


def max_input_tokens() -> int:
    """Model input window — chunking must stay below it or text is truncated."""
    return int(get_model().max_seq_length)


def count_tokens(text: str) -> int:
    """Token count with the model's own tokenizer (used to check chunk sizes)."""
    return len(get_model().tokenizer.encode(text, add_special_tokens=False))


# --- centering bias ---------------------------------------------------------


def bias_path() -> Path:
    from app.rag.store import chroma_dir

    return chroma_dir() / BIAS_FILENAME


def load_bias() -> np.ndarray | None:
    """Read the stored corpus mean (cached). None if absent or stale."""
    global _bias, _bias_loaded
    if _bias_loaded:
        return _bias
    _bias_loaded = True
    path = bias_path()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("model") == model_name():
                _bias = np.asarray(data["vector"], dtype=np.float32)
        except (ValueError, KeyError, OSError):
            _bias = None
    return _bias


def save_bias(vector: np.ndarray) -> None:
    global _bias, _bias_loaded
    path = bias_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "model": model_name(),
                "dim": int(vector.shape[0]),
                "vector": [float(x) for x in vector],
            }
        ),
        encoding="utf-8",
    )
    _bias = np.asarray(vector, dtype=np.float32)
    _bias_loaded = True


def clear_bias() -> None:
    """Forget the stored bias (full re-index recomputes it)."""
    global _bias, _bias_loaded
    _bias, _bias_loaded = None, False
    path = bias_path()
    if path.exists():
        path.unlink()


def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.maximum(norms, 1e-12)


def _apply_bias(matrix: np.ndarray) -> np.ndarray:
    if not get_settings().embedding_center:
        return matrix
    bias = load_bias()
    if bias is None or bias.shape[0] != matrix.shape[1]:
        return matrix
    return _normalize(matrix - bias)


# --- encoding ---------------------------------------------------------------


def _encode_raw(texts: list[str], prefix: str) -> np.ndarray:
    model = get_model()
    prepared = [prefix + t for t in texts] if prefix else list(texts)
    return model.encode(
        prepared,
        normalize_embeddings=True,  # cosine similarity == dot product
        show_progress_bar=False,
        convert_to_numpy=True,
    )


def embed_passages(texts: list[str], fit_bias: bool = False) -> list[list[float]]:
    """Embed document chunks (indexing side).

    `fit_bias=True` (full re-index only) recomputes and stores the centering
    vector from exactly these texts before centering them.
    """
    if not texts:
        return []
    raw = _encode_raw(texts, get_settings().embedding_passage_prefix)
    if fit_bias and get_settings().embedding_center:
        save_bias(raw.mean(axis=0))
    return [v.tolist() for v in _apply_bias(raw)]


def embed_query(text: str) -> list[float]:
    """Embed a user question (search side)."""
    raw = _encode_raw([text], get_settings().embedding_query_prefix)
    return _apply_bias(raw)[0].tolist()
