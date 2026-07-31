"""
Typed facts extracted by Passes 1–3, plus deterministic parsers.

These pydantic models mirror the pass tool schemas exactly. The parsers turn
the SDK-validated tool_input dict into a typed model with total-function
defaults — no arithmetic, no invention, so parsing is itself deterministic.
The LLM's stochastic step ends the moment these facts are built.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


# ─── Pass 2 — power spine ────────────────────────────────────────────

class SpineCircuit(BaseModel):
    circuit_id: str = ""
    description: str = ""
    breaker_a: int = 0
    breaker_poles: int = 1
    cable_size_mm2: float = 0.0
    cable_cores: int = 0
    num_points: int = 0
    load_type: str = "other"
    is_spare: bool = False
    notes: str = ""


class SpineDB(BaseModel):
    name: str = ""
    location: str = ""
    main_breaker_a: int = 0
    phases: int = 3
    voltage_v: int = 400
    ka_rating: float = 0.0
    enclosure_mount: str = "unknown"
    elcb_present: bool = False
    surge_protection: bool = False
    circuits: List[SpineCircuit] = Field(default_factory=list)
    confidence: float = 0.0


class Feeder(BaseModel):
    """A sub-main run between two nodes. `length_annotated` drives determinism."""
    from_source: str = ""
    to_db: str = ""
    cable_size_mm2: float = 0.0
    cable_cores: int = 4
    cable_type: str = "swa_pvc"
    earth_size_mm2: float = 0.0
    length_m: float = 0.0
    length_annotated: bool = False
    is_underground: bool = True
    confidence: float = 0.0


class IncomingSupply(BaseModel):
    supply_source: str = "unknown"
    kiosk_present: bool = False
    meter_count: int = 0
    incomer_cable_size_mm2: float = 0.0
    incomer_length_m: float = 0.0
    incomer_length_annotated: bool = False


class PowerSpine(BaseModel):
    distribution_boards: List[SpineDB] = Field(default_factory=list)
    feeders: List[Feeder] = Field(default_factory=list)
    incoming_supply: IncomingSupply = Field(default_factory=IncomingSupply)
    warnings: List[str] = Field(default_factory=list)


# ─── Pass 3 — layout takeoff ─────────────────────────────────────────

class TakeoffRoom(BaseModel):
    room_name: str = ""
    room_type: str = ""
    area_m2: float = 0.0
    served_by_db: str = ""
    ceiling_height_m: float = 0.0
    circuit_tags: List[str] = Field(default_factory=list)

    # lighting
    downlights: int = 0
    panel_lights: int = 0
    bulkheads: int = 0
    vapour_proof: int = 0
    floodlights: int = 0
    emergency_lights: int = 0
    pole_lights: int = 0
    # power
    double_sockets: int = 0
    single_sockets: int = 0
    waterproof_sockets: int = 0
    floor_sockets: int = 0
    data_outlets: int = 0
    # control
    switches_1lever: int = 0
    switches_2lever: int = 0
    switches_3lever: int = 0
    isolators: int = 0
    day_night_switches: int = 0

    confidence: float = 0.0

    _LIGHT_FIELDS = ("downlights", "panel_lights", "bulkheads", "vapour_proof",
                     "floodlights", "emergency_lights", "pole_lights")
    _OUTLET_FIELDS = ("double_sockets", "single_sockets", "waterproof_sockets",
                      "floor_sockets", "data_outlets")
    _SWITCH_FIELDS = ("switches_1lever", "switches_2lever", "switches_3lever",
                      "isolators", "day_night_switches")

    def light_points(self) -> int:
        return sum(getattr(self, f) for f in self._LIGHT_FIELDS)

    def power_points(self) -> int:
        return sum(getattr(self, f) for f in self._OUTLET_FIELDS)


class LayoutTakeoff(BaseModel):
    rooms: List[TakeoffRoom] = Field(default_factory=list)
    legend: Dict[str, str] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


# ─── Pass 1 — project context ────────────────────────────────────────

class DrawingIndexEntry(BaseModel):
    drawing_no: str = ""
    title: str = ""
    sheet_type: str = "other"


class ProjectContext(BaseModel):
    project_name: str = ""
    client_name: str = ""
    consultant_name: str = ""
    contractor_name: str = ""
    site_address: str = ""
    standard: str = ""
    revision: str = ""
    drawing_numbers: List[str] = Field(default_factory=list)
    buildings: List[str] = Field(default_factory=list)
    free_issue_items: List[str] = Field(default_factory=list)
    drawing_index: List[DrawingIndexEntry] = Field(default_factory=list)
    legend: Dict[str, str] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)


# ─── Aggregate ───────────────────────────────────────────────────────

class PdfFacts(BaseModel):
    """Everything the LLM eyes reported, merged across the drawing set."""
    context: ProjectContext = Field(default_factory=ProjectContext)
    spine: PowerSpine = Field(default_factory=PowerSpine)
    takeoff: LayoutTakeoff = Field(default_factory=LayoutTakeoff)


# ═══════════════════════════════════════════════════════════════════════
#  Deterministic parsers: tool_input dict → typed facts
# ═══════════════════════════════════════════════════════════════════════

def _s(d: Dict[str, Any], k: str, default: str = "") -> str:
    v = d.get(k, default)
    return str(v) if v is not None else default


def _i(d: Dict[str, Any], k: str, default: int = 0) -> int:
    try:
        return int(d.get(k, default))
    except (TypeError, ValueError):
        return default


def _f(d: Dict[str, Any], k: str, default: float = 0.0) -> float:
    try:
        return float(d.get(k, default))
    except (TypeError, ValueError):
        return default


def _b(d: Dict[str, Any], k: str, default: bool = False) -> bool:
    return bool(d.get(k, default))


def parse_project_context(tool_input: Dict[str, Any]) -> ProjectContext:
    return ProjectContext(
        project_name=_s(tool_input, "project_name"),
        client_name=_s(tool_input, "client_name"),
        consultant_name=_s(tool_input, "consultant_name"),
        contractor_name=_s(tool_input, "contractor_name"),
        site_address=_s(tool_input, "site_address"),
        standard=_s(tool_input, "standard"),
        revision=_s(tool_input, "revision"),
        drawing_numbers=[str(x) for x in tool_input.get("drawing_numbers", []) or []],
        buildings=[str(x) for x in tool_input.get("buildings", []) or []],
        free_issue_items=[str(x) for x in tool_input.get("free_issue_items", []) or []],
        drawing_index=[
            DrawingIndexEntry(
                drawing_no=_s(e, "drawing_no"),
                title=_s(e, "title"),
                sheet_type=_s(e, "sheet_type", "other"),
            )
            for e in tool_input.get("drawing_index", []) or []
        ],
        legend={str(k): str(v) for k, v in (tool_input.get("legend") or {}).items()},
        notes=[str(x) for x in tool_input.get("notes", []) or []],
    )


def _parse_circuit(d: Dict[str, Any]) -> SpineCircuit:
    return SpineCircuit(
        circuit_id=_s(d, "circuit_id"),
        description=_s(d, "description"),
        breaker_a=_i(d, "breaker_a"),
        breaker_poles=_i(d, "breaker_poles", 1),
        cable_size_mm2=_f(d, "cable_size_mm2"),
        cable_cores=_i(d, "cable_cores"),
        num_points=_i(d, "num_points"),
        load_type=_s(d, "load_type", "other"),
        is_spare=_b(d, "is_spare"),
        notes=_s(d, "notes"),
    )


def parse_power_spine(tool_input: Dict[str, Any]) -> PowerSpine:
    dbs = [
        SpineDB(
            name=_s(db, "name"),
            location=_s(db, "location"),
            main_breaker_a=_i(db, "main_breaker_a"),
            phases=_i(db, "phases", 3),
            voltage_v=_i(db, "voltage_v", 400),
            ka_rating=_f(db, "ka_rating"),
            enclosure_mount=_s(db, "enclosure_mount", "unknown"),
            elcb_present=_b(db, "elcb_present"),
            surge_protection=_b(db, "surge_protection"),
            circuits=[_parse_circuit(c) for c in db.get("circuits", []) or []],
            confidence=_f(db, "confidence"),
        )
        for db in tool_input.get("distribution_boards", []) or []
    ]
    feeders = [
        Feeder(
            from_source=_s(fd, "from_source"),
            to_db=_s(fd, "to_db"),
            cable_size_mm2=_f(fd, "cable_size_mm2"),
            cable_cores=_i(fd, "cable_cores", 4),
            cable_type=_s(fd, "cable_type", "swa_pvc"),
            earth_size_mm2=_f(fd, "earth_size_mm2"),
            length_m=_f(fd, "length_m"),
            length_annotated=_b(fd, "length_annotated"),
            is_underground=_b(fd, "is_underground", True),
            confidence=_f(fd, "confidence"),
        )
        for fd in tool_input.get("feeders", []) or []
    ]
    inc_d = tool_input.get("incoming_supply") or {}
    incoming = IncomingSupply(
        supply_source=_s(inc_d, "supply_source", "unknown"),
        kiosk_present=_b(inc_d, "kiosk_present"),
        meter_count=_i(inc_d, "meter_count"),
        incomer_cable_size_mm2=_f(inc_d, "incomer_cable_size_mm2"),
        incomer_length_m=_f(inc_d, "incomer_length_m"),
        incomer_length_annotated=_b(inc_d, "incomer_length_annotated"),
    )
    return PowerSpine(
        distribution_boards=dbs,
        feeders=feeders,
        incoming_supply=incoming,
        warnings=[str(w) for w in tool_input.get("extraction_warnings", []) or []],
    )


_ROOM_INT_FIELDS = (
    "downlights", "panel_lights", "bulkheads", "vapour_proof", "floodlights",
    "emergency_lights", "pole_lights", "double_sockets", "single_sockets",
    "waterproof_sockets", "floor_sockets", "data_outlets", "switches_1lever",
    "switches_2lever", "switches_3lever", "isolators", "day_night_switches",
)


def parse_layout_takeoff(tool_input: Dict[str, Any]) -> LayoutTakeoff:
    rooms: List[TakeoffRoom] = []
    for r in tool_input.get("rooms", []) or []:
        room = TakeoffRoom(
            room_name=_s(r, "room_name"),
            room_type=_s(r, "room_type"),
            area_m2=_f(r, "area_m2"),
            served_by_db=_s(r, "served_by_db"),
            ceiling_height_m=_f(r, "ceiling_height_m"),
            circuit_tags=[str(x) for x in r.get("circuit_tags", []) or []],
            confidence=_f(r, "confidence"),
            **{f: _i(r, f) for f in _ROOM_INT_FIELDS},
        )
        rooms.append(room)
    return LayoutTakeoff(
        rooms=rooms,
        legend={str(k): str(v) for k, v in (tool_input.get("legend") or {}).items()},
        warnings=[str(w) for w in tool_input.get("extraction_warnings", []) or []],
    )
