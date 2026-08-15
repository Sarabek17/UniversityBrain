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


class LLMError(RuntimeError):
    """The provider could not answer (network, quota, bad key, blocked input)."""


# Key the tool result is handed back under: Gemini's functionResponse payload is
# an object, our tools return plain text.
FUNCTION_RESULT_KEY = "result"


def _new_sdk_client(api_key: str):
    """Build the google-genai client. Imported lazily (mock mode needs no SDK)
    and kept as a module-level function so tests can replace it."""
    from google import genai

    return genai.Client(api_key=api_key)


class GeminiLLMClient(BaseLLMClient):
    """Google Gemini provider (google-genai SDK).

    Translation between the neutral formats above and the SDK:

        {"role": "user", "content": t}       -> Content(role="user",  [Part(text=t)])
        {"role": "assistant", "content": t}  -> Content(role="model", [Part(text=t)])
        {"role": "tool", "tool_name": n,     -> Content(role="model", [Part(function_call=n)])
                         "tool_result": r}      Content(role="user",  [Part(function_response=n, {result: r})])
        {"name", "description", "parameters"} -> types.FunctionDeclaration(...)
        system                                -> config.system_instruction

    The synthetic `model` turn in front of every tool result is required: the
    API only accepts a functionResponse that answers a functionCall. The
    neutral history does not carry the original arguments (the orchestrator
    stores the *result*), so the call is replayed with empty args — the model
    reads the result text, which is what it needs.

    Automatic function calling is switched OFF on purpose: the tool loop lives
    in `agents/orchestrator.py`, where the role check runs before any handler.
    """

    def __init__(self, api_key: str, model: str | None = None, client=None):
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is empty. Set it in .env or use LLM_PROVIDER=mock."
            )
        self.api_key = api_key
        self.model = (model or get_settings().gemini_model).strip()
        self._client = client  # tests inject a stub; otherwise built on demand

    # --- SDK plumbing -------------------------------------------------------

    @property
    def client(self):
        if self._client is None:
            self._client = _new_sdk_client(self.api_key)
        return self._client

    # --- neutral -> Gemini --------------------------------------------------

    @staticmethod
    def _append(contents: list, role: str, part) -> None:
        """Add a part, merging into the previous turn when the role repeats
        (an assistant sentence plus its tool call are one model turn)."""
        if contents and contents[-1].role == role:
            contents[-1].parts.append(part)
            return
        from google.genai import types

        contents.append(types.Content(role=role, parts=[part]))

    @classmethod
    def to_contents(cls, messages: list[dict]) -> list:
        from google.genai import types

        contents: list = []
        for message in messages or []:
            role = message.get("role")
            content = (message.get("content") or "").strip()
            if role == "tool":
                name = message.get("tool_name") or "tool"
                result = message.get("tool_result") or message.get("content") or ""
                cls._append(
                    contents,
                    "model",
                    types.Part(function_call=types.FunctionCall(name=name, args={})),
                )
                cls._append(
                    contents,
                    "user",
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=name, response={FUNCTION_RESULT_KEY: result}
                        )
                    ),
                )
            elif role == "assistant":
                if content:
                    cls._append(contents, "model", types.Part(text=content))
            elif content:
                # "user" and any stray "system" message: plain user turn.
                cls._append(contents, "user", types.Part(text=content))
        return contents

    @staticmethod
    def to_tools(tools: list[dict] | None) -> list | None:
        """Neutral declarations -> a single types.Tool with all functions."""
        if not tools:
            return None
        from google.genai import types

        declarations = [
            types.FunctionDeclaration(
                name=tool["name"],
                description=tool.get("description", ""),
                parameters=tool.get("parameters") or {"type": "object", "properties": {}},
            )
            for tool in tools
        ]
        return [types.Tool(function_declarations=declarations)]

    # --- Gemini -> neutral --------------------------------------------------

    @staticmethod
    def parse_response(response) -> LLMResponse:
        """First candidate only: text parts joined, function calls collected.

        `response.text` is not used — it warns and returns None as soon as the
        answer carries a function call, which is the normal case here.
        """
        texts: list[str] = []
        calls: list[ToolCall] = []
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates[:1]:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", None) or []:
                if getattr(part, "thought", None):
                    continue  # thinking summary, not an answer
                call = getattr(part, "function_call", None)
                if call is not None and getattr(call, "name", None):
                    calls.append(
                        ToolCall(name=call.name, arguments=dict(call.args or {}))
                    )
                    continue
                text = getattr(part, "text", None)
                if text:
                    texts.append(text)
        return LLMResponse(text="\n".join(texts).strip(), tool_calls=calls)

    # --- one turn -----------------------------------------------------------

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        from google.genai import types

        contents = self.to_contents(messages)
        if not contents:
            raise LLMError("Gemini so'rovi bo'sh: birorta xabar berilmadi.")

        config = types.GenerateContentConfig(
            system_instruction=(system or None),
            tools=self.to_tools(tools),
            # The tool loop (and the role check in it) is ours, not the SDK's.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        )
        try:
            response = self.client.models.generate_content(
                model=self.model, contents=contents, config=config
            )
        except Exception as exc:  # noqa: BLE001 - one clear error for the caller
            raise LLMError(f"Gemini so'rovi bajarilmadi ({self.model}): {exc}") from exc
        return self.parse_response(response)


def get_llm_client() -> BaseLLMClient:
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()
    if provider == "mock":
        return MockLLMClient()
    if provider == "gemini":
        return GeminiLLMClient(
            api_key=settings.gemini_api_key, model=settings.gemini_model
        )
    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r} (expected 'mock' or 'gemini')")
