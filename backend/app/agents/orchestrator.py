"""Chat flow: history -> role prompt -> LLM (+tools) -> tool loop -> answer.

One turn:
    1. load the conversation history (user/assistant messages),
    2. pick the role system prompt (`prompts/umumiy.md` + `prompts/<role>.md`),
    3. `llm.chat(messages, tools=tools_for_role(role), system=...)`,
    4. any tool call -> `registry.execute_tool` (role checked there) -> the
       result goes back into the message list and the model is called again,
    5. stop on the first text-only answer (max 5 iterations),
    6. return text + collected sources + the "not an official document" note.

Tool results are persisted as `ChatMessage(role=tool)` — an audit trail of what
the agent actually did — but only user/assistant turns are replayed as history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from sqlalchemy.orm import Session

from app.agents.registry import execute_tool, tools_for_role
from app.llm.client import get_llm_client
from app.models import ChatMessage, ChatRole, Conversation, User, UserRole

MAX_ITERATIONS = 5
HISTORY_LIMIT = 20  # last N user/assistant messages replayed to the model
TITLE_CHARS = 80

DISCLAIMER = (
    "AI javobi universitetning rasmiy hujjati hisoblanmaydi — muhim qarorlar "
    "uchun rasmiy manbaga murojaat qiling."
)

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
COMMON_PROMPT = "umumiy.md"

_EMPTY_ANSWER = (
    "Kechirasiz, bu savolga javob tayyorlay olmadim. Savolni boshqacha "
    "ifodalab ko'ring."
)


@dataclass
class AgentAnswer:
    text: str
    sources: list[dict] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    disclaimer: str = DISCLAIMER


@lru_cache(maxsize=None)
def load_system_prompt(role: UserRole) -> str:
    """Shared rules + the role-specific prompt file."""
    common = (PROMPTS_DIR / COMMON_PROMPT).read_text(encoding="utf-8").strip()
    role_file = PROMPTS_DIR / f"{role.value}.md"
    if not role_file.exists():
        return common
    return f"{common}\n\n{role_file.read_text(encoding='utf-8').strip()}"


# --- conversation storage ---------------------------------------------------


def get_conversation(db: Session, user: User, conversation_id: int) -> Conversation | None:
    """The user's own conversation, or None (never another user's)."""
    return (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user.id)
        .first()
    )


def list_conversations(db: Session, user: User) -> list[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.id.desc())
        .all()
    )


def create_conversation(db: Session, user: User, first_message: str) -> Conversation:
    title = " ".join(first_message.split())[:TITLE_CHARS] or "Yangi suhbat"
    conversation = Conversation(user_id=user.id, title=title)
    db.add(conversation)
    db.flush()
    return conversation


def _store(
    db: Session,
    conversation: Conversation,
    role: ChatRole,
    content: str,
    tool_name: str | None = None,
    sources: list[dict] | None = None,
) -> ChatMessage:
    message = ChatMessage(
        conversation_id=conversation.id,
        role=role,
        content=content,
        tool_name=tool_name,
        sources=sources or None,
    )
    db.add(message)
    db.flush()
    return message


def _history_messages(db: Session, conversation: Conversation) -> list[dict]:
    rows = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.conversation_id == conversation.id,
            ChatMessage.role.in_([ChatRole.user, ChatRole.assistant]),
        )
        .order_by(ChatMessage.id.desc())
        .limit(HISTORY_LIMIT)
        .all()
    )
    return [{"role": r.role.value, "content": r.content} for r in reversed(rows)]


# --- the loop ---------------------------------------------------------------


def _source_key(source: dict) -> tuple:
    return (
        source.get("type"),
        source.get("document_id"),
        source.get("chunk_id"),
        source.get("label"),
    )


def run_chat(
    db: Session, user: User, conversation: Conversation, message: str
) -> AgentAnswer:
    """Run one user turn to completion and persist everything."""
    history = _history_messages(db, conversation)
    _store(db, conversation, ChatRole.user, message)

    messages = history + [{"role": "user", "content": message}]
    tools = tools_for_role(user.role)
    system = load_system_prompt(user.role)
    client = get_llm_client()

    sources: list[dict] = []
    seen_sources: set[tuple] = set()
    tools_used: list[str] = []
    text = ""

    for _ in range(MAX_ITERATIONS):
        response = client.chat(messages, tools=tools, system=system)
        if not response.has_tool_calls:
            text = (response.text or "").strip()
            break

        if (response.text or "").strip():
            messages.append({"role": "assistant", "content": response.text})

        for call in response.tool_calls:
            result = execute_tool(call.name, call.arguments, db, user)
            tools_used.append(call.name)
            messages.append(
                {
                    "role": "tool",
                    "content": result.text,
                    "tool_name": call.name,
                    "tool_result": result.text,
                }
            )
            _store(
                db,
                conversation,
                ChatRole.tool,
                result.text,
                tool_name=call.name,
                sources=result.sources or None,
            )
            for source in result.sources:
                key = _source_key(source)
                if key not in seen_sources:
                    seen_sources.add(key)
                    sources.append(source)
    else:
        # Iteration budget spent: answer from what the tools already returned.
        text = _fallback_text(messages)

    if not text:
        text = _EMPTY_ANSWER

    _store(db, conversation, ChatRole.assistant, text, sources=sources or None)
    db.commit()
    return AgentAnswer(text=text, sources=sources, tools_used=tools_used)


def _fallback_text(messages: list[dict]) -> str:
    last_tool = next((m for m in reversed(messages) if m.get("role") == "tool"), None)
    if last_tool is None:
        return _EMPTY_ANSWER
    return (
        "Javobni to'liq yakunlay olmadim. Oxirgi topilgan ma'lumot:\n"
        f"{last_tool.get('content', '')}"
    )
