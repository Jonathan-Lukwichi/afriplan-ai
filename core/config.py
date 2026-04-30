"""
core.config — central configuration for AfriPlan v6.1.

Two main concerns:

1. Model identifiers and per-token costs for the PDF pipeline.
   Centralised so we never hard-code a model ID in five places again.

2. Per-pipeline gate thresholds. Each pipeline has its own. The PDF
   pipeline's gate has nothing to do with the DXF pipeline's gate,
   matching the independence rule (blueprint §0).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


# ╔═══════════════════════════════════════════════════════════════════╗
# ║ ANTHROPIC MODEL REGISTRY (PDF pipeline only)                      ║
# ╚═══════════════════════════════════════════════════════════════════╝

@dataclass(frozen=True)
class ModelSpec:
    """One AI model entry. Costs are per million tokens, in USD."""
    model_id: str
    display_name: str
    input_usd_per_mtok: float
    output_usd_per_mtok: float
    supports_vision: bool = True
    supports_tool_use: bool = True


# As of late 2025 / early 2026 — verified against Anthropic pricing
# https://docs.claude.com/en/docs/about-claude/models/overview
HAIKU_4_5 = ModelSpec(
    model_id="claude-haiku-4-5-20251001",
    display_name="Haiku 4.5",
    input_usd_per_mtok=1.00,
    output_usd_per_mtok=5.00,
)

SONNET_4_5 = ModelSpec(
    # Sonnet 4.6 has been released as the recommended balanced model.
    # We use 4.5 here as it's referenced throughout the blueprint;
    # bumping to 4.6 is a one-line change.
    model_id="claude-sonnet-4-5",
    display_name="Sonnet 4.5",
    input_usd_per_mtok=3.00,
    output_usd_per_mtok=15.00,
)

OPUS_4_6 = ModelSpec(
    model_id="claude-opus-4-6",
    display_name="Opus 4.6",
    input_usd_per_mtok=15.00,
    output_usd_per_mtok=75.00,
)

# Convenience map for telemetry
MODEL_REGISTRY: Dict[str, ModelSpec] = {
    HAIKU_4_5.model_id: HAIKU_4_5,
    SONNET_4_5.model_id: SONNET_4_5,
    OPUS_4_6.model_id: OPUS_4_6,
}


# Pipeline role → model. Only the PDF pipeline uses these; the DXF
# pipeline never imports this section.
PDF_PIPELINE_MODELS = {
    "classify": HAIKU_4_5,
    "extract": SONNET_4_5,
    "escalate": OPUS_4_6,
}


# ZAR / USD rate for cost reporting (rounded; refresh from XE quarterly)
ZAR_PER_USD: float = 18.50


def usd_to_zar(usd: float) -> float:
    return usd * ZAR_PER_USD


def estimate_cost_zar(input_tokens: int, output_tokens: int, model: ModelSpec) -> float:
    """Compute the rand cost of a single API call given token counts."""
    cost_usd = (
        input_tokens / 1_000_000.0 * model.input_usd_per_mtok
        + output_tokens / 1_000_000.0 * model.output_usd_per_mtok
    )
    return usd_to_zar(cost_usd)


# ╔═══════════════════════════════════════════════════════════════════╗
# ║ PDF PIPELINE GATES (LLM-aware)                                    ║
# ╚═══════════════════════════════════════════════════════════════════╝

@dataclass(frozen=True)
class PdfPipelineThresholds:
    # Per-field minimum confidence (LLM tool_use returned confidence)
    min_field_confidence: float = 0.60
    # Mean across-page confidence required for PASS
    min_mean_confidence: float = 0.75
    # Cross-page consistency: agreements / (agreements + disagreements)
    min_consistency_score: float = 0.80
    # Composite overall score required for PASS
    min_overall_score: float = 0.70
    # Baseline regression: max acceptable MAPE vs ground-truth BQ
    max_baseline_mape: float = 0.20
    # Repeat-run stability (CI): max % deviation across 3 runs
    max_repeat_run_deviation_pct: float = 0.05
    # Cost cap per run (alerts if exceeded)
    max_cost_zar: float = 8.00
    # Wall-clock cap per run
    max_duration_seconds: int = 60
    # Max PDF pages we'll process
    max_pages: int = 30
    # PDF rasterisation DPI for vision
    raster_dpi: int = 200


PDF_THRESHOLDS = PdfPipelineThresholds()


# ╔═══════════════════════════════════════════════════════════════════╗
# ║ DXF PIPELINE GATES (deterministic)                                ║
# ╚═══════════════════════════════════════════════════════════════════╝

@dataclass(frozen=True)
class DxfPipelineThresholds:
    # Coverage = recognised_blocks / total_blocks
    min_coverage_score: float = 0.80
    # Polyline cable lengths must match annotated lengths within ±5%
    max_cable_length_drift_pct: float = 0.05
    # Composite overall score required for PASS
    min_overall_score: float = 0.75
    # Baseline regression
    max_baseline_mape: float = 0.20
    # Performance
    max_duration_seconds: int = 5
    # Anomaly thresholds
    flag_orphan_layer_0_circles: bool = True
    flag_polyline_longer_than_m: float = 500.0


DXF_THRESHOLDS = DxfPipelineThresholds()


# ╔═══════════════════════════════════════════════════════════════════╗
# ║ DEFAULTS (shared)                                                 ║
# ╚═══════════════════════════════════════════════════════════════════╝

DEFAULT_VAT_PCT: float = 15.0
DEFAULT_MARKUP_PCT: float = 20.0
DEFAULT_CONTINGENCY_PCT: float = 5.0
DEFAULT_PAYMENT_TERMS: str = "40/40/20"

# Where we persist per-pipeline run logs
RUNS_DIR_PDF: str = "runs/pdf"
RUNS_DIR_DXF: str = "runs/dxf"
RUNS_DIR_COMPARISON: str = "runs/comparison"

# Where baseline ground-truth BQs live
BASELINES_DIR: str = "baselines"
