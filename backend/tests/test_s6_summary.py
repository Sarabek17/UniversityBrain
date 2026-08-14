"""S6 tests: role-angled summarization + map-reduce + the summary endpoint.

LLM_PROVIDER=mock, so the summary *text* is deterministic filler — what is
verified here is the mechanics: the role angle really reaches the prompt, a long
document really costs several LLM calls, the access rule is the documents one,
and the answer carries its source and the disclaimer.
"""

import pytest

from app.agents.registry import execute_tool
from app.llm.client import LLMResponse
from app.models import Document, User, UserRole
from app.services import documents as documents_service
from app.services import summarization

DEMO_PASSWORD = "demo123"
SECRET_TITLE_PART = "91-M"
SECRET_PHRASE = "XIZMAT FOYDALANISHI UCHUN"

ROLES_UNDER_TEST = (UserRole.student, UserRole.teacher, UserRole.staff)


# --- helpers ----------------------------------------------------------------


class RecordingClient:
    """Stand-in LLM client that records every prompt it is handed."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def chat(self, messages, tools=None, system=None):
        self.calls.append({"messages": messages, "tools": tools, "system": system})
        return LLMResponse(text=f"REZYUME#{len(self.calls)}")

    @property
    def prompts(self) -> list[str]:
        return [c["messages"][-1]["content"] for c in self.calls]


@pytest.fixture
def recorder(monkeypatch):
    """Replace the LLM client *inside the summarization service only*."""
    client = RecordingClient()
    monkeypatch.setattr(summarization, "get_llm_client", lambda: client)
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


def secret_id(client):
    match = [d for d in listed(client, "rashidova") if SECRET_TITLE_PART in d["title"]]
    assert len(match) == 1, match
    return match[0]["id"]


def long_text(parts: int) -> str:
    """Text guaranteed to split into `parts` paragraph-aligned parts."""
    block = "Universitet hujjati bandi. " * 40  # ~1080 chars, no blank lines
    per_part = summarization.PART_CHARS // len(block) + 1
    return "\n\n".join([block] * per_part * parts)


# --- 1. role angle ----------------------------------------------------------


def test_system_and_user_prompts_differ_per_role():
    systems = {r: summarization.system_prompt(r) for r in ROLES_UNDER_TEST}
    prompts = {
        r: summarization.build_summary_prompt(
            title="Buyruq 87", doc_type="order", language="uz", role=r, body="matn"
        )
        for r in ROLES_UNDER_TEST
    }

    assert len(set(systems.values())) == len(ROLES_UNDER_TEST), systems
    assert len(set(prompts.values())) == len(ROLES_UNDER_TEST), prompts

    for role in ROLES_UNDER_TEST:
        focus = summarization.ROLE_FOCUS[role]
        assert focus in systems[role]
        assert focus in prompts[role]
        for point in summarization.ROLE_POINTS[role]:
            assert point in prompts[role]

    # the angles are the ones the spec asks for (FUNKSIONALLIK 3.4)
    assert "muddat" in prompts[UserRole.student]
    assert "raqami" in prompts[UserRole.staff] and "ijrochilar" in prompts[UserRole.staff]
    assert "o'quv jarayoni" in prompts[UserRole.teacher]


def test_role_angle_reaches_the_llm_through_the_tool(recorder, db_session, users):
    seen = {}
    for username in ("aliyev", "umarov", "rashidova"):
        recorder.calls.clear()
        result = execute_tool(
            "hujjat_rezyume", {"nom": "Buyruq 87"}, db_session, users[username]
        )
        assert result.ok is True, result.text
        assert len(recorder.calls) == 1
        seen[username] = (recorder.calls[0]["system"], recorder.prompts[0])

    assert len({s for s, _ in seen.values()}) == 3, seen
    assert len({p for _, p in seen.values()}) == 3, seen
    assert summarization.ROLE_FOCUS[UserRole.student] in seen["aliyev"][1]
    assert summarization.ROLE_FOCUS[UserRole.teacher] in seen["umarov"][1]
    assert summarization.ROLE_FOCUS[UserRole.staff] in seen["rashidova"][1]


def test_every_role_has_its_own_angle():
    for role in UserRole:
        assert summarization.role_focus(role) == summarization.ROLE_FOCUS[role]
        assert summarization.role_points(role) == summarization.ROLE_POINTS[role]
    assert len({summarization.role_focus(r) for r in UserRole}) == len(list(UserRole))


# --- 2. map-reduce ----------------------------------------------------------


def test_short_text_is_one_llm_call(recorder):
    summary, parts, calls, truncated = summarization.summarize_text(
        "Qisqa hujjat matni.",
        title="Qisqa",
        doc_type="other",
        language="uz",
        role=UserRole.student,
    )
    assert (parts, calls, truncated) == (1, 1, False)
    assert len(recorder.calls) == 1
    assert summary == "REZYUME#1"
    assert "ORALIQ QAYDLAR" not in recorder.prompts[0]


def test_long_text_is_map_reduced(recorder):
    text = long_text(3)
    assert len(text) > 2 * summarization.PART_CHARS

    summary, parts, calls, truncated = summarization.summarize_text(
        text, title="Uzun nizom", doc_type="regulation", language="uz", role=UserRole.staff
    )

    assert parts >= 2, "uzun matn bo'linmadi"
    assert calls == parts + 1, "map chaqiruvlari + bitta reduce kutilgan edi"
    assert len(recorder.calls) == calls
    assert truncated is False
    assert summary == f"REZYUME#{calls}"

    # every part carries its own map prompt, the last call is the reduce
    for i, prompt in enumerate(recorder.prompts[:-1], start=1):
        assert f"{i}/{parts}-qismi" in prompt
        assert "QISM MATNI" in prompt
    reduce_prompt = recorder.prompts[-1]
    assert "ORALIQ QAYDLAR" in reduce_prompt
    for i in range(1, parts + 1):
        assert f"[{i}-qism]" in reduce_prompt
        assert f"REZYUME#{i}" in reduce_prompt
    assert summarization.ROLE_FOCUS[UserRole.staff] in reduce_prompt


def test_split_parts_respects_paragraphs_and_the_cap():
    single, truncated = summarization.split_parts("bitta paragraf")
    assert single == ["bitta paragraf"] and truncated is False

    parts, truncated = summarization.split_parts(long_text(4))
    assert len(parts) >= 4 and truncated is False
    assert all(len(p) <= summarization.PART_CHARS for p in parts)
    assert all(not p.startswith("\n") for p in parts)

    capped, truncated = summarization.split_parts(long_text(4), max_parts=2)
    assert len(capped) == 2 and truncated is True

    assert summarization.split_parts("   ") == ([], False)


def test_empty_document_raises(recorder):
    with pytest.raises(summarization.EmptyDocumentError):
        summarization.summarize_text(
            "", title="Bo'sh", doc_type="other", language="uz", role=UserRole.student
        )
    assert recorder.calls == []


def test_a_real_seed_document_triggers_map_reduce(client, db_session):
    """The longest corpus document (the Russian DB textbook) really splits."""
    documents = db_session.query(Document).all()
    biggest = max(
        documents, key=lambda d: len(documents_service.document_text(db_session, d))
    )
    text = documents_service.document_text(db_session, biggest)
    assert len(text) > summarization.PART_CHARS, (biggest.title, len(text))

    res = client.post(
        f"/documents/{biggest.id}/summary", headers=headers(client, "admin")
    )
    assert res.status_code == 200, res.text
    assert res.json()["parts"] >= 2, res.json()


# --- 3. the endpoint: access rule + source + disclaimer ---------------------


def test_student_summarizes_a_public_document(client):
    document = listed(client, "aliyev")[0]
    res = client.post(
        f"/documents/{document['id']}/summary", headers=headers(client, "aliyev")
    )
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["document_id"] == document["id"]
    assert body["title"] == document["title"]
    assert body["summary"].strip()
    assert body["parts"] >= 1
    assert body["source"]["type"] == "document"
    assert body["source"]["document_id"] == document["id"]
    assert document["title"] in body["source"]["label"]
    assert "rasmiy hujjat" in body["disclaimer"]


def test_student_cannot_summarize_the_confidential_order(client):
    res = client.post(
        f"/documents/{secret_id(client)}/summary", headers=headers(client, "aliyev")
    )
    # 404, not 403: the order's existence stays hidden (same rule as the viewer)
    assert res.status_code == 404, res.text
    assert SECRET_PHRASE not in res.text


def test_staff_summarizes_the_confidential_order(client):
    doc_id = secret_id(client)
    res = client.post(f"/documents/{doc_id}/summary", headers=headers(client, "rashidova"))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["document_id"] == doc_id
    assert SECRET_TITLE_PART in body["title"]
    assert body["summary"].strip()


def test_summary_endpoint_404_and_401(client):
    assert client.post("/documents/999999/summary", headers=headers(client, "admin")).status_code == 404
    assert client.post("/documents/1/summary").status_code == 401


# --- 4. the same path through the chat tool ---------------------------------


def test_chat_marker_runs_the_summary_tool_with_source_and_disclaimer(client):
    doc = listed(client, "aliyev")[0]
    res = client.post(
        "/chat",
        json={"message": 'use_tool:hujjat_rezyume:{"hujjat_id": %d}' % doc["id"]},
        headers=headers(client, "aliyev"),
    )
    assert res.status_code == 200, res.text
    answer = res.json()

    assert answer["text"].strip()
    assert "rasmiy hujjat" in answer["disclaimer"]
    assert any(s["document_id"] == doc["id"] for s in answer["sources"]), answer["sources"]

    detail = client.get(
        f"/chat/conversations/{answer['conversation_id']}",
        headers=headers(client, "aliyev"),
    ).json()
    assert any(m["tool_name"] == "hujjat_rezyume" for m in detail["messages"])


def test_tool_still_hides_the_confidential_order_by_title(db_session, users):
    denied = execute_tool(
        "hujjat_rezyume", {"nom": SECRET_TITLE_PART}, db_session, users["aliyev"]
    )
    assert denied.ok is False
    assert SECRET_PHRASE not in denied.text
    assert "topilmadi" in denied.text  # not "ruxsat yo'q": existence stays hidden

    allowed = execute_tool(
        "hujjat_rezyume", {"nom": SECRET_TITLE_PART}, db_session, users["rashidova"]
    )
    assert allowed.ok is True
    assert SECRET_TITLE_PART in allowed.sources[0]["title"]


def test_tool_reports_a_missing_document(db_session, users):
    missing = execute_tool(
        "hujjat_rezyume", {"hujjat_id": 999999}, db_session, users["admin"]
    )
    assert missing.ok is False and "topilmadi" in missing.text

    no_args = execute_tool("hujjat_rezyume", {}, db_session, users["aliyev"])
    assert no_args.ok is False and "nom" in no_args.text
