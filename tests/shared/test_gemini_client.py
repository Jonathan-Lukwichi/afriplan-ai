"""
Gemini behind the Anthropic-style interface: the same forced-tool calls go out, the same
tool_use blocks come back, a free-tier "too many requests" is waited out, and nothing
is ever sent to Google with a Claude key.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import core.gemini_client as gc
from core.config import GEMINI_FAST, GEMINI_MAIN, HAIKU_4_5, OPUS_5, ai_available, ai_provider
from core.gemini_client import GeminiClient, build_request, openapi_schema

TOOL = {
    "name": "extract_sld", "description": "Report the boards.", "strict": True,
    "input_schema": {"type": "object", "additionalProperties": False, "required": ["boards"],
                     "properties": {"boards": {"type": "array", "items": {
                         "type": "object", "additionalProperties": False, "required": ["name", "phases"],
                         "properties": {"name": {"type": "string"},
                                        "phases": {"type": "integer", "enum": [1, 3]}}}},
                                    "legend": {"type": "object", "additionalProperties": {"type": "string"}}}},
}


class _Http:
    def __init__(self, replies):
        self.replies, self.sent = list(replies), []

    def post(self, url, json=None, headers=None):
        self.sent.append((url, json, headers))
        status, body = self.replies.pop(0)
        return SimpleNamespace(status_code=status, json=lambda: body,
                               text=body if isinstance(body, str) else __import__("json").dumps(body))


def _answer(args, name="extract_sld"):
    return (200, {"candidates": [{"content": {"parts": [{"functionCall": {"name": name, "args": args}}]},
                                  "finishReason": "STOP"}],
                  "usageMetadata": {"promptTokenCount": 1200, "candidatesTokenCount": 80}})


def _call(client, model=OPUS_5.model_id):
    return client.messages.create(
        model=model, max_tokens=4096, system=[{"type": "text", "text": "You read drawings."}],
        tools=[TOOL], tool_choice={"type": "tool", "name": "extract_sld"},
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "iVBOR"}},
            {"type": "text", "text": "Read this SLD."}]}],
    )


def test_a_forced_tool_call_goes_out_and_comes_back_as_tool_use():
    http = _Http([_answer({"boards": [{"name": "DB-1", "phases": 3}]})])
    resp = _call(GeminiClient(api_key="AIza-test", http_client=http))
    [block] = resp.content
    assert block.type == "tool_use" and block.name == "extract_sld"
    assert block.input == {"boards": [{"name": "DB-1", "phases": 3}]}
    assert resp.usage.input_tokens == 1200 and resp.priced_as.input_usd_per_mtok == 0.0

    url, body, headers = http.sent[0]
    assert GEMINI_MAIN.model_id in url and headers["x-goog-api-key"] == "AIza-test"
    assert body["toolConfig"] == {"functionCallingConfig": {"mode": "ANY", "allowedFunctionNames": ["extract_sld"]}}
    assert body["systemInstruction"]["parts"][0]["text"] == "You read drawings."
    parts = body["contents"][0]["parts"]
    assert parts[0] == {"inlineData": {"mimeType": "image/png", "data": "iVBOR"}}
    decl = body["tools"][0]["functionDeclarations"][0]
    assert "strict" not in json.dumps(decl) and decl["parametersJsonSchema"]["required"] == ["boards"]


def test_easy_jobs_go_to_the_fast_model():
    http = _Http([_answer({"boards": []})])
    _call(GeminiClient(api_key="k", http_client=http), model=HAIKU_4_5.model_id)
    assert GEMINI_FAST.model_id in http.sent[0][0]


def test_too_many_requests_is_waited_out(monkeypatch):
    monkeypatch.setattr(gc.time, "sleep", lambda s: None)
    http = _Http([(429, '{"error": {"details": [{"retryDelay": "3s"}]}}'), _answer({"boards": []})])
    resp = _call(GeminiClient(api_key="k", http_client=http))
    assert resp.content[0].type == "tool_use" and len(http.sent) == 2


def test_a_refused_schema_is_retried_with_the_simple_form():
    http = _Http([(400, '{"error": {"message": "Invalid JSON schema in parametersJsonSchema"}}'),
                  _answer({"boards": []})])
    _call(GeminiClient(api_key="k", http_client=http))
    decl = http.sent[1][1]["tools"][0]["functionDeclarations"][0]
    assert "parameters" in decl and "parametersJsonSchema" not in decl


def test_simple_form_keeps_what_gemini_understands():
    s = openapi_schema(TOOL["input_schema"])
    board = s["properties"]["boards"]["items"]
    assert board["properties"]["phases"]["type"] == "INTEGER"
    assert "enum" not in board["properties"]["phases"]              # number enums → the description
    assert "1, 3" in board["properties"]["phases"]["description"]
    assert s["properties"]["legend"]["properties"]                  # a free-form map is never empty
    assert "additionalProperties" not in json.dumps(s)


def test_other_errors_are_raised_with_the_reason():
    http = _Http([(403, '{"error": {"message": "API key not valid"}}')])
    with pytest.raises(gc.GeminiError, match="API key not valid"):
        _call(GeminiClient(api_key="k", http_client=http))


def test_provider_follows_the_keys(monkeypatch):
    for k in ("AI_PROVIDER", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    assert ai_provider() == "claude" and not ai_available()
    monkeypatch.setenv("GEMINI_API_KEY", "AIza")
    assert ai_provider() == "gemini" and ai_available()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-x")
    assert ai_provider() == "claude"
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    assert ai_provider() == "gemini"


def test_the_pdf_reader_uses_gemini_and_never_sends_it_a_claude_key(monkeypatch):
    from agent.pdf_pipeline.llm import PdfLLM
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-real")
    llm = PdfLLM(api_key="sk-ant-should-not-leak", system_prompt="x")
    assert isinstance(llm._client, GeminiClient) and llm._client._key == "AIza-real"


def test_request_without_tools_is_plain_text():
    body = build_request(messages=[{"role": "user", "content": "Write a note."}], max_tokens=500)
    assert "tools" not in body and body["contents"][0]["parts"] == [{"text": "Write a note."}]
