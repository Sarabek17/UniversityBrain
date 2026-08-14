"""Index the seed document corpus into Chroma + SQLite.

Usage (from backend/, venv active):
    python -m seed.ingest_documents            # index documents with no chunks
    python -m seed.ingest_documents --reset    # wipe the collection and rebuild

Run it after `python -m seed.generate --reset` (that command clears the Chunk
table, so the corpus has to be re-indexed).
"""

import argparse
import sys

from app.db import SessionLocal, init_db
from app.rag import embeddings
from app.rag.ingest import ingest_all
from app.rag.store import chroma_dir, collection_count


def main() -> int:
    parser = argparse.ArgumentParser(description="UniAgent document indexer")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="drop the Chroma collection and all Chunk rows, then re-index",
    )
    args = parser.parse_args()

    init_db()
    print(f"Embedding modeli: {embeddings.model_name()} (yuklanmoqda...)")
    print(
        f"  o'lchov: {embeddings.embedding_dimension()}, "
        f"maksimal kirish: {embeddings.max_input_tokens()} token"
    )
    print(f"Chroma papkasi: {chroma_dir()}")

    db = SessionLocal()
    try:
        report = ingest_all(db, reset=args.reset)
    finally:
        db.close()

    for title in report["skipped"]:
        print(f"  o'tkazib yuborildi (allaqachon indekslangan): {title}")
    for problem in report["missing"]:
        print(f"  XATO: {problem}")

    print(
        f"\nIndekslandi: {report['documents']} hujjat, "
        f"{report['chunks']} bo'lak (chunk)."
    )
    print(f"Chroma kolleksiyasidagi vektorlar soni: {collection_count()}")
    if report["missing"]:
        print("XATO: ba'zi hujjatlar indekslanmadi!")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
