"""
Legend-Driven Symbol Extraction (LDSE) — the shared spec.

An electrical drawing's LEGEND is the ground truth for what its symbols mean.
Symbols vary between drawings; the legend is the per-drawing dictionary. Both
pipelines read their legend into this shared shape, so recognition adapts to
each drawing instead of relying on a hardcoded symbol table.

This module holds ONLY the shared data model + the description→BOQ bridge
(`classify_description`). The actual legend *extraction* lives in each pipeline
(DXF geometry vs PDF vision) so the pipelines stay independent (CLAUDE.md rule).

The golden bridge: a legend's DESCRIPTION text is standard English
("16A Double Switched Socket") which maps cleanly to a priced BOQ item —
regardless of what the glyph looks like or how the block is named.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field

from agent.shared.boq import BQSection, GapItem


class LegendEntry(BaseModel):
    """One row of a drawing's legend."""
    symbol_key: str = ""            # block name / glyph id the graphic resolves to
    description: str = ""           # raw legend text, e.g. "16A Double Switched Socket @300mm"
    canonical_item: str = ""        # normalised BOQ item name (from classify_description)
    section: BQSection = BQSection.FINAL_CABLES
    qty_in_legend: Optional[int] = None   # if the legend prints a QTY column
    mounting_mm: Optional[int] = None     # mounting height parsed from the text
    # graphic anchor (for geometry matching); optional
    graphic_x: float = 0.0
    graphic_y: float = 0.0
    source_ref: str = ""            # sheet / drawing reference


class Legend(BaseModel):
    """A drawing's (or project's) full symbol dictionary."""
    entries: List[LegendEntry] = Field(default_factory=list)
    source: str = ""               # "dxf" | "pdf"
    sheet_ref: str = ""

    def by_canonical(self) -> dict:
        out = {}
        for e in self.entries:
            out.setdefault(e.canonical_item, []).append(e)
        return out


# ─── description → BOQ item bridge ───────────────────────────────────
# Ordered rules on natural-language legend descriptions. First match wins.

_DESC_RULES: List[Tuple[re.Pattern[str], str, BQSection]] = [
    # Sockets / power
    (re.compile(r"double.*(switched\s*)?socket|2\s*gang.*socket|socket.*double", re.I),
        "16A Double Switched Socket", BQSection.POWER_OUTLETS),
    (re.compile(r"single.*(switched\s*)?socket|1\s*gang.*socket|socket.*single", re.I),
        "16A Single Switched Socket", BQSection.POWER_OUTLETS),
    (re.compile(r"weatherproof\s*socket|waterproof\s*socket|ip\d+\s*socket", re.I),
        "Weatherproof Socket", BQSection.POWER_OUTLETS),
    (re.compile(r"floor\s*(box|socket|outlet)", re.I),
        "Floor Box Socket", BQSection.POWER_OUTLETS),
    (re.compile(r"\bstove\b|cooker|oven|hob", re.I),
        "Stove Isolator/Outlet", BQSection.POWER_OUTLETS),
    # Data / comms
    (re.compile(r"data\s*(socket|outlet|point)|cat\s*6|rj\s*45|network\s*point", re.I),
        "Data Socket (CAT6)", BQSection.DATA_COMMS),
    (re.compile(r"telephone|\btel\b\s*(point|outlet)|\bTP\b", re.I),
        "Telephone Point", BQSection.DATA_COMMS),
    (re.compile(r"\btv\b|television|coax", re.I),
        "TV Outlet", BQSection.DATA_COMMS),
    # Switches / control
    (re.compile(r"day\s*/?\s*night|photocell|d\s*/\s*n\b", re.I),
        "Day/Night Switch", BQSection.LIGHTING),
    (re.compile(r"isolator|\bcos\b|change\s*over|\biso\b", re.I),
        "Isolator Switch", BQSection.POWER_OUTLETS),
    (re.compile(r"dimmer", re.I),
        "Dimmer Switch", BQSection.LIGHTING),
    (re.compile(r"(1|one)\s*lever|1\s*gang.*switch|single\s*switch", re.I),
        "1-Lever Switch", BQSection.LIGHTING),
    (re.compile(r"(2|two)\s*lever|2\s*gang.*switch", re.I),
        "2-Lever Switch", BQSection.LIGHTING),
    (re.compile(r"(3|three)\s*lever|3\s*gang.*switch", re.I),
        "3-Lever Switch", BQSection.LIGHTING),
    (re.compile(r"(4|four)\s*lever|4\s*gang.*switch", re.I),
        "4-Lever Switch", BQSection.LIGHTING),
    # Safety (before generic lighting — 'emergency light' must not match 'light')
    (re.compile(r"emergency\s*light|emergency\s*luminaire|\bemergency\b.*(fitting|light)", re.I),
        "Emergency Light", BQSection.FIRE_SAFETY),
    (re.compile(r"exit\s*sign|exit\s*light|\bexit\b", re.I),
        "Exit Sign", BQSection.FIRE_SAFETY),
    (re.compile(r"smoke\s*detector|smoke\s*alarm", re.I),
        "Smoke Detector", BQSection.FIRE_SAFETY),
    (re.compile(r"extinguisher", re.I),
        "Fire Extinguisher", BQSection.FIRE_SAFETY),
    # Lighting
    (re.compile(r"recessed.*(led|fluor)|led.*panel|\d+\s*x\s*\d+.*(led|fluor)|panel\s*light", re.I),
        "Recessed LED Panel", BQSection.LIGHTING),
    (re.compile(r"down\s*light|down\s*lighter|\bdl\b", re.I),
        "LED Downlight", BQSection.LIGHTING),
    (re.compile(r"flood\s*light|floodlight", re.I),
        "LED Floodlight", BQSection.LIGHTING),
    (re.compile(r"bulkhead", re.I),
        "Bulkhead Light", BQSection.LIGHTING),
    (re.compile(r"vapou?r\s*proof|weatherproof.*(light|fluor)|batten", re.I),
        "Vapour Proof Light", BQSection.LIGHTING),
    (re.compile(r"surface\s*mount.*(light|led)|ceiling\s*light|\bcl\b", re.I),
        "Surface LED Light", BQSection.LIGHTING),
    (re.compile(r"pendant", re.I),
        "Pendant Light", BQSection.LIGHTING),
    (re.compile(r"high\s*bay|ufo", re.I),
        "High Bay Light", BQSection.LIGHTING),
    (re.compile(r"pole\s*light|street\s*light|outdoor.*pole", re.I),
        "Pole Light", BQSection.LIGHTING),
    (re.compile(r"\bled\b|luminaire|lamp|fluor|\blight\b", re.I),
        "Light Fitting (generic)", BQSection.LIGHTING),
    # Distribution / supply
    (re.compile(r"distribution\s*board|\bdb\b|kiosk|db\s*board", re.I),
        "Distribution Board", BQSection.DISTRIBUTION),
    (re.compile(r"\bmeter\b|metering|kwh", re.I),
        "Energy Meter", BQSection.INCOMING),
    # Water / HVAC
    (re.compile(r"geyser|water\s*heater|hot\s*water\s*cylinder|hwc", re.I),
        "Geyser", BQSection.FINAL_CABLES),
    (re.compile(r"air\s*condition|aircon|\bhvac\b|split\s*unit|heat\s*pump", re.I),
        "Air Conditioning Unit", BQSection.FINAL_CABLES),
    (re.compile(r"extractor\s*fan|extract\s*fan|\bfan\b", re.I),
        "Extractor Fan", BQSection.FINAL_CABLES),
    # Renewables
    (re.compile(r"solar|photovoltaic|\bpv\b", re.I),
        "Solar PV Panel", BQSection.SOLAR_PV),
]

_MOUNTING_RE = re.compile(r"@?\s*(\d{3,4})\s*mm", re.I)


def classify_description(text: str) -> Optional[Tuple[str, BQSection]]:
    """
    Map a natural-language legend description to (canonical BOQ item, section).
    Returns None if the text isn't a recognisable electrical item (e.g. a
    category header like 'LIGHTS' or a note).
    """
    if not text:
        return None
    for pat, item, section in _DESC_RULES:
        if pat.search(text):
            return (item, section)
    return None


def parse_mounting_mm(text: str) -> Optional[int]:
    """Pull a mounting height in mm from a description, e.g. '@300mm above FFL'."""
    m = _MOUNTING_RE.search(text or "")
    return int(m.group(1)) if m else None


def build_legend_entry(description: str, *, symbol_key: str = "",
                       qty: Optional[int] = None, source_ref: str = "") -> Optional[LegendEntry]:
    """Turn one raw legend line into a LegendEntry, or None if not electrical."""
    hit = classify_description(description)
    if hit is None:
        return None
    canonical, section = hit
    return LegendEntry(
        symbol_key=symbol_key, description=description.strip(),
        canonical_item=canonical, section=section,
        qty_in_legend=qty, mounting_mm=parse_mounting_mm(description),
        source_ref=source_ref,
    )


def legend_from_symbol_map(mapping: dict, *, source: str = "", sheet_ref: str = "") -> Legend:
    """
    Build a Legend from a {symbol_glyph: description} map (how the PDF vision
    pass reports a legend). Dedupes to one entry per canonical BOQ item.
    """
    entries: dict = {}
    for symbol, description in (mapping or {}).items():
        entry = build_legend_entry(str(description), symbol_key=str(symbol), source_ref=sheet_ref)
        if entry is None:
            continue
        entries.setdefault(entry.canonical_item, entry)
    return Legend(entries=list(entries.values()), source=source, sheet_ref=sheet_ref)


def billed_canonical_items(descriptions) -> set:
    """
    The set of canonical BOQ items represented by a bunch of line descriptions.
    Each description is run through the SAME classifier as the legend, so a
    legend item and a billed line match even when their wording differs
    (e.g. legend 'Recessed LED Panel' vs line '600x1200 Recessed 3x18W LED panel').
    """
    items = set()
    for d in descriptions or []:
        hit = classify_description(str(d))
        if hit is not None:
            items.add(hit[0])
    return items


def coverage_gaps(legend: Legend, billed_items: set) -> List[GapItem]:
    """
    One gap per legend item that never made it into a priced line. The legend is
    the drawing's declared inventory of symbol types; anything it lists that we
    did not bill is a visible 'declared but not counted' — never a silent miss.
    `billed_items` is the set of canonical items already billed
    (see `billed_canonical_items`).
    """
    out: List[GapItem] = []
    if not legend or not legend.entries:
        return out
    for entry in legend.entries:
        if entry.canonical_item in billed_items:
            continue
        out.append(GapItem(
            section=entry.section,
            description=f"Legend lists '{entry.canonical_item}' but no instances were counted",
            assumption="Symbol declared in the legend but not matched/counted in the drawing.",
            suggested_action="Verify the count from the drawing.",
            severity="medium", drawing_ref=f"{legend.source or 'legend'}",
        ))
    return out
