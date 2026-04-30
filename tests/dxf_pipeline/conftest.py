"""
DXF pipeline test fixtures.

Builds synthetic DXFs in memory so tests don't depend on third-party
files. The PDF pipeline conftest is intentionally separate; per the
blueprint independence rule, neither test suite touches the other's
fixtures.
"""

from __future__ import annotations

import io
from typing import Iterable, Tuple

import ezdxf
import pytest


def _build_synthetic_dxf(
    *,
    inserts: Iterable[Tuple[str, str, int]],
    polylines_mm: Iterable[Tuple[str, list[Tuple[float, float]]]] = (),
    layer_0_circles: int = 0,
    extra_blocks: Iterable[str] = (),
    extra_layers: Iterable[str] = (),
    insunits: int = 4,                    # 4 = mm
) -> bytes:
    """
    Build a fresh in-memory DXF.

    inserts:        sequence of (block_name, layer_name, count) — defines
                    block definitions and the number of INSERTs to emit
    polylines_mm:   sequence of (layer_name, [(x,y), ...]) — emits LWPOLYLINE
    layer_0_circles: number of orphan circles on layer 0
    extra_blocks:   block names whose definitions we add but don't insert
    extra_layers:   layer names to register without entities
    insunits:       AutoCAD INSUNITS value (4=mm, 6=metres, etc.)
    """
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = insunits

    # Block definitions
    seen_blocks: set[str] = set()
    for block_name, _, _ in inserts:
        if block_name in seen_blocks:
            continue
        blk = doc.blocks.new(name=block_name)
        blk.add_circle((0, 0), radius=50)
        seen_blocks.add(block_name)

    for block_name in extra_blocks:
        if block_name not in seen_blocks:
            blk = doc.blocks.new(name=block_name)
            blk.add_circle((0, 0), radius=10)
            seen_blocks.add(block_name)

    # Layer registration
    seen_layers: set[str] = set()
    for _, layer_name, _ in inserts:
        if layer_name not in seen_layers and layer_name not in doc.layers:
            doc.layers.add(name=layer_name, color=1)
            seen_layers.add(layer_name)
    for layer_name in extra_layers:
        if layer_name not in seen_layers and layer_name not in doc.layers:
            doc.layers.add(name=layer_name, color=1)
            seen_layers.add(layer_name)

    msp = doc.modelspace()

    # Inserts
    for block_name, layer_name, count in inserts:
        for i in range(count):
            msp.add_blockref(
                block_name,
                insert=(i * 1000, 0),
                dxfattribs={"layer": layer_name},
            )

    # Polylines
    for layer_name, points in polylines_mm:
        msp.add_lwpolyline(points, dxfattribs={"layer": layer_name})

    # Layer 0 circles (orphans)
    for i in range(layer_0_circles):
        msp.add_circle((i * 100, 0), radius=30, dxfattribs={"layer": "0"})

    buf = io.StringIO()
    doc.write(buf)
    return buf.getvalue().encode("utf-8")


@pytest.fixture
def small_dxf_bytes() -> bytes:
    """Tiny DXF with one of each common fixture."""
    return _build_synthetic_dxf(
        inserts=[
            ("DL",  "ELEC_LIGHTING", 4),
            ("DS",  "ELEC_POWER",    3),
            ("SW2", "ELEC_SWITCH",   2),
            ("EM",  "ELEC_SAFETY",   1),
        ],
        polylines_mm=[
            ("ELEC_LIGHTING", [(0, 0), (1000, 0), (1000, 1000)]),  # 2 m total
        ],
        layer_0_circles=0,
    )


@pytest.fixture
def realistic_dxf_bytes() -> bytes:
    """Larger DXF: matches the pattern of a small commercial DXF."""
    return _build_synthetic_dxf(
        inserts=[
            ("DL",       "ELEC_LIGHTING", 24),
            ("PANEL",    "ELEC_LIGHTING", 8),
            ("EM",       "ELEC_SAFETY",   6),
            ("EXIT",     "ELEC_SAFETY",   4),
            ("DS",       "ELEC_POWER",    20),
            ("SS",       "ELEC_POWER",    8),
            ("WP",       "ELEC_POWER",    4),
            ("SW1",      "ELEC_SWITCH",   8),
            ("SW2",      "ELEC_SWITCH",   12),
            ("DATA",     "ELEC_DATA",     16),
            ("DB",       "ELEC_DB",       2),
        ],
        polylines_mm=[
            ("ELEC_LIGHTING", [(0, 0), (5000, 0), (5000, 3000)]),         # 8 m
            ("ELEC_POWER",    [(0, 0), (3000, 0), (3000, 4000)]),         # 7 m
            ("ELEC_DATA",     [(0, 0), (10000, 0), (10000, 5000)]),       # 15 m
        ],
        layer_0_circles=2,
    )


@pytest.fixture
def dxf_with_unrecognised_blocks() -> bytes:
    """DXF where most blocks aren't electrical — coverage should be low."""
    return _build_synthetic_dxf(
        inserts=[
            ("DL",       "ELEC_LIGHTING",  2),
            ("Wall_001", "A-WALL",         8),
            ("Door_007", "A-WALL",         6),
            ("Some_Junk","MISC",           4),
        ],
    )


@pytest.fixture
def dxf_in_metres() -> bytes:
    """DXF whose units are metres, not mm."""
    return _build_synthetic_dxf(
        inserts=[("DL", "ELEC_LIGHTING", 3)],
        polylines_mm=[("ELEC_LIGHTING", [(0, 0), (5, 0)])],   # in metres now: 5m
        insunits=6,                                           # 6 = metres
    )
