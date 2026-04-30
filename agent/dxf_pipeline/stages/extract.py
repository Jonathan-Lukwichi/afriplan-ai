"""
Stage D3 — Extract.

Walk the model space once, classify each entity, and return a
DxfExtraction. Block names are mapped via patterns.py; everything else
is recorded as raw geometry for downstream evaluation.

This is the deterministic core. Same DXF in → same extraction out.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Iterable, List, Tuple

from ezdxf.document import Drawing
from ezdxf.entities import (
    DXFEntity,
    Insert,
    Line,
    LWPolyline,
    Polyline,
    Circle,
    Text,
    MText,
)

from agent.dxf_pipeline.models import (
    DxfBlock,
    DxfCircle,
    DxfExtraction,
    DxfPolyline,
    DxfText,
    LayerInfo,
    Point2D,
)
from agent.dxf_pipeline.patterns import classify_block_name, is_skip_block_name


def _polyline_length_units(points: Iterable[Tuple[float, float]]) -> float:
    """Sum of segment lengths along a polyline in raw drawing units."""
    pts = list(points)
    if len(pts) < 2:
        return 0.0
    total = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        total += math.hypot(x2 - x1, y2 - y1)
    return total


def _line_length_units(start: tuple[float, float], end: tuple[float, float]) -> float:
    return math.hypot(end[0] - start[0], end[1] - start[1])


def extract(
    doc: Drawing,
    units_to_metre: float,
    layer_index: List[LayerInfo],
) -> DxfExtraction:
    """
    Walk the modelspace, classify entities, return DxfExtraction.

    `units_to_metre` converts drawing units → metres for polyline lengths.
    `layer_index` is the LayerInfo list from stage D2 (carried through).
    """
    blocks: List[DxfBlock] = []
    texts: List[DxfText] = []
    polylines: List[DxfPolyline] = []
    circles_layer_0: List[DxfCircle] = []
    warnings: List[str] = []

    block_count_by_canonical: Counter[str] = Counter()
    fixture_count_by_category: Counter[str] = Counter()
    unrecognised: Counter[str] = Counter()

    total_polyline_length_m = 0.0

    for entity in doc.modelspace():
        try:
            kind = entity.dxftype()

            # ── INSERT (block reference) ─────────────────────────────
            if kind == "INSERT":
                ins: Insert = entity  # type: ignore[assignment]
                raw_name = ins.dxf.name

                # Skip architectural / furniture blocks entirely — they are
                # not part of the recognise-vs-unrecognise calculation.
                if is_skip_block_name(raw_name):
                    continue

                spec = classify_block_name(raw_name)

                pos = (ins.dxf.insert.x, ins.dxf.insert.y)
                rotation = float(getattr(ins.dxf, "rotation", 0.0))

                block = DxfBlock(
                    block_name=raw_name.lower().strip(),
                    raw_block_name=raw_name,
                    layer=ins.dxf.layer,
                    position=Point2D(x=pos[0], y=pos[1]),
                    rotation_deg=rotation,
                    fixture_canonical=spec.canonical_name if spec else None,
                    fixture_category=spec.category.value if spec else None,
                    recognised=spec is not None,
                )
                blocks.append(block)

                if spec is not None:
                    block_count_by_canonical[spec.canonical_name] += 1
                    fixture_count_by_category[spec.category.value] += 1
                else:
                    unrecognised[raw_name] += 1

            # ── TEXT / MTEXT ─────────────────────────────────────────
            elif kind in ("TEXT", "MTEXT"):
                t = entity  # type: ignore[assignment]
                if isinstance(t, MText):
                    text_value = t.text
                    pos = (t.dxf.insert.x, t.dxf.insert.y)
                    height = float(getattr(t.dxf, "char_height", 0.0))
                else:
                    text_value = t.dxf.text  # type: ignore[union-attr]
                    pos = (t.dxf.insert.x, t.dxf.insert.y)  # type: ignore[union-attr]
                    height = float(getattr(t.dxf, "height", 0.0))

                texts.append(
                    DxfText(
                        text=str(text_value),
                        layer=t.dxf.layer,
                        position=Point2D(x=pos[0], y=pos[1]),
                        height=height,
                    )
                )

            # ── LINE ─────────────────────────────────────────────────
            elif kind == "LINE":
                line: Line = entity  # type: ignore[assignment]
                length_units = _line_length_units(
                    (line.dxf.start.x, line.dxf.start.y),
                    (line.dxf.end.x, line.dxf.end.y),
                )
                length_m = length_units * units_to_metre
                polylines.append(
                    DxfPolyline(
                        layer=line.dxf.layer,
                        length_m=length_m,
                        point_count=2,
                        is_closed=False,
                    )
                )
                total_polyline_length_m += length_m

            # ── LWPOLYLINE / POLYLINE ────────────────────────────────
            elif kind == "LWPOLYLINE":
                pl: LWPolyline = entity  # type: ignore[assignment]
                pts = [(p[0], p[1]) for p in pl.get_points("xy")]
                length_m = _polyline_length_units(pts) * units_to_metre
                polylines.append(
                    DxfPolyline(
                        layer=pl.dxf.layer,
                        length_m=length_m,
                        point_count=len(pts),
                        is_closed=bool(pl.closed),
                    )
                )
                total_polyline_length_m += length_m

            elif kind == "POLYLINE":
                pl2: Polyline = entity  # type: ignore[assignment]
                pts = [(v.dxf.location.x, v.dxf.location.y) for v in pl2.vertices]
                length_m = _polyline_length_units(pts) * units_to_metre
                polylines.append(
                    DxfPolyline(
                        layer=pl2.dxf.layer,
                        length_m=length_m,
                        point_count=len(pts),
                        is_closed=bool(pl2.is_closed),
                    )
                )
                total_polyline_length_m += length_m

            # ── CIRCLE ───────────────────────────────────────────────
            elif kind == "CIRCLE":
                c: Circle = entity  # type: ignore[assignment]
                if c.dxf.layer == "0":
                    circles_layer_0.append(
                        DxfCircle(
                            layer=c.dxf.layer,
                            center=Point2D(x=c.dxf.center.x, y=c.dxf.center.y),
                            radius=float(c.dxf.radius),
                        )
                    )

            # other entity types ignored — they don't carry electrical data

        except Exception as e:  # noqa: BLE001 — defensive against malformed entities
            warnings.append(f"Skipped {entity.dxftype()}: {e}")

    return DxfExtraction(
        layers=layer_index,
        blocks=blocks,
        texts=texts,
        polylines=polylines,
        circles_layer_0=circles_layer_0,
        block_counts_by_type=dict(block_count_by_canonical),
        raw_block_names_unrecognised=sorted(unrecognised.keys()),
        fixture_counts_by_category=dict(fixture_count_by_category),
        total_polyline_length_m=total_polyline_length_m,
        extraction_warnings=warnings,
    )
