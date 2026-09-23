"""
The layered BOQ network — how a bill of quantities is actually produced.

    Layer 0  DRAWINGS     sld · lighting_layout · plug_layout · site_plan · schedule …
    Layer 1  EVIDENCE     what an estimator reads off them (counts, lengths, DB list)
    Layer 2  QUANTITIES   PRIMARY items (counted / measured)  +
                          DERIVED items (fitted ratios over primary items — evaluation.ratios)
    Layer 3  PRICED LINES qty × rate (core.rate_model / the reference rates)
    Layer 4  TOTALS       section → building → project (+contingency, VAT, P&Gs)

This module encodes the Layer 0 → Layer 2 edges: for every ItemKey family, which
drawing types carry its evidence and how it is measured. It is the single source
for three product questions:

  • What drawings are needed for a complete BOQ?        → requirements_matrix()
  • What can be produced from what was uploaded?        → reproducible_families()
  • Which drawing should the user send next, and why?   → missing_for()

It is an explicit, explainable graph — the "network" whose weights are the fitted
ratios. No training, no hidden state.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Iterable, List, Set

from pydantic import BaseModel, Field


class DrawingType(str, Enum):
    SLD = "sld"
    LIGHTING = "lighting_layout"
    PLUGS = "plug_layout"
    SITE = "site_plan"
    SCHEDULE = "schedule"
    LEGEND = "legend"
    REGISTER = "register"
    ARCHITECTURAL = "architectural"


class Method(str, Enum):
    COUNT = "count"              # enumerate symbols
    LENGTH = "length"            # measure / read annotated runs
    DERIVED = "derived"          # fitted ratio over primary items
    PROVISIONAL = "provisional"  # a sum / allowance, not on any drawing
    PRELIMS = "prelims"          # time-related site establishment


class ItemNode(BaseModel):
    family: str
    method: Method
    requires: List[List[DrawingType]] = Field(default_factory=list)   # OR of AND-groups
    derived_from: List[str] = Field(default_factory=list)             # primary families
    note: str = ""


def _n(family, method, requires=(), derived_from=(), note=""):
    return family, ItemNode(
        family=family, method=method,
        requires=[list(g) for g in requires], derived_from=list(derived_from), note=note,
    )


D = DrawingType
_LIGHTS = ["light_panel", "light_flood", "light_vapour_proof", "light_bulkhead",
           "light_downlight", "light_emergency", "light_other"]
_SOCKETS = ["socket_double", "socket_single", "socket_weatherproof", "socket_floor"]
_SWITCHES = ["switch", "day_night_switch"]

NETWORK: Dict[str, ItemNode] = dict([
    # ── distribution & bulk supply (SLD / schedule) ──
    _n("db", Method.COUNT, [[D.SLD], [D.SCHEDULE]], note="one per board on the SLD"),
    _n("breaker", Method.COUNT, [[D.SLD], [D.SCHEDULE]]),
    _n("meter", Method.COUNT, [[D.SLD]]),
    _n("kiosk", Method.COUNT, [[D.SLD]]),
    _n("plinth", Method.DERIVED, derived_from=["kiosk"], note="one per kiosk"),
    # ── feeders (lengths annotated on SLD; site plan gives true route) ──
    _n("swa_cable", Method.LENGTH, [[D.SLD]], note="feeder size/cores on SLD; route length from SLD annotation or site plan"),
    _n("abc_cable", Method.LENGTH, [[D.SLD]]),
    _n("surfix", Method.LENGTH, [[D.SLD]]),
    _n("bcew", Method.DERIVED, derived_from=["swa_cable"], note="same length as its feeder"),
    _n("termination", Method.DERIVED, derived_from=["swa_cable", "abc_cable"], note="2 per cable run"),
    _n("trench", Method.DERIVED, derived_from=["swa_cable"], note="underground feeder length (site plan improves)"),
    _n("warning_tape", Method.DERIVED, derived_from=["swa_cable"], note="= trench length"),
    _n("sleeve", Method.LENGTH, [[D.SITE]], note="road/paving crossings on site plan"),
    _n("manhole", Method.COUNT, [[D.SITE]]),
    # ── outlets & control (plug layout) ──
    *[_n(f, Method.COUNT, [[D.PLUGS]]) for f in _SOCKETS],
    _n("data_outlet", Method.COUNT, [[D.PLUGS]]),
    _n("isolator", Method.COUNT, [[D.PLUGS]], note="aircon / geyser / signage isolators"),
    # ── lighting & switching (lighting layout) ──
    *[_n(f, Method.COUNT, [[D.LIGHTING]]) for f in _LIGHTS],
    _n("light_highmast", Method.COUNT, [[D.SITE], [D.LIGHTING]]),
    _n("light_solar_post", Method.COUNT, [[D.SITE], [D.LIGHTING]]),
    _n("light_pole", Method.COUNT, [[D.SITE], [D.LIGHTING]]),
    _n("switch", Method.COUNT, [[D.LIGHTING]]),
    _n("day_night_switch", Method.COUNT, [[D.LIGHTING]]),
    _n("exit_sign", Method.COUNT, [[D.LIGHTING]]),
    _n("smoke_detector", Method.COUNT, [[D.LIGHTING]]),
    _n("fire_extinguisher", Method.COUNT, [[D.PLUGS], [D.LIGHTING]]),
    # ── derived installation materials (never drawn as symbols) ──
    _n("wall_box", Method.DERIVED, derived_from=_SOCKETS + ["isolator"] + _SWITCHES,
       note="one flush box per outlet / switch"),
    _n("extension_box", Method.DERIVED, derived_from=_SOCKETS),
    _n("waterproof_box", Method.DERIVED, derived_from=["socket_weatherproof"] + _SOCKETS),
    _n("chasing", Method.DERIVED, derived_from=_SOCKETS + ["isolator"] + _SWITCHES,
       note="one wall chase per flush point"),
    _n("conduit", Method.DERIVED, derived_from=_LIGHTS + _SOCKETS + _SWITCHES),
    _n("draw_wire", Method.DERIVED, derived_from=_SOCKETS),
    _n("round_box", Method.DERIVED, derived_from=_LIGHTS, note="ceiling looping box per point"),
    _n("gp_wire", Method.DERIVED, derived_from=_LIGHTS + _SOCKETS,
       note="single-core wire per colour; point method"),
    _n("plug_top", Method.DERIVED, derived_from=_LIGHTS, note="plug-in fittings on trunking"),
    _n("trunking", Method.DERIVED, derived_from=_LIGHTS, note="route drawn on layout; fitted ratio until measured"),
    _n("trunking_cover", Method.DERIVED, derived_from=["trunking"] + _LIGHTS),
    _n("trunking_bend", Method.DERIVED, derived_from=["trunking"] + _LIGHTS),
    _n("trunking_tee", Method.DERIVED, derived_from=["trunking"] + _LIGHTS),
    _n("cable_tray", Method.DERIVED, derived_from=_LIGHTS + ["db"]),
    _n("wire_basket", Method.DERIVED, derived_from=_LIGHTS + ["db"]),
    # ── never from drawings ──
    _n("connection_fee", Method.PROVISIONAL, note="utility fee — provisional sum"),
    _n("coc", Method.PROVISIONAL, note="certificate of compliance — fixed sum"),
    _n("prelims", Method.PRELIMS, note="P&Gs: site staff, establishment, plant (time-based)"),
    _n("other", Method.PROVISIONAL),
])


def _direct(node: ItemNode, uploaded: Set[DrawingType]) -> bool:
    return any(set(group) <= uploaded for group in node.requires)


def reproducible(family: str, uploaded: Set[DrawingType], _seen: frozenset = frozenset()) -> bool:
    """Can `family` be quantified from the uploaded drawing types?"""
    node = NETWORK.get(family)
    if node is None or node.method in (Method.PROVISIONAL, Method.PRELIMS):
        return False
    if node.method == Method.DERIVED:
        seen = _seen | {family}
        return any(reproducible(p, uploaded, seen) for p in node.derived_from if p not in seen)
    return _direct(node, uploaded)


def reproducible_families(uploaded: Set[DrawingType]) -> Set[str]:
    return {f for f in NETWORK if reproducible(f, uploaded)}


def _first_request(family: str, uploaded: Set[DrawingType], _seen: frozenset = frozenset()):
    node = NETWORK.get(family)
    if node is None or node.method in (Method.PROVISIONAL, Method.PRELIMS):
        return None
    if node.method == Method.DERIVED:
        for p in node.derived_from:
            if p not in _seen:
                req = _first_request(p, uploaded, _seen | {family})
                if req is not None:
                    return req
        return None
    for group in node.requires:
        missing = [d for d in group if d not in uploaded]
        if missing:
            return missing[0]
    return None


def missing_for(families: Iterable[str], uploaded: Set[DrawingType]) -> Dict[DrawingType, List[str]]:
    """For each family that is NOT reproducible, the first drawing that would unlock it."""
    out: Dict[DrawingType, List[str]] = {}
    for fam in families:
        if reproducible(fam, uploaded):
            continue
        req = _first_request(fam, uploaded)
        if req is not None:
            out.setdefault(req, []).append(fam)
    return out


def requirements_matrix() -> Dict[str, str]:
    """family → 'method: drawing requirement' in plain words."""
    out: Dict[str, str] = {}
    for fam, node in NETWORK.items():
        if node.method == Method.DERIVED:
            req = "derived from " + ", ".join(node.derived_from[:4]) + ("…" if len(node.derived_from) > 4 else "")
        elif node.requires:
            req = " or ".join("+".join(d.value for d in g) for g in node.requires)
        else:
            req = "not on drawings"
        out[fam] = f"{node.method.value}: {req}" + (f" — {node.note}" if node.note else "")
    return out
