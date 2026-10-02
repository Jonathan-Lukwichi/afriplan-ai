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

import os
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
    supports_temperature: bool = True   # Opus 5 / Sonnet 5 reject `temperature` (400)


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

# Current generation (2026-09). Pricing per the Anthropic model table.
OPUS_5 = ModelSpec(
    model_id="claude-opus-5",
    display_name="Opus 5",
    input_usd_per_mtok=5.00,
    output_usd_per_mtok=25.00,
    supports_temperature=False,
)

SONNET_5 = ModelSpec(
    model_id="claude-sonnet-5",
    display_name="Sonnet 5",
    input_usd_per_mtok=2.00,
    output_usd_per_mtok=10.00,
    supports_temperature=False,
)

# Convenience map for telemetry
MODEL_REGISTRY: Dict[str, ModelSpec] = {
    m.model_id: m for m in (HAIKU_4_5, SONNET_4_5, OPUS_4_6, OPUS_5, SONNET_5)
}


# Pipeline role → model. Only the PDF pipeline uses these; the DXF
# pipeline never imports this section. Reading a drawing page is the hard part,
# so it gets the most capable model; classifying a page is easy and stays on Haiku.
EXTRACT_MODEL = OPUS_5
CLASSIFY_MODEL = HAIKU_4_5
ESCALATE_MODEL = OPUS_5          # already the top model: escalation re-asks nothing new
MATCH_MODEL = OPUS_5             # combining (ADR-0008): which names from the two readers are the same thing;
                                 # once per project, so accuracy matters more than cost
PDF_PIPELINE_MODELS = {
    "classify": CLASSIFY_MODEL,
    "extract": EXTRACT_MODEL,
    "escalate": ESCALATE_MODEL,
}
# Pages are read in parallel; each worker is one request in flight.
PDF_PARALLEL_PAGES = 6


# ╔═══════════════════════════════════════════════════════════════════╗
# ║ GOOGLE GEMINI — the free alternative (core/gemini_client.py)      ║
# ╚═══════════════════════════════════════════════════════════════════╝
# Priced at R 0: Google's free tier (rate-limited). The IDs can be changed without code
# via GEMINI_MODEL / GEMINI_FAST_MODEL in api/.env (e.g. a Pro model if your quota has one).

GEMINI_MAIN = ModelSpec(
    model_id=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
    display_name="Gemini (main)",
    input_usd_per_mtok=0.0,
    output_usd_per_mtok=0.0,
)
GEMINI_FAST = ModelSpec(
    model_id=os.environ.get("GEMINI_FAST_MODEL", "gemini-3.5-flash-lite"),
    display_name="Gemini (fast)",
    input_usd_per_mtok=0.0,
    output_usd_per_mtok=0.0,
)
# When a model is busy (503) or retired (404), the call is repeated once on this one.
GEMINI_FALLBACK = ModelSpec(
    model_id=os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash"),
    display_name="Gemini (fallback)",
    input_usd_per_mtok=0.0,
    output_usd_per_mtok=0.0,
)


def gemini_model_for(model_id: str) -> ModelSpec:
    """The Gemini model that does a Claude model's job: Haiku's easy jobs (sorting pages)
    go to the fast model, everything else (reading drawings, naming, matching) to the main one."""
    for spec in (GEMINI_MAIN, GEMINI_FAST):
        if model_id == spec.model_id:
            return spec
    return GEMINI_FAST if model_id == HAIKU_4_5.model_id else GEMINI_MAIN


def ai_provider() -> str:
    """'claude' or 'gemini'. AI_PROVIDER in api/.env decides; otherwise Claude when its key is
    set, else Gemini when its key is set. Read at call time (after api/.env is loaded)."""
    chosen = os.environ.get("AI_PROVIDER", "").strip().lower()
    if chosen in ("claude", "gemini"):
        return chosen
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude"
    return "gemini" if os.environ.get("GEMINI_API_KEY") else "claude"


def ai_available() -> bool:
    """Is there a key for the chosen provider?"""
    return bool(os.environ.get("GEMINI_API_KEY" if ai_provider() == "gemini" else "ANTHROPIC_API_KEY"))


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
