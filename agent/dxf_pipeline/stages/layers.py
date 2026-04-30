"""
Stage D2 — Layer Analysis.

Walk the document's layer table, mark electrical layers, and detect
multi-block projects (e.g. Wedela has 4 buildings → expect to see
layers tagged BLOCK_A, BLOCK_B, …).
"""

from __future__ import annotations

import re
from collections import Counter
from typing import List, Set

from ezdxf.document import Drawing

from agent.dxf_pipeline.models import DxfLayerAnalysis, LayerInfo
from core.layer_aliases import is_electrical_layer


_BLOCK_TAG_PATTERN = re.compile(r"\b(?:block|building|bldg)[-_\s]?([A-Z0-9]+)\b", re.I)


def analyse_layers(doc: Drawing) -> DxfLayerAnalysis:
    """Inspect the document's layer table; return a DxfLayerAnalysis."""

    # Count entities per layer
    per_layer_count: Counter[str] = Counter()
    for entity in doc.modelspace():
        layer_name = entity.dxf.layer if hasattr(entity.dxf, "layer") else "0"
        per_layer_count[layer_name] += 1

    layers: List[LayerInfo] = []
    electrical_layers: List[str] = []
    layers_named_electrical_with_no_blocks: List[str] = []

    for layer in doc.layers:
        name = layer.dxf.name
        is_elec = is_electrical_layer(name)
        count = per_layer_count.get(name, 0)

        info = LayerInfo(
            name=name,
            color=layer.dxf.color if hasattr(layer.dxf, "color") else 7,
            is_electrical=is_elec,
            entity_count=count,
        )
        layers.append(info)

        if is_elec:
            electrical_layers.append(name)
            if count == 0:
                layers_named_electrical_with_no_blocks.append(name)

    # Detect multi-block projects from layer names
    block_tags: Set[str] = set()
    for info in layers:
        m = _BLOCK_TAG_PATTERN.search(info.name)
        if m:
            block_tags.add(m.group(1).upper())

    return DxfLayerAnalysis(
        layers=layers,
        electrical_layers=electrical_layers,
        building_blocks_detected=sorted(block_tags),
        layers_named_electrical_with_no_blocks=layers_named_electrical_with_no_blocks,
    )
