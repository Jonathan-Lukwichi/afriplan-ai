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
"too many requests" answer is waited out and retried.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from core.config import ModelSpec, gemini_model_for

log = logging.getLogger(__name__)

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_RETRY_STATUS = {429, 500, 502, 503, 504}


class GeminiError(RuntimeError):
    pass


class GeminiClient:
    """Drop-in for `anthropic.Anthropic` where only `messages.create` is used."""

    def __init__(self, *, api_key: str, http_client: Any = None, max_concurrent: int = 2,
                 max_retries: int = 6, timeout_s: float = 300.0):
        if not api_key:
            raise GeminiError("GEMINI_API_KEY is not set")
        self._key = api_key
        self._http = http_client or _default_http(timeout_s)
        self._gate = threading.Semaphore(max(1, max_concurrent))
        self._retries = max_retries
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
        url = API_URL.format(model=model_id)
        delay = 5.0
        for attempt in range(self._retries + 1):
            with self._gate:
                resp = self._http.post(url, json=body, headers={"x-goog-api-key": self._key,
                                                                "content-type": "application/json"})
            if resp.status_code == 200:
                return resp.json()
            text = resp.text[:600]
            if resp.status_code in _RETRY_STATUS and attempt < self._retries:
                wait = _retry_delay(text) or delay
                log.info("Gemini %s (attempt %d) — waiting %.0fs", resp.status_code, attempt + 1, wait)
                time.sleep(min(wait, 60.0))
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
