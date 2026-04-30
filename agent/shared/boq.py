"""
Bill of Quantities — the canonical deliverable of either pipeline.

Both the PDF pipeline and the DXF pipeline produce a `BillOfQuantities`
with the same shape, so the cross-comparison layer can diff them
section by section.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, computed_field


# ─── BQ section taxonomy (SA industry standard, 14 sections) ──────────

class BQSection(str, Enum):
    INCOMING = "SECTION 1: MAIN INCOMING SUPPLY & METERING"
    DISTRIBUTION = "SECTION 2: DISTRIBUTION BOARDS"
    SUBMAIN_CABLES = "SECTION 3: SUB-MAIN DISTRIBUTION CABLES"
    FINAL_CABLES = "SECTION 4: FINAL SUB-CIRCUIT CABLES"
    LIGHTING = "SECTION 5: LIGHTING INSTALLATION"
    POWER_OUTLETS = "SECTION 6: POWER OUTLETS INSTALLATION"
    DATA_COMMS = "SECTION 7: DATA & COMMUNICATIONS"
    CONTAINMENT = "SECTION 8: CABLE CONTAINMENT"
    UNDERGROUND = "SECTION 9: UNDERGROUND WORKS & SLEEVES"
    SOLAR_PV = "SECTION 10: SOLAR PV ELECTRICAL PROVISIONS"
    EARTHING = "SECTION 11: EARTHING & BONDING"
    FIRE_SAFETY = "SECTION 12: FIRE SAFETY PROVISIONS"
    TESTING = "SECTION 13: TESTING, COMMISSIONING & DOCUMENTATION"
    PRELIMS = "SECTION 14: PRELIMINARY & GENERAL"

    @property
    def section_number(self) -> int:
        return _SECTION_NUMBERS[self]

    @property
    def short_label(self) -> str:
        return _SECTION_SHORT_LABELS[self]


_SECTION_NUMBERS: Dict[BQSection, int] = {
    BQSection.INCOMING: 1,
    BQSection.DISTRIBUTION: 2,
    BQSection.SUBMAIN_CABLES: 3,
    BQSection.FINAL_CABLES: 4,
    BQSection.LIGHTING: 5,
    BQSection.POWER_OUTLETS: 6,
    BQSection.DATA_COMMS: 7,
    BQSection.CONTAINMENT: 8,
    BQSection.UNDERGROUND: 9,
    BQSection.SOLAR_PV: 10,
    BQSection.EARTHING: 11,
    BQSection.FIRE_SAFETY: 12,
    BQSection.TESTING: 13,
    BQSection.PRELIMS: 14,
}

_SECTION_SHORT_LABELS: Dict[BQSection, str] = {
    BQSection.INCOMING: "Incoming",
    BQSection.DISTRIBUTION: "Distribution",
    BQSection.SUBMAIN_CABLES: "Sub-mains",
    BQSection.FINAL_CABLES: "Final cables",
    BQSection.LIGHTING: "Lighting",
    BQSection.POWER_OUTLETS: "Outlets",
    BQSection.DATA_COMMS: "Data",
    BQSection.CONTAINMENT: "Containment",
    BQSection.UNDERGROUND: "Underground",
    BQSection.SOLAR_PV: "Solar",
    BQSection.EARTHING: "Earthing",
    BQSection.FIRE_SAFETY: "Fire safety",
    BQSection.TESTING: "Testing",
    BQSection.PRELIMS: "Prelims",
}


# ─── Confidence flag (per line item, drives UI colouring) ─────────────

class ItemConfidence(str, Enum):
    EXTRACTED = "extracted"     # read directly from drawing → green
    INFERRED = "inferred"       # derived from related data → yellow
    ESTIMATED = "estimated"     # default/guess → red, needs review
    MANUAL = "manual"           # contractor-entered → blue


# ─── Single BQ line item ──────────────────────────────────────────────

class BQLineItem(BaseModel):
    """
    One row in the bill of quantities.

    Quantity-only mode: unit_price_zar = 0, total_zar = 0
    Estimated mode:     unit_price_zar > 0, total_zar = qty * unit_price_zar
    """

    item_no: int = 0
    section: BQSection = BQSection.FINAL_CABLES
    category: str = ""
    description: str = ""
    unit: str = "each"
    qty: float = 1.0
    unit_price_zar: float = 0.0
    total_zar: float = 0.0
    source: ItemConfidence = ItemConfidence.EXTRACTED
    building_block: str = ""
    notes: str = ""
    is_rate_only: bool = False

    drawing_ref: str = ""
    subsection: str = ""
    locations: List[str] = Field(default_factory=list)
    circuit_details: str = ""

    @property
    def item_number_str(self) -> str:
        """Hierarchical item number: '4.15' = section 4, item 15."""
        return f"{self.section.section_number}.{self.item_no}"


# ─── Bill of Quantities (full deliverable) ────────────────────────────

class BillOfQuantities(BaseModel):
    """
    Canonical BQ output. Either pipeline produces this. The
    cross-comparison layer can diff two instances field-by-field.
    """

    # Provenance
    project_name: str = ""
    pipeline: Literal["pdf", "dxf"]
    run_id: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    # Line items
    line_items: List[BQLineItem] = Field(default_factory=list)

    # Pricing parameters used
    contractor_markup_pct: float = 20.0
    contingency_pct: float = 5.0
    vat_pct: float = 15.0

    # Computed totals (filled by the price stage)
    subtotal_zar: float = 0.0
    contingency_zar: float = 0.0
    markup_zar: float = 0.0
    total_excl_vat_zar: float = 0.0
    vat_zar: float = 0.0
    total_incl_vat_zar: float = 0.0

    # Quality
    items_extracted: int = 0
    items_inferred: int = 0
    items_estimated: int = 0
    items_rate_only: int = 0

    @computed_field
    @property
    def total_items(self) -> int:
        return len(self.line_items)

    @computed_field
    @property
    def section_subtotals_zar(self) -> Dict[str, float]:
        """Subtotal per section (uses BQSection.value as key for JSON-safety)."""
        out: Dict[str, float] = {}
        for item in self.line_items:
            key = item.section.value
            out[key] = out.get(key, 0.0) + item.total_zar
        return out

    @computed_field
    @property
    def section_subtotals_short(self) -> Dict[str, float]:
        """Subtotal per section keyed by short label (e.g. 'Lighting')."""
        out: Dict[str, float] = {}
        for item in self.line_items:
            key = item.section.short_label
            out[key] = out.get(key, 0.0) + item.total_zar
        return out

    @computed_field
    @property
    def quantity_confidence(self) -> float:
        """Fraction of items that came directly from extraction."""
        if not self.line_items:
            return 0.0
        return self.items_extracted / len(self.line_items)
