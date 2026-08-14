"""Tool registry: name + description + JSON Schema + handler + allowed roles.

Permission is enforced HERE, in the backend (FUNKSIONALLIK 3.2): if the model
asks for a tool the user's role may not use, the handler is **never called** —
`execute_tool` returns a "ruxsat yo'q" tool result instead. It does not raise,
so the agent loop keeps running and the model can explain the refusal.

Adding a tool = one file in `agents/tools/` + a `register(...)` call there.
Nothing else in the project changes.

    from app.agents.registry import Tool, ToolResult, register

    def handler(db, user, args) -> ToolResult: ...

    register(Tool(name="...", description="...", parameters={...},
                  handler=handler, roles=(UserRole.staff,)))
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy.orm import Session

from app.models import User, UserRole

ALL_ROLES: tuple[UserRole, ...] = tuple(UserRole)


@dataclass
class ToolResult:
    """What a tool gives back: text for the model + citations for the user."""

    text: str
    sources: list[dict] = field(default_factory=list)
    ok: bool = True

    def as_dict(self) -> dict:
        return {"text": self.text, "sources": self.sources, "ok": self.ok}


ToolHandler = Callable[[Session, User, dict], ToolResult]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str  # shown to the model — it decides from this text
    parameters: dict  # JSON Schema
    handler: ToolHandler
    roles: tuple[UserRole, ...]  # admin is always allowed on top of these

    def is_allowed_for(self, role: UserRole) -> bool:
        return role == UserRole.admin or role in self.roles

    def as_llm_dict(self) -> dict:
        """Provider-neutral tool declaration (see llm/client.py)."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


_TOOLS: dict[str, Tool] = {}
_builtins_loaded = False


def register(tool: Tool) -> Tool:
    if tool.name in _TOOLS:
        raise ValueError(f"Tool nomi takrorlandi: {tool.name!r}")
    _TOOLS[tool.name] = tool
    return tool


def unregister(name: str) -> None:
    """Remove a tool (used by tests; S13 could disable tools with it)."""
    _TOOLS.pop(name, None)


def _ensure_builtins() -> None:
    """Import the built-in tool modules once; each registers itself."""
    global _builtins_loaded
    if _builtins_loaded:
        return
    _builtins_loaded = True  # set first: the import below calls register()
    from app.agents import tools  # noqa: F401


def get_tool(name: str) -> Tool | None:
    _ensure_builtins()
    return _TOOLS.get(name)


def all_tools() -> list[Tool]:
    _ensure_builtins()
    return list(_TOOLS.values())


def tools_for_role(role: UserRole) -> list[dict]:
    """Tool declarations handed to the LLM for this role."""
    return [t.as_llm_dict() for t in all_tools() if t.is_allowed_for(role)]


def tool_names_for_role(role: UserRole) -> list[str]:
    return [t.name for t in all_tools() if t.is_allowed_for(role)]


def execute_tool(name: str, args: dict | None, db: Session, user: User) -> ToolResult:
    """Run a tool for `user` after checking the role. Never raises."""
    tool = get_tool(name)
    if tool is None:
        return ToolResult(
            text=(
                f"Noma'lum vosita: '{name}'. Mavjud vositalar: "
                f"{', '.join(tool_names_for_role(user.role)) or 'yo‘q'}."
            ),
            ok=False,
        )
    if not tool.is_allowed_for(user.role):
        # Backend-level block: the handler is not called at all.
        return ToolResult(
            text=(
                f"Ruxsat yo'q: '{name}' vositasi '{user.role.value}' roli uchun "
                "ochiq emas. Bu ma'lumotni foydalanuvchiga bera olmaysiz."
            ),
            ok=False,
        )
    try:
        return tool.handler(db, user, dict(args or {}))
    except Exception as exc:  # a broken tool must not kill the conversation
        return ToolResult(text=f"'{name}' vositasida xatolik: {exc}", ok=False)
