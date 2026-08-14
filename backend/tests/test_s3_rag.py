"""S3 tests: multilingual retrieval + access-level filtering.

The `indexed_corpus` fixture (conftest) loads the embedding model and indexes
the whole seed corpus once per session — the first test is slow on purpose.
"""

import pytest

from app.models import User
from app.rag.search import search

SECRET_TITLE_PART = "91-M"


@pytest.fixture(scope="session")
def users(db_session, indexed_corpus):
    """Demo users by username (see PROGRESS.md heroes)."""

    def get(username):
        return db_session.query(User).filter_by(username=username).one()

    return {
        name: get(name)
        for name in ("aliyev", "umarov", "nazarova", "rashidova", "admin")
    }


def titles(results):
    return [r.title for r in results]


def test_uzbek_question_finds_uzbek_regulation(users):
    """"Juftlik vaqtlari" -> ichki tartib nizomi (3.1-band jadvali)."""
    results = search("juftlik vaqtlari qanday, dars soat nechchida boshlanadi?",
                     users["aliyev"], top_k=5)
    assert results, "hech narsa topilmadi"
    top = results[0]
    assert "ichki tartib" in top.title.lower(), titles(results)
    assert "08:30" in top.text, top.text[:200]  # the pair-times table (3.1)
    assert top.language == "uz"


def test_uzbek_question_finds_english_ml_document(users):
    """Cross-lingual retrieval: Uzbek question -> English ML chapter."""
    results = search("mashinaviy o'qitish nima?", users["aliyev"], top_k=5)
    assert results
    found = [r for r in results if r.document_id and "Machine Learning" in r.title]
    assert found, f"inglizcha hujjat topilmadi: {titles(results)}"
    assert found[0].language == "en"


def test_result_carries_document_identity(users):
    """Every hit must be citable: title + document_id + position + score."""
    results = search("SQL so'rovlar topshirig'i", users["aliyev"], top_k=3)
    assert results
    for r in results:
        assert r.document_id > 0
        assert r.title
        assert r.text.strip()
        assert r.order_index >= 0
        assert 0.0 <= r.score <= 1.0  # blended semantic + keyword relevance
        assert r.chunk_id is not None
    assert results == sorted(results, key=lambda r: -r.score)


def test_student_never_sees_staff_only_order(users):
    """Direct hunt for the confidential order must return nothing of it."""
    queries = [
        "attestatsiya buyrug'i",
        "Buyruq 91-M",
        "o'qituvchilar attestatsiyasi komissiyasi tarkibi",
        "xizmat foydalanishi uchun buyruq",
    ]
    for query in queries:
        results = search(query, users["aliyev"], top_k=10)
        assert all(SECRET_TITLE_PART not in r.title for r in results), (
            f"maxfiy hujjat talabaga chiqdi: {query} -> {titles(results)}"
        )
        assert all(r.access_level == "public" for r in results), titles(results)


@pytest.mark.parametrize("username", ["umarov", "nazarova"])
def test_teacher_and_tutor_also_blocked_from_staff_order(users, username):
    results = search("attestatsiya buyrug'i 91-M", users[username], top_k=10)
    assert all(SECRET_TITLE_PART not in r.title for r in results), titles(results)


def test_staff_finds_the_confidential_order(users):
    results = search("attestatsiya buyrug'i", users["rashidova"], top_k=5)
    assert results
    hits = [r for r in results if SECRET_TITLE_PART in r.title]
    assert hits, f"staff maxfiy hujjatni topmadi: {titles(results)}"
    assert hits[0].access_level == "staff"


def test_admin_sees_everything(users):
    results = search("attestatsiya buyrug'i", users["admin"], top_k=5)
    assert any(SECRET_TITLE_PART in r.title for r in results), titles(results)


def test_empty_query_returns_nothing(users):
    assert search("   ", users["aliyev"]) == []
