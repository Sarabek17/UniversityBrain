"""S4 tests: agent core, tool registry permissions, chat history, RBAC.

Needs `indexed_corpus` (S3 fixture) — the chat flow really searches the vector
store; nothing here is stubbed except the LLM provider (LLM_PROVIDER=mock,
deterministic).
"""

import pytest

from app.agents.registry import Tool, ToolResult, execute_tool, register, tools_for_role, unregister
from app.models import User, UserRole

DEMO_PASSWORD = "demo123"
SECRET_TITLE_PART = "91-M"
# Phrases that exist ONLY inside the confidential order (buyruq 91-M)
SECRET_PHRASES = ["Ne'matov", "Hakimova", "XIZMAT FOYDALANISHI UCHUN"]

PROBE_TOOL = "s4_probe_staff_only"


@pytest.fixture(scope="module")
def chat_client(client, indexed_corpus):
    """TestClient with the corpus indexed (the agent really searches)."""
    return client


@pytest.fixture(scope="module")
def users(db_session):
    def get(username):
        return db_session.query(User).filter_by(username=username).one()

    return {n: get(n) for n in ("aliyev", "karimov", "rashidova", "admin", "umarov")}


def headers(client, username):
    res = client.post(
        "/auth/login", json={"username": username, "password": DEMO_PASSWORD}
    )
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def ask(client, username, message, conversation_id=None):
    body = {"message": message}
    if conversation_id is not None:
        body["conversation_id"] = conversation_id
    res = client.post("/chat", json=body, headers=headers(client, username))
    assert res.status_code == 200, res.text
    return res.json()


def messages_of(client, username, conversation_id):
    res = client.get(
        f"/chat/conversations/{conversation_id}", headers=headers(client, username)
    )
    assert res.status_code == 200, res.text
    return res.json()["messages"]


# --- 1. the DoD flow --------------------------------------------------------


def test_student_chat_answers_with_sources_and_tool_call(chat_client):
    answer = ask(
        chat_client, "aliyev", "Ma'lumotlar bazasi fanidan topshiriq nima edi?"
    )
    assert answer["text"].strip()
    assert answer["sources"], "javobda manba yo'q"
    assert "rasmiy hujjat" in answer["disclaimer"]

    top = answer["sources"][0]
    assert top["type"] == "document"
    assert top["document_id"] and top["title"] and top["label"]

    tool_messages = [
        m for m in messages_of(chat_client, "aliyev", answer["conversation_id"])
        if m["role"] == "tool"
    ]
    assert tool_messages, "hech qanday vosita chaqirilmadi"
    assert any(m["tool_name"] == "hujjat_qidir" for m in tool_messages)


# --- 2. confidential document stays invisible in chat -----------------------


def test_student_chat_never_leaks_confidential_order(chat_client):
    for question in (
        "Buyruq 91-M nima haqida?",
        "O'qituvchilar attestatsiyasi komissiyasi tarkibi kim?",
    ):
        answer = ask(chat_client, "aliyev", question)
        for phrase in SECRET_PHRASES:
            assert phrase not in answer["text"], (question, answer["text"])
        assert all(
            SECRET_TITLE_PART not in (s.get("title") or "")
            for s in answer["sources"]
        ), answer["sources"]


def test_staff_chat_finds_the_confidential_order(chat_client):
    answer = ask(chat_client, "rashidova", "Attestatsiya buyrug'i haqida ayting")
    assert any(
        SECRET_TITLE_PART in (s.get("title") or "") for s in answer["sources"]
    ), answer["sources"]


# --- 3. registry: backend-level permission ----------------------------------


@pytest.fixture
def probe_tool():
    """A staff-only tool that records whether its handler ever ran."""
    state = {"ran": 0}

    def handler(db, user, args):
        state["ran"] += 1
        return ToolResult(text="probe bajarildi")

    register(
        Tool(
            name=PROBE_TOOL,
            description="Test uchun: faqat dekanat roliga ochiq vosita.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=handler,
            roles=(UserRole.staff,),
        )
    )
    try:
        yield state
    finally:
        unregister(PROBE_TOOL)


def test_registry_blocks_tool_for_wrong_role(probe_tool, db_session, users):
    result = execute_tool(PROBE_TOOL, {}, db_session, users["aliyev"])
    assert result.ok is False
    assert "Ruxsat yo'q" in result.text
    assert probe_tool["ran"] == 0, "ruxsatsiz bo'lsa ham handler ishladi!"

    # ...and the tool is not even offered to that role
    assert PROBE_TOOL not in [t["name"] for t in tools_for_role(UserRole.student)]
    assert PROBE_TOOL in [t["name"] for t in tools_for_role(UserRole.staff)]

    # allowed role runs it; admin is a superuser everywhere
    assert execute_tool(PROBE_TOOL, {}, db_session, users["rashidova"]).ok is True
    assert execute_tool(PROBE_TOOL, {}, db_session, users["admin"]).ok is True
    assert probe_tool["ran"] == 2


def test_summary_tool_refuses_confidential_document_for_student(db_session, users):
    from app.models import Document

    secret = (
        db_session.query(Document)
        .filter(Document.title.ilike(f"%{SECRET_TITLE_PART}%"))
        .one()
    )
    denied = execute_tool(
        "hujjat_rezyume", {"hujjat_id": secret.id}, db_session, users["aliyev"]
    )
    assert denied.ok is False
    assert "Ruxsat yo'q" in denied.text
    assert all(p not in denied.text for p in SECRET_PHRASES)

    allowed = execute_tool(
        "hujjat_rezyume", {"hujjat_id": secret.id}, db_session, users["rashidova"]
    )
    assert allowed.ok is True
    assert allowed.sources[0]["document_id"] == secret.id


def test_schedule_tool_keeps_the_caller_in_scope(db_session, users):
    own = execute_tool("jadval_kor", {"kun": "hafta"}, db_session, users["aliyev"])
    assert own.ok is True
    assert "AT-24-01" in own.text
    assert "AT-24-02" not in own.text, "talaba boshqa guruh jadvalini ko'rdi"

    foreign = execute_tool(
        "jadval_kor", {"guruh": "IQ-24-01", "kun": "hafta"}, db_session, users["aliyev"]
    )
    assert foreign.ok is False
    assert "Ruxsat yo'q" in foreign.text

    staff = execute_tool(
        "jadval_kor", {"guruh": "AT-24-02", "kun": "hafta"}, db_session, users["rashidova"]
    )
    assert staff.ok is True and "AT-24-02" in staff.text


# --- 4. conversation history + ownership ------------------------------------


def test_conversation_history_continues(chat_client):
    first = ask(chat_client, "aliyev", "Juftlik vaqtlari qanday?")
    second = ask(
        chat_client,
        "aliyev",
        "Dars jadvalimni ko'rsat",
        conversation_id=first["conversation_id"],
    )
    assert second["conversation_id"] == first["conversation_id"]

    stored = messages_of(chat_client, "aliyev", first["conversation_id"])
    user_texts = [m["content"] for m in stored if m["role"] == "user"]
    assert user_texts == ["Juftlik vaqtlari qanday?", "Dars jadvalimni ko'rsat"]
    assert len([m for m in stored if m["role"] == "assistant"]) == 2

    listed = chat_client.get(
        "/chat/conversations", headers=headers(chat_client, "aliyev")
    )
    assert listed.status_code == 200
    assert first["conversation_id"] in [c["id"] for c in listed.json()]


def test_other_users_conversation_is_not_accessible(chat_client):
    mine = ask(chat_client, "aliyev", "Topshiriq muddati qachon?")
    cid = mine["conversation_id"]

    res = chat_client.get(
        f"/chat/conversations/{cid}", headers=headers(chat_client, "karimov")
    )
    assert res.status_code in (403, 404), res.text

    # ...and it is not in the other user's list, nor can they write into it
    listed = chat_client.get(
        "/chat/conversations", headers=headers(chat_client, "karimov")
    ).json()
    assert cid not in [c["id"] for c in listed]

    posted = chat_client.post(
        "/chat",
        json={"message": "salom", "conversation_id": cid},
        headers=headers(chat_client, "karimov"),
    )
    assert posted.status_code in (403, 404), posted.text


def test_chat_requires_authentication(chat_client):
    assert chat_client.post("/chat", json={"message": "salom"}).status_code == 401
    assert chat_client.get("/chat/conversations").status_code == 401
