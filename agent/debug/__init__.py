"""
AfriPlan Electrical - Debug Utilities

Tools for debugging extraction pipeline:
- Save page images with region overlays
- Export intermediate results
- Visualize classification decisions
"""

from .artifacts import DebugConfig, DebugArtifactSaver, save_debug_artifacts
from .overlays import (
    draw_region_overlay, draw_text_blocks_overlay,
    draw_classification_label, create_comparison_image
)

__all__ = [
    "DebugConfig",
    "DebugArtifactSaver",
    "save_debug_artifacts",
    "draw_region_overlay",
    "draw_text_blocks_overlay",
    "draw_classification_label",
    "create_comparison_image",
]
