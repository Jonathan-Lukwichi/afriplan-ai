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


def _daily_quota_429(model: str):
    """Google's real shape: the per-day quotaId comes after a long message and a help link
    (past the first 600 characters), and a retryDelay is offered even though waiting is useless."""
    return (429, json.dumps({"error": {
        "code": 429, "status": "RESOURCE_EXHAUSTED",
        "message": "You exceeded your current quota, please check your plan and billing details. " * 4
                   + f"* Quota exceeded for metric: generativelanguage.googleapis.com/"
                     f"generate_content_free_tier_requests, limit: 20, model: {model}",
        "details": [
            {"@type": "type.googleapis.com/google.rpc.Help",
             "links": [{"description": "Learn more about Gemini API quotas",
                        "url": "https://ai.google.dev/gemini-api/docs/rate-limits"}]},
            {"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [{
                "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
                "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
                "quotaDimensions": {"model": model, "location": "global"}, "quotaValue": "20"}]},
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "41s"}]}}))


def test_a_used_up_daily_quota_fails_at_once_with_a_plain_reason(monkeypatch):
    from core.config import GEMINI_FALLBACK
    slept = []
    monkeypatch.setattr(gc.time, "sleep", slept.append)
    http = _Http([_daily_quota_429(GEMINI_MAIN.model_id), _daily_quota_429(GEMINI_FALLBACK.model_id)])
    with pytest.raises(gc.GeminiError, match="daily") as err:
        _call(GeminiClient(api_key="k", http_client=http))
    assert slept == []                                  # no waiting on a limit that resets tomorrow
    assert len(http.sent) == 2                          # the main model once, the fallback once
    assert "AI_PROVIDER=claude" in str(err.value)       # says what to do instead


def test_a_model_out_of_daily_quota_is_not_asked_again(monkeypatch):
    from core.config import GEMINI_FALLBACK
    monkeypatch.setattr(gc.time, "sleep", lambda s: None)
    http = _Http([_daily_quota_429(GEMINI_MAIN.model_id), _daily_quota_429(GEMINI_FALLBACK.model_id)])
    client = GeminiClient(api_key="k", http_client=http)
    for _ in range(3):                                  # e.g. the next pages of the same run
        with pytest.raises(gc.GeminiError, match="daily"):
            _call(client)
    assert len(http.sent) == 2


def test_a_wait_is_announced_so_the_screen_can_show_it(monkeypatch):
    monkeypatch.setattr(gc.time, "sleep", lambda s: None)
    notes = []
    http = _Http([(429, '{"error": {"details": [{"retryDelay": "41s"}]}}'), _answer({"boards": []})])
    _call(GeminiClient(api_key="k", http_client=http, on_wait=notes.append))
    assert len(notes) == 1 and "42 s" in notes[0] and "busy" in notes[0]


def test_a_busy_or_retired_model_falls_back_to_the_steady_one(monkeypatch):
    from core.config import GEMINI_FALLBACK
    monkeypatch.setattr(gc.time, "sleep", lambda s: None)
    http = _Http([(404, '{"error": {"message": "model is no longer available"}}'), _answer({"boards": []})])
    resp = _call(GeminiClient(api_key="k", http_client=http))
    assert GEMINI_FALLBACK.model_id in http.sent[1][0] and resp.model == GEMINI_FALLBACK.model_id


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
