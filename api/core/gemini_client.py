"""
Google Gemini behind the same interface as the Anthropic client — a free alternative.

Everything in AfriPlan that calls an AI (the PDF reader, AI symbol names, the combining
matcher, Live Pricing replies) calls `client.messages.create(...)` with Anthropic-style
arguments and reads Anthropic-style `tool_use` blocks back. `GeminiClient` accepts exactly
those arguments, sends them to the Gemini REST API (plain HTTPS, no extra package) and
returns an object of the same shape, so no caller changes. The rules stay the same: the
model must answer through the forced tool (function calling, mode ANY), and Python checks
the answer against the schema and asks again when it is wrong.

Free-tier limits are small (a few requests a minute), so requests are throttled and a
"too many requests" answer is waited out and retried — except a used-up DAILY quota, which
fails at once with a plain reason (waiting cannot help until it resets) and is remembered,
so the rest of the run does not ask that model again.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional

from core.config import GEMINI_FALLBACK, ModelSpec, gemini_model_for

log = logging.getLogger(__name__)

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_RETRY_STATUS = {429, 500, 502, 503, 504}


class GeminiError(RuntimeError):
    pass


class GeminiQuotaError(GeminiError):
    """The free daily quota of a model is used up — retrying today is pointless."""


def _is_daily_quota(error_text: str) -> bool:
    return "PerDay" in error_text


def _daily_quota_message(model_id: str, error_text: str = "") -> str:
    m = re.search(r'"quotaValue":\s*"(\d+)"', error_text)
    limit = f"{m.group(1)} requests a day" if m else "a small number of requests a day"
    return (f"Gemini's free daily limit is used up for {model_id} (the free tier allows {limit}; "
            "a drawing set needs several requests per page). It resets at midnight US Pacific time "
            "(about 09:00-10:00 in South Africa). To read PDFs now: set AI_PROVIDER=claude in api/.env "
            "(paid API), or use the DOE workflow in Claude Code (subscription).")


class GeminiClient:
    """Drop-in for `anthropic.Anthropic` where only `messages.create` is used."""

    def __init__(self, *, api_key: str, http_client: Any = None, max_concurrent: int = 2,
                 max_retries: int = 6, timeout_s: float = 300.0,
                 on_wait: Optional[Callable[[str], None]] = None):
        if not api_key:
            raise GeminiError("GEMINI_API_KEY is not set")
        self._key = api_key
        self._http = http_client or _default_http(timeout_s)
        self._gate = threading.Semaphore(max(1, max_concurrent))
        self._retries = max_retries
        self._on_wait = on_wait                     # tells the screen why nothing moves for a while
        self._out_of_quota: Dict[str, str] = {}     # model id -> reason, for the rest of this client's life
        self.messages = self            # so callers can write client.messages.create(...)

    # ── the one method callers use ────────────────────────────────────

    def create(self, *, model: str, messages: List[Dict[str, Any]], max_tokens: int = 4096,
               system: Any = None, tools: Optional[List[Dict[str, Any]]] = None,
               tool_choice: Optional[Dict[str, Any]] = None, temperature: Optional[float] = None,
               **_ignored: Any):
        spec = gemini_model_for(model)
        body = build_request(messages=messages, max_tokens=max_tokens, system=system, tools=tools,
                             tool_choice=tool_choice, temperature=temperature)
        try:
            try:
                data = self._post(spec.model_id, body)
            except GeminiError as e:
                busy_or_gone = isinstance(e, GeminiQuotaError) or any(f"error {c}" in str(e) for c in (404, 429, 503))
                if not busy_or_gone or spec.model_id == GEMINI_FALLBACK.model_id:
                    raise
                log.warning("Gemini %s unavailable (%s) — using %s", spec.model_id, str(e)[:80],
                            GEMINI_FALLBACK.model_id)
                spec = GEMINI_FALLBACK
                data = self._post(spec.model_id, body)
        except GeminiError as e:
            if tools and "schema" in str(e).lower():
                log.warning("Gemini refused the JSON schema; retrying with a simplified schema")
                body = build_request(messages=messages, max_tokens=max_tokens, system=system, tools=tools,
                                     tool_choice=tool_choice, temperature=temperature, simple_schema=True)
                data = self._post(spec.model_id, body)
            else:
                raise
        return parse_response(data, spec)

    # ── transport ─────────────────────────────────────────────────────

    def _post(self, model_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        if model_id in self._out_of_quota:
            raise GeminiQuotaError(self._out_of_quota[model_id])
        url = API_URL.format(model=model_id)
        delay = 5.0
        for attempt in range(self._retries + 1):
            with self._gate:
                resp = self._http.post(url, json=body, headers={"x-goog-api-key": self._key,
                                                                "content-type": "application/json"})
            if resp.status_code == 200:
                return resp.json()
            full = resp.text or ""                  # the quota id and retryDelay sit past char 600
            text = full[:600]
            if resp.status_code == 429 and _is_daily_quota(full):
                self._out_of_quota[model_id] = _daily_quota_message(model_id, full)
                log.warning("Gemini %s: free daily quota used up — not retrying", model_id)
                raise GeminiQuotaError(self._out_of_quota[model_id])
            if resp.status_code in _RETRY_STATUS and attempt < self._retries:
                wait = min(_retry_delay(full) or delay, 60.0)
                log.info("Gemini %s (attempt %d) — waiting %.0fs", resp.status_code, attempt + 1, wait)
                if self._on_wait is not None:
                    self._on_wait(f"Gemini busy (free tier limit per minute) - waiting {wait:.0f} s, "
                                  f"attempt {attempt + 1} of {self._retries}")
                time.sleep(wait)
                delay = min(delay * 2, 60.0)
                continue
            raise GeminiError(f"Gemini API error {resp.status_code}: {text}")
        raise GeminiError("Gemini API: retries exhausted")


def _default_http(timeout_s: float):
    """httpx with the same TLS tolerance as the Anthropic path (Avast-style local proxies)."""
    import ssl

    import httpx
    ctx = ssl.create_default_context()
    ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return httpx.Client(verify=ctx, timeout=timeout_s)


def _retry_delay(error_text: str) -> Optional[float]:
    m = re.search(r'"retryDelay":\s*"(\d+(?:\.\d+)?)s"', error_text)
    return float(m.group(1)) + 1.0 if m else None


# ─── Anthropic-style request → Gemini request ────────────────────────

def build_request(*, messages, max_tokens, system=None, tools=None, tool_choice=None, temperature=None,
                  simple_schema: bool = False) -> Dict[str, Any]:
    body: Dict[str, Any] = {"contents": [_content(m) for m in messages]}
    sys_text = _system_text(system)
    if sys_text:
        body["systemInstruction"] = {"parts": [{"text": sys_text}]}
    gen: Dict[str, Any] = {"maxOutputTokens": int(max_tokens) + 8192}   # room for the model's thinking
    if temperature is not None:
        gen["temperature"] = temperature
    body["generationConfig"] = gen
    if tools:
        decls = []
        for t in tools:
            d: Dict[str, Any] = {"name": t["name"], "description": t.get("description", "")}
            schema = t.get("input_schema") or {"type": "object", "properties": {}}
            if simple_schema:
                d["parameters"] = openapi_schema(schema)
            else:
                d["parametersJsonSchema"] = json_schema(schema)
            decls.append(d)
        body["tools"] = [{"functionDeclarations": decls}]
        forced = (tool_choice or {}).get("name") if (tool_choice or {}).get("type") == "tool" else None
        body["toolConfig"] = {"functionCallingConfig": (
            {"mode": "ANY", "allowedFunctionNames": [forced]} if forced else {"mode": "AUTO"})}
    return body


def _system_text(system: Any) -> str:
    if not system:
        return ""
    if isinstance(system, str):
        return system
    return "\n\n".join(b.get("text", "") for b in system if isinstance(b, dict))


def _content(message: Dict[str, Any]) -> Dict[str, Any]:
    role = "model" if message.get("role") == "assistant" else "user"
    content = message.get("content", "")
    if isinstance(content, str):
        return {"role": role, "parts": [{"text": content}]}
    parts = []
    for block in content:
        kind = block.get("type")
        if kind == "text":
            parts.append({"text": block.get("text", "")})
        elif kind == "image":
            src = block.get("source", {})
            parts.append({"inlineData": {"mimeType": src.get("media_type", "image/png"),
                                         "data": src.get("data", "")}})
    return {"role": role, "parts": parts or [{"text": ""}]}


_DROP = {"strict", "$schema", "title", "default", "examples"}


def json_schema(schema: Any) -> Any:
    """The tool's JSON Schema, minus keys Gemini does not use."""
    if isinstance(schema, dict):
        return {k: json_schema(v) for k, v in schema.items() if k not in _DROP}
    if isinstance(schema, list):
        return [json_schema(v) for v in schema]
    return schema


def openapi_schema(schema: Any) -> Any:
    """Fallback: Gemini's older OpenAPI subset — string-only enums, no free-form maps."""
    if not isinstance(schema, dict):
        return schema
    t = schema.get("type", "object")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), "string")
    out: Dict[str, Any] = {"type": str(t).upper()}
    if schema.get("description"):
        out["description"] = schema["description"]
    enum = schema.get("enum")
    if enum is not None:
        if out["type"] == "STRING":
            out["enum"] = [str(e) for e in enum]
        else:
            out["description"] = (out.get("description", "") + f" One of: {', '.join(map(str, enum))}.").strip()
    for k in ("minimum", "maximum", "minItems", "maxItems", "nullable", "format"):
        if k in schema:
            out[k] = schema[k]
    if out["type"] == "ARRAY":
        out["items"] = openapi_schema(schema.get("items", {"type": "string"}))
    if out["type"] == "OBJECT":
        props = {k: openapi_schema(v) for k, v in (schema.get("properties") or {}).items()}
        if not props:                       # a free-form map (e.g. a legend) is not expressible
            props = {"entries": {"type": "STRING", "description": "Leave empty."}}
        out["properties"] = props
        req = [r for r in schema.get("required", []) if r in props]
        if req:
            out["required"] = req
    return out


# ─── Gemini response → Anthropic-style response ──────────────────────

def parse_response(data: Dict[str, Any], spec: ModelSpec):
    blocks = []
    candidates = data.get("candidates") or []
    finish = candidates[0].get("finishReason", "") if candidates else ""
    for part in ((candidates[0].get("content") or {}).get("parts") or []) if candidates else []:
        if "functionCall" in part:
            fc = part["functionCall"]
            args = fc.get("args") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except ValueError:
                    args = {}
            blocks.append(SimpleNamespace(type="tool_use", name=fc.get("name", ""), input=args,
                                          id=f"gemini_{len(blocks)}"))
        elif "text" in part and not part.get("thought"):
            blocks.append(SimpleNamespace(type="text", text=part["text"]))
    usage = data.get("usageMetadata") or {}
    return SimpleNamespace(
        content=blocks,
        stop_reason="tool_use" if any(b.type == "tool_use" for b in blocks) else (finish or "end_turn").lower(),
        usage=SimpleNamespace(
            input_tokens=int(usage.get("promptTokenCount", 0) or 0),
            output_tokens=int(usage.get("candidatesTokenCount", 0) or 0) + int(usage.get("thoughtsTokenCount", 0) or 0),
            cache_read_input_tokens=0, cache_creation_input_tokens=0,
        ),
        model=spec.model_id,
        priced_as=spec,                     # callers price the call on THIS model (free tier: R 0)
    )
