"""
AfriPlan Electrical v1.0 - Reconciliation Stage

The ONLY stage that uses LLM calls, and ONLY when needed.
Resolves ambiguities between SLD counts and layout counts.

Deterministic extraction is ALWAYS tried first:
1. SLD extraction (circuit schedules) - source of truth for counts
2. Layout scanning (circuit labels) - verification
3. Legend extraction (fixture types) - symbol mapping

LLM reconciliation is called ONLY when:
- SLD and layout counts differ by > 2 points
- Missing circuit assignments
- Ambiguous fixture types

Usage:
    from agent.stages.reconcile import reconcile_extraction

    # Pass deterministic results
    final_data = reconcile_extraction(
        sld_data=sld_result,
        layout_data=layout_scans,
        legend_data=legend,
        use_llm=True,  # Set False to skip LLM entirely
    )
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

from agent.models import PageInfo, StageResult, PipelineStage, ItemConfidence
from agent.utils import Timer
from agent.stages.extract_sld import SLDExtractionResult
from agent.extractors.circuit_label_scanner import (
    CircuitLabelScanResult,
    match_with_sld_counts,
)

logger = logging.getLogger(__name__)


@dataclass
class ReconciliationIssue:
    """An issue that may need LLM resolution."""
    issue_type: str  # "count_mismatch", "missing_assignment", "ambiguous_type"
    circuit_id: str
    sld_value: Any
    layout_value: Any
    description: str
    severity: str = "warning"  # "critical", "warning", "info"
    resolved: bool = False
    resolution: str = ""
    confidence: ItemConfidence = ItemConfidence.INFERRED


@dataclass
class ReconciliationResult:
    """Complete reconciliation result."""
    # Final resolved counts (SLD is source of truth, adjusted if needed)
    final_counts: Dict[str, int] = field(default_factory=dict)
    # Issues found and their resolutions
    issues: List[ReconciliationIssue] = field(default_factory=list)
    # BOQ items ready for pricing
    boq_items: List[Dict[str, Any]] = field(default_factory=list)
    # Statistics
    total_lighting_points: int = 0
    total_power_points: int = 0
    total_dedicated_circuits: int = 0
    # LLM usage
    llm_called: bool = False
    llm_reason: str = ""
    # Confidence
    overall_confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)


# Tolerance for count mismatches before escalating to LLM
COUNT_MISMATCH_TOLERANCE = 2


def reconcile_extraction(
    sld_data: Optional[SLDExtractionResult],
    layout_scans: Dict[int, CircuitLabelScanResult],
    legend_data: Optional[Dict[str, Any]] = None,
    use_llm: bool = True,
    anthropic_client: Optional[Any] = None,
) -> ReconciliationResult:
    """
    Reconcile deterministic extraction results.

    Priority:
    1. SLD circuit schedule "No Of Point" is source of truth
    2. Layout scans verify/supplement SLD data
    3. Legend provides fixture type mapping
    4. LLM called ONLY for unresolvable ambiguities

    Args:
        sld_data: Result from extract_all_dbs
        layout_scans: Results from scan_layout_pages
        legend_data: Results from extract_legend_from_pages
        use_llm: Whether to allow LLM calls for ambiguity resolution
        anthropic_client: Anthropic client if LLM is needed

    Returns:
        ReconciliationResult with final BOQ data
    """
    result = ReconciliationResult()

    # Step 1: Start with SLD data as source of truth
    if sld_data and sld_data.dbs:
        for db in sld_data.dbs:
            for circuit in db.circuits:
                circuit_key = f"{db.name}/{circuit.circuit_id}"
                result.final_counts[circuit.circuit_id] = circuit.num_points

                # Track totals
                if circuit.circuit_type == "lighting":
                    result.total_lighting_points += circuit.num_points
                elif circuit.circuit_type == "power":
                    result.total_power_points += circuit.num_points
                elif circuit.circuit_type in ("dedicated", "spare"):
                    result.total_dedicated_circuits += 1

    # Step 2: Aggregate layout counts
    layout_counts: Dict[str, int] = {}
    for page_num, scan in layout_scans.items():
        for label, count in scan.labels.items():
            layout_counts[label] = layout_counts.get(label, 0) + count

    # Step 3: Compare SLD vs Layout counts
    issues_found = []

    for circuit_id, sld_count in result.final_counts.items():
        layout_count = layout_counts.get(circuit_id, 0)
        difference = abs(sld_count - layout_count)

        if difference > COUNT_MISMATCH_TOLERANCE:
            issues_found.append(ReconciliationIssue(
                issue_type="count_mismatch",
                circuit_id=circuit_id,
                sld_value=sld_count,
                layout_value=layout_count,
                description=f"SLD shows {sld_count} points but layout has {layout_count}",
                severity="warning" if difference <= 5 else "critical",
            ))

    # Check for circuits on layout but not in SLD
    for label, count in layout_counts.items():
        if label not in result.final_counts and count > 0:
            issues_found.append(ReconciliationIssue(
                issue_type="missing_assignment",
                circuit_id=label,
                sld_value=0,
                layout_value=count,
                description=f"Circuit {label} found on layout but not in SLD",
                severity="warning",
            ))

    result.issues = issues_found

    # Step 4: Attempt automatic resolution
    for issue in result.issues:
        if issue.issue_type == "count_mismatch":
            # Trust SLD for "No Of Point" row data
            # Layout counts can miss items or double-count
            issue.resolved = True
            issue.resolution = "Using SLD count as source of truth"
            issue.confidence = ItemConfidence.EXTRACTED

        elif issue.issue_type == "missing_assignment":
            # Add to final counts with lower confidence
            result.final_counts[issue.circuit_id] = issue.layout_value
            issue.resolved = True
            issue.resolution = "Added from layout with inferred confidence"
            issue.confidence = ItemConfidence.INFERRED

    # Step 5: Check if LLM is needed
    critical_unresolved = [
        i for i in result.issues
        if i.severity == "critical" and not i.resolved
    ]

    if critical_unresolved and use_llm and anthropic_client:
        # This is the ONLY LLM call in the entire extraction
        result.llm_called = True
        result.llm_reason = f"Resolving {len(critical_unresolved)} critical ambiguities"

        try:
            _resolve_with_llm(result, critical_unresolved, anthropic_client)
        except Exception as e:
            logger.error(f"LLM reconciliation failed: {e}")
            result.warnings.append(f"LLM reconciliation failed: {e}")
            # Continue without LLM resolution

    # Step 6: Build BOQ items
    result.boq_items = _build_boq_items(
        final_counts=result.final_counts,
        sld_data=sld_data,
        legend_data=legend_data,
    )

    # Step 7: Calculate overall confidence
    if result.issues:
        resolved_count = sum(1 for i in result.issues if i.resolved)
        resolution_rate = resolved_count / len(result.issues)
        result.overall_confidence = 0.7 + (0.3 * resolution_rate)
    else:
        result.overall_confidence = 0.95  # No issues = high confidence

    # Add warnings for unresolved issues
    unresolved = [i for i in result.issues if not i.resolved]
    for issue in unresolved:
        result.warnings.append(f"Unresolved: {issue.description}")

    return result


def _resolve_with_llm(
    result: ReconciliationResult,
    issues: List[ReconciliationIssue],
    client: Any,
) -> None:
    """
    Use LLM to resolve critical ambiguities.

    This is the ONLY LLM call in the extraction pipeline.
    Uses Haiku for cost efficiency.
    """
    # Build minimal prompt with just the ambiguities
    prompt = """You are resolving ambiguities in electrical BOQ extraction.
For each issue, determine the most likely correct count.
Respond in JSON format.

Issues to resolve:
"""
    for i, issue in enumerate(issues):
        prompt += f"""
{i+1}. Circuit {issue.circuit_id}:
   - SLD schedule says: {issue.sld_value} points
   - Layout count shows: {issue.layout_value} points
   - Issue: {issue.description}
"""

    prompt += """
Respond with JSON:
{
  "resolutions": [
    {"circuit_id": "L1", "resolved_count": 8, "reasoning": "brief reason"}
  ]
}

IMPORTANT: Trust the SLD schedule "No Of Point" row when available - it's the official count.
Layout counts may miss symbols or double-count shared fixtures.
"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",  # Cheapest model for reconciliation
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text

        # Parse JSON response
        json_match = response_text
        if "```json" in response_text:
            json_match = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            json_match = response_text.split("```")[1].split("```")[0]

        parsed = json.loads(json_match)

        # Apply resolutions
        for resolution in parsed.get("resolutions", []):
            circuit_id = resolution.get("circuit_id")
            resolved_count = resolution.get("resolved_count")
            reasoning = resolution.get("reasoning", "")

            # Find matching issue
            for issue in issues:
                if issue.circuit_id == circuit_id:
                    result.final_counts[circuit_id] = resolved_count
                    issue.resolved = True
                    issue.resolution = f"LLM: {reasoning}"
                    issue.confidence = ItemConfidence.ESTIMATED
                    break

    except Exception as e:
        logger.error(f"LLM resolution parsing failed: {e}")
        # Leave issues unresolved


def _build_boq_items(
    final_counts: Dict[str, int],
    sld_data: Optional[SLDExtractionResult],
    legend_data: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Build BOQ items from reconciled counts.
    """
    items = []

    # Group by circuit type
    lighting_total = 0
    power_total = 0
    dedicated_list = []

    for circuit_id, count in final_counts.items():
        circuit_upper = circuit_id.upper()
        if circuit_upper.startswith("L"):
            lighting_total += count
        elif circuit_upper.startswith("P"):
            power_total += count
        elif circuit_upper.startswith(("AC", "GY", "ST", "HP", "PP", "GM", "ISO")):
            dedicated_list.append(circuit_id)

    # Add lighting summary
    if lighting_total > 0:
        items.append({
            "category": "Lighting",
            "description": "Light points (as per SLD schedule)",
            "quantity": lighting_total,
            "unit": "pts",
            "confidence": ItemConfidence.EXTRACTED.value,
            "source": "sld_schedule",
        })

    # Add power summary
    if power_total > 0:
        items.append({
            "category": "Power",
            "description": "Socket outlets (as per SLD schedule)",
            "quantity": power_total,
            "unit": "pts",
            "confidence": ItemConfidence.EXTRACTED.value,
            "source": "sld_schedule",
        })

    # Add dedicated circuits
    for circuit_id in dedicated_list:
        items.append({
            "category": "Dedicated Circuits",
            "description": f"Dedicated circuit {circuit_id}",
            "quantity": 1,
            "unit": "circuit",
            "confidence": ItemConfidence.EXTRACTED.value,
            "source": "sld_schedule",
        })

    # Add DB board if SLD data available
    if sld_data:
        for db in sld_data.dbs:
            items.append({
                "category": "Distribution Board",
                "description": f"DB {db.name} - {db.total_circuits} ways",
                "quantity": 1,
                "unit": "unit",
                "confidence": ItemConfidence.EXTRACTED.value,
                "source": "sld_schedule",
                "details": {
                    "main_breaker_a": db.main_breaker_a,
                    "total_circuits": db.total_circuits,
                    "spare_circuits": db.spare_circuits,
                },
            })

    return items


def reconcile_with_stage_result(
    sld_data: Optional[SLDExtractionResult],
    layout_scans: Dict[int, CircuitLabelScanResult],
    legend_data: Optional[Dict[str, Any]] = None,
    use_llm: bool = True,
    anthropic_client: Optional[Any] = None,
) -> Tuple[ReconciliationResult, StageResult]:
    """
    Reconcile with StageResult for pipeline integration.
    """
    with Timer("reconcile") as timer:
        result = reconcile_extraction(
            sld_data=sld_data,
            layout_scans=layout_scans,
            legend_data=legend_data,
            use_llm=use_llm,
            anthropic_client=anthropic_client,
        )

        stage_result = StageResult(
            stage=PipelineStage.DISCOVER,
            success=result.overall_confidence > 0.5,
            confidence=result.overall_confidence,
            data={
                "total_lighting_points": result.total_lighting_points,
                "total_power_points": result.total_power_points,
                "total_dedicated_circuits": result.total_dedicated_circuits,
                "issues_count": len(result.issues),
                "resolved_count": sum(1 for i in result.issues if i.resolved),
                "llm_called": result.llm_called,
            },
            model_used="claude-haiku-4-5" if result.llm_called else None,
            tokens_used=0,  # Could track if needed
            cost_zar=0.18 if result.llm_called else 0.0,  # ~R0.18 for Haiku call
            processing_time_ms=timer.elapsed_ms,
            errors=[],
            warnings=result.warnings,
        )

        return result, stage_result
