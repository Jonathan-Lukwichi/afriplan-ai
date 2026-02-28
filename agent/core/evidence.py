"""
AfriPlan AI v5 — Evidence & Confidence
========================================
Every extracted entity carries:
  - confidence score (0.0 - 1.0)
  - evidence chain (source page, crop coords, OCR snippet, model tokens)

This is what makes the system *defensible* when a contractor asks:
"Why did you say P2 is 3680W?"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Tuple


@dataclass
class Evidence:
    """
    Provenance chain for any extracted value.

    When a contractor asks "why did you say P2 is 3680W?", the system
    points to: source file → page number → crop region → OCR text →
    model response → specific JSON path.
    """
    source_file: str = ""
    page_number: int = 0
    region_name: str = ""                    # "schedule_table", "legend", "floor_plan"
    crop_coords: Tuple[float, ...] = ()      # (x0%, y0%, x1%, y1%) of full page
    ocr_snippet: str = ""                    # Raw OCR text that was used
    model_tokens: List[str] = field(default_factory=list)  # Key tokens model used
    raw_model_response: str = ""             # Full JSON response from model
    extraction_pass: str = ""                # "sld_schedule", "legend", "circuit_cluster"

    def summary(self) -> str:
        parts = []
        if self.source_file:
            parts.append(f"File: {self.source_file}")
        if self.page_number:
            parts.append(f"Page {self.page_number}")
        if self.region_name:
            parts.append(f"Region: {self.region_name}")
        if self.model_tokens:
            parts.append(f"Tokens: {', '.join(self.model_tokens[:5])}")
        return " → ".join(parts)


@dataclass
class Confident:
    """Wrapper that attaches confidence + evidence to any extracted value."""
    value: Any = None
    confidence: float = 0.0      # 0.0 = no confidence, 1.0 = certain
    evidence: Evidence = field(default_factory=Evidence)

    def is_reliable(self, threshold: float = 0.6) -> bool:
        return self.confidence >= threshold

    def __repr__(self) -> str:
        return f"Confident({self.value}, conf={self.confidence:.2f})"
