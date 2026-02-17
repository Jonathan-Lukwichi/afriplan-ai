"""
AfriPlan Electrical v4.1 — AI Agent Package

7-Stage Pipeline for Quantity Take-Off Acceleration:
1. INGEST - Document preprocessing (PyMuPDF + Pillow)
2. CLASSIFY - Fast tier routing (Haiku 4.5)
3. DISCOVER - JSON extraction with confidence (Sonnet 4.5 → Opus escalation)
4. REVIEW - Contractor review/edit interface (NEW in v4.1)
5. VALIDATE - SANS 10142-1 compliance checks
6. PRICE - Dual BQ generation (quantity-only + estimated)
7. OUTPUT - Final result assembly

Model Strategy:
- Haiku 4.5: Fast classification (~R0.18/doc)
- Sonnet 4.5: Balanced extraction (~R1.80/doc)
- Opus 4.6: Escalation for low confidence (~R8.50/doc)

v4.1 Philosophy:
- AI extracts quantities, contractor reviews/corrects, then applies own prices
- Primary output: Quantity-only BQ (contractor fills prices)
- Secondary output: Estimated BQ (ballpark reference only)
- ItemConfidence: EXTRACTED (green), INFERRED (yellow), ESTIMATED (red), MANUAL (blue)
"""

from agent.models import (
    # Enums
    ServiceTier,
    ExtractionMode,
    ItemConfidence,
    PipelineStage,
    BQSection,
    Severity,

    # Contractor/Site
    ContractorProfile,
    LabourRates,
    SiteConditions,

    # Pipeline Data
    DocumentSet,
    ExtractionResult,
    ValidationResult,
    ValidationFlag,
    PricingResult,
    BQLineItem,
    StageResult,
    PipelineResult,

    # Extraction Models
    BuildingBlock,
    Room,
    DistributionBoard,
    Circuit,
    FixtureCounts,
    SiteCableRun,

    # Review/Corrections
    CorrectionLog,
)

from agent.pipeline import (
    AfriPlanPipeline,
    create_pipeline,
    process_single_document,
    extract_quantities_only,
)

# Legacy v3.0 agent (still used by Smart Upload page)
from agent.afriplan_agent import AfriPlanAgent

from agent.stages import (
    ingest,
    classify,
    discover,
    ReviewManager,
    validate,
    price,
    generate_output,
)

__all__ = [
    # Version
    '__version__',

    # Enums
    'ServiceTier',
    'ExtractionMode',
    'ItemConfidence',
    'PipelineStage',
    'BQSection',
    'Severity',

    # Contractor/Site
    'ContractorProfile',
    'LabourRates',
    'SiteConditions',

    # Pipeline Data
    'DocumentSet',
    'ExtractionResult',
    'ValidationResult',
    'ValidationFlag',
    'PricingResult',
    'BQLineItem',
    'StageResult',
    'PipelineResult',

    # Extraction Models
    'BuildingBlock',
    'Room',
    'DistributionBoard',
    'Circuit',
    'FixtureCounts',
    'SiteCableRun',

    # Review
    'CorrectionLog',
    'ReviewManager',

    # Pipeline
    'AfriPlanPipeline',
    'AfriPlanAgent',  # Legacy v3.0 compatibility
    'create_pipeline',
    'process_single_document',
    'extract_quantities_only',

    # Stage Functions
    'ingest',
    'classify',
    'discover',
    'validate',
    'price',
    'generate_output',
]

__version__ = '4.1.0'
