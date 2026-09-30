"""
Say which names from the two readers are the same real thing — the AI half of combining (ADR-0008).

Combining (`api/consolidate/combine.py`) first pairs everything Python can match exactly.
Only the leftovers come here: a board the PDF calls "KIOSK busbar" and the DWG calls
"KIOSK"; a fitting the DWG knows as "DL-12W" and the PDF as "LED Downlight". The model
answers through a strict tool whose choices are ONLY the names offered — same, different
or unsure, with a short reason. It never counts, measures, prices or picks which reader
wins: Python does that from the evidence.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from core.config import MATCH_MODEL, ModelSpec, estimate_cost_zar

log = logging.getLogger(__name__)

MAX_NAMES = 80

SYSTEM_PROMPT = (
    "You compare two readings of the same South African electrical drawing set: one from the "
    "CAD files (DWG) and one from the PDF prints. Each reading names equipment or fittings in "
    "its own words. For every PDF name, say which DWG name is the same real thing, if any. "
    "Distribution boards, kiosks and mini-subs are named by their tag (DB-AB1, KIOSK); extra "
    "words such as a drawing number, 'busbar', 'existing' or a location usually describe the "
    "same equipment. A board with a different number (DB-1 vs DB-2) is a different board. "
    "Answer 'unsure' rather than guessing. You never count, measure or price anything."
)


def _tool(dwg_names: Sequence[str], pdf_names: Sequence[str]) -> Dict[str, Any]:
    return {
        "name": "match_names",
        "description": "For every PDF name, the DWG name that is the same thing, or none.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["matches"],
            "properties": {
                "matches": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["pdf_name", "dwg_name", "verdict", "reason"],
                        "properties": {
                            "pdf_name": {"type": "string", "enum": list(pdf_names)},
                            "dwg_name": {"type": "string", "enum": [*dwg_names, ""],
                                         "description": "'' when no DWG name is the same thing."},
                            "verdict": {"type": "string", "enum": ["same", "different", "unsure"]},
                            "reason": {"type": "string", "description": "A few words."},
                        },
                    },
                },
            },
        },
    }


def match_names(kind: str, dwg_names: Sequence[str], pdf_names: Sequence[str], *, client,
                model: ModelSpec = MATCH_MODEL) -> Tuple[Dict[str, Tuple[str, str, str]], float]:
    """{PDF name: (DWG name or '', verdict, reason)} and the rand cost of the call."""
    dwg_names, pdf_names = list(dwg_names)[:MAX_NAMES], list(pdf_names)[:MAX_NAMES]
    if not dwg_names or not pdf_names:
        return {}, 0.0
    what = "equipment (boards, kiosks, supplies)" if kind == "equipment" else "fittings and outlets"
    text = (f"Kind of names: {what}.\n\nDWG names:\n" + "\n".join(f"- {n}" for n in dwg_names)
            + "\n\nPDF names:\n" + "\n".join(f"- {n}" for n in pdf_names)
            + "\n\nCall match_names once, with one entry for every PDF name.")
    tool = _tool(dwg_names, pdf_names)
    response = client.messages.create(
        model=model.model_id, max_tokens=4000, system=SYSTEM_PROMPT, tools=[tool],
        tool_choice={"type": "tool", "name": "match_names"},
        messages=[{"role": "user", "content": text}],
    )
    usage = getattr(response, "usage", None)
    cost = estimate_cost_zar(getattr(usage, "input_tokens", 0) or 0, getattr(usage, "output_tokens", 0) or 0,
                             getattr(response, "priced_as", None) or model) if usage is not None else 0.0
    block = next((b for b in response.content if getattr(b, "type", "") == "tool_use"), None)
    if block is None:
        log.warning("match_names was not called; nothing matched")
        return {}, cost
    out: Dict[str, Tuple[str, str, str]] = {}
    for m in block.input.get("matches", []) or []:
        pdf_name, dwg_name = str(m.get("pdf_name", "")), str(m.get("dwg_name", ""))
        verdict, reason = str(m.get("verdict", "unsure")), str(m.get("reason", ""))
        if pdf_name not in pdf_names or (dwg_name and dwg_name not in dwg_names):
            continue
        if verdict not in ("same", "different", "unsure"):
            verdict = "unsure"
        if verdict == "same" and not dwg_name:
            verdict = "unsure"                       # 'same' as nothing is not an answer
        out[pdf_name] = (dwg_name, verdict, reason)
    return out, cost


def make_name_matcher(*, client, on_cost: Optional[Callable[[float], None]] = None,
                      model: ModelSpec = MATCH_MODEL):
    """The callable combining receives (dependency injection — consolidate never imports this).
    An API failure returns no matches, so combining carries on with exact matches alone."""
    def matcher(kind: str, dwg_names: List[str], pdf_names: List[str]) -> Dict[str, Tuple[str, str, str]]:
        try:
            found, cost = match_names(kind, dwg_names, pdf_names, client=client, model=model)
        except Exception as e:  # noqa: BLE001 — matching is optional
            log.error("AI name matching failed: %s", e)
            return {}
        if on_cost is not None:
            on_cost(cost)
        return found
    return matcher
