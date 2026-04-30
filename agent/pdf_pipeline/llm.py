"""
Anthropic client wrapper for the PDF pipeline.

Responsibilities:
  • Hold a single anthropic.Anthropic client
  • Build vision-enabled requests with prompt-caching on the system prompt
  • Force tool_use with strict schemas (no JSON-from-text parsing)
  • Implement retry-with-error-feedback on schema validation failure
  • Track tokens / cost into a StageCost record
  • Optional escalation hook (Sonnet → Opus) when retry exhausts
"""

from __future__ import annotations

import base64
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ValidationError

from agent.pdf_pipeline.models import StageCost
from core.config import (
    HAIKU_4_5,
    OPUS_4_6,
    SONNET_4_5,
    ModelSpec,
    estimate_cost_zar,
)

log = logging.getLogger(__name__)


# ─── Lazy-loaded SDK handle ───────────────────────────────────────────

_anthropic_module = None


def _get_anthropic():
    """Import anthropic on demand so the package can be imported without it."""
    global _anthropic_module
    if _anthropic_module is None:
        import anthropic  # type: ignore
        _anthropic_module = anthropic
    return _anthropic_module


# ─── Response container ───────────────────────────────────────────────

@dataclass
class ToolCallResult:
    """One successful tool_use round-trip."""
    tool_name: str
    tool_input: Dict[str, Any]
    cost: StageCost = field(default_factory=lambda: StageCost(stage_name="unknown"))
    raw_response: Any = None


class LLMError(RuntimeError):
    """Raised when the LLM cannot produce a schema-valid tool call."""


# ─── Client wrapper ───────────────────────────────────────────────────

class PdfLLM:
    """
    Wrapper around anthropic.Anthropic with PDF-pipeline conventions baked in.

    Use as:
        llm = PdfLLM(api_key=..., system_prompt=...)
        result = llm.call_with_tool(
            model=SONNET_4_5,
            user_text="Extract circuits from this SLD page.",
            page_image_b64=image_b64,
            tools=[EXTRACT_SLD_TOOL],
            forced_tool_name="extract_sld",
            stage_name="extract:sld",
        )
        print(result.tool_input)
    """

    DEFAULT_MAX_TOKENS = 4096
    DEFAULT_RETRIES_ON_VALIDATION = 1   # one retry-with-feedback before escalation

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        system_prompt: str,
        client: Any = None,
    ):
        if client is not None:
            self._client = client
        else:
            anthropic = _get_anthropic()
            self._client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self._system_prompt = system_prompt

    # ── public API ────────────────────────────────────────────────────

    def call_with_tool(
        self,
        *,
        model: ModelSpec,
        user_text: str,
        page_image_b64: Optional[str],
        tools: List[Dict[str, Any]],
        forced_tool_name: Optional[str] = None,
        stage_name: str = "llm",
        max_tokens: Optional[int] = None,
        validator: Optional[type[BaseModel]] = None,
        retries: int = DEFAULT_RETRIES_ON_VALIDATION,
        escalate_to: Optional[ModelSpec] = None,
    ) -> ToolCallResult:
        """
        Send one vision-enabled request that MUST emit a tool call.

        If `validator` is supplied, the tool input is parsed through the
        Pydantic model. On validation failure we retry once with the
        validation error pasted back to the model. If that retry also
        fails AND `escalate_to` is set, we re-issue with the higher-tier
        model. The cost record reflects the total token spend.
        """
        cost = StageCost(stage_name=stage_name, model_id=model.model_id)
        last_validation_error: Optional[str] = None

        for attempt in range(retries + 1):
            messages = self._build_messages(
                user_text=user_text,
                page_image_b64=page_image_b64,
                prior_validation_error=last_validation_error,
            )
            try:
                response = self._messages_create(
                    model_id=model.model_id,
                    max_tokens=max_tokens or self.DEFAULT_MAX_TOKENS,
                    tools=tools,
                    forced_tool_name=forced_tool_name,
                    messages=messages,
                )
            except Exception as e:  # noqa: BLE001 — preserve error chain for caller
                raise LLMError(f"Anthropic API call failed: {e}") from e

            self._accumulate_cost(cost, response, model)
            cost.retry_count = attempt

            tool_block = self._extract_tool_block(response, forced_tool_name)
            if tool_block is None:
                last_validation_error = (
                    "You did not call the required tool. Call the tool exactly once."
                )
                continue

            tool_input = tool_block.input
            if validator is not None:
                try:
                    validator(**tool_input)
                except ValidationError as ve:
                    last_validation_error = (
                        "Your previous tool call failed schema validation:\n\n"
                        f"{ve}\n\nFix it and call the tool again."
                    )
                    log.info("Validation failed (attempt %d): %s", attempt, ve)
                    continue

            # success
            return ToolCallResult(
                tool_name=tool_block.name,
                tool_input=tool_input,
                cost=cost,
                raw_response=response,
            )

        # exhausted retries — escalate if we have a higher tier
        if escalate_to is not None and escalate_to.model_id != model.model_id:
            log.warning(
                "Escalating %s → %s after %d failed attempt(s)",
                model.display_name,
                escalate_to.display_name,
                retries + 1,
            )
            return self.call_with_tool(
                model=escalate_to,
                user_text=user_text,
                page_image_b64=page_image_b64,
                tools=tools,
                forced_tool_name=forced_tool_name,
                stage_name=stage_name + "+escalated",
                max_tokens=max_tokens,
                validator=validator,
                retries=0,           # one shot at the escalated model
                escalate_to=None,    # no further escalation
            )

        raise LLMError(
            f"{model.display_name} failed to produce a schema-valid tool call "
            f"after {retries + 1} attempt(s). Last error: {last_validation_error}"
        )

    # ── private helpers ───────────────────────────────────────────────

    def _build_messages(
        self,
        *,
        user_text: str,
        page_image_b64: Optional[str],
        prior_validation_error: Optional[str],
    ) -> List[Dict[str, Any]]:
        content: List[Dict[str, Any]] = []
        if page_image_b64 is not None:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": page_image_b64,
                    },
                }
            )
        text = user_text
        if prior_validation_error:
            text = f"{user_text}\n\n---\n{prior_validation_error}"
        content.append({"type": "text", "text": text})
        return [{"role": "user", "content": content}]

    def _messages_create(
        self,
        *,
        model_id: str,
        max_tokens: int,
        tools: List[Dict[str, Any]],
        forced_tool_name: Optional[str],
        messages: List[Dict[str, Any]],
    ):
        kwargs: Dict[str, Any] = {
            "model": model_id,
            "max_tokens": max_tokens,
            "system": [
                {
                    "type": "text",
                    "text": self._system_prompt,
                    "cache_control": {"type": "ephemeral"},   # frozen prefix → cache hit
                }
            ],
            "tools": tools,
            "messages": messages,
        }
        if forced_tool_name:
            kwargs["tool_choice"] = {"type": "tool", "name": forced_tool_name}

        started = time.perf_counter()
        response = self._client.messages.create(**kwargs)
        elapsed = time.perf_counter() - started
        log.debug("messages.create %s in %.2fs", model_id, elapsed)
        return response

    def _accumulate_cost(self, cost: StageCost, response: Any, model: ModelSpec) -> None:
        usage = getattr(response, "usage", None)
        if usage is None:
            return
        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0

        cost.input_tokens += input_tokens
        cost.output_tokens += output_tokens
        cost.cache_read_tokens += cache_read
        cost.cache_write_tokens += cache_write
        cost.cost_zar += estimate_cost_zar(
            input_tokens + cache_read + cache_write,
            output_tokens,
            model,
        )

    def _extract_tool_block(self, response: Any, forced_tool_name: Optional[str]):
        """Return the single tool_use content block, or None."""
        for block in getattr(response, "content", []) or []:
            if getattr(block, "type", None) == "tool_use":
                if forced_tool_name and getattr(block, "name", "") != forced_tool_name:
                    continue
                return block
        return None


# ─── Convenience factory for the standard PDF-pipeline LLM ────────────

def build_default_pdf_llm(*, api_key: Optional[str] = None) -> PdfLLM:
    from agent.pdf_pipeline.prompts.system_prompt import SYSTEM_PROMPT
    return PdfLLM(api_key=api_key, system_prompt=SYSTEM_PROMPT)


# Re-export models so callers don't need two imports
__all__ = [
    "PdfLLM",
    "ToolCallResult",
    "LLMError",
    "build_default_pdf_llm",
    "HAIKU_4_5",
    "SONNET_4_5",
    "OPUS_4_6",
]
