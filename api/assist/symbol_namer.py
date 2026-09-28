"""
Name unnamed CAD symbol shapes with the AI — once (ADR-0007).

The DXF pipeline groups loose symbol line-work into repeated shapes and draws one
picture per shape (agent/dxf_pipeline/passes/shapes.py). This module shows those
pictures, numbered, together with the drawing's legend text to the vision model in ONE
request, and makes it choose — through a strict tool schema — a name from the fixed
catalogue (agent/shared/symbol_catalogue.py), "Not an electrical symbol" or "Unsure".
The model never counts, measures or prices: geometry already counted every copy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from agent.shared.symbol_catalogue import CHOICES, NOT_ELECTRICAL, UNSURE
from core.config import EXTRACT_MODEL, ModelSpec, estimate_cost_zar

log = logging.getLogger(__name__)

MAX_SHAPES_PER_REQUEST = 40

NAME_SYMBOLS_TOOL: Dict[str, Any] = {
    "name": "name_symbols",
    "description": "Name every numbered symbol picture from the allowed list.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["symbols"],
        "properties": {
            "symbols": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "item", "legend_line"],
                    "properties": {
                        "id": {"type": "string", "description": "The symbol number, e.g. 'S3'."},
                        "item": {"type": "string", "enum": CHOICES},
                        "legend_line": {"type": "string",
                                        "description": "The legend line this symbol matches, or '' if none."},
                    },
                },
            },
        },
    },
}

SYSTEM_PROMPT = (
    "You identify symbols on South African electrical installation drawings. You are shown "
    "numbered pictures of symbols cut from a drawing, and the drawing's legend. Say what each "
    "symbol is, using the legend wherever it describes the symbol. Choose only from the allowed "
    "names. Symbols that look alike (the same shape drawn longer, shorter or turned) are "
    "normally the same item — name them consistently. Doors, windows, sanitary ware, "
    "furniture, walls, board outlines and dimension marks are "
    f"'{NOT_ELECTRICAL}'. If you cannot tell, answer '{UNSURE}' rather than guessing. You never "
    "count, measure or price anything."
)


@dataclass
class ShapeName:
    item: str
    legend_line: str = ""


def name_shapes(groups: Sequence, legend_lines: Sequence[str], *, client, model: ModelSpec = EXTRACT_MODEL
                ) -> Tuple[Dict[str, ShapeName], float]:
    """{signature: ShapeName} for the given ShapeGroups (unique signatures), and the rand cost."""
    groups = [g for g in groups if getattr(g, "image_png_b64", "")][:MAX_SHAPES_PER_REQUEST]
    if not groups:
        return {}, 0.0
    legend = "\n".join(f"- {line}" for line in legend_lines if line.strip()) or "(no legend text found)"
    content: List[Dict[str, Any]] = [{"type": "text", "text": f"Legend of this drawing set:\n{legend}"}]
    ids: Dict[str, str] = {}
    for i, g in enumerate(groups, start=1):
        sid = f"S{i}"
        ids[sid] = g.signature
        content.append({"type": "text", "text": f"Symbol {sid}: drawn {g.count} times on {g.sheet or 'the drawing'}."})
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                    "data": g.image_png_b64}})
    content.append({"type": "text", "text": "Call name_symbols once, with an entry for every symbol number."})

    response = client.messages.create(
        model=model.model_id,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        tools=[NAME_SYMBOLS_TOOL],
        tool_choice={"type": "tool", "name": "name_symbols"},
        messages=[{"role": "user", "content": content}],
    )
    usage = getattr(response, "usage", None)
    cost = estimate_cost_zar(getattr(usage, "input_tokens", 0) or 0, getattr(usage, "output_tokens", 0) or 0, model) \
        if usage is not None else 0.0
    block = next((b for b in response.content if getattr(b, "type", "") == "tool_use"), None)
    if block is None:
        log.warning("name_symbols was not called; no symbols named")
        return {}, cost
    out: Dict[str, ShapeName] = {}
    for entry in block.input.get("symbols", []) or []:
        sig = ids.get(str(entry.get("id", "")))
        item = str(entry.get("item", UNSURE))
        if sig and item in CHOICES:
            out[sig] = ShapeName(item=item, legend_line=str(entry.get("legend_line", "")))
    return out, cost


def make_shape_namer(*, client, remembered: Dict[str, Tuple[str, str]],
                     on_named: Optional[Callable[[str, str], None]] = None):
    """
    The callable the DXF project run receives (dependency injection — the pipeline never
    imports this module). Shapes already named (by a person or an earlier AI call) are
    reused for free; only new shapes are sent to the AI. Returns
    ({signature: (item, named_by)}, rand cost).
    """
    def namer(groups, legend_lines) -> Tuple[Dict[str, Tuple[str, str]], float]:
        names = {g.signature: remembered[g.signature] for g in groups if g.signature in remembered}
        new = [g for g in groups if g.signature not in remembered]
        cost = 0.0
        if new:
            try:
                found, cost = name_shapes(new, legend_lines, client=client)
            except Exception as e:  # noqa: BLE001 — naming is optional; the run continues without it
                log.error("AI symbol naming failed: %s", e)
                found = {}
            for sig, n in found.items():
                names[sig] = (n.item, "ai")
                if on_named is not None:
                    on_named(sig, n.item)
        return names, cost
    return namer
