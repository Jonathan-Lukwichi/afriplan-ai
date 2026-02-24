"""
AfriPlan Electrical - Region Cropping Stage

Detect and crop key regions on electrical drawing pages:
- Title block (typically bottom-right)
- Legend (often right side or lower-right)
- Schedule/table area (SLD circuit tables)
- Main drawing area (largest remaining area)
- Notes area (optional)

Uses hybrid approach:
1. Heuristic defaults based on common drawing layouts
2. Text density analysis
3. OpenCV contour/line detection (optional)

No AI/cloud APIs used.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass

try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

from agent.models import (
    BoundingBox, PageRegions, DetectionMethod, ExtractionWarning, Severity
)
from agent.parsers.pdf_text import TextBlock

logger = logging.getLogger(__name__)


# ============================================================================
# HEURISTIC CONSTANTS (for SA engineering drawings)
# ============================================================================

# Title block typically in bottom-right corner
# Usually ~15-20% of page width, ~10-15% of page height
TITLE_BLOCK_HEURISTIC = {
    "x0_pct": 0.70,  # Start at 70% from left
    "y0_pct": 0.85,  # Start at 85% from top
    "x1_pct": 1.00,  # End at right edge
    "y1_pct": 1.00,  # End at bottom edge
}

# Legend often on right side
LEGEND_HEURISTIC = {
    "x0_pct": 0.75,  # Start at 75% from left
    "y0_pct": 0.30,  # Start at 30% from top
    "x1_pct": 1.00,  # End at right edge
    "y1_pct": 0.80,  # End at 80% from top (above title block)
}

# Schedule/table area (SLD) - typically center-right
SCHEDULE_HEURISTIC = {
    "x0_pct": 0.40,  # Start at 40% from left
    "y0_pct": 0.10,  # Start at 10% from top
    "x1_pct": 0.95,  # End at 95% from left
    "y1_pct": 0.85,  # End at 85% from top
}

# Main drawing area - largest remaining space
MAIN_DRAWING_HEURISTIC = {
    "x0_pct": 0.02,  # Small margin from left
    "y0_pct": 0.02,  # Small margin from top
    "x1_pct": 0.70,  # End at 70% (before legend/title)
    "y1_pct": 0.90,  # End at 90% (before title block)
}

# Notes area - often bottom-left
NOTES_HEURISTIC = {
    "x0_pct": 0.02,  # Small margin from left
    "y0_pct": 0.85,  # Start at 85% from top
    "x1_pct": 0.40,  # End at 40% from left
    "y1_pct": 0.98,  # Near bottom
}

# Keywords for region detection
TITLE_BLOCK_KEYWORDS = [
    "drawn", "checked", "approved", "date", "rev", "scale",
    "drawing no", "drwg no", "project", "client", "consultant"
]

LEGEND_KEYWORDS = [
    "legend", "key", "symbol", "switch", "socket", "light",
    "fixture", "note:", "notes:"
]

SCHEDULE_KEYWORDS = [
    "circuit", "wattage", "wire size", "breaker", "description",
    "load", "cable", "points", "no.", "type"
]


@dataclass
class RegionCandidate:
    """A candidate region with confidence score."""
    name: str
    bbox: BoundingBox
    confidence: float
    method: DetectionMethod
    keywords_found: List[str]


def detect_page_regions(
    page_image: Optional[Any] = None,
    text_blocks: Optional[List[TextBlock]] = None,
    page_width: int = 0,
    page_height: int = 0,
    enable_opencv: bool = True,
    fallback_to_heuristic: bool = True,
) -> PageRegions:
    """
    Detect key regions on a page.

    Args:
        page_image: Page image as numpy array (for OpenCV)
        text_blocks: List of positioned text blocks
        page_width: Page width in pixels
        page_height: Page height in pixels
        enable_opencv: Use OpenCV for contour detection
        fallback_to_heuristic: Fall back to heuristic if detection fails

    Returns:
        PageRegions with detected bounding boxes
    """
    result = PageRegions()
    warnings = []

    if page_width == 0 or page_height == 0:
        logger.warning("Page dimensions not provided")
        result.warnings.append(ExtractionWarning(
            code="NO_DIMENSIONS",
            message="Page dimensions not provided",
            severity=Severity.WARNING,
            source_stage="crop",
        ))
        return result

    # Strategy 1: Keyword-based detection (most reliable)
    if text_blocks:
        keyword_regions = _detect_regions_by_keywords(
            text_blocks, page_width, page_height
        )

        if keyword_regions.get("title_block"):
            result.title_block = keyword_regions["title_block"]
            result.all_regions["title_block_keyword"] = keyword_regions["title_block"]

        if keyword_regions.get("legend"):
            result.legend = keyword_regions["legend"]
            result.all_regions["legend_keyword"] = keyword_regions["legend"]

        if keyword_regions.get("schedule"):
            result.schedule = keyword_regions["schedule"]
            result.all_regions["schedule_keyword"] = keyword_regions["schedule"]

    # Strategy 2: OpenCV contour detection (for table boundaries)
    if enable_opencv and HAS_OPENCV and page_image is not None:
        try:
            opencv_regions = _detect_regions_by_opencv(
                page_image, page_width, page_height
            )

            # Use OpenCV results if better than keyword results
            for name, bbox in opencv_regions.items():
                existing = result.all_regions.get(f"{name}_keyword")
                if not existing or bbox.confidence > existing.confidence:
                    result.all_regions[f"{name}_opencv"] = bbox

                    if name == "schedule" and (not result.schedule or bbox.confidence > result.schedule.confidence):
                        result.schedule = bbox

        except Exception as e:
            logger.warning(f"OpenCV detection failed: {e}")
            warnings.append(ExtractionWarning(
                code="OPENCV_FAILED",
                message=f"OpenCV detection failed: {e}",
                severity=Severity.INFO,
                source_stage="crop",
            ))

    # Strategy 3: Fallback to heuristic defaults
    if fallback_to_heuristic:
        if not result.title_block:
            result.title_block = _heuristic_bbox(
                TITLE_BLOCK_HEURISTIC, page_width, page_height, "title_block"
            )
            result.all_regions["title_block_heuristic"] = result.title_block

        if not result.legend:
            result.legend = _heuristic_bbox(
                LEGEND_HEURISTIC, page_width, page_height, "legend"
            )
            result.all_regions["legend_heuristic"] = result.legend

        if not result.schedule:
            result.schedule = _heuristic_bbox(
                SCHEDULE_HEURISTIC, page_width, page_height, "schedule"
            )
            result.all_regions["schedule_heuristic"] = result.schedule

        if not result.main_drawing:
            result.main_drawing = _heuristic_bbox(
                MAIN_DRAWING_HEURISTIC, page_width, page_height, "main_drawing"
            )
            result.all_regions["main_drawing_heuristic"] = result.main_drawing

        if not result.notes:
            result.notes = _heuristic_bbox(
                NOTES_HEURISTIC, page_width, page_height, "notes"
            )
            result.all_regions["notes_heuristic"] = result.notes

    # Set detection status
    result.detection_successful = (
        result.title_block is not None or
        result.legend is not None or
        result.schedule is not None
    )

    # Determine method used
    methods_used = set()
    for key in result.all_regions:
        if "keyword" in key:
            methods_used.add("keyword")
        elif "opencv" in key:
            methods_used.add("opencv")
        elif "heuristic" in key:
            methods_used.add("heuristic")

    result.method_used = "+".join(sorted(methods_used)) or "none"
    result.warnings = warnings

    return result


def _detect_regions_by_keywords(
    text_blocks: List[TextBlock],
    page_width: int,
    page_height: int,
) -> Dict[str, BoundingBox]:
    """
    Detect regions by finding keyword clusters.
    """
    regions = {}

    # Convert text blocks to proper format if needed
    blocks = []
    for tb in text_blocks:
        if hasattr(tb, 'text'):
            blocks.append(tb)

    if not blocks:
        return regions

    # Find title block keywords
    title_matches = _find_keyword_cluster(
        blocks, TITLE_BLOCK_KEYWORDS, page_width, page_height
    )
    if title_matches:
        regions["title_block"] = title_matches

    # Find legend keywords
    legend_matches = _find_keyword_cluster(
        blocks, LEGEND_KEYWORDS, page_width, page_height
    )
    if legend_matches:
        regions["legend"] = legend_matches

    # Find schedule keywords
    schedule_matches = _find_keyword_cluster(
        blocks, SCHEDULE_KEYWORDS, page_width, page_height
    )
    if schedule_matches:
        regions["schedule"] = schedule_matches

    return regions


def _find_keyword_cluster(
    blocks: List[TextBlock],
    keywords: List[str],
    page_width: int,
    page_height: int,
    expansion: float = 50.0,  # Expand bbox by this many pixels
) -> Optional[BoundingBox]:
    """
    Find a cluster of blocks containing keywords and return bounding box.
    """
    matching_blocks = []

    for block in blocks:
        text_lower = block.text.lower() if hasattr(block, 'text') else ""
        for kw in keywords:
            if kw in text_lower:
                matching_blocks.append(block)
                break

    if len(matching_blocks) < 2:
        return None

    # Calculate bounding box of all matching blocks
    x0 = min(b.x0 for b in matching_blocks if hasattr(b, 'x0'))
    y0 = min(b.y0 for b in matching_blocks if hasattr(b, 'y0'))
    x1 = max(b.x1 for b in matching_blocks if hasattr(b, 'x1'))
    y1 = max(b.y1 for b in matching_blocks if hasattr(b, 'y1'))

    # Expand bbox
    x0 = max(0, x0 - expansion)
    y0 = max(0, y0 - expansion)
    x1 = min(page_width, x1 + expansion)
    y1 = min(page_height, y1 + expansion)

    bbox = BoundingBox(
        x0=x0, y0=y0, x1=x1, y1=y1,
        page_width=page_width,
        page_height=page_height,
        detection_method=DetectionMethod.KEYWORD_BBOX,
        confidence=min(1.0, len(matching_blocks) / 5.0),  # More matches = higher confidence
    )
    bbox.normalize()

    return bbox


def _detect_regions_by_opencv(
    page_image: Any,
    page_width: int,
    page_height: int,
) -> Dict[str, BoundingBox]:
    """
    Detect table/schedule regions using OpenCV line detection.
    """
    if not HAS_OPENCV:
        return {}

    regions = {}

    try:
        # Convert to grayscale if needed
        if len(page_image.shape) == 3:
            gray = cv2.cvtColor(page_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = page_image

        # Detect edges
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Detect lines
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=100,
            minLineLength=50,
            maxLineGap=10
        )

        if lines is None:
            return regions

        # Find horizontal and vertical lines
        h_lines = []
        v_lines = []

        for line in lines:
            x1, y1, x2, y2 = line[0]

            # Horizontal line (small y difference)
            if abs(y2 - y1) < 10:
                h_lines.append((min(x1, x2), y1, max(x1, x2), y2))

            # Vertical line (small x difference)
            if abs(x2 - x1) < 10:
                v_lines.append((x1, min(y1, y2), x2, max(y1, y2)))

        # Find table regions (areas bounded by lines)
        if h_lines and v_lines:
            # Find intersections to detect table cells
            # For now, use the extent of detected lines as schedule region

            all_x = [l[0] for l in h_lines] + [l[2] for l in h_lines]
            all_y = [l[1] for l in v_lines] + [l[3] for l in v_lines]

            if all_x and all_y:
                x0 = min(all_x)
                x1 = max(all_x)
                y0 = min(all_y)
                y1 = max(all_y)

                # Only consider it a schedule if it's a reasonable size
                width_pct = (x1 - x0) / page_width
                height_pct = (y1 - y0) / page_height

                if 0.2 < width_pct < 0.8 and 0.1 < height_pct < 0.7:
                    bbox = BoundingBox(
                        x0=x0, y0=y0, x1=x1, y1=y1,
                        page_width=page_width,
                        page_height=page_height,
                        detection_method=DetectionMethod.CONTOUR_DETECTED,
                        confidence=0.7,
                    )
                    bbox.normalize()
                    regions["schedule"] = bbox

    except Exception as e:
        logger.warning(f"OpenCV region detection error: {e}")

    return regions


def _heuristic_bbox(
    heuristic: Dict[str, float],
    page_width: int,
    page_height: int,
    region_name: str,
) -> BoundingBox:
    """
    Create a bounding box from heuristic percentages.
    """
    bbox = BoundingBox(
        x0=heuristic["x0_pct"] * page_width,
        y0=heuristic["y0_pct"] * page_height,
        x1=heuristic["x1_pct"] * page_width,
        y1=heuristic["y1_pct"] * page_height,
        page_width=page_width,
        page_height=page_height,
        detection_method=DetectionMethod.DEFAULT_HEURISTIC,
        confidence=0.3,  # Low confidence for heuristics
    )
    bbox.normalize()
    return bbox


def crop_region(
    page_image: Any,
    bbox: BoundingBox,
) -> Optional[Any]:
    """
    Crop a region from a page image.

    Args:
        page_image: Page image as numpy array
        bbox: Bounding box to crop

    Returns:
        Cropped image as numpy array
    """
    if page_image is None:
        return None

    try:
        x0, y0, x1, y1 = int(bbox.x0), int(bbox.y0), int(bbox.x1), int(bbox.y1)
        return page_image[y0:y1, x0:x1]
    except Exception as e:
        logger.warning(f"Error cropping region: {e}")
        return None


def get_text_in_region(
    text_blocks: List[TextBlock],
    bbox: BoundingBox,
) -> List[TextBlock]:
    """
    Get text blocks within a bounding box.

    Args:
        text_blocks: All text blocks on page
        bbox: Region bounding box

    Returns:
        Text blocks within the region
    """
    result = []

    for block in text_blocks:
        # Check if block center is within bbox
        if hasattr(block, 'x0') and hasattr(block, 'y0'):
            center_x = (block.x0 + block.x1) / 2 if hasattr(block, 'x1') else block.x0
            center_y = (block.y0 + block.y1) / 2 if hasattr(block, 'y1') else block.y0

            if (bbox.x0 <= center_x <= bbox.x1 and
                bbox.y0 <= center_y <= bbox.y1):
                result.append(block)

    return result
