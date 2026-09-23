"""
ItemKey taxonomy — one identity for a BOQ item, whoever wrote the description.

A human bill says "WHITE, 100X100, 16 Ampere ... double switched socket outlet",
the PDF pipeline says "16A double switched socket — Office", the DXF pipeline
says "Double Socket". All three are ItemKey("socket_double", ""). Matching
predicted lines to reference lines is only possible on this normalised key.

    family  what the item is                  (drives the BOQ network + section)
    spec    the variant that changes price/qty (cable size+cores, conduit size...)
            — deliberately "" where pipelines cannot see the variant (socket amps,
              light wattage), so identity is not lost on wording differences.

Rules are ordered; first match wins. Pure, deterministic, no I/O.
"""

from __future__ import annotations

import re
from typing import Callable, Dict, List, NamedTuple, Optional, Tuple


class ItemKey(NamedTuple):
    family: str
    spec: str = ""

    def __str__(self) -> str:
        return f"{self.family}|{self.spec}" if self.spec else self.family


# ─── normalisation helpers ───────────────────────────────────────────

def _norm(text: str) -> str:
    t = (text or "").replace("²", "2").replace(" ", " ").lower()
    t = re.sub(r"sq\.?\s*mm", "mm2", t)
    t = re.sub(r"(\d)\s*mm\s*2\b", r"\1mm2", t)
    return re.sub(r"\s+", " ", t).strip()


_SIZE = re.compile(r"(\d+(?:\.\d+)?)\s*mm2")
_CORES = re.compile(r"(?:x\s*)?(\d)\s*(?:c\b|core)")
_DIAM = re.compile(r"(\d{2,3})\s*mm")
_TRUNK = re.compile(r"\bp\s?(\d{4})\b")


def _size(t: str) -> str:
    m = _SIZE.search(t)
    return f"{m.group(1)}mm2" if m else ""


def _cable_spec(t: str) -> str:
    size = _size(t)
    m = _CORES.search(t[t.find("mm2"):] if "mm2" in t else t)
    return f"{size}|{m.group(1)}c" if m and size else size


_COUNT_UNITS = {"ea", "each", "no", "no.", "nr", "pc", "pcs"}


# ─── rules ───────────────────────────────────────────────────────────
# Each rule: (regex on normalised text, family, spec-extractor or None)

Spec = Optional[Callable[[str], str]]


def _switch_spec(t: str) -> str:
    m = re.search(r"(\d)\s*[- ]?\s*(?:lever|gang)", t)
    levers = m.group(1) if m else "1"
    ways = "2way" if re.search(r"2\s*[- ]?\s*way", t) else "1way"
    return f"{levers}lever|{ways}"


def _chasing_spec(t: str) -> str:
    if re.search(r"1\s*m\s*x\s*1\s*m", t):
        return "1mx1m"
    h = re.search(r"(\d+)\s*m\s*\(height\)|for\s*(\d+)\s*m\b", t)
    d = re.search(r"(\d{2})\s*mm\s*conduit", t)
    height = (h.group(1) or h.group(2)) if h else ""
    return "|".join(x for x in (f"{height}m" if height else "", f"{d.group(1)}mm" if d else "") if x)


def _conduit_spec(t: str) -> str:
    m = _DIAM.search(t)
    base = f"{m.group(1)}mm" if m else ""
    return f"{base}|galv" if "galvani" in t else base


_RULES: List[Tuple[re.Pattern, str, Spec]] = [
    # ── bulk supply / kiosk ──
    (re.compile(r"\bkiosk\b"), "kiosk", None),
    (re.compile(r"plinth"), "plinth", None),
    (re.compile(r"connection fee"), "connection_fee", None),
    (re.compile(r"certificate of complia"), "coc", None),
    (re.compile(r"mccb|mcb/"), "breaker", lambda t: (re.search(r"(\d+)\s*a\b", t).group(1) + "a") if re.search(r"(\d+)\s*a\b", t) else ""),
    # ── underground ──
    (re.compile(r"trench"), "trench", None),
    (re.compile(r"warning tape|danger tape"), "warning_tape", None),
    (re.compile(r"sleeve"), "sleeve", lambda t: (_DIAM.search(t).group(1) + "mm") if _DIAM.search(t) else ""),
    (re.compile(r"manhole"), "manhole", lambda t: "fibre" if "fibre" in t else "electrical"),
    # ── containment ──
    (re.compile(r"trunking.*cover"), "trunking_cover", lambda t: f"p{_TRUNK.search(t).group(1)}" if _TRUNK.search(t) else ""),
    (re.compile(r"trunking.*bend"), "trunking_bend", lambda t: f"p{_TRUNK.search(t).group(1)}" if _TRUNK.search(t) else ""),
    (re.compile(r"trunking.*t-?\s?piece"), "trunking_tee", lambda t: f"p{_TRUNK.search(t).group(1)}" if _TRUNK.search(t) else ""),
    (re.compile(r"trunking"), "trunking", lambda t: f"p{_TRUNK.search(t).group(1)}" if _TRUNK.search(t) else ""),
    (re.compile(r"wire basket"), "wire_basket", lambda t: (_DIAM.search(t).group(1) + "mm") if _DIAM.search(t) else ""),
    (re.compile(r"cable tray"), "cable_tray", lambda t: (_DIAM.search(t).group(1) + "mm") if _DIAM.search(t) else ""),
    (re.compile(r"chasing"), "chasing", _chasing_spec),
    (re.compile(r"draw wire"), "draw_wire", None),
    (re.compile(r"galvanised conduit \d+ ?met|straps"), "other", None),
    (re.compile(r"conduit"), "conduit", _conduit_spec),
    (re.compile(r"round box|looping box"), "round_box", None),
    (re.compile(r"round plug|plug top|\blead 3 pin"), "plug_top", lambda t: "5a" if re.search(r"\b5\s*amp", t) else ""),
    (re.compile(r"wall ?box"), "wall_box", lambda t: "100x100" if re.search(r"100\s*x\s*100", t) else ("100x50" if re.search(r"100\s*x\s*50", t) else "")),
    (re.compile(r"extension box"), "extension_box", None),
    (re.compile(r"waterproof box"), "waterproof_box", None),
    # ── wiring ──
    (re.compile(r"gp wire|reticulation wire"), "gp_wire", _size),
    (re.compile(r"surfix"), "surfix", _cable_spec),
    (re.compile(r"\babc\b"), "abc_cable", _cable_spec),
    # ── outlets / control (before lighting so 'switched socket' is a socket) ──
    (re.compile(r"double.*socket|socket.*double|2\s*gang.*socket"), "socket_double", None),
    (re.compile(r"single.*socket|socket.*single"), "socket_single", None),
    (re.compile(r"weatherproof socket|waterproof socket"), "socket_weatherproof", None),
    (re.compile(r"floor (box|socket)"), "socket_floor", None),
    (re.compile(r"socket|power outlet"), "socket_double", None),
    (re.compile(r"data (socket|outlet|point)|cat ?6|rj45"), "data_outlet", None),
    (re.compile(r"isolator"), "isolator", None),
    (re.compile(r"day ?/? ?night"), "day_night_switch", None),
    (re.compile(r"\bswitch\b|lever"), "switch", _switch_spec),
    # ── lighting ──
    (re.compile(r"flood.*post|high ?mast"), "light_highmast", None),
    (re.compile(r"solar.*(post|lantern)"), "light_solar_post", None),
    (re.compile(r"flood ?light"), "light_flood", None),
    (re.compile(r"vapou?r ?proof|\bbatten\b"), "light_vapour_proof", None),
    (re.compile(r"bulkhead"), "light_bulkhead", None),
    (re.compile(r"down ?light"), "light_downlight", None),
    (re.compile(r"600 ?x ?1200|recessed|led panel"), "light_panel", None),
    (re.compile(r"emergency"), "light_emergency", None),
    (re.compile(r"pole light|street light"), "light_pole", None),
    (re.compile(r"exit sign"), "exit_sign", None),
    (re.compile(r"extinguisher"), "fire_extinguisher", None),
    (re.compile(r"smoke detector"), "smoke_detector", None),
    (re.compile(r"\blight\b|luminaire|fluorescent|pendant|spotlight"), "light_other", None),
    # ── distribution ──
    (re.compile(r"\bdb\b|db[- ]?\w+:|distribution board"), "db", None),
    (re.compile(r"energy meter|\bmeter\b"), "meter", None),
]

_ROLE_ONLY = re.compile(r"^\s*(supply|install)\s*$", re.I)


def line_role(description: str) -> str:
    """supply | install | combined — the SA supply/install split convention."""
    t = _norm(description)
    if re.match(r"^supply\b(?! and install)", t):
        return "supply"
    if re.match(r"^install\b", t):
        return "install"
    return "combined"


def classify_item(description: str, *, parent: str = "", unit: str = "") -> ItemKey:
    """
    Map one BOQ line to its ItemKey.

    `parent` is the spec header row above a bare 'Supply'/'Install' child row in
    a human bill ('95mm2 x 4C PVC SWA PVC 600-1000V Cable'). `unit` separates a
    cable (m) from its termination (Ea) when both share the same parent text.
    """
    text = description or ""
    if _ROLE_ONLY.match(text) and parent:
        text = parent
    t = _norm(text)
    counted = (unit or "").strip().lower() in _COUNT_UNITS

    # Cables / earths / terminations need the unit, so they are handled first.
    if re.search(r"terminat", t):
        return ItemKey("termination", ("bcew|" + _size(t)) if "bcew" in t else _size(t))
    if "bcew" in t or ("earth" in t and _size(t)):
        return ItemKey("termination", "bcew|" + _size(t)) if counted else ItemKey("bcew", _size(t))
    if re.search(r"\bswa\b|armou?r", t) or (re.search(r"\d\s*core cable", t) and "abc" not in t):
        spec = _cable_spec(t)
        return ItemKey("termination", _size(t)) if counted else ItemKey("swa_cable", spec)

    for pat, family, spec_fn in _RULES:
        if pat.search(t):
            return ItemKey(family, spec_fn(t) if spec_fn else "")
    return ItemKey("other", "")


# ─── family → Wedela bill section letter ─────────────────────────────
# A: DBs / excavations / main cables   B: trunking, wiring, trays
# C: general purpose outlets           D: general lighting
# F: bulk power (kiosk / minisub)      X: not a drawing-derived item

BILL_SECTION_OF: Dict[str, str] = {
    **{f: "A" for f in ("trench", "warning_tape", "sleeve", "manhole", "db", "swa_cable",
                        "bcew", "termination", "abc_cable", "meter")},
    **{f: "B" for f in ("cable_tray", "wire_basket", "trunking", "trunking_cover",
                        "trunking_bend", "trunking_tee", "round_box", "plug_top", "gp_wire",
                        "surfix")},
    **{f: "C" for f in ("socket_double", "socket_single", "socket_weatherproof",
                        "socket_floor", "data_outlet", "isolator", "wall_box",
                        "extension_box", "waterproof_box", "chasing", "conduit",
                        "draw_wire")},
    **{f: "D" for f in ("light_panel", "light_flood", "light_highmast", "light_solar_post",
                        "light_vapour_proof", "light_bulkhead", "light_downlight",
                        "light_emergency", "light_pole", "light_other", "switch",
                        "day_night_switch", "exit_sign", "fire_extinguisher",
                        "smoke_detector")},
    **{f: "F" for f in ("kiosk", "plinth", "breaker", "connection_fee", "coc")},
    "other": "X",
}

FAMILIES: List[str] = sorted(BILL_SECTION_OF)
