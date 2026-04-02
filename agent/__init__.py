"""
AfriPlan Electrical v5.1 — AI Agent Package

Extraction Pipelines:
━━━━━━━━━━━━━━━━━━━━

1. UNIVERSAL EXTRACTOR (v5.1 — Recommended)
   5-Strategy chain for ANY SA electrical drawing PDF:
   - Strategy 0: DXF DIRECT — ezdxf block counting (100% accurate, R0.00)
   - Strategy 1: TEXT LAYER — PyMuPDF text mining + spatial parsing (R0.00)
   - Strategy 2: LEGEND FINDER — keyword-based legend region detection (R0.00)
   - Strategy 3: LEGEND CROP AI — send legend crop to Haiku (R0.18)
   - Strategy 4: FULL-PAGE AI — Sonnet fallback for scanned PDFs (R1.80)

   Tested on: Wedela (AutoCAD), 3 Cubes/Megchem (ArchiCAD)
   Usage: from agent import extract_from_pdf, extract_from_dxf

2. LEGACY 7-STAGE PIPELINE (v4.11)
   Full-page AI extraction with model escalation:
   INGEST → CLASSIFY → DISCOVER → REVIEW → VALIDATE → PRICE → OUTPUT
   Usage: from agent import AfriPlanPipeline, create_pipeline

3. DETERMINISTIC PIPELINE (v5.0)
   No-AI extraction using regex + heuristics only.
   Usage: from agent import run_deterministic_pipeline

Model Strategy:
- Haiku 4.5: Legend crop reading (~R0.18/page)
- Sonnet 4.5: Full-page fallback (~R1.80/page)
- Opus 4.6: Escalation for low confidence (~R8.50/page)
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
    SimplifiedResult,
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

# Deterministic (non-AI) pipeline for local-only processing
from agent.deterministic_pipeline import (
    DeterministicPipeline,
    DeterministicPipelineResult,
    run_deterministic_pipeline,
    run_deterministic_pipeline_bytes,
    quick_extract,
)

# Universal Extractor v1.0 — 5-Strategy Chain (text → legend → AI crop → DXF)
from agent.universal_extractor import (
    UniversalExtractor,
    TextLayerMiner,
    LegendRegionFinder,
    LegendCropReader,
    extract_from_pdf,
    print_extraction_report,
    DocumentResult,
    PageResult,
    FixtureItem,
    ExtractionStrategy,
    FixtureCategory,
    DrawingType,
)

# DXF Extractor — 100% accurate extraction from AutoCAD files
from agent.dxf_extractor import (
    DXFExtractor,
    extract_from_dxf,
    extract_from_dxf_bytes,
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
    'SimplifiedResult',
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

    # Deterministic Pipeline (v5.0 - No AI)
    'DeterministicPipeline',
    'DeterministicPipelineResult',
    'run_deterministic_pipeline',
    'run_deterministic_pipeline_bytes',
    'quick_extract',

    # Universal Extractor (v5.1 - 5-Strategy Chain)
    'UniversalExtractor',
    'TextLayerMiner',
    'LegendRegionFinder',
    'LegendCropReader',
    'extract_from_pdf',
    'print_extraction_report',
    'DocumentResult',
    'PageResult',
    'FixtureItem',
    'ExtractionStrategy',
    'FixtureCategory',
    'DrawingType',

    # DXF Extractor (v5.1 - Zero-cost AutoCAD extraction)
    'DXFExtractor',
    'extract_from_dxf',
    'extract_from_dxf_bytes',
]

__version__ = '5.1.0'  # Universal Extractor + DXF support
