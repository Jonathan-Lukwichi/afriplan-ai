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
from typing import Dict, List, Optional

from agent.dxf_pipeline.passes.recognize import DxfRecognition
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
from core import constants
from core.rate_model import (
    DEFAULT_CREW,
    DEFAULT_PARAMS,
    CrewRates,
    RateParams,
    build_rate,
    cable_install_rate,
)


@dataclass(frozen=True)
class DxfAssembleConfig:
    default_point_install_labour: float = 85.0     # fitting install fallback
    retic_light_size: str = "1.5mm2"
    retic_power_size: str = "2.5mm2"
    db_enclosure_price: float = 4500.0


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
) -> BillOfQuantities:
    """Deterministically turn a DXF recognition into a priced A–H bill."""
    lines: List[BQLineItem] = []
    gaps: List[GapItem] = []

    _assemble_dbs(lines, gaps, rec, config)
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

def _assemble_dbs(lines, gaps, rec: DxfRecognition, cfg: DxfAssembleConfig) -> None:
    for db in rec.db_refs():
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
