"""
Findings — what a reader found on the drawings, before any price (ADR-0008).

Both engines produce these; `agent.shared.pricing.price_findings` turns them into a bill,
and the combining step merges the two readers' findings first. Every finding says who
read it, on which sheet, and how it was known (`Evidence`), so combining can keep the
strongest one by a rule that does not depend on the project.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field

from agent.shared.boq import BQSection, GapItem, ItemConfidence


class Evidence(str, Enum):
    MEASURED = "measured"   # length measured on CAD geometry (site plan, wiring polylines)
    COUNTED = "counted"     # every copy counted in the CAD file (blocks, repeated shapes)
    WRITTEN = "written"     # exact text in the CAD file (SLD ratings, a length written on the drawing)
    SEEN = "seen"           # read by the AI from a picture of the drawing
    ASSUMED = "assumed"     # not on the drawings — a documented default

    @property
    def rank(self) -> int:
        return _RANK[self]


KIOSK_ALLOWANCE = "Main LV kiosk"   # item name of a kiosk allowed for without its board

_RANK = {Evidence.MEASURED: 5, Evidence.COUNTED: 4, Evidence.WRITTEN: 3,
         Evidence.SEEN: 2, Evidence.ASSUMED: 1}


class _Finding(BaseModel):
    reader: Literal["dxf", "pdf"] = "dxf"
    sheet: str = ""                      # drawing it came from (becomes the line's drawing_ref)
    building: str = ""                   # building / room / board it belongs to
    evidence: Evidence = Evidence.WRITTEN
    confidence: ItemConfidence = ItemConfidence.EXTRACTED   # how the bill line is flagged
    assumption: str = ""
    notes: str = ""
    gaps: List[GapItem] = Field(default_factory=list)   # things to check about THIS finding —
                                                        # dropped with it if combining drops it


class BoardFinding(_Finding):
    """A distribution board and what its SLD shows."""
    name: str
    phases: int = 3
    main_breaker_a: int = 0
    ka: float = 0.0
    circuits: List[Tuple[int, int]] = Field(default_factory=list)   # (amps, poles) per way in use
    spares: int = 0
    motor_starters: int = 0
    isolators: int = 0
    master_switch: bool = False
    three_phase_ways: int = 0
    elcb: bool = False
    surge: bool = False
    floor_standing: bool = False
    contents_known: bool = True          # False: only the board's tag was seen (e.g. on a layout)
    main_kiosk: bool = False             # the main LV kiosk: board + outdoor housing + plinth


class FeederFinding(_Finding):
    """A sub-main cable from one board to another."""
    from_board: str
    to_board: str
    cable_size_mm2: float = 0.0
    cable_cores: int = 4
    earth_size_mm2: float = 0.0          # 0: the SANS rule for this cable size
    underground: bool = True
    length_m: float = 0.0
    trench_m: float = 0.0                # trench billed with THIS feeder (0: shared, billed upstream)


class ItemFinding(_Finding):
    """A counted or allowed-for item: fittings, outlets, switches, a plinth, a meter."""
    description: str
    section: BQSection = BQSection.FINAL_CABLES
    item: str = ""                       # shared catalogue name when known (for combining)
    unit: str = "No"
    qty: float = 0.0
    material_zar: float = 0.0            # supply price the reader looked up (Python, never the LLM)
    install_zar: float = 0.0
    price_zar: Optional[float] = None    # a fixed unit price, used as-is
    free_issue: bool = False             # supplied by the client: install only
    location: str = ""                   # room it was counted in, when known


class WireFinding(_Finding):
    """Final-circuit wiring, per circuit or per room."""
    description: str
    size_key: str = "2.5mm2"
    metres: float = 0.0
    circuit: str = ""


class Findings(BaseModel):
    boards: List[BoardFinding] = Field(default_factory=list)
    feeders: List[FeederFinding] = Field(default_factory=list)
    items: List[ItemFinding] = Field(default_factory=list)
    wires: List[WireFinding] = Field(default_factory=list)
    gaps: List[GapItem] = Field(default_factory=list)        # about the drawing set, not one finding
    sheet_words: Dict[str, List[str]] = Field(default_factory=dict)   # sheet → words printed on it

    def all(self) -> list:
        return [*self.boards, *self.feeders, *self.items, *self.wires]

    def all_gaps(self) -> List[GapItem]:
        return [*self.gaps, *(g for f in self.all() for g in f.gaps)]

    def extend(self, other: "Findings") -> None:
        self.boards += other.boards
        self.feeders += other.feeders
        self.items += other.items
        self.wires += other.wires
        self.gaps += other.gaps
        self.sheet_words.update(other.sheet_words)
