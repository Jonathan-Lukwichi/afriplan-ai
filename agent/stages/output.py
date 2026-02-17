"""
OUTPUT Stage: Assembly stage — builds final PipelineResult with weighted confidence.

Combines all stage results into the final output structure.
"""

from typing import List, Optional

from agent.models import (
    PipelineResult, StageResult, PipelineStage,
    DocumentSet, ExtractionResult, ValidationResult, PricingResult,
    ServiceTier, ExtractionMode, ContractorProfile, SiteConditions,
    ConfidenceLevel
)
from agent.utils import Timer


def generate_output(
    stages: List[StageResult],
    doc_set: DocumentSet,
    tier: ServiceTier,
    mode: ExtractionMode,
    extraction: ExtractionResult,
    validation: Optional[ValidationResult] = None,
    pricing: Optional[PricingResult] = None,
    contractor: Optional[ContractorProfile] = None,
    site: Optional[SiteConditions] = None,
) -> PipelineResult:
    """
    OUTPUT stage: Build final PipelineResult.

    Args:
        stages: List of stage results from all pipeline stages
        doc_set: Processed documents
        tier: Project classification tier
        mode: Extraction mode
        extraction: Final extraction result
        validation: Validation result
        pricing: Pricing result
        contractor: Contractor profile
        site: Site conditions

    Returns:
        Complete PipelineResult
    """
    with Timer("output") as timer:
        # Calculate overall confidence (weighted average)
        confidence_weights = {
            PipelineStage.INGEST: 0.05,
            PipelineStage.CLASSIFY: 0.10,
            PipelineStage.DISCOVER: 0.50,
            PipelineStage.REVIEW: 0.10,
            PipelineStage.VALIDATE: 0.15,
            PipelineStage.PRICE: 0.10,
        }

        weighted_confidence = 0.0
        total_weight = 0.0

        for stage in stages:
            weight = confidence_weights.get(stage.stage, 0.0)
            weighted_confidence += stage.confidence * weight
            total_weight += weight

        overall_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.0

        # Calculate total cost
        total_cost_zar = sum(s.cost_zar for s in stages)
        total_tokens = sum(s.tokens_used for s in stages)

        # Collect all errors and warnings
        all_errors = []
        all_warnings = []
        for stage in stages:
            all_errors.extend(stage.errors)
            all_warnings.extend(stage.warnings)

        # Determine overall success
        success = all(s.success for s in stages) and not any(
            e for e in all_errors if "critical" in e.lower() or "fatal" in e.lower()
        )

        # Get tier confidence from classify stage
        tier_confidence = 0.0
        for stage in stages:
            if stage.stage == PipelineStage.CLASSIFY:
                tier_confidence = stage.confidence
                break

        # Build final result
        result = PipelineResult(
            stages=stages,
            success=success,
            tier=tier,
            tier_confidence=tier_confidence,
            extraction_mode=mode,
            document_set=doc_set,
            extraction=extraction,
            validation=validation,
            pricing=pricing,
            contractor_profile=contractor,
            site_conditions=site,
            overall_confidence=overall_confidence,
            total_cost_zar=total_cost_zar,
            total_tokens=total_tokens,
            errors=all_errors,
            warnings=all_warnings,
        )

        # Add output stage result
        output_stage = StageResult(
            stage=PipelineStage.OUTPUT,
            success=True,
            confidence=1.0,
            data={
                "overall_confidence": overall_confidence,
                "confidence_level": result.confidence_level.value,
                "total_cost_zar": total_cost_zar,
                "total_tokens": total_tokens,
            },
            processing_time_ms=timer.elapsed_ms,
        )
        result.stages.append(output_stage)

        return result


def calculate_confidence_level(confidence: float) -> ConfidenceLevel:
    """Calculate confidence level from numeric confidence."""
    if confidence >= 0.70:
        return ConfidenceLevel.HIGH
    elif confidence >= 0.40:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def format_pipeline_summary(result: PipelineResult) -> str:
    """Format a human-readable summary of the pipeline result."""
    lines = [
        f"Pipeline Result Summary",
        f"=" * 40,
        f"Success: {'Yes' if result.success else 'No'}",
        f"Tier: {result.tier.value}",
        f"Mode: {result.extraction_mode.value}",
        f"Overall Confidence: {result.overall_confidence:.1%}",
        f"Confidence Level: {result.confidence_level.value}",
        f"",
        f"Documents: {len(result.document_set.documents)}",
        f"Total Pages: {result.document_set.total_pages}",
        f"Building Blocks: {result.num_building_blocks}",
        f"",
        f"Extraction:",
        f"  - Distribution Boards: {len(result.extraction.all_distribution_boards)}",
        f"  - Rooms: {len(result.extraction.all_rooms)}",
        f"  - Site Cable Runs: {len(result.extraction.site_cable_runs)}",
        f"",
    ]

    if result.validation:
        lines.extend([
            f"Validation:",
            f"  - Compliance Score: {result.validation.compliance_score:.1f}%",
            f"  - Passed: {result.validation.passed}",
            f"  - Failed: {result.validation.failed}",
            f"  - Auto-corrected: {result.validation.auto_corrections}",
            f"",
        ])

    if result.pricing:
        lines.extend([
            f"Pricing:",
            f"  - Total BQ Items: {result.pricing.total_items}",
            f"  - Items from Extraction: {result.pricing.items_from_extraction}",
            f"  - Items Estimated: {result.pricing.items_estimated}",
            f"  - Estimated Total: R {result.pricing.estimate_total_incl_vat_zar:,.2f}",
            f"",
        ])

    lines.extend([
        f"Cost:",
        f"  - API Cost: R {result.total_cost_zar:.2f}",
        f"  - Tokens Used: {result.total_tokens:,}",
        f"",
        f"Stage Results:",
    ])

    for stage in result.stages:
        status = "✓" if stage.success else "✗"
        lines.append(
            f"  {status} {stage.stage.value}: {stage.confidence:.1%} "
            f"({stage.processing_time_ms}ms)"
        )

    if result.errors:
        lines.extend([f"", f"Errors ({len(result.errors)}):"])
        for error in result.errors[:5]:
            lines.append(f"  - {error}")

    if result.warnings:
        lines.extend([f"", f"Warnings ({len(result.warnings)}):"])
        for warning in result.warnings[:5]:
            lines.append(f"  - {warning}")

    return "\n".join(lines)
