"""
Pass 4 (rule-set) + Pass 5 (assemble & price) — the DETERMINISTIC BRAIN.

Given a `PdfFacts` object (what the LLM eyes reported), this module produces a
fully priced `BillOfQuantities` with a gap report — using only pure Python and
the rate model. No LLM, no network, no clock, no randomness. The same facts
always yield the identical bill; this is the determinism contract.

The estimator rule-set (from the reference bills + methodology):
  • every feeder → Supply + Install cable lines, a same-length BCEW earth,
    2 terminations (both ends), and — if underground — trench + warning tape
  • feeder length: used as-drawn; if not annotated, a documented default is
    assumed and a GapItem is emitted (never silent)
  • fittings/outlets → one combined Supply+Install line each; FREE-ISSUE items
    become install-only
  • reticulation wire → point method: points × average routed length per point
    (an allowance, flagged), lighting in 1.5 mm², power in 2.5 mm²
  • rates come from core.rate_model (crew×hours + material ×markup + add-ons)
  • +contingency, +VAT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from agent.pdf_pipeline.passes.facts import Feeder, PdfFacts, SpineDB, TakeoffRoom
from agent.shared import (
    BillOfQuantities,
    BQLineItem,
    BQSection,
    ContractorProfile,
    GapItem,
    ItemConfidence,
    LineKind,
)
from agent.shared.routes import RouteMatch, RouteNetwork, equipment_key
from core import constants
from core.rate_model import (
    DEFAULT_CREW,
    DEFAULT_PARAMS,
    CrewRates,
    RateParams,
    bcew_install_rate,
    build_rate,
    cable_install_rate,
    TERMINATION_MATERIAL,
    classify_point,
    db_build_up,
    earth_size_for,
    fitting_install_rate,
    routed_length,
    termination_install_rate,
    trench_build_up,
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
    trench_rate_per_m: float = round(trench_build_up().combined_rate, 2)   # built up: dig, sand, backfill, reinstate
    warning_tape_rate_per_m: float = 5.4


DEFAULT_CONFIG = AssembleConfig()


# room count field → (price_map, price_key, install_key|None, section, description, unit)
_FITTING_SPECS: Dict[str, Tuple[str, str, Optional[str], BQSection, str, str]] = {
    "downlights":        ("light", "downlight_led_6w",     "downlight_6w",       BQSection.LIGHTING, "6W LED downlight", "No"),
    "panel_lights":      ("light", "recessed_led_600x1200","recessed_600x1200",  BQSection.LIGHTING, "600x1200 recessed 3x18W LED panel", "No"),
    "bulkheads":         ("light", "bulkhead_24w",         "bulkhead_24w",       BQSection.LIGHTING, "24W bulkhead light", "No"),
    "vapour_proof":      ("light", "vapor_proof_2x24w",    "vapor_proof_2x24w",  BQSection.LIGHTING, "2x24W vapour-proof LED", "No"),
    "floodlights":       ("light", "flood_light_30w",      "flood_30w",          BQSection.LIGHTING, "30W LED floodlight", "No"),
    "emergency_lights":  ("light", "emergency_light_led",  None,                 BQSection.LIGHTING, "LED emergency light", "No"),
    "pole_lights":       ("light", "pole_light_60w",       None,                 BQSection.LIGHTING, "60W outdoor pole light", "No"),
    "solar_post_lights": ("light", "solar_post_light_100w", None,                BQSection.LIGHTING, "100W LED solar post lantern (complete with pole)", "No"),
    "high_mast_poles":   ("light", "high_mast_2x600w_10m", None,                 BQSection.LIGHTING, "2x600W LED flood light on 10m high-mast post", "No"),
    "double_sockets":    ("socket","double_socket_300",    None,                 BQSection.POWER_OUTLETS, "16A double switched socket", "No"),
    "single_sockets":    ("socket","single_socket_300",    None,                 BQSection.POWER_OUTLETS, "16A single switched socket", "No"),
    "waterproof_sockets":("socket","double_socket_waterproof", None,            BQSection.POWER_OUTLETS, "16A double waterproof socket", "No"),
    "floor_sockets":     ("socket","floor_box",            None,                 BQSection.POWER_OUTLETS, "Floor box socket outlet", "No"),
    "data_outlets":      ("socket","data_points_cat6",     None,                 BQSection.DATA_COMMS,    "CAT6 data outlet", "No"),
    "switches_1lever":   ("switch","switch_1lever_1way",   None,                 BQSection.POWER_OUTLETS, "1-lever 1-way switch", "No"),
    "switches_2lever":   ("switch","switch_2lever_1way",   None,                 BQSection.POWER_OUTLETS, "2-lever 1-way switch", "No"),
    "switches_3lever":   ("switch","switch_3lever_1way",   None,                 BQSection.POWER_OUTLETS, "3-lever 1-way switch", "No"),
    "isolators":         ("switch","isolator_30a",         None,                 BQSection.POWER_OUTLETS, "30A isolator switch", "No"),
    "day_night_switches":("switch","day_night_switch",     None,                 BQSection.POWER_OUTLETS, "Day/night switch", "No"),
}

_PRICE_MAPS = {
    "light": constants.LIGHT_PRICES,
    "socket": constants.SOCKET_PRICES,
    "switch": constants.SWITCH_PRICES,
}


def _size_key(mm2: float) -> str:
    """50.0 → '50mm2', 2.5 → '2.5mm2'."""
    if mm2 <= 0:
        return ""
    return f"{int(mm2)}mm2" if float(mm2).is_integer() else f"{mm2}mm2"


def _cable_material_per_m(size_mm2: float) -> Optional[float]:
    return constants.CABLE_PRICES.get(f"swa_{_size_key(size_mm2)}_4c")


def _retic_material_per_m(size_key: str) -> Optional[float]:
    return constants.CABLE_PRICES.get(f"surfix_{size_key}_3c")


# ─── Assembler ───────────────────────────────────────────────────────────────

@dataclass
class _Acc:
    lines: List[BQLineItem] = field(default_factory=list)
    gaps: List[GapItem] = field(default_factory=list)


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
    acc = _Acc()
    acc.gaps.extend(facts.extraction_gaps)
    if routes is not None and routes.found:
        for w in routes.warnings:                    # attribution doubts on the site plan: never silent
            acc.gaps.append(GapItem(
                section=BQSection.SUBMAIN_CABLES, description=w, assumption="Route attribution as read.",
                suggested_action="Check the site plan.", severity="medium", drawing_ref="Site plan",
            ))

    _assemble_incoming(acc, facts, config, params)
    _assemble_distribution(acc, facts)
    _assemble_feeders(acc, facts, config, crew, params, routes)
    _assemble_takeoff(acc, facts, config, crew, params)

    _number_lines(acc.lines)

    boq = BillOfQuantities(
        project_name=project_name or facts.context.project_name,
        pipeline="pdf",
        run_id=run_id,
        line_items=acc.lines,
        gaps=acc.gaps,
        contingency_pct=params.contingency_pct * 100,
        vat_pct=params.vat_pct * 100,
    )
    _finalise_totals(boq, params)
    _count_provenance(boq)
    return boq


# ─── Section 1 — incoming supply ─────────────────────────────────────────────

def _assemble_incoming(acc: _Acc, facts: PdfFacts, cfg: AssembleConfig, params: RateParams) -> None:
    inc = facts.spine.incoming_supply
    if inc.kiosk_present:
        acc.lines.append(BQLineItem(
            section=BQSection.INCOMING, description="Mini-substation / LV kiosk supply & install",
            unit="Sum", qty=1, unit_price_zar=constants.DB_PRICES.get("kiosk_lv_outdoor", 45000.0),
            source=ItemConfidence.EXTRACTED, line_kind=LineKind.COMBINED, building_block="Bulk Supply",
        ))
    if inc.meter_count:
        acc.lines.append(BQLineItem(
            section=BQSection.INCOMING, description="Energy meter installed in kiosk",
            unit="Ea", qty=inc.meter_count, unit_price_zar=1720.0,
            source=ItemConfidence.EXTRACTED, building_block="Bulk Supply",
        ))
    _finalise_line_totals(acc.lines)


# ─── Section 2 — distribution boards ─────────────────────────────────────────

def _assemble_distribution(acc: _Acc, facts: PdfFacts) -> None:
    for db in facts.spine.distribution_boards:
        ways = max(len(db.circuits), 1)
        # Complete board from its SLD contents (issue 004): enclosure + incomer +
        # every non-spare breaker + ELCB + SPD, wired and installed.
        price = round(db_build_up(
            ways=ways, phases=db.phases or 3, main_breaker_a=db.main_breaker_a,
            circuits=[(c.breaker_a, c.breaker_poles) for c in db.circuits if not c.is_spare],
            elcb=db.elcb_present, surge=db.surge_protection,
            floor_standing=db.enclosure_mount == "floor_standing",
        ).combined_rate, 2)
        acc.lines.append(BQLineItem(
            section=BQSection.DISTRIBUTION,
            description=(
                f"{db.name or 'DB'}: {db.phases}ph "
                f"{db.main_breaker_a}A, {len(db.circuits)}-way, "
                f"{db.enclosure_mount.replace('_', ' ')}"
            ),
            unit="Sum", qty=1, unit_price_zar=price,
            source=ItemConfidence.EXTRACTED, line_kind=LineKind.COMBINED,
            building_block=db.name or db.location or "Distribution",
            drawing_ref="SLD",
        ))
    _finalise_line_totals(acc.lines)


# ─── Section 3/9 — feeders + earth + terminations + trench ───────────────────

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


def _assemble_feeders(
    acc: _Acc, facts: PdfFacts, cfg: AssembleConfig, crew: CrewRates, params: RateParams,
    routes: Optional[RouteNetwork] = None,
) -> None:
    claimed: Set[int] = set()                         # route edges whose trench is already billed
    feeders = _route_order(facts.spine.feeders, routes) if routes is not None else facts.spine.feeders
    for fd in feeders:
        match = _feeder_route(fd, routes)
        length, assumed = _feeder_length(fd, cfg)
        trench = length
        bldg = fd.to_db or "Sub-mains"
        size_key = _size_key(fd.cable_size_mm2)
        label = f"{int(fd.cable_size_mm2)}mm² x{fd.cable_cores}C SWA feeder {fd.from_source}→{fd.to_db}"

        if match is not None:
            length = match.length_m * (1 + cfg.route_slack_pct / 100) + 2 * cfg.route_end_allowance_m
            trench = routes.length_of(match.edges - claimed)
            claimed |= match.edges
            assumed = False
            src = ItemConfidence.INFERRED
            assumption_txt = (f"Route measured {match.length_m:.1f} m on the site plan, "
                              f"+{cfg.route_slack_pct:g}% and {cfg.route_end_allowance_m:g} m at each end.")
            acc.gaps.append(GapItem(
                section=BQSection.SUBMAIN_CABLES, building_block=bldg,
                description=f"Feeder {fd.from_source}→{fd.to_db} length taken from the site-plan route",
                assumption=assumption_txt,
                suggested_action="Check the route against the designer's cable schedule or on site.",
                severity="low", drawing_ref="Site plan",
            ))
            if match.stated_m and abs(match.stated_m - match.length_m) > cfg.label_conflict_pct / 100 * match.length_m:
                acc.gaps.append(GapItem(
                    section=BQSection.SUBMAIN_CABLES, building_block=bldg,
                    description=(f"Feeder {fd.from_source}→{fd.to_db}: lengths written on the site plan "
                                 f"add to {match.stated_m:g} m, the drawn route scales to {match.length_m:.0f} m"),
                    assumption="Priced on the scaled route.",
                    suggested_action="Confirm which is right — written dimensions normally govern.",
                    severity="medium", drawing_ref="Site plan",
                ))
        elif assumed:
            on_plan = routes is not None and routes.found
            acc.gaps.append(GapItem(
                section=BQSection.SUBMAIN_CABLES, building_block=bldg,
                description=(f"Feeder {fd.from_source}→{fd.to_db} has no drawn route on the site plan" if on_plan
                             else f"Feeder {fd.from_source}→{fd.to_db} length not annotated on SLD"),
                assumption=f"Assumed {cfg.assumed_feeder_m:.0f} m default run.",
                suggested_action=("Draw or confirm the route for this board on the site plan." if on_plan
                                  else "Upload the electrical site plan (vector PDF) or confirm the length on site."),
                severity="high", drawing_ref="SLD",
            ))
        if match is None:
            src = ItemConfidence.ASSUMED if assumed else ItemConfidence.EXTRACTED
            assumption_txt = f"Length assumed {length:.0f} m (not drawn)." if assumed else ""

        # Cable: Supply + Install split
        material = _cable_material_per_m(fd.cable_size_mm2) or 0.0
        install = cable_install_rate(size_key, crew) or 0.0
        if material == 0.0:
            acc.gaps.append(GapItem(
                section=BQSection.SUBMAIN_CABLES, building_block=bldg,
                description=f"No material price for {size_key} SWA cable",
                assumption="Supply rate set to 0 pending a price.",
                suggested_action="Add this cable size to the price list.", severity="medium",
            ))
        rate = build_rate(material_cost=material, install_labour=install, params=params)
        _add_split(acc, BQSection.SUBMAIN_CABLES, f"Supply {label}", "m", length,
                   rate.supply_rate, src, bldg, assumption=assumption_txt)
        _add_split(acc, BQSection.SUBMAIN_CABLES, f"Install {label}", "m", length,
                   rate.install_rate, src, bldg, assumption=assumption_txt)

        # BCEW earth — same length
        e_size = fd.earth_size_mm2 or earth_size_for(fd.cable_size_mm2)
        e_key = _size_key(e_size)
        e_material = constants.CABLE_PRICES.get(f"earth_wire_{e_key}", 0.0)
        e_install = bcew_install_rate(e_key, crew) or 0.0
        e_rate = build_rate(material_cost=e_material, install_labour=e_install, params=params)
        _add_split(acc, BQSection.SUBMAIN_CABLES, f"Supply {int(e_size)}mm² BCEW earth", "m", length,
                   e_rate.supply_rate, src, bldg)
        _add_split(acc, BQSection.SUBMAIN_CABLES, f"Install {int(e_size)}mm² BCEW earth", "m", length,
                   e_rate.install_rate, src, bldg)

        # Terminations — 2 ends
        t_material = TERMINATION_MATERIAL.get(size_key, 0.0)
        t_install = termination_install_rate(size_key, crew) or 0.0
        t_rate = build_rate(material_cost=t_material, install_labour=t_install, params=params)
        acc.lines.append(BQLineItem(
            section=BQSection.SUBMAIN_CABLES, description=f"Terminate {int(fd.cable_size_mm2)}mm² SWA (both ends)",
            unit="Ea", qty=2, unit_price_zar=round(t_rate.combined_rate, 2),
            source=ItemConfidence.EXTRACTED, line_kind=LineKind.COMBINED, building_block=bldg,
        ))

        # Trench + tape if underground
        if fd.is_underground and trench > 0:          # 0: the route shares a trench billed upstream
            _add_line(acc, BQSection.UNDERGROUND, f"Trench 600mm for {fd.from_source}→{fd.to_db}",
                      "m", round(trench, 2), cfg.trench_rate_per_m, src, bldg, assumption=assumption_txt)
            _add_line(acc, BQSection.UNDERGROUND, "Warning tape 300mm above cable",
                      "m", round(trench, 2), cfg.warning_tape_rate_per_m, src, bldg)

    _finalise_line_totals(acc.lines)


def _feeder_length(fd: Feeder, cfg: AssembleConfig) -> Tuple[float, bool]:
    """Return (length_m, was_assumed). Deterministic: annotated length wins."""
    if fd.length_annotated and fd.length_m > 0:
        return fd.length_m, False
    return cfg.assumed_feeder_m, True


# ─── Section 5/6 — fittings, outlets, reticulation wire ──────────────────────

def _assemble_takeoff(
    acc: _Acc, facts: PdfFacts, cfg: AssembleConfig, crew: CrewRates, params: RateParams
) -> None:
    free_issue = [s.lower() for s in facts.context.free_issue_items]

    for room in facts.takeoff.rooms:
        bldg = room.served_by_db or room.room_name or "General"
        for fieldname, spec in _FITTING_SPECS.items():
            count = getattr(room, fieldname, 0)
            if count <= 0:
                continue
            price_kind, price_key, install_key, section, desc, unit = spec
            material = _PRICE_MAPS[price_kind].get(price_key, 0.0)
            install = (fitting_install_rate(install_key, crew) if install_key else None) \
                or cfg.default_point_install_labour
            is_free = _is_free_issue(desc, free_issue)
            if is_free:
                unit_price = round(install, 2)   # install-only
                note = "Free-issued by client — install only."
            else:
                rate = build_rate(material_cost=material, install_labour=install, params=params)
                unit_price = round(rate.combined_rate, 2)
                note = ""
            acc.lines.append(BQLineItem(
                section=section, description=f"{desc} — {room.room_name}".rstrip(" —"),
                unit=unit, qty=count, unit_price_zar=unit_price,
                source=ItemConfidence.EXTRACTED, line_kind=LineKind.COMBINED,
                building_block=bldg, notes=note, drawing_ref="Layout",
                locations=[room.room_name] if room.room_name else [],
            ))

        _assemble_reticulation(acc, room, cfg, crew, params, bldg)

    _finalise_line_totals(acc.lines)


def _assemble_reticulation(
    acc: _Acc, room: TakeoffRoom, cfg: AssembleConfig, crew: CrewRates,
    params: RateParams, bldg: str,
) -> None:
    """Point-method reticulation wire: points × average routed length (allowance)."""
    lights = room.light_points()
    powers = room.power_points()
    ceiling = room.ceiling_height_m or cfg.default_ceiling_m

    if lights > 0:
        length = round(lights * cfg.light_m_per_point, 1)
        pclass = classify_point(routed_length(
            ceiling_height_m=ceiling, mount_height_m=cfg.light_mount_m,
            horizontal_run_m=cfg.light_m_per_point,
        ))
        _add_retic(acc, room, cfg.retic_light_size, length, "lighting", pclass.value, crew, params, bldg)
    if powers > 0:
        length = round(powers * cfg.power_m_per_point, 1)
        pclass = classify_point(routed_length(
            ceiling_height_m=ceiling, mount_height_m=cfg.socket_mount_m,
            horizontal_run_m=cfg.power_m_per_point,
        ))
        _add_retic(acc, room, cfg.retic_power_size, length, "power", pclass.value, crew, params, bldg)


def _add_retic(
    acc: _Acc, room: TakeoffRoom, size_key: str, length: float, kind: str,
    pclass: str, crew: CrewRates, params: RateParams, bldg: str,
) -> None:
    material = _retic_material_per_m(size_key) or 0.0
    # 1.5mm² has no crew×hours entry (smallest is 2.5mm²) → fall back to a nominal rate
    install = cable_install_rate(size_key, crew) or 25.0
    rate = build_rate(material_cost=material, install_labour=install, params=params)
    section = BQSection.FINAL_CABLES
    acc.lines.append(BQLineItem(
        section=section,
        description=f"{size_key} {kind} reticulation wire — {room.room_name}".rstrip(" —"),
        unit="m", qty=length, unit_price_zar=round(rate.combined_rate, 2),
        source=ItemConfidence.ASSUMED, line_kind=LineKind.COMBINED, building_block=bldg,
        assumption=f"Point-method allowance ({pclass}); {length:g} m from point count.",
        drawing_ref="Layout",
    ))
    acc.gaps.append(GapItem(
        section=section, building_block=bldg,
        description=f"{kind.title()} reticulation wire for {room.room_name} not dimensioned",
        assumption=f"Allowance {length:g} m ({size_key}, {pclass} point class).",
        suggested_action="Verify cable run lengths against the layout.",
        severity="low", drawing_ref="Layout",
    ))


def _is_free_issue(description: str, free_issue: List[str]) -> bool:
    d = description.lower()
    return any(tok and (tok in d or d in tok) for tok in free_issue)


# ─── line helpers ────────────────────────────────────────────────────────────

def _add_split(
    acc: _Acc, section: BQSection, desc: str, unit: str, qty: float,
    rate: float, source: ItemConfidence, bldg: str, assumption: str = "",
) -> None:
    kind = LineKind.SUPPLY if desc.lower().startswith("supply") else LineKind.INSTALL
    acc.lines.append(BQLineItem(
        section=section, description=desc, unit=unit, qty=round(qty, 2),
        unit_price_zar=round(rate, 2), source=source, line_kind=kind,
        building_block=bldg, assumption=assumption,
    ))


def _add_line(
    acc: _Acc, section: BQSection, desc: str, unit: str, qty: float,
    rate: float, source: ItemConfidence, bldg: str, assumption: str = "",
) -> None:
    acc.lines.append(BQLineItem(
        section=section, description=desc, unit=unit, qty=round(qty, 2),
        unit_price_zar=round(rate, 2), source=source, line_kind=LineKind.COMBINED,
        building_block=bldg, assumption=assumption,
    ))


def _finalise_line_totals(lines: List[BQLineItem]) -> None:
    for ln in lines:
        ln.total_zar = round(ln.qty * ln.unit_price_zar, 2)


def _number_lines(lines: List[BQLineItem]) -> None:
    counters: Dict[int, int] = {}
    # stable order: by section number, keeping insertion order within a section
    lines.sort(key=lambda l: l.section.section_number)
    for ln in lines:
        n = ln.section.section_number
        counters[n] = counters.get(n, 0) + 1
        ln.item_no = counters[n]


def _finalise_totals(boq: BillOfQuantities, params: RateParams) -> None:
    subtotal = round(sum(l.total_zar for l in boq.line_items), 2)
    contingency = round(subtotal * params.contingency_pct, 2)
    excl_vat = round(subtotal + contingency, 2)
    vat = round(excl_vat * params.vat_pct, 2)
    boq.subtotal_zar = subtotal
    boq.contingency_zar = contingency
    boq.markup_zar = 0.0                      # markup is baked into built-up rates
    boq.contractor_markup_pct = 0.0           # ...so page 3 must not add it again
    boq.total_excl_vat_zar = excl_vat
    boq.vat_zar = vat
    boq.total_incl_vat_zar = round(excl_vat + vat, 2)


def _count_provenance(boq: BillOfQuantities) -> None:
    boq.items_extracted = sum(1 for l in boq.line_items if l.source == ItemConfidence.EXTRACTED)
    boq.items_inferred = sum(1 for l in boq.line_items if l.source == ItemConfidence.INFERRED)
    boq.items_assumed = sum(1 for l in boq.line_items if l.source == ItemConfidence.ASSUMED)
    boq.items_provisional = sum(1 for l in boq.line_items if l.source == ItemConfidence.PROVISIONAL)
    boq.items_estimated = sum(1 for l in boq.line_items if l.source == ItemConfidence.ESTIMATED)
