"""S14: the Gemini provider (`app/llm/client.GeminiLLMClient`).

No API key and no network here: the SDK client is replaced by a stub that
records what it was asked for and returns a hand-built response object. That
covers the only two things this class does — translating the neutral message /
tool formats into google-genai objects and back.
"""

import pytest
from google.genai import types

from app.llm.client import (
    FUNCTION_RESULT_KEY,
    GeminiLLMClient,
    LLMError,
    MockLLMClient,
    get_llm_client,
)

API_KEY = "test-key-not-a-real-one"

SEARCH_TOOL = {
    "name": "hujjat_qidir",
    "description": "Hujjatlardan qidirish",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Qidiruv so'rovi"},
            "top_k": {"type": "integer", "minimum": 1, "maximum": 8},
        },
        "required": ["query"],
    },
}

TRANSLATE_TOOL = {
    "name": "tarjima_qil",
    "description": "Hujjatni tarjima qiladi",
    "parameters": {
        "type": "object",
        "properties": {"til": {"type": "string", "enum": ["uz", "ru", "en"]}},
        "required": [],
    },
}


class StubModels:
    """Stands in for `genai.Client().models`."""

    def __init__(self, response=None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls: list[dict] = []

    def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if self.error is not None:
            raise self.error
        return self.response


class StubClient:
    def __init__(self, response=None, error: Exception | None = None):
        self.models = StubModels(response=response, error=error)


def text_response(text: str):
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(role="model", parts=[types.Part(text=text)])
            )
        ]
    )


def tool_response(name: str, args: dict, text: str = ""):
    parts = []
    if text:
        parts.append(types.Part(text=text))
    parts.append(
        types.Part(function_call=types.FunctionCall(name=name, args=args))
    )
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=parts))]
    )


def make_client(**kwargs) -> tuple[GeminiLLMClient, StubClient]:
    stub = StubClient(**kwargs)
    return GeminiLLMClient(api_key=API_KEY, model="gemini-test", client=stub), stub


# --- provider selection ------------------------------------------------------


def test_default_provider_is_mock():
    """LLM_PROVIDER stays "mock" until the key is connected."""
    assert isinstance(get_llm_client(), MockLLMClient)


def test_empty_key_is_refused():
    with pytest.raises(ValueError):
        GeminiLLMClient(api_key="")


# --- neutral messages -> google-genai contents -------------------------------


def test_user_and_assistant_messages_become_contents():
    contents = GeminiLLMClient.to_contents(
        [
            {"role": "user", "content": "Salom"},
            {"role": "assistant", "content": "Assalomu alaykum"},
            {"role": "user", "content": "Kontraktim qancha?"},
        ]
    )
    assert [c.role for c in contents] == ["user", "model", "user"]
    assert contents[0].parts[0].text == "Salom"
    assert contents[1].parts[0].text == "Assalomu alaykum"


def test_empty_assistant_message_is_dropped():
    contents = GeminiLLMClient.to_contents(
        [{"role": "user", "content": "Savol"}, {"role": "assistant", "content": ""}]
    )
    assert len(contents) == 1


def test_tool_message_becomes_function_call_plus_response():
    """Gemini only accepts a functionResponse that answers a functionCall, so
    the missing model turn is replayed in front of every tool result."""
    contents = GeminiLLMClient.to_contents(
        [
            {"role": "user", "content": "Kontraktim qancha?"},
            {
                "role": "tool",
                "content": "Qoldiq 0 so'm",
                "tool_name": "tolov_holati",
                "tool_result": "Qoldiq 0 so'm",
            },
        ]
    )
    assert [c.role for c in contents] == ["user", "model", "user"]
    call = contents[1].parts[0].function_call
    assert call.name == "tolov_holati"
    assert call.args == {}
    answer = contents[2].parts[0].function_response
    assert answer.name == "tolov_holati"
    assert answer.response == {FUNCTION_RESULT_KEY: "Qoldiq 0 so'm"}


def test_assistant_text_merges_into_the_same_model_turn_as_the_tool_call():
    contents = GeminiLLMClient.to_contents(
        [
            {"role": "user", "content": "Savol"},
            {"role": "assistant", "content": "Bir tekshiray"},
            {
                "role": "tool",
                "content": "natija",
                "tool_name": "hujjat_qidir",
                "tool_result": "natija",
            },
        ]
    )
    assert [c.role for c in contents] == ["user", "model", "user"]
    model_turn = contents[1]
    assert model_turn.parts[0].text == "Bir tekshiray"
    assert model_turn.parts[1].function_call.name == "hujjat_qidir"


def test_two_tool_results_alternate_correctly():
    contents = GeminiLLMClient.to_contents(
        [
            {"role": "user", "content": "Savol"},
            {"role": "tool", "tool_name": "a", "tool_result": "1", "content": "1"},
            {"role": "tool", "tool_name": "b", "tool_result": "2", "content": "2"},
        ]
    )
    assert [c.role for c in contents] == ["user", "model", "user", "model", "user"]
    assert contents[3].parts[0].function_call.name == "b"


# --- neutral tool declarations -> google-genai tools -------------------------


def test_tool_declarations_are_converted():
    tools = GeminiLLMClient.to_tools([SEARCH_TOOL, TRANSLATE_TOOL])
    assert len(tools) == 1  # one Tool holding every function
    declarations = tools[0].function_declarations
    assert [d.name for d in declarations] == ["hujjat_qidir", "tarjima_qil"]

    search = declarations[0]
    assert search.description == "Hujjatlardan qidirish"
    assert set(search.parameters.properties) == {"query", "top_k"}
    assert search.parameters.required == ["query"]
    assert search.parameters.properties["query"].type == types.Type.STRING
    assert search.parameters.properties["top_k"].type == types.Type.INTEGER

    translate = declarations[1]
    assert translate.parameters.properties["til"].enum == ["uz", "ru", "en"]


def test_no_tools_means_no_declarations():
    assert GeminiLLMClient.to_tools(None) is None
    assert GeminiLLMClient.to_tools([]) is None


# --- google-genai response -> LLMResponse ------------------------------------


def test_text_answer_is_parsed():
    client, _ = make_client(response=text_response("Kontrakt to'liq to'langan."))
    answer = client.chat([{"role": "user", "content": "Kontraktim?"}])
    assert answer.text == "Kontrakt to'liq to'langan."
    assert answer.tool_calls == []
    assert not answer.has_tool_calls


def test_tool_call_answer_is_parsed():
    client, _ = make_client(
        response=tool_response("hujjat_qidir", {"query": "kutubxona", "top_k": 3})
    )
    answer = client.chat(
        [{"role": "user", "content": "Kutubxona?"}], tools=[SEARCH_TOOL]
    )
    assert answer.has_tool_calls
    call = answer.tool_calls[0]
    assert call.name == "hujjat_qidir"
    assert call.arguments == {"query": "kutubxona", "top_k": 3}


def test_text_and_tool_call_together():
    client, _ = make_client(
        response=tool_response("hujjat_qidir", {"query": "x"}, text="Qidirib ko'ray")
    )
    answer = client.chat([{"role": "user", "content": "x"}], tools=[SEARCH_TOOL])
    assert answer.text == "Qidirib ko'ray"
    assert answer.tool_calls[0].name == "hujjat_qidir"


def test_thought_parts_are_skipped():
    response = types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(text="ichki fikr", thought=True),
                        types.Part(text="Javob"),
                    ],
                )
            )
        ]
    )
    assert GeminiLLMClient.parse_response(response).text == "Javob"


def test_empty_response_gives_empty_answer():
    """A blocked or empty candidate list must not crash the agent loop."""
    answer = GeminiLLMClient.parse_response(types.GenerateContentResponse())
    assert answer.text == ""
    assert answer.tool_calls == []


# --- request wiring ----------------------------------------------------------


def test_system_prompt_model_and_tools_reach_the_sdk():
    client, stub = make_client(response=text_response("ok"))
    client.chat(
        [{"role": "user", "content": "Savol"}],
        tools=[SEARCH_TOOL],
        system="Sen universitet agentisan.",
    )
    (call,) = stub.models.calls
    assert call["model"] == "gemini-test"
    assert call["config"].system_instruction == "Sen universitet agentisan."
    assert call["config"].tools[0].function_declarations[0].name == "hujjat_qidir"
    # The tool loop is ours: the SDK must not run handlers by itself.
    assert call["config"].automatic_function_calling.disable is True
    assert [c.role for c in call["contents"]] == ["user"]


def test_no_system_prompt_is_sent_as_none():
    client, stub = make_client(response=text_response("ok"))
    client.chat([{"role": "user", "content": "Savol"}])
    (call,) = stub.models.calls
    assert call["config"].system_instruction is None
    assert call["config"].tools is None


# --- failures ----------------------------------------------------------------


def test_sdk_failure_becomes_llm_error():
    client, _ = make_client(error=RuntimeError("429 quota exceeded"))
    with pytest.raises(LLMError) as excinfo:
        client.chat([{"role": "user", "content": "Savol"}])
    message = str(excinfo.value)
    assert "gemini-test" in message
    assert "quota" in message


def test_empty_message_list_is_refused_before_the_call():
    client, stub = make_client(response=text_response("ok"))
    with pytest.raises(LLMError):
        client.chat([])
    assert stub.models.calls == []


def test_sdk_client_is_built_lazily_from_the_key(monkeypatch):
    """No SDK client (and no key use) until the first call needs one."""
    from app.llm import client as client_module

    built: list[str] = []
    sentinel = StubClient(response=text_response("ok"))

    def fake_new_sdk_client(api_key: str):
        built.append(api_key)
        return sentinel

    monkeypatch.setattr(client_module, "_new_sdk_client", fake_new_sdk_client)
    gemini = GeminiLLMClient(api_key=API_KEY, model="gemini-test")
    assert built == []  # construction alone must not touch the SDK
    gemini.chat([{"role": "user", "content": "Savol"}])
    assert built == [API_KEY]
    gemini.chat([{"role": "user", "content": "Yana"}])
    assert built == [API_KEY]  # built once, reused
