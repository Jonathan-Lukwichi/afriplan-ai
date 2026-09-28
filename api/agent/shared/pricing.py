"""
The one pricer (ADR-0008): findings → a priced BillOfQuantities.

Whichever reader found a board, a feeder, an item or a wire, it is priced here the same
way, from core.rate_model (crew×hours + material ×markup). Pure Python: the same findings
always give the identical bill.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal

from agent.shared.boq import (
    BillOfQuantities,
    BQLineItem,
    BQSection,
    ItemConfidence,
    LineKind,
)
from agent.shared.findings import BoardFinding, FeederFinding, Findings, ItemFinding, WireFinding
from core import constants
from core.rate_model import (
    DEFAULT_CREW,
    DEFAULT_PARAMS,
    TERMINATION_MATERIAL,
    CrewRates,
    RateParams,
    bcew_install_rate,
    build_rate,
    cable_install_rate,
    db_build_up,
    earth_size_for,
    termination_install_rate,
    trench_build_up,
)


@dataclass(frozen=True)
class PricingConfig:
    tag_only_board_price: float = 4500.0          # a board seen only as a tag: nominal enclosure
    trench_rate_per_m: float = round(trench_build_up().combined_rate, 2)   # dig, sand, backfill, reinstate
    warning_tape_rate_per_m: float = 5.4
    nominal_wire_install_per_m: float = 25.0      # 1.5mm² has no crew×hours entry


DEFAULT_PRICING = PricingConfig()


def price_findings(
    findings: Findings,
    *,
    pipeline: Literal["pdf", "dxf"],
    project_name: str = "",
    run_id: str = "",
    crew: CrewRates = DEFAULT_CREW,
    params: RateParams = DEFAULT_PARAMS,
    config: PricingConfig = DEFAULT_PRICING,
) -> BillOfQuantities:
    lines: List[BQLineItem] = []
    for b in findings.boards:
        lines += _board_lines(b, crew, params, config)
    for f in findings.feeders:
        lines += _feeder_lines(f, crew, params, config)
    for it in findings.items:
        lines.append(_item_line(it, params))
    for w in findings.wires:
        lines.append(_wire_line(w, crew, params, config))
    for ln in lines:
        ln.total_zar = round(ln.qty * ln.unit_price_zar, 2)
    number_lines(lines)
    boq = BillOfQuantities(
        project_name=project_name, pipeline=pipeline, run_id=run_id,
        line_items=lines, gaps=list(findings.gaps),
        contingency_pct=params.contingency_pct * 100, vat_pct=params.vat_pct * 100,
    )
    finalise_totals(boq, params)
    return boq


# ─── boards ──────────────────────────────────────────────────────────

def board_description(b: BoardFinding) -> str:
    if not b.contents_known:
        return f"{b.name}: distribution board (rating per SLD)"
    ways = len(b.circuits) + b.spares
    extras = [f"{b.motor_starters} motor starters" if b.motor_starters else "",
              f"{b.isolators} isolators" if b.isolators else "",
              "master switch" if b.master_switch else "",
              f"{b.three_phase_ways} three-phase ways" if b.three_phase_ways else ""]
    extras = [e for e in extras if e]
    return ((f"{b.name}: outdoor LV kiosk complete, " if b.main_kiosk else f"{b.name}: ")
            + f"{b.phases}ph {b.main_breaker_a}A, {b.ka:g}kA, {ways}-way ({b.spares} spare)"
            + (f", {', '.join(extras)}" if extras else ""))


def _board_lines(b: BoardFinding, crew, params, cfg: PricingConfig) -> List[BQLineItem]:
    if not b.contents_known:
        return [BQLineItem(
            section=BQSection.DISTRIBUTION, description=board_description(b), unit="Sum", qty=1,
            unit_price_zar=cfg.tag_only_board_price, source=b.confidence, line_kind=LineKind.COMBINED,
            building_block=b.building or b.name, drawing_ref=b.sheet, notes=b.notes,
            assumption=b.assumption,
        )]
    rate = db_build_up(ways=len(b.circuits) + b.spares, phases=b.phases, main_breaker_a=b.main_breaker_a,
                       circuits=b.circuits, elcb=b.elcb, surge=b.surge, floor_standing=b.floor_standing,
                       motor_starters=b.motor_starters, isolators=b.isolators,
                       master_switch=b.master_switch, crew=crew, params=params)
    price = rate.combined_rate
    source, assumption = b.confidence, b.assumption
    if b.main_kiosk:
        # ONE complete item: the board plus the outdoor free-standing kiosk that houses it
        # (not drawn on an SLD — market-estimate price, to confirm).
        price += constants.DB_PRICES.get("kiosk_lv_outdoor", 0.0) * params.material_markup
        source = ItemConfidence.INFERRED
        assumption = assumption or "Board read from the SLD; the outdoor kiosk housing is a market-estimate price."
    out = [BQLineItem(
        section=BQSection.DISTRIBUTION, description=board_description(b), unit="Sum", qty=1,
        unit_price_zar=round(price, 2), source=source, line_kind=LineKind.COMBINED,
        building_block=b.building or b.name, drawing_ref=b.sheet, assumption=assumption, notes=b.notes,
    )]
    if b.main_kiosk:
        out.append(BQLineItem(
            section=BQSection.DISTRIBUTION, description="Supply and install concrete plinth (main LV enclosure base)",
            unit="Sum", qty=1, unit_price_zar=round(constants.DB_PRICES.get("kiosk_plinth_concrete", 0.0), 2),
            source=ItemConfidence.INFERRED, line_kind=LineKind.COMBINED,
            building_block=b.building or b.name, drawing_ref=b.sheet,
            assumption="A kiosk stands on a cast plinth (not drawn on the SLD); market-estimate price.",
        ))
    return out


# ─── feeders ─────────────────────────────────────────────────────────

def size_key(mm2: float) -> str:
    """50.0 → '50mm2', 2.5 → '2.5mm2'."""
    return f"{int(mm2)}mm2" if float(mm2).is_integer() else f"{mm2}mm2"


def _feeder_lines(f: FeederFinding, crew, params, cfg: PricingConfig) -> List[BQLineItem]:
    key = size_key(f.cable_size_mm2)
    label = f"{f.cable_size_mm2:g}mm² x{f.cable_cores}C SWA feeder {f.from_board}→{f.to_board}"
    cable = build_rate(material_cost=constants.CABLE_PRICES.get(f"swa_{key}_4c", 0.0),
                       install_labour=cable_install_rate(key, crew) or 0.0, params=params)
    e_mm2 = f.earth_size_mm2 or earth_size_for(f.cable_size_mm2)
    e_key = size_key(e_mm2)
    earth = build_rate(material_cost=constants.CABLE_PRICES.get(f"earth_wire_{e_key}", 0.0),
                       install_labour=bcew_install_rate(e_key, crew) or 0.0, params=params)
    term = build_rate(material_cost=TERMINATION_MATERIAL.get(key, 0.0),
                      install_labour=termination_install_rate(key, crew) or 0.0, params=params)
    rows = [
        (BQSection.SUBMAIN_CABLES, f"Supply {label}", "m", f.length_m, cable.supply_rate, LineKind.SUPPLY),
        (BQSection.SUBMAIN_CABLES, f"Install {label}", "m", f.length_m, cable.install_rate, LineKind.INSTALL),
        (BQSection.SUBMAIN_CABLES, f"Supply {e_mm2:g}mm² BCEW earth", "m", f.length_m, earth.supply_rate, LineKind.SUPPLY),
        (BQSection.SUBMAIN_CABLES, f"Install {e_mm2:g}mm² BCEW earth", "m", f.length_m, earth.install_rate, LineKind.INSTALL),
        (BQSection.SUBMAIN_CABLES, f"Terminate {f.cable_size_mm2:g}mm² SWA (both ends)", "Ea", 2,
         term.combined_rate, LineKind.COMBINED),
    ]
    if f.underground and f.trench_m > 0:           # 0: the whole route shares a trench billed upstream
        rows += [
            (BQSection.UNDERGROUND, f"Trench 600mm for {f.from_board}→{f.to_board}", "m", f.trench_m,
             cfg.trench_rate_per_m, LineKind.COMBINED),
            (BQSection.UNDERGROUND, "Warning tape 300mm above cable", "m", f.trench_m,
             cfg.warning_tape_rate_per_m, LineKind.COMBINED),
        ]
    return [BQLineItem(
        section=section, description=desc, unit=unit, qty=round(qty, 2),
        unit_price_zar=round(rate, 2), line_kind=kind, building_block=f.building or f.to_board,
        source=ItemConfidence.EXTRACTED if unit == "Ea" else f.confidence,
        assumption="" if unit == "Ea" else f.assumption, drawing_ref=f.sheet, notes=f.notes,
    ) for section, desc, unit, qty, rate, kind in rows]


# ─── items and wiring ────────────────────────────────────────────────

def _item_line(it: ItemFinding, params) -> BQLineItem:
    if it.price_zar is not None:
        price = it.price_zar
    elif it.free_issue:
        price = it.install_zar                      # supplied by the client: install only
    else:
        price = build_rate(material_cost=it.material_zar, install_labour=it.install_zar,
                           params=params).combined_rate
    return BQLineItem(
        section=it.section, description=it.description, unit=it.unit, qty=it.qty,
        unit_price_zar=round(price, 2), source=it.confidence, line_kind=LineKind.COMBINED,
        building_block=it.building, drawing_ref=it.sheet, assumption=it.assumption, notes=it.notes,
        locations=[it.location] if it.location else [],
    )


def _wire_line(w: WireFinding, crew, params, cfg: PricingConfig) -> BQLineItem:
    material = constants.CABLE_PRICES.get(f"surfix_{w.size_key}_3c", 0.0)
    install = cable_install_rate(w.size_key, crew) or cfg.nominal_wire_install_per_m
    rate = build_rate(material_cost=material, install_labour=install, params=params)
    return BQLineItem(
        section=BQSection.FINAL_CABLES, description=w.description, unit="m", qty=round(w.metres, 2),
        unit_price_zar=round(rate.combined_rate, 2), source=w.confidence, line_kind=LineKind.COMBINED,
        building_block=w.building, drawing_ref=w.sheet, circuit_details=w.circuit,
        assumption=w.assumption, notes=w.notes,
    )


# ─── bill helpers (shared by both engines) ───────────────────────────

def number_lines(lines: List[BQLineItem]) -> None:
    """Stable order by section, keeping insertion order within a section; number within it."""
    lines.sort(key=lambda l: l.section.section_number)
    counters: Dict[int, int] = {}
    for ln in lines:
        n = ln.section.section_number
        counters[n] = counters.get(n, 0) + 1
        ln.item_no = counters[n]


def finalise_totals(boq: BillOfQuantities, params: RateParams = DEFAULT_PARAMS) -> None:
    """Totals, and how many lines are read / worked out / guessed. Markup is already in the rates."""
    for ln in boq.line_items:
        ln.total_zar = round(ln.qty * ln.unit_price_zar, 2)
    subtotal = round(sum(l.total_zar for l in boq.line_items), 2)
    contingency = round(subtotal * params.contingency_pct, 2)
    excl = round(subtotal + contingency, 2)
    vat = round(excl * params.vat_pct, 2)
    boq.subtotal_zar = subtotal
    boq.contingency_zar = contingency
    boq.markup_zar = 0.0
    boq.contractor_markup_pct = 0.0
    boq.total_excl_vat_zar = excl
    boq.vat_zar = vat
    boq.total_incl_vat_zar = round(excl + vat, 2)
    count = lambda c: sum(1 for l in boq.line_items if l.source == c)   # noqa: E731
    boq.items_extracted = count(ItemConfidence.EXTRACTED)
    boq.items_inferred = count(ItemConfidence.INFERRED)
    boq.items_assumed = count(ItemConfidence.ASSUMED)
    boq.items_provisional = count(ItemConfidence.PROVISIONAL)
    boq.items_estimated = count(ItemConfidence.ESTIMATED)
