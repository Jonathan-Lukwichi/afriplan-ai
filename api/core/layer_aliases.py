"""
DXF layer-name normalisation.

Different CAD vendors use different layer-name conventions for the
same logical layer ("electrical lighting"). This file is the canonical
list of aliases we recognise.

The DXF pipeline imports `is_electrical_layer()` and `normalise_layer()`
to build a stable layer index regardless of which CAD tool produced
the file.
"""

from __future__ import annotations

import re
from typing import List


# ─── Canonical electrical-layer prefixes ──────────────────────────────

ELECTRICAL_LAYER_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"^elec", re.I),
    re.compile(r"^e[-_]", re.I),
    re.compile(r"^mep[-_]?elec", re.I),
    re.compile(r"_elec$", re.I),
    re.compile(r"electrical", re.I),
    re.compile(r"\b(lights?|lighting|luminaires?)\b", re.I),
    re.compile(r"\b(power|sockets?|outlets?)\b", re.I),
    re.compile(r"\b(switches?)\b", re.I),
    re.compile(r"\b(data|comms?)\b", re.I),
    re.compile(r"distribution[-_ ]?boards?", re.I),
    re.compile(r"\bDB[-_ ]", re.I),
    re.compile(r"\bMSB\b", re.I),
    # AutoCAD plant standard
    re.compile(r"^B_ELEC", re.I),
    # PDF-imported electrical layers (frequent in ArchiCAD exports)
    re.compile(r"^PDF_ELEC|^PDF_MEP", re.I),
]


# Layer names we know carry text labels for circuit / fixture annotations
ELECTRICAL_TEXT_LAYERS = {
    "PDF_TEXT", "B_ELECTRICAL", "E_TEXT", "ELEC_TEXT",
    "ELEC-TEXT", "MEP_TEXT", "ANNOT_ELEC",
}


def is_electrical_layer(layer_name: str) -> bool:
    """True if the layer name matches any known electrical convention."""
    if not layer_name:
        return False
    name = layer_name.strip()
    if name.upper() in ELECTRICAL_TEXT_LAYERS:
        return True
    for pat in ELECTRICAL_LAYER_PATTERNS:
        if pat.search(name):
            return True
    return False


# ─── Architectural / non-electrical layers (to isolate the electrical) ──

ARCHITECTURAL_LAYER_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"wall|column|slab|roof|stair|railing|beam|structural", re.I),
    re.compile(r"furniture|interior|basin|cabinet|door|window|shell", re.I),
    re.compile(r"dimension|hatch|grid|axis|border|title|annotation", re.I),
    re.compile(r"caddie|morph|plumb|sanitary|landscap|parking|glaz|handrail", re.I),
    # AIA / ISO 13567 CAD layer discipline prefixes. Electrical (E-), Fire (F-)
    # and Telecom (T-) are NOT here — everything else is another trade.
    re.compile(r"^[ACILMPQSVWX][-_]", re.I),          # A-DOOR, P-SANR-FIXT, C-PRKG, S-COLS…
    re.compile(r"^(arch|civ|struct|plumb|mech|land|equip|survey)", re.I),
]


# ─── Wiring layers (where cable length is measured) ─────────────────────

WIRING_LAYER_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"wire|cable|circuit|conduit|reticulation|wiring", re.I),
]


def is_wiring_layer(layer_name: str) -> bool:
    """
    True for layers that carry actual CABLE/WIRE geometry (so we measure their
    length). Distinct from is_electrical_layer: an electrical *symbol* layer
    (e.g. 'MEP Electrical') holds fixture line-work we must NOT count as cable.
    """
    if not layer_name:
        return False
    return any(p.search(layer_name) for p in WIRING_LAYER_PATTERNS)


def is_architectural_layer(layer_name: str) -> bool:
    """
    True for layers that carry architectural / structural / furniture geometry
    we must NOT treat as electrical (e.g. wall polylines counted as cable).
    Electrical-layer matches win — a layer that looks electrical is never
    treated as architectural.
    """
    if not layer_name:
        return False
    if is_electrical_layer(layer_name):
        return False
    name = layer_name.strip()
    return any(p.search(name) for p in ARCHITECTURAL_LAYER_PATTERNS)


def normalise_layer(layer_name: str) -> str:
    """
    Reduce a layer name to a stable, comparable form.
    Used for grouping and de-duplicating layer counts.
    """
    if not layer_name:
        return ""
    n = layer_name.strip().upper()
    # Drop common prefixes
    n = re.sub(r"^(PDF_|B_|E_|ELEC[-_]?)", "", n)
    # Replace separators with single space
    n = re.sub(r"[-_]+", " ", n)
    return n.strip()
