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


class MockLLMClient(BaseLLMClient):
    """Deterministic offline provider for development and tests.

    Behavior:
    - If tools are given and the last user message mentions a tool name
      (or contains the marker "use_tool:<name>"), returns a tool call for
      the first matching tool with empty/marker arguments.
    - Otherwise returns a deterministic text answer derived from the last
      user message (stable hash suffix so tests can assert determinism).
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

        if tools:
            marker_call = self._marker_tool_call(last_text, tools)
            if marker_call is not None:
                return LLMResponse(text="", tool_calls=[marker_call])
            for tool in tools:
                name = tool.get("name", "")
                if name and name in last_text:
                    return LLMResponse(
                        text="", tool_calls=[ToolCall(name=name, arguments={})]
                    )

        # If the previous message is a tool result, summarize it deterministically
        last_msg = messages[-1] if messages else {}
        if last_msg.get("role") == "tool":
            result = last_msg.get("tool_result") or last_msg.get("content") or ""
            return LLMResponse(
                text=f"[mock] Tool '{last_msg.get('tool_name', '?')}' result: {result}"
            )

        digest = hashlib.sha256(last_text.encode("utf-8")).hexdigest()[:8]
        return LLMResponse(text=f"[mock:{digest}] Echo: {last_text}")

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
