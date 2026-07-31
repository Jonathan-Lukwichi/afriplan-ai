"""
Pass 1–4 of the DXF rebuild — recognise the electrical content of a drawing.

This is the DXF analogue of the PDF pipeline's "eyes", except it is fully
deterministic: it reads geometry, not an image. It walks the modelspace once
and produces a structured `DxfRecognition`:

  • electrical symbols — from named blocks AND from geometry (a circle on the
    lighting layer is a light), each with layer + position
  • circuit tags — text like "L1" / "DB-S3" on the wiring layers, parsed into
    (circuit_id, db_ref)
  • cable length — summed ONLY on electrical layers (walls no longer pollute
    the total), split by layer and assigned to the nearest circuit tag
  • room labels + areas — from room-name text

The single most important fix over the old extract stage: measurement and
symbol recognition happen on the ELECTRICAL layers only.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ezdxf.document import Drawing

from agent.dxf_pipeline.patterns import (
    FixtureCategory,
    FixtureSpec,
    classify_block_name,
    classify_geometry_symbol,
    is_skip_block_name,
    parse_circuit_tag,
)
from core.layer_aliases import (
    is_architectural_layer,
    is_electrical_layer,
    is_wiring_layer,
)

# Fallback spec for an unknown block sitting on an electrical layer.
_UNCLASSIFIED_ELEC = FixtureSpec("Electrical Symbol (unclassified)", FixtureCategory.OTHER, 0.0)


# ─── Result models ───────────────────────────────────────────────────

@dataclass
class RecognisedSymbol:
    canonical_name: str
    category: str
    layer: str
    x: float
    y: float
    source: str            # "block" | "geometry"
    raw_name: str = ""
    room: str = ""         # filled by the spatial pass
    building: str = ""     # filled by the spatial pass


@dataclass
class CircuitTag:
    circuit_id: Optional[str]
    db_ref: Optional[str]
    layer: str
    x: float
    y: float
    text: str


@dataclass
class RoomLabel:
    name: str
    area_m2: float
    x: float
    y: float


@dataclass
class DxfRecognition:
    units_to_metre: float = 1.0
    symbols: List[RecognisedSymbol] = field(default_factory=list)
    circuit_tags: List[CircuitTag] = field(default_factory=list)
    rooms: List[RoomLabel] = field(default_factory=list)

    cable_length_m_by_layer: Dict[str, float] = field(default_factory=dict)
    cable_length_m_by_circuit: Dict[str, float] = field(default_factory=dict)
    electrical_cable_length_m: float = 0.0

    unrecognised_blocks: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # ── convenience aggregates ──
    def symbol_counts(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for s in self.symbols:
            out[s.canonical_name] = out.get(s.canonical_name, 0) + 1
        return out

    def db_refs(self) -> List[str]:
        return sorted({t.db_ref for t in self.circuit_tags if t.db_ref})

    def circuit_ids(self) -> List[str]:
        return sorted({t.circuit_id for t in self.circuit_tags if t.circuit_id})


# ─── Units ───────────────────────────────────────────────────────────

_INSUNITS_TO_METRE = {1: 0.0254, 2: 0.3048, 4: 0.001, 5: 0.01, 6: 1.0}


def _units_to_metre(doc: Drawing) -> float:
    """
    Drawing-units → metres. Uses $INSUNITS when it is set to a real unit.
    When the drawing is 'unitless' ($INSUNITS=0) — common in Revit/ArchiCAD
    exports — infer the scale from the model extents: a building spanning
    thousands of units is almost certainly drawn in millimetres.
    """
    insunits = int(doc.header.get("$INSUNITS", 0))
    factor = _INSUNITS_TO_METRE.get(insunits, 1.0)   # unitless/unknown → 1.0 tentatively
    try:
        emax = doc.header.get("$EXTMAX", (0.0, 0.0, 0.0))
        emin = doc.header.get("$EXTMIN", (0.0, 0.0, 0.0))
        span = max(abs(emax[0] - emin[0]), abs(emax[1] - emin[1]))
    except Exception:  # noqa: BLE001
        span = 0.0
    # Sanity override: if the stated units imply an absurd building/site span
    # (> 2 km), the file mislabels its units and is really in millimetres.
    if span * factor > 2000:
        return 0.001
    # Unitless but clearly drawn large → millimetres.
    if insunits == 0 and span > 1000:
        return 0.001
    return factor


# ─── Text cleaning ───────────────────────────────────────────────────

_AREA_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*m\b")   # "186,9 m" / "12.5 m"


def _plain_text(entity) -> str:
    """Best-effort plain text from TEXT or MTEXT (strips MTEXT format codes)."""
    kind = entity.dxftype()
    if kind == "MTEXT":
        try:
            return entity.plain_text()
        except Exception:  # noqa: BLE001
            return str(getattr(entity, "text", ""))
    return str(getattr(entity.dxf, "text", ""))


def _parse_area_m2(text: str) -> float:
    m = _AREA_RE.search(text)
    if not m:
        return 0.0
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return 0.0


# ─── Geometry helpers ────────────────────────────────────────────────

def _line_len(e) -> float:
    return math.hypot(e.dxf.end.x - e.dxf.start.x, e.dxf.end.y - e.dxf.start.y)


def _poly_len(pts) -> float:
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def _arc_len(e) -> float:
    ang = abs(e.dxf.end_angle - e.dxf.start_angle) % 360.0
    return math.radians(ang) * float(e.dxf.radius)


def _entity_midpoint(e) -> Optional[Tuple[float, float]]:
    k = e.dxftype()
    try:
        if k == "LINE":
            return ((e.dxf.start.x + e.dxf.end.x) / 2, (e.dxf.start.y + e.dxf.end.y) / 2)
        if k == "LWPOLYLINE":
            pts = [(p[0], p[1]) for p in e.get_points("xy")]
            return pts[len(pts) // 2] if pts else None
        if k == "ARC":
            return (e.dxf.center.x, e.dxf.center.y)
    except Exception:  # noqa: BLE001
        return None
    return None


# ─── The recognition pass ────────────────────────────────────────────

def recognise(doc: Drawing) -> DxfRecognition:
    """Walk the modelspace once and recognise all electrical content."""
    u2m = _units_to_metre(doc)
    rec = DxfRecognition(units_to_metre=u2m)
    msp = doc.modelspace()

    room_layer_re = re.compile(r"room\s*name|room", re.I)
    wire_segments: List[Tuple[float, Tuple[float, float]]] = []  # (length_m, midpoint)

    for e in msp:
        try:
            kind = e.dxftype()
            layer = getattr(e.dxf, "layer", "0")
            elec = is_electrical_layer(layer)
            arch = is_architectural_layer(layer)
            wiring = is_wiring_layer(layer)

            # ── INSERT: named block symbol ──
            if kind == "INSERT":
                raw = e.dxf.name
                spec = classify_block_name(raw)        # name wins, even on a wrong layer
                if spec is None:
                    if arch or is_skip_block_name(raw):
                        continue                       # other-trade block → ignore
                    if elec:
                        spec = _UNCLASSIFIED_ELEC      # unknown, but on an electrical layer
                if spec is not None:
                    rec.symbols.append(RecognisedSymbol(
                        canonical_name=spec.canonical_name, category=spec.category.value,
                        layer=layer, x=e.dxf.insert.x, y=e.dxf.insert.y,
                        source="block", raw_name=raw,
                    ))
                else:
                    rec.unrecognised_blocks.append(raw)

            # ── CIRCLE / ARC: geometry symbol + wiring loops ──
            elif kind in ("CIRCLE", "ARC"):
                spec = classify_geometry_symbol(kind, layer)
                if spec is not None and not wiring:
                    rec.symbols.append(RecognisedSymbol(
                        canonical_name=spec.canonical_name, category=spec.category.value,
                        layer=layer, x=e.dxf.center.x, y=e.dxf.center.y, source="geometry",
                    ))
                # arcs on WIRING layers are cable loops → measure
                if kind == "ARC" and wiring:
                    length_m = _arc_len(e) * u2m
                    rec.cable_length_m_by_layer[layer] = rec.cable_length_m_by_layer.get(layer, 0.0) + length_m
                    rec.electrical_cable_length_m += length_m
                    mp = _entity_midpoint(e)
                    if mp:
                        wire_segments.append((length_m, mp))

            # ── TEXT / MTEXT: circuit tags + room labels ──
            elif kind in ("TEXT", "MTEXT"):
                text = _plain_text(e).strip()
                if not text:
                    continue
                px = getattr(e.dxf, "insert", None)
                x = px.x if px else 0.0
                y = px.y if px else 0.0
                if elec:
                    cid, db = parse_circuit_tag(text)
                    if cid or db:
                        rec.circuit_tags.append(CircuitTag(
                            circuit_id=cid, db_ref=db, layer=layer, x=x, y=y, text=text,
                        ))
                if room_layer_re.search(layer):
                    rec.rooms.append(RoomLabel(name=text, area_m2=_parse_area_m2(text), x=x, y=y))

            # ── LINE / LWPOLYLINE: cable ONLY on wiring layers ──
            elif kind in ("LINE", "LWPOLYLINE"):
                if not wiring:
                    continue          # symbol line-work on a non-wiring electrical layer is NOT cable
                if kind == "LINE":
                    length_m = _line_len(e) * u2m
                else:
                    pts = [(p[0], p[1]) for p in e.get_points("xy")]
                    length_m = _poly_len(pts) * u2m
                rec.cable_length_m_by_layer[layer] = rec.cable_length_m_by_layer.get(layer, 0.0) + length_m
                rec.electrical_cable_length_m += length_m
                mp = _entity_midpoint(e)
                if mp:
                    wire_segments.append((length_m, mp))

        except Exception as ex:  # noqa: BLE001 — never crash on a malformed entity
            rec.warnings.append(f"Skipped {e.dxftype()}: {ex}")

    _assign_cable_to_circuits(rec, wire_segments)
    rec.electrical_cable_length_m = round(rec.electrical_cable_length_m, 3)
    rec.cable_length_m_by_layer = {k: round(v, 3) for k, v in rec.cable_length_m_by_layer.items()}
    rec.unrecognised_blocks = sorted(set(rec.unrecognised_blocks))
    return rec


def _assign_cable_to_circuits(rec: DxfRecognition, wire_segments) -> None:
    """Assign each wire segment's length to its nearest circuit tag (by midpoint)."""
    tags = [t for t in rec.circuit_tags if t.circuit_id]
    if not tags:
        rec.cable_length_m_by_circuit = {"unassigned": round(rec.electrical_cable_length_m, 3)}
        return
    for length_m, (mx, my) in wire_segments:
        nearest = min(tags, key=lambda t: math.hypot(t.x - mx, t.y - my))
        key = nearest.circuit_id or "unassigned"
        rec.cable_length_m_by_circuit[key] = rec.cable_length_m_by_circuit.get(key, 0.0) + length_m
    rec.cable_length_m_by_circuit = {k: round(v, 3) for k, v in rec.cable_length_m_by_circuit.items()}
