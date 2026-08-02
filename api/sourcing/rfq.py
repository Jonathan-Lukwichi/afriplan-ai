"""
sourcing.rfq — the request-for-quote email channel.

Trade-counter suppliers (Voltex, ARB, Waco …) don't publish prices; you email a
schedule and a human replies. This module automates both ends:

  • draft_rfq()   — turns a set of BOQ lines into a clean, professional RFQ
                    email addressed to one supplier. Deterministic template;
                    no LLM needed to send.
  • QuoteParser   — parses a free-text supplier REPLY back into structured
                    SupplierQuotes. The reply is unstructured prose/tables, so
                    this is where an LLM earns its keep. We use strict tool_use
                    (same discipline as the PDF pipeline: the model fills a
                    schema, it never hand-rolls JSON), and the client is
                    injectable so tests run fully offline.

RFQ is asynchronous — you can't get a price back in the same second — so it is
NOT a synchronous SupplierConnector. The UI drives it: draft → send → paste the
reply → parse.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from core.config import HAIKU_4_5, SONNET_4_5, ModelSpec
from sourcing.models import (
    Availability,
    QuoteRequestItem,
    SourcingChannel,
    SupplierInfo,
    SupplierQuote,
)

log = logging.getLogger(__name__)


# ─── Outbound: draft the RFQ email (pure template, deterministic) ────────────

def draft_rfq(
    supplier: SupplierInfo,
    items: List[QuoteRequestItem],
    *,
    contractor_name: str = "",
    project_name: str = "",
    reply_by_days: int = 3,
) -> Dict[str, str]:
    """Return {'to', 'subject', 'body'} for an RFQ email to one supplier."""
    proj = project_name or "our current project"
    ref_line = f" (Project: {project_name})" if project_name else ""
    lines = []
    for i, it in enumerate(items, 1):
        lines.append(
            f"  {i:>2}. {it.description} — {it.qty:g} {it.unit}"
            + (f"  [pref: {it.manufacturer_hint}]" if it.manufacturer_hint else "")
        )
    schedule = "\n".join(lines)
    signoff = contractor_name or "The Estimating Team"

    subject = f"Request for Quotation — {len(items)} electrical item(s){ref_line}"
    body = (
        f"Dear {supplier.name} Sales Team,\n\n"
        f"We are preparing a tender for {proj} and would appreciate your best "
        f"trade pricing on the following electrical materials. For each line "
        f"please confirm:\n"
        f"  • unit price (ZAR, excl VAT)\n"
        f"  • current stock availability\n"
        f"  • lead time (working days) if not ex-stock\n"
        f"  • quote validity period\n\n"
        f"SCHEDULE OF ITEMS:\n{schedule}\n\n"
        f"Kindly reply within {reply_by_days} working days. Thank you for your "
        f"assistance.\n\nRegards,\n{signoff}\n"
    )
    return {"to": supplier.contact_email, "subject": subject, "body": body}


# ─── Inbound: parse a free-text reply into structured quotes (LLM) ───────────

# Strict schema the model must fill — no free-form JSON parsing.
PARSE_QUOTES_TOOL: Dict[str, Any] = {
    "name": "submit_parsed_quotes",
    "description": (
        "Return the price, availability and lead time for each requested item "
        "exactly as stated in the supplier's reply. Do not invent values; if the "
        "reply does not state a field, use the schema default and set "
        "availability to 'unknown'."
    ),
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "quotes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "item_ref": {"type": "string", "description": "The item reference/number it maps to."},
                        "matched_description": {"type": "string"},
                        "unit_price_zar": {"type": "number", "minimum": 0},
                        "availability": {
                            "type": "string",
                            "enum": [a.value for a in Availability],
                        },
                        "lead_time_days": {"type": "integer", "minimum": 0},
                        "stock_qty": {"type": "number", "minimum": 0},
                        "min_order_qty": {"type": "number", "minimum": 0},
                        "valid_until": {"type": "string", "description": "ISO date or ''"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": ["item_ref", "unit_price_zar", "availability", "lead_time_days"],
                },
            }
        },
        "required": ["quotes"],
    },
}


class QuoteParser:
    """LLM-backed parser turning a supplier reply into SupplierQuotes.

    Pass `client` (anything with `.messages.create`) to run offline in tests;
    otherwise an anthropic client is built lazily from `api_key`.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        client: Any = None,
        model: ModelSpec = HAIKU_4_5,
        escalate_to: ModelSpec = SONNET_4_5,
    ):
        self._client = client
        self._api_key = api_key
        self._model = model
        self._escalate_to = escalate_to

    def _ensure_client(self) -> Any:
        if self._client is None:
            import anthropic  # type: ignore
            kwargs: Dict[str, Any] = {}
            if self._api_key:
                kwargs["api_key"] = self._api_key
            self._client = anthropic.Anthropic(**kwargs)
        return self._client

    def parse_reply(
        self,
        supplier: SupplierInfo,
        items: List[QuoteRequestItem],
        reply_text: str,
    ) -> List[SupplierQuote]:
        client = self._ensure_client()
        schedule = "\n".join(
            f"- ref {it.item_ref}: {it.description} ({it.qty:g} {it.unit})" for it in items
        )
        user_text = (
            "A supplier replied to our RFQ. Map each priced line in their reply "
            "to the matching requested item by ref, and fill the tool.\n\n"
            f"REQUESTED ITEMS:\n{schedule}\n\n"
            f"SUPPLIER REPLY (verbatim):\n\"\"\"\n{reply_text}\n\"\"\""
        )
        response = client.messages.create(
            model=self._model.model_id,
            max_tokens=2048,
            tools=[PARSE_QUOTES_TOOL],
            tool_choice={"type": "tool", "name": PARSE_QUOTES_TOOL["name"]},
            messages=[{"role": "user", "content": [{"type": "text", "text": user_text}]}],
        )
        tool_input = self._extract_tool_input(response)
        if tool_input is None:
            log.warning("QuoteParser got no tool_use block from the model.")
            return []
        return self._to_quotes(supplier, tool_input, reply_text)

    @staticmethod
    def _extract_tool_input(response: Any) -> Optional[Dict[str, Any]]:
        for block in getattr(response, "content", []) or []:
            if getattr(block, "type", None) == "tool_use":
                inp = getattr(block, "input", None)
                if isinstance(inp, str):
                    try:
                        return json.loads(inp)
                    except json.JSONDecodeError:
                        return None
                return inp
        return None

    @staticmethod
    def _to_quotes(
        supplier: SupplierInfo, tool_input: Dict[str, Any], reply_text: str
    ) -> List[SupplierQuote]:
        out: List[SupplierQuote] = []
        for q in tool_input.get("quotes", []):
            try:
                avail = Availability(q.get("availability", "unknown"))
            except ValueError:
                avail = Availability.UNKNOWN
            out.append(SupplierQuote(
                item_ref=str(q.get("item_ref", "")),
                supplier_id=supplier.supplier_id,
                supplier_name=supplier.name,
                channel=SourcingChannel.RFQ_EMAIL,
                unit_price_zar=float(q.get("unit_price_zar", 0) or 0),
                availability=avail,
                stock_qty=q.get("stock_qty"),
                lead_time_days=int(q.get("lead_time_days", 0) or 0),
                min_order_qty=float(q.get("min_order_qty", 1) or 1),
                valid_until=q.get("valid_until") or None,
                notes=f"Parsed from {supplier.name} RFQ reply.",
                raw_source=reply_text[:500],
                parse_confidence=float(q.get("confidence", 0.85) or 0.85),
            ))
        return out
