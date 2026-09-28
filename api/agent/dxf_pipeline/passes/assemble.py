"""
Pass 6 — assemble & price a DXF recognition into an A–H BillOfQuantities.

The DXF analogue of the PDF pipeline's deterministic brain. The crucial
difference: DXF quantities are MEASURED, not assumed — block counts are exact
enumeration and cable lengths come from geometry. So most lines are EXTRACTED,
not ASSUMED, and there are far fewer gaps than the vision path.

Pricing reuses the shared crew×hours rate model (core.rate_model) so a DXF bill
and a PDF bill price the same item identically. This module must NOT import
agent.pdf_pipeline.* (CLAUDE.md single rule) — it shares only core + agent.shared.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set

from agent.dxf_pipeline.passes.recognize import DxfRecognition
from agent.dxf_pipeline.passes.sld import SldFacts
from agent.dxf_pipeline.patterns import (
    EXACT_BLOCK_MAP,
    REGEX_BLOCK_PATTERNS,
    FixtureCategory,
)
from agent.shared import (
    BillOfQuantities,
    BQLineItem,
    BQSection,
    ContractorProfile,
    GapItem,
    ItemConfidence,
    LineKind,
)
from agent.shared.routes import RouteNetwork, equipment_key
from core import constants
from core.rate_model import (
    DEFAULT_CREW,
    DEFAULT_PARAMS,
    CrewRates,
    RateParams,
    TERMINATION_MATERIAL,
    bcew_install_rate,
    build_rate,
    cable_install_rate,
    db_build_up,
    earth_size_for,
    termination_install_rate,
    trench_build_up,
)


@dataclass(frozen=True)
class DxfAssembleConfig:
    default_point_install_labour: float = 85.0     # fitting install fallback
    retic_light_size: str = "1.5mm2"
    retic_power_size: str = "2.5mm2"
    db_enclosure_price: float = 4500.0
    assumed_feeder_m: float = 30.0                 # SLDs rarely print route lengths (issue 002)
    route_slack_pct: float = 5.0                   # snaking / sag on a route measured from the site plan
    route_end_allowance_m: float = 1.5             # per end: rise into the board + termination tail
    label_conflict_pct: float = 25.0               # designer's written lengths vs the scaled route
    route_slack_pct: float = 5.0                   # snaking / sag on a route measured from the site plan
    route_end_allowance_m: float = 1.5             # per end: rise into the board + termination tail
    label_conflict_pct: float = 25.0               # designer's written lengths vs the scaled route
    trench_rate_per_m: float = round(trench_build_up().combined_rate, 2)   # built up: dig, sand, backfill, reinstate
    warning_tape_rate_per_m: float = 5.4


DEFAULT_DXF_CONFIG = DxfAssembleConfig()


_CATEGORY_TO_SECTION: Dict[str, BQSection] = {
    "lighting": BQSection.LIGHTING,
    "power": BQSection.POWER_OUTLETS,
    "switch": BQSection.POWER_OUTLETS,
    "data": BQSection.DATA_COMMS,
    "safety": BQSection.FIRE_SAFETY,
    "hvac": BQSection.FINAL_CABLES,
    "water": BQSection.FINAL_CABLES,
    "distribution": BQSection.DISTRIBUTION,
    "other": BQSection.FINAL_CABLES,
}


def _fitting_material_price(canonical_name: str) -> float:
    """Default supply price for a canonical fixture, from the pattern table."""
    for spec in EXACT_BLOCK_MAP.values():
        if spec.canonical_name == canonical_name:
            return spec.default_unit_price_zar
    for _, spec in REGEX_BLOCK_PATTERNS:
        if spec.canonical_name == canonical_name:
            return spec.default_unit_price_zar
    return 0.0


def _category_of(canonical_name: str) -> str:
    for spec in EXACT_BLOCK_MAP.values():
        if spec.canonical_name == canonical_name:
            return spec.category.value
    for _, spec in REGEX_BLOCK_PATTERNS:
        if spec.canonical_name == canonical_name:
            return spec.category.value
    return "other"


def build_boq_from_recognition(
    rec: DxfRecognition,
    *,
    project_name: str = "",
    run_id: str = "",
    contractor: Optional[ContractorProfile] = None,
    crew: CrewRates = DEFAULT_CREW,
    params: RateParams = DEFAULT_PARAMS,
    config: DxfAssembleConfig = DEFAULT_DXF_CONFIG,
    sld: Optional[SldFacts] = None,
    routes: Optional[RouteNetwork] = None,
    known_boards: Iterable[str] = (),
) -> BillOfQuantities:
    """Deterministically turn a DXF recognition (+ SLD facts, if the drawing is an SLD;
    + the site plan's measured routes, when one was supplied) into a priced A–H bill.
    `known_boards`: boards already priced from an SLD elsewhere in the project — a
    layout's circuit tags must not bill them a second time."""
    lines: List[BQLineItem] = []
    gaps: List[GapItem] = []

    if sld is not None and sld.boards:
        _assemble_sld_boards(lines, sld, crew, params)       # the SLD is the authority on boards
    else:
        _assemble_dbs(lines, gaps, rec, config, skip={equipment_key(b) for b in known_boards})
    if sld is not None and sld.feeders:
        _assemble_sld_feeders(lines, gaps, sld, crew, params, config, routes=routes)
    _assemble_fittings(lines, rec, crew, params)
    _assemble_reticulation(lines, rec, crew, params, config)

    _number(lines)
    for ln in lines:
        ln.total_zar = round(ln.qty * ln.unit_price_zar, 2)

    boq = BillOfQuantities(
        project_name=project_name, pipeline="dxf", run_id=run_id,
        line_items=lines, gaps=gaps,
        contingency_pct=params.contingency_pct * 100, vat_pct=params.vat_pct * 100,
    )
    _finalise_totals(boq, params)
    _count_provenance(boq)
    return boq


# ─── Section 2 — distribution boards (from DB refs on the wiring) ─────

def _assemble_dbs(lines, gaps, rec: DxfRecognition, cfg: DxfAssembleConfig,
                  skip: Set[str] = frozenset()) -> None:
    for db in rec.db_refs():
        if equipment_key(db) in skip:
            continue
        lines.append(BQLineItem(
            section=BQSection.DISTRIBUTION,
            description=f"{db}: distribution board (rating per SLD)",
            unit="Sum", qty=1, unit_price_zar=cfg.db_enclosure_price,
            source=ItemConfidence.EXTRACTED, line_kind=LineKind.COMBINED,
            building_block=db, drawing_ref="DXF",
            notes="DB inferred from circuit tags; ways/rating not in layout DXF.",
        ))
        gaps.append(GapItem(
            section=BQSection.DISTRIBUTION, building_block=db,
            description=f"{db} rating/ways not in the layout DXF",
            assumption="Priced as a nominal enclosure.",
            suggested_action="Confirm DB size from the SLD/schedule.",
            severity="medium", drawing_ref="DXF",
        ))


# ─── Section 2/3/9 — boards and feeders read from an SLD drawing (issue 001) ─

def _size_key(mm2: float) -> str:
    return f"{int(mm2)}mm2" if float(mm2).is_integer() else f"{mm2}mm2"


def _board_circuits(b) -> list:
    """(amps, poles) per way; the circuits wired in 4-core cable are 3-pole — the largest first."""
    order = sorted(range(len(b.circuits)), key=lambda i: -b.circuits[i][0])
    three = set(order[:b.three_phase_ways])
    return [(a, 3 if i in three else p) for i, (a, p) in enumerate(b.circuits)]


def _assemble_sld_boards(lines, sld: SldFacts, crew: CrewRates, params: RateParams) -> None:
    for b in sld.boards:
        rate = db_build_up(ways=len(b.circuits) + b.spares, phases=b.phases,
                           main_breaker_a=b.main_breaker_a, circuits=_board_circuits(b),
                           motor_starters=b.motor_starters, isolators=b.isolators,
                           master_switch=b.master_switch, crew=crew, params=params)
        extras = [f"{b.motor_starters} motor starters" if b.motor_starters else "",
                  f"{b.isolators} isolators" if b.isolators else "",
                  "master switch" if b.master_switch else "",
                  f"{b.three_phase_ways} three-phase ways" if b.three_phase_ways else ""]
        extras = [e for e in extras if e]
        kiosk = b.name == "KIOSK"
        # The main kiosk is ONE complete item: its board plus the outdoor free-standing
        # kiosk that houses it (not drawn on the SLD — market-estimate, confirm).
        price = rate.combined_rate + (constants.DB_PRICES.get("kiosk_lv_outdoor", 0.0) * params.material_markup
                                      if kiosk else 0.0)
        lines.append(BQLineItem(
            section=BQSection.DISTRIBUTION,
            description=((f"{b.name}: outdoor LV kiosk complete, " if kiosk else f"{b.name}: ")
                         + f"{b.phases}ph {b.main_breaker_a}A, {b.ka:g}kA, "
                         f"{len(b.circuits) + b.spares}-way ({b.spares} spare)"
                         + (f", {', '.join(extras)}" if extras else "")),
            unit="Sum", qty=1, unit_price_zar=round(price, 2),
            source=ItemConfidence.INFERRED if kiosk else ItemConfidence.EXTRACTED, line_kind=LineKind.COMBINED,
            building_block=b.name, drawing_ref=b.source or "SLD (DXF)",
            assumption=("Board read from the SLD; the outdoor kiosk housing is a market-estimate price."
                        if kiosk else ""),
            notes="Board, incomer, breakers, starters and isolators read from the SLD; ELCB/SPD not priced unless shown.",
        ))
        if kiosk:
            lines.append(BQLineItem(
                section=BQSection.DISTRIBUTION, description="Supply and install concrete plinth (main LV enclosure base)", unit="Sum", qty=1,
                unit_price_zar=round(constants.DB_PRICES.get("kiosk_plinth_concrete", 0.0), 2),
                source=ItemConfidence.INFERRED, line_kind=LineKind.COMBINED,
                building_block=b.name, drawing_ref=b.source or "SLD (DXF)",
                assumption="A kiosk stands on a cast plinth (not drawn on the SLD); market-estimate price.",
            ))


def _feeder_order(feeders, routes: Optional[RouteNetwork] = None) -> list:
    """Upstream feeders first, then shorter routes first, so a trench shared along
    the way is billed with the feeder that runs along it before branching off."""
    parent = {equipment_key(f.to_db): equipment_key(f.from_source) for f in feeders}

    def route_m(f) -> float:
        r = routes.route(f.from_source, f.to_db) if routes is not None and routes.found else None
        return r.length_m if r is not None else float("inf")

    def depth(k: str) -> int:
        seen = {k}
        n = 0
        while k in parent and parent[k] not in seen:
            k = parent[k]
            seen.add(k)
            n += 1
        return n
    return sorted(feeders, key=lambda f: (depth(equipment_key(f.to_db)), route_m(f)))


def _assemble_sld_feeders(lines, gaps, sld: SldFacts, crew: CrewRates, params: RateParams,
                          cfg: DxfAssembleConfig, routes: Optional[RouteNetwork] = None) -> None:
    claimed: Set[int] = set()                        # route edges whose trench is already billed
    for fd in _feeder_order(sld.feeders, routes):
        ref = fd.source or "SLD (DXF)"
        match = routes.route(fd.from_source, fd.to_db) if routes is not None and routes.found else None
        if fd.length_annotated and fd.length_m > 0:
            length, trench, src, note = fd.length_m, fd.length_m, ItemConfidence.EXTRACTED, ""
        elif match is not None:
            length = match.length_m * (1 + cfg.route_slack_pct / 100) + 2 * cfg.route_end_allowance_m
            trench = routes.length_of(match.edges - claimed)
            claimed |= match.edges
            src = ItemConfidence.INFERRED
            note = (f"Route measured {match.length_m:.1f} m on the site plan, "
                    f"+{cfg.route_slack_pct:g}% and {cfg.route_end_allowance_m:g} m at each end.")
            gaps.append(GapItem(
                section=BQSection.SUBMAIN_CABLES, building_block=fd.to_db,
                description=f"Feeder {fd.from_source}→{fd.to_db} length taken from the site-plan route",
                assumption=note,
                suggested_action="Check the route against the designer's cable schedule or on site.",
                severity="low", drawing_ref=ref,
            ))
            if match.stated_m and abs(match.stated_m - match.length_m) > cfg.label_conflict_pct / 100 * match.length_m:
                gaps.append(GapItem(
                    section=BQSection.SUBMAIN_CABLES, building_block=fd.to_db,
                    description=(f"Feeder {fd.from_source}→{fd.to_db}: lengths written on the site plan "
                                 f"add to {match.stated_m:g} m, the drawn route scales to {match.length_m:.0f} m"),
                    assumption="Priced on the scaled route.",
                    suggested_action="Confirm which is right — written dimensions normally govern.",
                    severity="medium", drawing_ref=ref,
                ))
        else:
            length = trench = cfg.assumed_feeder_m
            src = ItemConfidence.ASSUMED
            note = f"Length assumed {length:.0f} m (not printed on the SLD)."
            on_plan = routes is not None and routes.found
            gaps.append(GapItem(
                section=BQSection.SUBMAIN_CABLES, building_block=fd.to_db,
                description=(f"Feeder {fd.from_source}→{fd.to_db} has no drawn route on the site plan"
                             if on_plan else f"Feeder {fd.from_source}→{fd.to_db} route length not on the SLD"),
                assumption=f"Assumed {length:.0f} m.",
                suggested_action=("Draw or confirm the route for this board on the site plan."
                                  if on_plan else "Measure the route on the site plan (upload it) or confirm on site."),
                severity="high", drawing_ref=ref,
            ))
        key = _size_key(fd.cable_size_mm2)
        label = f"{fd.cable_size_mm2:g}mm² x{fd.cable_cores}C SWA feeder {fd.from_source}→{fd.to_db}"
        cable = build_rate(material_cost=constants.CABLE_PRICES.get(f"swa_{key}_4c", 0.0),
                           install_labour=cable_install_rate(key, crew) or 0.0, params=params)
        e_mm2 = earth_size_for(fd.cable_size_mm2)
        e_key = _size_key(e_mm2)
        earth = build_rate(material_cost=constants.CABLE_PRICES.get(f"earth_wire_{e_key}", 0.0),
                           install_labour=bcew_install_rate(e_key, crew) or 0.0, params=params)
        term = build_rate(material_cost=TERMINATION_MATERIAL.get(key, 0.0),
                          install_labour=termination_install_rate(key, crew) or 0.0, params=params)
        rows = [
            (BQSection.SUBMAIN_CABLES, f"Supply {label}", "m", length, cable.supply_rate, LineKind.SUPPLY),
            (BQSection.SUBMAIN_CABLES, f"Install {label}", "m", length, cable.install_rate, LineKind.INSTALL),
            (BQSection.SUBMAIN_CABLES, f"Supply {e_mm2:g}mm² BCEW earth", "m", length, earth.supply_rate, LineKind.SUPPLY),
            (BQSection.SUBMAIN_CABLES, f"Install {e_mm2:g}mm² BCEW earth", "m", length, earth.install_rate, LineKind.INSTALL),
            (BQSection.SUBMAIN_CABLES, f"Terminate {fd.cable_size_mm2:g}mm² SWA (both ends)", "Ea", 2,
             term.combined_rate, LineKind.COMBINED),
        ]
        if fd.is_underground and trench > 0:           # 0: the whole route shares a trench billed upstream
            rows += [
                (BQSection.UNDERGROUND, f"Trench 600mm for {fd.from_source}→{fd.to_db}", "m", trench,
                 cfg.trench_rate_per_m, LineKind.COMBINED),
                (BQSection.UNDERGROUND, "Warning tape 300mm above cable", "m", trench,
                 cfg.warning_tape_rate_per_m, LineKind.COMBINED),
            ]
        for section, desc, unit, qty, rate, kind in rows:
            lines.append(BQLineItem(
                section=section, description=desc, unit=unit, qty=round(qty, 2),
                unit_price_zar=round(rate, 2), line_kind=kind, building_block=fd.to_db,
                source=ItemConfidence.EXTRACTED if unit == "Ea" else src,
                assumption="" if unit == "Ea" else note, drawing_ref=ref,
            ))

# ─── Section 5/6 — fittings (exact counts from blocks + geometry) ────

def _assemble_fittings(lines, rec: DxfRecognition, crew: CrewRates, params: RateParams) -> None:
    # group by (canonical, building_block) so the take-off is per-room/building
    grouped: Dict[tuple, int] = {}
    for s in rec.symbols:
        bldg = s.room or s.building or ""
        grouped[(s.canonical_name, bldg)] = grouped.get((s.canonical_name, bldg), 0) + 1

    for (canonical, bldg), qty in sorted(grouped.items(), key=lambda kv: (-kv[1], kv[0][0])):
        category = _category_of(canonical)
        section = _CATEGORY_TO_SECTION.get(category, BQSection.FINAL_CABLES)
        material = _fitting_material_price(canonical)
        install = DEFAULT_DXF_CONFIG.default_point_install_labour
        rate = build_rate(material_cost=material, install_labour=install, params=params)
        desc = f"{canonical} — {bldg}" if bldg else canonical
        lines.append(BQLineItem(
            section=section, description=desc, unit="No", qty=float(qty),
            unit_price_zar=round(rate.combined_rate, 2),
            source=ItemConfidence.EXTRACTED, line_kind=LineKind.COMBINED,
            building_block=bldg, drawing_ref="DXF",
            notes="Exact count from DXF blocks/geometry.",
        ))


# ─── Section 4 — reticulation cable (MEASURED per circuit, not assumed) ─

def _assemble_reticulation(lines, rec: DxfRecognition, crew: CrewRates,
                           params: RateParams, cfg: DxfAssembleConfig) -> None:
    for circuit, length_m in sorted(rec.cable_length_m_by_circuit.items()):
        if length_m <= 0:
            continue
        is_lighting = circuit.upper().startswith("L")
        size = cfg.retic_light_size if is_lighting else cfg.retic_power_size
        material = constants.CABLE_PRICES.get(f"surfix_{size}_3c", 0.0)
        install = cable_install_rate(size, crew) or 25.0
        rate = build_rate(material_cost=material, install_labour=install, params=params)
        kind = "lighting" if is_lighting else "power"
        label = circuit if circuit != "unassigned" else "unassigned circuits"
        lines.append(BQLineItem(
            section=BQSection.FINAL_CABLES,
            description=f"{size} {kind} reticulation wire — circuit {label}",
            unit="m", qty=round(length_m, 2), unit_price_zar=round(rate.combined_rate, 2),
            source=ItemConfidence.EXTRACTED, line_kind=LineKind.COMBINED,
            building_block=label, drawing_ref="DXF geometry",
            circuit_details=circuit,
            notes="Cable length MEASURED from DXF polylines/arcs (exact, not assumed).",
        ))


# ─── helpers ─────────────────────────────────────────────────────────

def _number(lines: List[BQLineItem]) -> None:
    lines.sort(key=lambda l: l.section.section_number)
    counters: Dict[int, int] = {}
    for ln in lines:
        n = ln.section.section_number
        counters[n] = counters.get(n, 0) + 1
        ln.item_no = counters[n]


def _finalise_totals(boq: BillOfQuantities, params: RateParams) -> None:
    subtotal = round(sum(l.total_zar for l in boq.line_items), 2)
    contingency = round(subtotal * params.contingency_pct, 2)
    excl = round(subtotal + contingency, 2)
    vat = round(excl * params.vat_pct, 2)
    boq.subtotal_zar = subtotal
    boq.contingency_zar = contingency
    boq.markup_zar = 0.0
    boq.contractor_markup_pct = 0.0     # rates already include the x1.3 material markup
    boq.total_excl_vat_zar = excl
    boq.vat_zar = vat
    boq.total_incl_vat_zar = round(excl + vat, 2)


def _count_provenance(boq: BillOfQuantities) -> None:
    boq.items_extracted = sum(1 for l in boq.line_items if l.source == ItemConfidence.EXTRACTED)
    boq.items_assumed = sum(1 for l in boq.line_items if l.source == ItemConfidence.ASSUMED)
    boq.items_provisional = sum(1 for l in boq.line_items if l.source == ItemConfidence.PROVISIONAL)
