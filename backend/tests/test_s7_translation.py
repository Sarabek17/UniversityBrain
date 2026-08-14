"""S7 tests: paragraph-aligned translation + term rule + the Translation cache.

LLM_PROVIDER=mock, so the translated *text* is deterministic filler — what is
verified here is the mechanics the domain rules depend on: the original is never
replaced, the paragraph counts line up, the term rule really reaches the prompt,
a second request costs zero LLM calls, and the access rule is the documents one.
"""

import re

import pytest

from app.agents.registry import execute_tool
from app.llm.client import LLMResponse
from app.models import Document, Translation, User
from app.services import translation

DEMO_PASSWORD = "demo123"
SECRET_TITLE_PART = "91-M"
SECRET_PHRASE = "XIZMAT FOYDALANISHI UCHUN"

PROMPT_MARKER_RE = re.compile(r"^\[\[(\d+)\]\]$", re.MULTILINE)


# --- helpers ----------------------------------------------------------------


class RecordingClient:
    """Stand-in LLM client that records every prompt it is handed.

    By default it answers a batched prompt in the `[[n]]` format the prompt
    asks for (the happy path). Set `obey_markers = False` to play a model that
    ignores the format — that must trigger the per-paragraph fallback.
    """

    def __init__(self, obey_markers: bool = True) -> None:
        self.calls: list[dict] = []
        self.obey_markers = obey_markers

    def chat(self, messages, tools=None, system=None):
        self.calls.append({"messages": messages, "tools": tools, "system": system})
        prompt = messages[-1]["content"]
        indices = PROMPT_MARKER_RE.findall(prompt)
        if self.obey_markers and indices:
            return LLMResponse(
                text="\n\n".join(f"[[{i}]]\nTARJIMA-{i}" for i in indices)
            )
        return LLMResponse(text=f"TARJIMA#{len(self.calls)}")

    @property
    def prompts(self) -> list[str]:
        return [c["messages"][-1]["content"] for c in self.calls]


@pytest.fixture
def recorder(monkeypatch):
    """Replace the LLM client *inside the translation service only*."""
    client = RecordingClient()
    monkeypatch.setattr(translation, "get_llm_client", lambda: client)
    return client


@pytest.fixture(scope="module")
def users(db_session):
    def get(username):
        return db_session.query(User).filter_by(username=username).one()

    return {n: get(n) for n in ("aliyev", "umarov", "rashidova", "admin")}


def headers(client, username):
    res = client.post(
        "/auth/login", json={"username": username, "password": DEMO_PASSWORD}
    )
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def listed(client, username):
    res = client.get("/documents", headers=headers(client, username))
    assert res.status_code == 200, res.text
    return res.json()


def foreign_document(client, language="en"):
    """A document that is really in another language (the ML chapter)."""
    match = [d for d in listed(client, "aliyev") if d["language"] == language]
    assert match, f"{language} tilidagi hujjat topilmadi"
    return match[0]


def secret_id(client):
    match = [d for d in listed(client, "rashidova") if SECRET_TITLE_PART in d["title"]]
    assert len(match) == 1, match
    return match[0]["id"]


def clear_cache(db, document_id=None, language=None):
    query = db.query(Translation)
    if document_id is not None:
        query = query.filter(Translation.document_id == document_id)
    if language is not None:
        query = query.filter(Translation.language == language)
    query.delete(synchronize_session=False)
    db.commit()


def post_translate(client, document_id, username, language="uz"):
    return client.post(
        f"/documents/{document_id}/translate?target_language={language}",
        headers=headers(client, username),
    )


def sample_text(paragraphs: int) -> str:
    return "\n\n".join(
        f"Paragraf {i}: universitet hujjatining bandi." for i in range(1, paragraphs + 1)
    )


# --- 1. paragraph alignment (the two columns line up) -----------------------


def test_split_and_normalize_paragraphs():
    assert translation.split_paragraphs("bir\n\n\n  ikki  \n\n") == ["bir", "ikki"]
    assert translation.split_paragraphs("") == []
    # a translated paragraph must not carry a blank line: the cache round-trips
    # by splitting on exactly that.
    collapsed = translation.normalize_paragraph("a\n\n b \n\n\nc")
    assert collapsed == "a\n b \nc"
    assert len(translation.split_paragraphs(collapsed)) == 1


def test_translation_keeps_the_paragraph_count(recorder):
    originals = translation.split_paragraphs(sample_text(9))
    translated, calls = translation.translate_paragraphs(
        originals, title="Sinov", source_language="en", target_language="uz"
    )
    assert len(translated) == len(originals) == 9
    assert calls == len(translation.batch_paragraphs(originals))  # one batch here
    assert translated == [f"TARJIMA-{i}" for i in range(1, 10)]


def test_fallback_keeps_the_count_when_the_model_ignores_the_markers(monkeypatch):
    client = RecordingClient(obey_markers=False)
    monkeypatch.setattr(translation, "get_llm_client", lambda: client)

    originals = translation.split_paragraphs(sample_text(6))
    translated, calls = translation.translate_paragraphs(
        originals, title="Sinov", source_language="en", target_language="uz"
    )
    assert len(translated) == len(originals) == 6
    # 1 batch call that came back unusable + 6 single-paragraph calls
    assert calls == 7
    assert len(set(translated)) == 6, translated


def test_batch_response_parsing_is_strict():
    good = "[[1]]\nbir\n\n[[2]]\nikki"
    assert translation.parse_batch_response(good, 2) == ["bir", "ikki"]

    assert translation.parse_batch_response(good, 3) is None  # wrong count
    assert translation.parse_batch_response("bir\n\nikki", 2) is None  # no markers
    assert translation.parse_batch_response("[[2]]\nbir\n\n[[1]]\nikki", 2) is None
    assert translation.parse_batch_response("[[1]]\n\n[[2]]\nikki", 2) is None  # empty


def test_long_text_is_split_into_batches():
    paragraphs = ["x" * 900] * 10
    batches = translation.batch_paragraphs(paragraphs)
    assert len(batches) > 1
    assert [i for b in batches for i in b] == list(range(10))  # order kept, nothing lost


# --- 2. the term rule reaches the prompt (domain rule 4) --------------------


def test_term_rule_is_in_every_prompt_and_in_the_system_prompt():
    prompts = [
        translation.system_prompt("uz"),
        translation.build_batch_prompt(
            title="T", source_language="en", target_language="uz", paragraphs=["a", "b"]
        ),
        translation.build_paragraph_prompt(
            title="T", source_language="en", target_language="uz", paragraph="a"
        ),
    ]
    for prompt in prompts:
        assert "qavs ichida" in prompt, prompt
        assert "(machine learning)" in prompt, prompt
        assert "o'zgartirmasdan ko'chir" in prompt, prompt


def test_term_rule_reaches_the_llm_through_the_service(recorder, db_session, users):
    document = (
        db_session.query(Document).filter_by(language="en").first()
    )
    assert document is not None
    clear_cache(db_session, document.id, "uz")

    translation.translate_document(db_session, document, users["aliyev"], "uz")
    assert recorder.calls, "LLM chaqirilmadi"
    for prompt in recorder.prompts:
        assert "(machine learning)" in prompt
    for call in recorder.calls:
        assert "qavs ichida" in call["system"]


# --- 3. the cache: second request costs zero LLM calls ----------------------


def test_second_translation_comes_from_the_cache(client, db_session, recorder):
    document = foreign_document(client)
    clear_cache(db_session, document["id"], "uz")

    first = post_translate(client, document["id"], "aliyev")
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["cached"] is False
    used = len(recorder.calls)
    assert used > 0, "birinchi tarjima LLM ni chaqirmadi"

    second = post_translate(client, document["id"], "aliyev")
    assert second.status_code == 200, second.text
    second_body = second.json()

    assert len(recorder.calls) == used, "kesh ishlamadi: LLM qayta chaqirildi"
    assert second_body["cached"] is True
    assert second_body["paragraphs"] == first_body["paragraphs"]

    db_session.rollback()  # drop this session's snapshot before re-reading
    rows = (
        db_session.query(Translation)
        .filter(Translation.document_id == document["id"], Translation.language == "uz")
        .all()
    )
    assert len(rows) == 1, "kesh qatori takrorlandi"


def test_stale_cache_is_rebuilt(db_session, users, recorder):
    document = db_session.query(Document).filter_by(language="en").first()
    translation.store_translation(db_session, document.id, "uz", ["faqat bitta"])

    result = translation.translate_document(db_session, document, users["aliyev"], "uz")

    assert result.cached is False, "eski (mos kelmaydigan) kesh ishlatildi"
    assert len(result.paragraphs) > 1
    assert result.llm_calls > 0
    clear_cache(db_session, document.id, "uz")


# --- 4. the endpoint: original preserved, access rule, source ---------------


def test_endpoint_returns_aligned_pairs_and_keeps_the_original(client, db_session):
    document = foreign_document(client)
    clear_cache(db_session, document["id"], "uz")

    res = post_translate(client, document["id"], "aliyev")
    assert res.status_code == 200, res.text
    body = res.json()

    detail = client.get(
        f"/documents/{document['id']}", headers=headers(client, "aliyev")
    ).json()
    originals = translation.split_paragraphs(detail["text"])

    assert body["paragraph_count"] == len(body["paragraphs"]) == len(originals)
    assert [p["original"] for p in body["paragraphs"]] == originals
    assert [p["index"] for p in body["paragraphs"]] == list(
        range(1, len(originals) + 1)
    )
    assert all(p["translated"].strip() for p in body["paragraphs"])

    assert body["source_language"] == "en"
    assert body["target_language"] == "uz"
    assert body["same_language"] is False
    assert body["truncated"] is False
    assert body["source"]["type"] == "document"
    assert body["source"]["document_id"] == document["id"]
    assert "rasmiy hujjat" in body["disclaimer"]


def test_same_language_document_is_not_sent_to_the_llm(client, db_session, recorder):
    uzbek = [d for d in listed(client, "aliyev") if d["language"] == "uz"][0]
    res = post_translate(client, uzbek["id"], "aliyev")
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["same_language"] is True
    assert recorder.calls == []
    assert all(p["original"] == p["translated"] for p in body["paragraphs"])

    db_session.rollback()
    assert (
        db_session.query(Translation).filter_by(document_id=uzbek["id"]).count() == 0
    ), "kerak bo'lmagan tarjima keshga yozildi"


def test_student_cannot_translate_the_confidential_order(client):
    res = post_translate(client, secret_id(client), "aliyev")
    # 404, not 403: the order's existence stays hidden (same rule as the viewer)
    assert res.status_code == 404, res.text
    assert SECRET_PHRASE not in res.text


def test_staff_translates_the_confidential_order(client, db_session):
    doc_id = secret_id(client)
    clear_cache(db_session, doc_id, "en")
    res = post_translate(client, doc_id, "rashidova", language="en")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["document_id"] == doc_id
    assert body["target_language"] == "en"
    assert body["paragraph_count"] > 0


def test_endpoint_rejects_an_unknown_language(client):
    document = foreign_document(client)
    res = post_translate(client, document["id"], "aliyev", language="fr")
    assert res.status_code == 400, res.text


def test_translate_endpoint_404_and_401(client):
    assert (
        post_translate(client, 999999, "admin").status_code == 404
    ), "mavjud bo'lmagan hujjat"
    assert client.post("/documents/1/translate").status_code == 401


# --- 5. the same path through the chat tool ---------------------------------


def test_tool_returns_translation_with_the_original_and_a_source(
    db_session, users, client
):
    document = foreign_document(client)
    result = execute_tool(
        "tarjima_qil", {"hujjat_id": document["id"]}, db_session, users["aliyev"]
    )
    assert result.ok is True, result.text
    assert "[asl]" in result.text and "[tarjima]" in result.text
    assert result.sources and result.sources[0]["document_id"] == document["id"]
    assert "original" in result.sources[0]["label"].lower()


def test_tool_finds_the_document_by_title_and_rejects_a_bad_language(
    db_session, users, client
):
    by_title = execute_tool(
        "tarjima_qil", {"nom": "Machine Learning"}, db_session, users["aliyev"]
    )
    assert by_title.ok is True, by_title.text

    bad = execute_tool(
        "tarjima_qil", {"nom": "Machine Learning", "til": "de"}, db_session, users["aliyev"]
    )
    assert bad.ok is False and "qo'llab-quvvatlanmaydi" in bad.text


def test_tool_still_hides_the_confidential_order_by_title(db_session, users):
    denied = execute_tool(
        "tarjima_qil", {"nom": SECRET_TITLE_PART}, db_session, users["aliyev"]
    )
    assert denied.ok is False
    assert SECRET_PHRASE not in denied.text
    assert "topilmadi" in denied.text  # not "ruxsat yo'q": existence stays hidden

    allowed = execute_tool(
        "tarjima_qil",
        {"nom": SECRET_TITLE_PART, "til": "en"},
        db_session,
        users["rashidova"],
    )
    assert allowed.ok is True
    assert SECRET_TITLE_PART in allowed.sources[0]["title"]


def test_chat_marker_runs_the_translation_tool(client):
    document = foreign_document(client)
    res = client.post(
        "/chat",
        json={"message": 'use_tool:tarjima_qil:{"hujjat_id": %d}' % document["id"]},
        headers=headers(client, "aliyev"),
    )
    assert res.status_code == 200, res.text
    answer = res.json()

    assert answer["text"].strip()
    assert "rasmiy hujjat" in answer["disclaimer"]
    assert any(s["document_id"] == document["id"] for s in answer["sources"])

    detail = client.get(
        f"/chat/conversations/{answer['conversation_id']}",
        headers=headers(client, "aliyev"),
    ).json()
    assert any(m["tool_name"] == "tarjima_qil" for m in detail["messages"])


def test_cross_language_rule_is_in_the_shared_prompt():
    from app.agents.orchestrator import load_system_prompt
    from app.models import UserRole

    prompt = load_system_prompt(UserRole.student)
    assert "tarjima_qil" in prompt
    assert "(machine learning)" in prompt
