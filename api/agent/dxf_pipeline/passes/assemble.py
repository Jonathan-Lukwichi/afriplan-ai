"""
Pass 6 — what a DXF recognition shows, as findings; priced by the one pricer (ADR-0008).

The DXF analogue of the PDF pipeline's deterministic brain. The crucial
difference: DXF quantities are MEASURED, not assumed — block counts are exact
enumeration and cable lengths come from geometry. So most lines are EXTRACTED,
not ASSUMED, and there are far fewer gaps than the vision path.

Pricing is `agent.shared.pricing.price_findings`, so a DXF bill and a PDF bill price
the same item identically. This module must NOT import agent.pdf_pipeline.*
(CLAUDE.md single rule) — it shares only core + agent.shared.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Set

from agent.dxf_pipeline.passes.recognize import DxfRecognition
from agent.dxf_pipeline.passes.sld import SldFacts
from agent.dxf_pipeline.patterns import EXACT_BLOCK_MAP, REGEX_BLOCK_PATTERNS
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
from agent.shared.pricing import price_findings
from agent.shared.routes import RouteNetwork, equipment_key
from agent.shared.symbol_catalogue import catalogue_item
from core.rate_model import DEFAULT_CREW, DEFAULT_PARAMS, CrewRates, RateParams


@dataclass(frozen=True)
class DxfAssembleConfig:
    default_point_install_labour: float = 85.0     # fitting install fallback
    retic_light_size: str = "1.5mm2"
    retic_power_size: str = "2.5mm2"
    assumed_feeder_m: float = 30.0                 # SLDs rarely print route lengths (issue 002)
    route_slack_pct: float = 5.0                   # snaking / sag on a route measured from the site plan
    route_end_allowance_m: float = 1.5             # per end: rise into the board + termination tail
    label_conflict_pct: float = 25.0               # designer's written lengths vs the scaled route


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
    + the site plan's measured routes, when one was supplied) into a priced A–H bill:
    what was read (`findings_from_recognition`), priced by the one pricer."""
    findings = findings_from_recognition(rec, config=config, sld=sld, routes=routes,
                                         known_boards=known_boards)
    return price_findings(findings, pipeline="dxf", project_name=project_name, run_id=run_id,
                          crew=crew, params=params)


def findings_from_recognition(
    rec: DxfRecognition,
    *,
    config: DxfAssembleConfig = DEFAULT_DXF_CONFIG,
    sld: Optional[SldFacts] = None,
    routes: Optional[RouteNetwork] = None,
    known_boards: Iterable[str] = (),
) -> Findings:
    """What this drawing shows, unpriced. `known_boards`: boards already found on an SLD
    elsewhere in the project — a layout's circuit tags must not add them a second time."""
    out = Findings()
    if sld is not None and sld.boards:
        out.boards += [_sld_board(b) for b in sld.boards]      # the SLD is the authority on boards
    else:
        _tagged_boards(out, rec, skip={equipment_key(b) for b in known_boards})
    if sld is not None and sld.feeders:
        _sld_feeders(out, sld, config, routes=routes)
    _fittings(out, rec, config)
    _wiring(out, rec, config)
    return out


# ─── boards ──────────────────────────────────────────────────────────

def _tagged_boards(out: Findings, rec: DxfRecognition, skip: Set[str] = frozenset()) -> None:
    for db in rec.db_refs():
        if equipment_key(db) in skip:
            continue
        out.boards.append(BoardFinding(
            name=db, contents_known=False, sheet="DXF", evidence=Evidence.WRITTEN,
            notes="DB inferred from circuit tags; ways/rating not in layout DXF.",
        ))
        out.boards[-1].gaps.append(GapItem(
            section=BQSection.DISTRIBUTION, building_block=db,
            description=f"{db} rating/ways not in the layout DXF",
            assumption="Priced as a nominal enclosure.",
            suggested_action="Confirm DB size from the SLD/schedule.",
            severity="medium", drawing_ref="DXF",
        ))


def _board_circuits(b) -> list:
    """(amps, poles) per way; the circuits wired in 4-core cable are 3-pole — the largest first."""
    order = sorted(range(len(b.circuits)), key=lambda i: -b.circuits[i][0])
    three = set(order[:b.three_phase_ways])
    return [(a, 3 if i in three else p) for i, (a, p) in enumerate(b.circuits)]


def _sld_board(b) -> BoardFinding:
    return BoardFinding(
        name=b.name, phases=b.phases, main_breaker_a=b.main_breaker_a, ka=b.ka,
        circuits=_board_circuits(b), spares=b.spares, motor_starters=b.motor_starters,
        isolators=b.isolators, master_switch=b.master_switch, three_phase_ways=b.three_phase_ways,
        main_kiosk=b.name == "KIOSK", sheet=b.source or "SLD (DXF)", evidence=Evidence.WRITTEN,
        notes="Board, incomer, breakers, starters and isolators read from the SLD; ELCB/SPD not priced unless shown.",
    )


# ─── feeders: length from the SLD text, the site-plan route, or assumed ─

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


def _sld_feeders(out: Findings, sld: SldFacts, cfg: DxfAssembleConfig,
                 routes: Optional[RouteNetwork] = None) -> None:
    claimed: Set[int] = set()                        # route edges whose trench is already billed
    for fd in _feeder_order(sld.feeders, routes):
        gaps: list = []
        ref = fd.source or "SLD (DXF)"
        match = routes.route(fd.from_source, fd.to_db) if routes is not None and routes.found else None
        if fd.length_annotated and fd.length_m > 0:
            length, trench, note = fd.length_m, fd.length_m, ""
            src, ev = ItemConfidence.EXTRACTED, Evidence.WRITTEN
        elif match is not None:
            length = match.length_m * (1 + cfg.route_slack_pct / 100) + 2 * cfg.route_end_allowance_m
            trench = routes.length_of(match.edges - claimed)
            claimed |= match.edges
            src, ev = ItemConfidence.INFERRED, Evidence.MEASURED
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
            src, ev = ItemConfidence.ASSUMED, Evidence.ASSUMED
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
        out.feeders.append(FeederFinding(
            from_board=fd.from_source, to_board=fd.to_db, cable_size_mm2=fd.cable_size_mm2,
            cable_cores=fd.cable_cores, underground=fd.is_underground, length_m=length, trench_m=trench,
            sheet=ref, evidence=ev, confidence=src, assumption=note, gaps=gaps,
        ))


# ─── Section 5/6 — fittings (exact counts from blocks + geometry) ────

def _fittings(out: Findings, rec: DxfRecognition, cfg: DxfAssembleConfig) -> None:
    # group by (canonical, building_block) so the take-off is per-room/building
    grouped: Dict[tuple, int] = {}
    for s in rec.symbols:
        bldg = s.room or s.building or ""
        grouped[(s.canonical_name, bldg)] = grouped.get((s.canonical_name, bldg), 0) + 1

    for (canonical, bldg), qty in sorted(grouped.items(), key=lambda kv: (-kv[1], kv[0][0])):
        out.items.append(ItemFinding(
            description=f"{canonical} — {bldg}" if bldg else canonical,
            section=_CATEGORY_TO_SECTION.get(_category_of(canonical), BQSection.FINAL_CABLES),
            item=canonical if catalogue_item(canonical) else "",
            qty=float(qty), material_zar=_fitting_material_price(canonical),
            install_zar=cfg.default_point_install_labour, building=bldg, sheet="DXF",
            evidence=Evidence.COUNTED, notes="Exact count from DXF blocks/geometry.",
        ))


# ─── Section 4 — reticulation cable (MEASURED per circuit, not assumed) ─

def _wiring(out: Findings, rec: DxfRecognition, cfg: DxfAssembleConfig) -> None:
    for circuit, length_m in sorted(rec.cable_length_m_by_circuit.items()):
        if length_m <= 0:
            continue
        is_lighting = circuit.upper().startswith("L")
        size = cfg.retic_light_size if is_lighting else cfg.retic_power_size
        kind = "lighting" if is_lighting else "power"
        label = circuit if circuit != "unassigned" else "unassigned circuits"
        out.wires.append(WireFinding(
            description=f"{size} {kind} reticulation wire — circuit {label}",
            size_key=size, metres=length_m, circuit=circuit, building=label, sheet="DXF geometry",
            evidence=Evidence.MEASURED,
            notes="Cable length MEASURED from DXF polylines/arcs (exact, not assumed).",
        ))
