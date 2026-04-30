"""
AfriPlan Electrical v6.1 — Core business logic package.

Contains:
- constants: SA unit prices and labour rates (shared by both pipelines)
- standards: SANS 10142-1 rule helpers (shared)
- config: per-pipeline thresholds and AI model registry (PDF only)
"""

from .constants import (
    LIGHT_PRICES,
    SOCKET_PRICES,
    SWITCH_PRICES,
    CABLE_PRICES,
    DB_PRICES,
    LABOUR_RATES,
    get_default_price,
)
from .standards import (
    SANS_10142_RULES,
    validate_circuit_points,
    calculate_diversity_factor,
    calculate_voltage_drop,
)
from .config import (
    HAIKU_4_5,
    SONNET_4_5,
    OPUS_4_6,
    MODEL_REGISTRY,
    PDF_PIPELINE_MODELS,
    PDF_THRESHOLDS,
    DXF_THRESHOLDS,
    estimate_cost_zar,
    usd_to_zar,
    DEFAULT_VAT_PCT,
    DEFAULT_MARKUP_PCT,
    DEFAULT_CONTINGENCY_PCT,
    DEFAULT_PAYMENT_TERMS,
    RUNS_DIR_PDF,
    RUNS_DIR_DXF,
    RUNS_DIR_COMPARISON,
    BASELINES_DIR,
)

__all__ = [
    # constants
    "LIGHT_PRICES",
    "SOCKET_PRICES",
    "SWITCH_PRICES",
    "CABLE_PRICES",
    "DB_PRICES",
    "LABOUR_RATES",
    "get_default_price",
    # standards
    "SANS_10142_RULES",
    "validate_circuit_points",
    "calculate_diversity_factor",
    "calculate_voltage_drop",
    # config
    "HAIKU_4_5",
    "SONNET_4_5",
    "OPUS_4_6",
    "MODEL_REGISTRY",
    "PDF_PIPELINE_MODELS",
    "PDF_THRESHOLDS",
    "DXF_THRESHOLDS",
    "estimate_cost_zar",
    "usd_to_zar",
    "DEFAULT_VAT_PCT",
    "DEFAULT_MARKUP_PCT",
    "DEFAULT_CONTINGENCY_PCT",
    "DEFAULT_PAYMENT_TERMS",
    "RUNS_DIR_PDF",
    "RUNS_DIR_DXF",
    "RUNS_DIR_COMPARISON",
    "BASELINES_DIR",
]
