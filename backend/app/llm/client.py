"""Provider-independent LLM interface.

The ONLY module allowed to talk to an LLM provider. Everything else calls
`get_llm_client()` and works with `LLMResponse` / `ToolCall`.

Message format (provider-neutral, list[dict]):
    {"role": "system" | "user" | "assistant" | "tool", "content": str,
     "tool_name": str | None, "tool_result": str | None}

Tool definition format (provider-neutral, list[dict]):
    {"name": str, "description": str, "parameters": <JSON Schema dict>}
"""

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.config import get_settings


@dataclass
class ToolCall:
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


class BaseLLMClient(ABC):
    """Abstract provider-independent LLM client."""

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        """Run one model turn. May return text, tool calls, or both."""
        raise NotImplementedError


SEARCH_TOOL = "hujjat_qidir"  # the mock's default first step (S4)
MOCK_ANSWER_CHARS = 600


def _clip(text: str, limit: int = MOCK_ANSWER_CHARS) -> str:
    """Cap mock output. Tool-less callers (S6 summarization) pass a whole
    document in the prompt — echoing it verbatim would make the "summary"
    longer than the document. The digest still covers the full text, so the
    response stays deterministic and unique per input."""
    text = text.strip()
    return text if len(text) <= limit else text[:limit].rstrip() + " […]"


class MockLLMClient(BaseLLMClient):
    """Deterministic offline provider for development and tests.

    Tool selection (only while no tool result is in the transcript yet):
    1. explicit marker `use_tool:<name>` (optionally `:{"arg": 1}`) in the
       last user message,
    2. a tool name appearing literally in the last user message,
    3. otherwise `hujjat_qidir(query=<user message>)` if that tool is offered —
       so the whole agent flow (search -> sources -> answer) is exercised
       without an API key.

    Once a tool result is present the mock always answers with text, built
    from that result — the agent loop therefore always terminates, and the
    answer never repeats the user's question back (no fake facts).
    """

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        last_user = next(
            (m for m in reversed(messages) if m.get("role") == "user"), None
        )
        last_text = (last_user or {}).get("content", "") or ""
        tool_messages = [m for m in messages if m.get("role") == "tool"]

        if tools and not tool_messages:
            call = self._pick_tool_call(last_text, tools)
            if call is not None:
                return LLMResponse(text="", tool_calls=[call])

        if tool_messages:
            return LLMResponse(text=self._answer_from_tool(tool_messages[-1]))

        digest = hashlib.sha256(last_text.encode("utf-8")).hexdigest()[:8]
        return LLMResponse(text=f"[mock:{digest}] Echo: {_clip(last_text)}")

    def _pick_tool_call(self, text: str, tools: list[dict]) -> ToolCall | None:
        marker_call = self._marker_tool_call(text, tools)
        if marker_call is not None:
            return marker_call
        for tool in tools:
            name = tool.get("name", "")
            if name and name in text:
                return ToolCall(name=name, arguments=self._default_arguments(name, text))
        if text.strip() and any(t.get("name") == SEARCH_TOOL for t in tools):
            return ToolCall(name=SEARCH_TOOL, arguments={"query": text})
        return None

    @staticmethod
    def _default_arguments(name: str, text: str) -> dict:
        return {"query": text} if name == SEARCH_TOOL else {}

    @staticmethod
    def _answer_from_tool(message: dict) -> str:
        """Deterministic answer built ONLY from the tool result."""
        name = message.get("tool_name") or "?"
        result = (message.get("tool_result") or message.get("content") or "").strip()
        if not result:
            return f"[mock] '{name}' vositasi natija qaytarmadi."
        return f"[mock] '{name}' vositasi natijasi asosida:\n{_clip(result)}"

    @staticmethod
    def _marker_tool_call(text: str, tools: list[dict]) -> ToolCall | None:
        # Explicit marker: use_tool:<name> or use_tool:<name>:{"arg": 1}
        marker = "use_tool:"
        idx = text.find(marker)
        if idx == -1:
            return None
        rest = text[idx + len(marker):].strip()
        name, _, args_part = rest.partition(":")
        name = name.strip().split()[0] if name.strip() else ""
        known = {t.get("name") for t in tools}
        if name not in known:
            return None
        arguments: dict = {}
        if args_part.strip().startswith("{"):
            try:
                arguments = json.loads(args_part.strip())
            except json.JSONDecodeError:
                arguments = {}
        return ToolCall(name=name, arguments=arguments)


class GeminiLLMClient(BaseLLMClient):
    """Google Gemini provider skeleton.

    The API key is connected at the end of the project (see PROGRESS.md).
    Until then this class must not be used; construction validates the key,
    chat() raises to prevent silent fallthrough. Implementation lands when
    LLM_PROVIDER=gemini is enabled: google-genai SDK, tool declarations
    mapped from the neutral format above.
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is empty. Set it in .env or use LLM_PROVIDER=mock."
            )
        self.api_key = api_key

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        raise NotImplementedError(
            "Gemini provider is not wired up yet (key connected at project end)."
        )


def get_llm_client() -> BaseLLMClient:
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()
    if provider == "mock":
        return MockLLMClient()
    if provider == "gemini":
        return GeminiLLMClient(api_key=settings.gemini_api_key)
    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r} (expected 'mock' or 'gemini')")
