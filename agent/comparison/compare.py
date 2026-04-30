"""
Compute a PipelineComparison from one PdfPipelineRun and one
DxfPipelineRun. This function NEVER mutates either input.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from agent.comparison.models import (
    FieldDiscrepancy,
    PipelineComparison,
    SectionAgreement,
)


def compare_runs(
    *,
    pdf_run,
    dxf_run,
) -> PipelineComparison:
    """
    Diff a PDF run and DXF run section by section.

    Both must have produced a non-None BoQ — otherwise we return an empty
    comparison flagged with the reason.
    """
    if pdf_run.boq is None or dxf_run.boq is None:
        return PipelineComparison(
            project_name=(pdf_run.boq or dxf_run.boq).project_name if (pdf_run.boq or dxf_run.boq) else "",
            pdf_run_id=pdf_run.run_id,
            dxf_run_id=dxf_run.run_id,
        )

    pdf_boq = pdf_run.boq
    dxf_boq = dxf_run.boq

    # ── 1. Section subtotals diff ─────────────────────────────────────
    section_agreements: Dict[str, SectionAgreement] = {}
    pdf_by_section = _group_by_section_value(pdf_boq.line_items)
    dxf_by_section = _group_by_section_value(dxf_boq.line_items)
    all_sections = set(pdf_by_section.keys()) | set(dxf_by_section.keys())

    for section in all_sections:
        pdf_items = pdf_by_section.get(section, [])
        dxf_items = dxf_by_section.get(section, [])
        pdf_sub = sum(it.total_zar for it in pdf_items)
        dxf_sub = sum(it.total_zar for it in dxf_items)

        pdf_descs = {it.description for it in pdf_items}
        dxf_descs = {it.description for it in dxf_items}

        delta = dxf_sub - pdf_sub
        delta_pct = None
        if pdf_sub > 0:
            delta_pct = delta / pdf_sub

        section_agreements[section] = SectionAgreement(
            section=section,
            pdf_subtotal=round(pdf_sub, 2),
            dxf_subtotal=round(dxf_sub, 2),
            delta_zar=round(delta, 2),
            delta_pct=delta_pct,
            items_only_in_pdf=sorted(pdf_descs - dxf_descs),
            items_only_in_dxf=sorted(dxf_descs - pdf_descs),
            items_in_both=len(pdf_descs & dxf_descs),
        )

    # ── 2. Per-field discrepancies (qty per description) ──────────────
    field_disagreements: List[FieldDiscrepancy] = []
    pdf_by_desc = _index_by_description(pdf_boq.line_items)
    dxf_by_desc = _index_by_description(dxf_boq.line_items)
    all_descs = set(pdf_by_desc.keys()) | set(dxf_by_desc.keys())
    for desc in sorted(all_descs):
        pdf_qty = pdf_by_desc.get(desc, 0.0)
        dxf_qty = dxf_by_desc.get(desc, 0.0)
        if pdf_qty == dxf_qty:
            continue
        denom = max(abs(pdf_qty), abs(dxf_qty), 1.0)
        field_disagreements.append(
            FieldDiscrepancy(
                field_path=f"qty.{desc}",
                pdf_value=pdf_qty,
                dxf_value=dxf_qty,
                delta_abs=round(abs(pdf_qty - dxf_qty), 4),
                delta_pct=round(abs(pdf_qty - dxf_qty) / denom, 4),
                note=_disagreement_note(pdf_qty, dxf_qty),
            )
        )

    # ── 3. Agreement score ────────────────────────────────────────────
    if all_descs:
        matched = sum(1 for d in all_descs if pdf_by_desc.get(d, 0.0) == dxf_by_desc.get(d, 0.0))
        agreement_score = matched / len(all_descs)
    else:
        agreement_score = 0.0

    # ── 4. Total difference ───────────────────────────────────────────
    total_diff_pct = None
    if pdf_boq.total_excl_vat_zar > 0:
        total_diff_pct = abs(
            dxf_boq.total_excl_vat_zar - pdf_boq.total_excl_vat_zar
        ) / pdf_boq.total_excl_vat_zar

    # ── 5. Baseline regression (optional) ─────────────────────────────
    pdf_mape = pdf_run.evaluation.baseline_mape
    dxf_mape = dxf_run.evaluation.baseline_mape
    winner = _winner_vs_baseline(pdf_mape, dxf_mape)

    return PipelineComparison(
        project_name=pdf_boq.project_name or dxf_boq.project_name,
        pdf_run_id=pdf_run.run_id,
        dxf_run_id=dxf_run.run_id,
        section_agreements=section_agreements,
        field_disagreements=field_disagreements,
        agreement_score=round(agreement_score, 4),
        pdf_cost_zar=pdf_run.cost_zar,
        dxf_cost_zar=dxf_run.cost_zar,
        pdf_total_excl_vat=pdf_boq.total_excl_vat_zar,
        dxf_total_excl_vat=dxf_boq.total_excl_vat_zar,
        total_difference_pct=total_diff_pct,
        pdf_vs_baseline_mape=pdf_mape,
        dxf_vs_baseline_mape=dxf_mape,
        winner_vs_baseline=winner,
    )


# ─── helpers ──────────────────────────────────────────────────────────

def _group_by_section_value(line_items) -> Dict[str, list]:
    by_section: Dict[str, list] = defaultdict(list)
    for it in line_items:
        by_section[it.section.value].append(it)
    return by_section


def _index_by_description(line_items) -> Dict[str, float]:
    """description → total qty (sums duplicates)."""
    out: Dict[str, float] = defaultdict(float)
    for it in line_items:
        out[it.description] += it.qty
    return out


def _disagreement_note(pdf_qty: float, dxf_qty: float) -> str:
    if pdf_qty == 0:
        return "Only DXF detected this item"
    if dxf_qty == 0:
        return "Only PDF detected this item"
    return ""


def _winner_vs_baseline(pdf_mape, dxf_mape):
    if pdf_mape is None and dxf_mape is None:
        return "no_baseline"
    if pdf_mape is None:
        return "dxf"
    if dxf_mape is None:
        return "pdf"
    if abs(pdf_mape - dxf_mape) < 0.005:
        return "tie"
    return "pdf" if pdf_mape < dxf_mape else "dxf"
