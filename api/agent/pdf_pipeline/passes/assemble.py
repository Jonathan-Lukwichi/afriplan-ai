"""
Pass 4 (rule-set) + Pass 5 (assemble & price) — the DETERMINISTIC BRAIN.

Given a `PdfFacts` object (what the LLM eyes reported), this module states what the
drawings show as findings (`findings_from_facts`) and prices them with the one pricer
shared with the DXF engine (`agent.shared.pricing`, ADR-0008). No LLM, no network, no
clock, no randomness. The same facts always yield the identical bill.

The estimator rule-set (from the reference bills + methodology):
  • every feeder → Supply + Install cable lines, a same-length BCEW earth,
    2 terminations (both ends), and — if underground — trench + warning tape
  • feeder length: as written on the drawing; else the route measured on a vector
    site plan; else a documented default is assumed and a GapItem is emitted
  • fittings/outlets → one combined Supply+Install line each; FREE-ISSUE items
    become install-only
  • reticulation wire → point method: points × average routed length per point
    (an allowance, flagged), lighting in 1.5 mm², power in 2.5 mm²
  • rates come from core.rate_model (crew×hours + material ×markup + add-ons)
  • +contingency, +VAT
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from agent.pdf_pipeline.passes.facts import Feeder, PdfFacts, TakeoffRoom
from agent.shared import (
    BillOfQuantities,
    BQSection,
    ContractorProfile,
    GapItem,
    ItemConfidence,
)
from agent.shared.findings import (
    BoardFinding,
    Evidence,
    FeederFinding,
    Findings,
    ItemFinding,
    WireFinding,
)
from agent.shared.pricing import price_findings, size_key as _size_key
from agent.shared.routes import RouteMatch, RouteNetwork, equipment_key
from core import constants
from core.rate_model import (
    DEFAULT_CREW,
    DEFAULT_PARAMS,
    CrewRates,
    RateParams,
    classify_point,
    fitting_install_rate,
    routed_length,
)


# ─── Deterministic assembly configuration (all fixed → deterministic) ────────

@dataclass(frozen=True)
class AssembleConfig:
    assumed_feeder_m: float = 30.0           # used when a feeder length isn't drawn
    route_slack_pct: float = 5.0             # a route measured on the site plan: snaking / sag
    route_end_allowance_m: float = 1.5       # per end: rise into the board + termination tail
    label_conflict_pct: float = 25.0         # designer's written lengths vs the scaled route
    default_ceiling_m: float = 3.0
    light_mount_m: float = 3.0               # lights at ceiling → ~0 drop
    socket_mount_m: float = 0.3
    light_m_per_point: float = 8.0           # avg routed metres per lighting point
    power_m_per_point: float = 10.0          # avg routed metres per power point (incl. live+neutral)
    retic_light_size: str = "1.5mm2"
    retic_power_size: str = "2.5mm2"
    default_point_install_labour: float = 85.0   # fallback fitting install (LABOUR_RATES per_point)
    kiosk_price: float = constants.DB_PRICES.get("kiosk_lv_outdoor", 45000.0)
    meter_price: float = 1720.0


DEFAULT_CONFIG = AssembleConfig()


# room count field → (price_map, price_key, install_key|None, section, description, catalogue name)
_FITTING_SPECS: Dict[str, Tuple[str, str, Optional[str], BQSection, str, str]] = {
    "downlights":        ("light", "downlight_led_6w",     "downlight_6w",       BQSection.LIGHTING, "6W LED downlight", "LED Downlight"),
    "panel_lights":      ("light", "recessed_led_600x1200","recessed_600x1200",  BQSection.LIGHTING, "600x1200 recessed 3x18W LED panel", "Recessed LED Panel"),
    "bulkheads":         ("light", "bulkhead_24w",         "bulkhead_24w",       BQSection.LIGHTING, "24W bulkhead light", "Bulkhead Light"),
    "vapour_proof":      ("light", "vapor_proof_2x24w",    "vapor_proof_2x24w",  BQSection.LIGHTING, "2x24W vapour-proof LED", "Vapour-Proof Light"),
    "floodlights":       ("light", "flood_light_30w",      "flood_30w",          BQSection.LIGHTING, "30W LED floodlight", "LED Floodlight"),
    "emergency_lights":  ("light", "emergency_light_led",  None,                 BQSection.LIGHTING, "LED emergency light", "Emergency Light"),
    "pole_lights":       ("light", "pole_light_60w",       None,                 BQSection.LIGHTING, "60W outdoor pole light", "Pole Light"),
    "solar_post_lights": ("light", "solar_post_light_100w", None,                BQSection.LIGHTING, "100W LED solar post lantern (complete with pole)", "Solar Post Light"),
    "high_mast_poles":   ("light", "high_mast_2x600w_10m", None,                 BQSection.LIGHTING, "2x600W LED flood light on 10m high-mast post", "High-Mast Light"),
    "double_sockets":    ("socket","double_socket_300",    None,                 BQSection.POWER_OUTLETS, "16A double switched socket", "16A Double Switched Socket"),
    "single_sockets":    ("socket","single_socket_300",    None,                 BQSection.POWER_OUTLETS, "16A single switched socket", "16A Single Switched Socket"),
    "waterproof_sockets":("socket","double_socket_waterproof", None,            BQSection.POWER_OUTLETS, "16A double waterproof socket", "Weatherproof Socket"),
    "floor_sockets":     ("socket","floor_box",            None,                 BQSection.POWER_OUTLETS, "Floor box socket outlet", "Floor Box Socket"),
    "data_outlets":      ("socket","data_points_cat6",     None,                 BQSection.DATA_COMMS,    "CAT6 data outlet", "Data Socket (CAT6)"),
    "switches_1lever":   ("switch","switch_1lever_1way",   None,                 BQSection.POWER_OUTLETS, "1-lever 1-way switch", "1-Lever Switch"),
    "switches_2lever":   ("switch","switch_2lever_1way",   None,                 BQSection.POWER_OUTLETS, "2-lever 1-way switch", "2-Lever Switch"),
    "switches_3lever":   ("switch","switch_3lever_1way",   None,                 BQSection.POWER_OUTLETS, "3-lever 1-way switch", "3-Lever Switch"),
    "isolators":         ("switch","isolator_30a",         None,                 BQSection.POWER_OUTLETS, "30A isolator switch", "Isolator Switch"),
    "day_night_switches":("switch","day_night_switch",     None,                 BQSection.POWER_OUTLETS, "Day/night switch", "Day/Night Switch"),
}

_PRICE_MAPS = {
    "light": constants.LIGHT_PRICES,
    "socket": constants.SOCKET_PRICES,
    "switch": constants.SWITCH_PRICES,
}


# ─── Assembler ───────────────────────────────────────────────────────────────

def build_boq_from_facts(
    facts: PdfFacts,
    *,
    project_name: str = "",
    run_id: str = "",
    contractor: Optional[ContractorProfile] = None,
    crew: CrewRates = DEFAULT_CREW,
    params: RateParams = DEFAULT_PARAMS,
    config: AssembleConfig = DEFAULT_CONFIG,
    routes: Optional[RouteNetwork] = None,
) -> BillOfQuantities:
    """Deterministically turn extracted facts into a priced Bill of Quantities.
    `routes`: cable routes measured on a vector site plan (no LLM) — feeders whose
    length is not written take the measured route instead of the default."""
    findings = findings_from_facts(facts, config=config, routes=routes, crew=crew)
    return price_findings(findings, pipeline="pdf", run_id=run_id,
                          project_name=project_name or facts.context.project_name,
                          crew=crew, params=params)


def findings_from_facts(
    facts: PdfFacts,
    *,
    config: AssembleConfig = DEFAULT_CONFIG,
    routes: Optional[RouteNetwork] = None,
    crew: CrewRates = DEFAULT_CREW,
) -> Findings:
    """What the AI read on the drawings (+ routes measured on a vector site plan), unpriced."""
    out = Findings(gaps=list(facts.extraction_gaps))
    if routes is not None and routes.found:
        for w in routes.warnings:                    # attribution doubts on the site plan: never silent
            out.gaps.append(GapItem(
                section=BQSection.SUBMAIN_CABLES, description=w, assumption="Route attribution as read.",
                suggested_action="Check the site plan.", severity="medium", drawing_ref="Site plan",
            ))
    _incoming(out, facts, config)
    _boards(out, facts)
    _feeders(out, facts, config, routes)
    _takeoff(out, facts, config, crew)
    return out


# ─── Section 1 — incoming supply ─────────────────────────────────────────────

def _incoming(out: Findings, facts: PdfFacts, cfg: AssembleConfig) -> None:
    inc = facts.spine.incoming_supply
    if inc.kiosk_present:
        out.items.append(ItemFinding(
            reader="pdf", section=BQSection.INCOMING, description="Mini-substation / LV kiosk supply & install",
            unit="Sum", qty=1, price_zar=cfg.kiosk_price, building="Bulk Supply", evidence=Evidence.SEEN,
        ))
    if inc.meter_count:
        out.items.append(ItemFinding(
            reader="pdf", section=BQSection.INCOMING, description="Energy meter installed in kiosk",
            unit="Ea", qty=inc.meter_count, price_zar=cfg.meter_price, building="Bulk Supply",
            evidence=Evidence.SEEN,
        ))


# ─── Section 2 — distribution boards: complete from their SLD contents ───────

def _boards(out: Findings, facts: PdfFacts) -> None:
    for db in facts.spine.distribution_boards:
        out.boards.append(BoardFinding(
            reader="pdf", name=db.name or "DB", phases=db.phases or 3, main_breaker_a=db.main_breaker_a,
            ka=db.ka_rating,
            circuits=[(c.breaker_a, c.breaker_poles) for c in db.circuits if not c.is_spare],
            spares=sum(1 for c in db.circuits if c.is_spare),
            elcb=db.elcb_present, surge=db.surge_protection,
            floor_standing=db.enclosure_mount == "floor_standing",
            building=db.name or db.location or "Distribution", sheet="SLD", evidence=Evidence.SEEN,
        ))


# ─── Section 3/9 — feeders: written length, measured route, or assumed ───────

def _feeder_route(fd: Feeder, routes: Optional[RouteNetwork]) -> Optional[RouteMatch]:
    if fd.length_annotated and fd.length_m > 0:
        return None                                  # a written length always wins
    return routes.route(fd.from_source, fd.to_db) if routes is not None and routes.found else None


def _route_order(feeders: List[Feeder], routes: Optional[RouteNetwork]) -> List[Feeder]:
    """Upstream first, then shorter routes: a trench shared along the way is billed with
    the feeder that runs along it before branching off (same rule as the DXF pipeline)."""
    parent = {equipment_key(f.to_db): equipment_key(f.from_source) for f in feeders}

    def depth(k: str) -> int:
        seen, n = {k}, 0
        while k in parent and parent[k] not in seen:
            k = parent[k]
            seen.add(k)
            n += 1
        return n

    def route_m(f: Feeder) -> float:
        r = _feeder_route(f, routes)
        return r.length_m if r is not None else float("inf")
    return sorted(feeders, key=lambda f: (depth(equipment_key(f.to_db)), route_m(f)))


def _feeders(out: Findings, facts: PdfFacts, cfg: AssembleConfig,
             routes: Optional[RouteNetwork] = None) -> None:
    claimed: Set[int] = set()                         # route edges whose trench is already billed
    feeders = _route_order(facts.spine.feeders, routes) if routes is not None else facts.spine.feeders
    for fd in feeders:
        match = _feeder_route(fd, routes)
        bldg = fd.to_db or "Sub-mains"
        if match is not None:
            length = match.length_m * (1 + cfg.route_slack_pct / 100) + 2 * cfg.route_end_allowance_m
            trench = routes.length_of(match.edges - claimed)
            claimed |= match.edges
            src, ev = ItemConfidence.INFERRED, Evidence.MEASURED
            note = (f"Route measured {match.length_m:.1f} m on the site plan, "
                    f"+{cfg.route_slack_pct:g}% and {cfg.route_end_allowance_m:g} m at each end.")
            out.gaps.append(GapItem(
                section=BQSection.SUBMAIN_CABLES, building_block=bldg,
                description=f"Feeder {fd.from_source}→{fd.to_db} length taken from the site-plan route",
                assumption=note,
                suggested_action="Check the route against the designer's cable schedule or on site.",
                severity="low", drawing_ref="Site plan",
            ))
            if match.stated_m and abs(match.stated_m - match.length_m) > cfg.label_conflict_pct / 100 * match.length_m:
                out.gaps.append(GapItem(
                    section=BQSection.SUBMAIN_CABLES, building_block=bldg,
                    description=(f"Feeder {fd.from_source}→{fd.to_db}: lengths written on the site plan "
                                 f"add to {match.stated_m:g} m, the drawn route scales to {match.length_m:.0f} m"),
                    assumption="Priced on the scaled route.",
                    suggested_action="Confirm which is right — written dimensions normally govern.",
                    severity="medium", drawing_ref="Site plan",
                ))
        elif fd.length_annotated and fd.length_m > 0:
            length = trench = fd.length_m
            src, ev, note = ItemConfidence.EXTRACTED, Evidence.SEEN, ""
        else:
            length = trench = cfg.assumed_feeder_m
            src, ev = ItemConfidence.ASSUMED, Evidence.ASSUMED
            note = f"Length assumed {length:.0f} m (not drawn)."
            on_plan = routes is not None and routes.found
            out.gaps.append(GapItem(
                section=BQSection.SUBMAIN_CABLES, building_block=bldg,
                description=(f"Feeder {fd.from_source}→{fd.to_db} has no drawn route on the site plan" if on_plan
                             else f"Feeder {fd.from_source}→{fd.to_db} length not annotated on SLD"),
                assumption=f"Assumed {cfg.assumed_feeder_m:.0f} m default run.",
                suggested_action=("Draw or confirm the route for this board on the site plan." if on_plan
                                  else "Upload the electrical site plan (vector PDF) or confirm the length on site."),
                severity="high", drawing_ref="SLD",
            ))
        if not constants.CABLE_PRICES.get(f"swa_{_size_key(fd.cable_size_mm2)}_4c"):
            out.gaps.append(GapItem(
                section=BQSection.SUBMAIN_CABLES, building_block=bldg,
                description=f"No material price for {_size_key(fd.cable_size_mm2)} SWA cable",
                assumption="Supply rate set to 0 pending a price.",
                suggested_action="Add this cable size to the price list.", severity="medium",
            ))
        out.feeders.append(FeederFinding(
            reader="pdf", from_board=fd.from_source, to_board=fd.to_db, cable_size_mm2=fd.cable_size_mm2,
            cable_cores=fd.cable_cores, earth_size_mm2=fd.earth_size_mm2, underground=fd.is_underground,
            length_m=length, trench_m=trench, building=bldg, sheet="SLD", evidence=ev,
            confidence=src, assumption=note,
        ))


# ─── Section 5/6 — fittings, outlets, reticulation wire ──────────────────────

def _takeoff(out: Findings, facts: PdfFacts, cfg: AssembleConfig, crew: CrewRates) -> None:
    free_issue = [s.lower() for s in facts.context.free_issue_items]
    for room in facts.takeoff.rooms:
        bldg = room.served_by_db or room.room_name or "General"
        for fieldname, (price_kind, price_key, install_key, section, desc, name) in _FITTING_SPECS.items():
            count = getattr(room, fieldname, 0)
            if count <= 0:
                continue
            is_free = _is_free_issue(desc, free_issue)
            out.items.append(ItemFinding(
                reader="pdf", description=f"{desc} — {room.room_name}".rstrip(" —"), section=section,
                item=name, qty=count, material_zar=_PRICE_MAPS[price_kind].get(price_key, 0.0),
                install_zar=(fitting_install_rate(install_key, crew) if install_key else None)
                or cfg.default_point_install_labour,
                free_issue=is_free, building=bldg, location=room.room_name, sheet="Layout",
                evidence=Evidence.SEEN, notes="Free-issued by client — install only." if is_free else "",
            ))
        _wiring(out, room, cfg, bldg)


def _wiring(out: Findings, room: TakeoffRoom, cfg: AssembleConfig, bldg: str) -> None:
    """Point-method reticulation wire: points × average routed length (allowance)."""
    ceiling = room.ceiling_height_m or cfg.default_ceiling_m
    for kind, points, per_point, mount, size in (
        ("lighting", room.light_points(), cfg.light_m_per_point, cfg.light_mount_m, cfg.retic_light_size),
        ("power", room.power_points(), cfg.power_m_per_point, cfg.socket_mount_m, cfg.retic_power_size),
    ):
        if points <= 0:
            continue
        length = round(points * per_point, 1)
        pclass = classify_point(routed_length(ceiling_height_m=ceiling, mount_height_m=mount,
                                              horizontal_run_m=per_point)).value
        out.wires.append(WireFinding(
            reader="pdf", description=f"{size} {kind} reticulation wire — {room.room_name}".rstrip(" —"),
            size_key=size, metres=length, building=bldg, sheet="Layout", evidence=Evidence.ASSUMED,
            confidence=ItemConfidence.ASSUMED,
            assumption=f"Point-method allowance ({pclass}); {length:g} m from point count.",
        ))
        out.gaps.append(GapItem(
            section=BQSection.FINAL_CABLES, building_block=bldg,
            description=f"{kind.title()} reticulation wire for {room.room_name} not dimensioned",
            assumption=f"Allowance {length:g} m ({size}, {pclass} point class).",
            suggested_action="Verify cable run lengths against the layout.",
            severity="low", drawing_ref="Layout",
        ))


def _is_free_issue(description: str, free_issue: List[str]) -> bool:
    d = description.lower()
    return any(tok and (tok in d or d in tok) for tok in free_issue)
