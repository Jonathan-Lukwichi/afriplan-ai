"""
AfriPlan AI Agent Package - 6-Stage Pipeline Orchestrator

This package implements the v3.0 AI architecture for intelligent document
analysis and quotation generation.

Pipeline Stages:
1. INGEST - Document processing (PyMuPDF + Pillow)
2. CLASSIFY - Fast tier routing (Haiku 4.5)
3. DISCOVER - JSON extraction (Sonnet 4.5 -> Opus escalation)
4. VALIDATE - SANS 10142-1 compliance
5. PRICE - Deterministic calculation (Python only)
6. OUTPUT - PDF/Excel generation

Model Strategy:
- Haiku 4.5: Fast classification (~R0.18/doc)
- Sonnet 4.5: Balanced extraction (~R1.80/doc)
- Opus 4.6: Escalation for low confidence (~R8.50/doc)

Service Tiers:
- Residential: Room-by-room, ADMD (NRS 034)
- Commercial: Area-based W/m², 3-phase balancing
- Maintenance: COC inspection + remedial quotations
"""

from agent.afriplan_agent import (
    AfriPlanAgent,
    PipelineResult,
    StageResult,
    PipelineStage,
)
from agent.classifier import (
    TierClassifier,
    ClassificationResult,
    ServiceTier,
)

__all__ = [
    'AfriPlanAgent',
    'PipelineResult',
    'StageResult',
    'PipelineStage',
    'TierClassifier',
    'ClassificationResult',
    'ServiceTier',
]

__version__ = '3.0.0'
