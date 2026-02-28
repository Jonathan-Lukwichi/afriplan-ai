"""
AfriPlan AI v5 — Table Zone Detector (OpenCV)
===============================================
Addresses the critic's key fix: "Split multi-DB page can't stay a placeholder."

Uses deterministic computer vision to find rectangular table regions on SLD pages:
  1. Binarize with adaptive threshold
  2. Detect long horizontal/vertical lines (morphological operations)
  3. Find rectangular table regions from line intersections
  4. Cluster into 1/2/4 DB zones
  
Then extraction runs PER DETECTED ZONE, making retries cheaper 
(re-run only the failed zone).

This is the cheap, deterministic gate BEFORE the expensive LLM call.
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

from PIL import Image


@dataclass
class TableZone:
    """A detected rectangular table region on an SLD page."""
    x0: int              # pixel coordinates in the input image
    y0: int
    x1: int
    y1: int
    zone_index: int      # 0, 1, 2, 3 (for multi-DB pages)
    confidence: float    # How likely this is a real table region
    
    # Cropped image of just this zone
    image_b64: str = ""
    
    # Optional: detected DB label near this zone
    db_label_hint: str = ""
    
    @property
    def width(self) -> int:
        return self.x1 - self.x0
    
    @property
    def height(self) -> int:
        return self.y1 - self.y0
    
    @property
    def area(self) -> int:
        return self.width * self.height
    
    @property
    def center(self) -> Tuple[int, int]:
        return ((self.x0 + self.x1) // 2, (self.y0 + self.y1) // 2)


def detect_table_zones(
    image_b64: str,
    min_table_width_pct: float = 0.25,
    min_table_height_pct: float = 0.10,
    max_zones: int = 4,
) -> List[TableZone]:
    """
    Detect table regions on an SLD page crop.
    
    Algorithm:
    1. Convert to grayscale and binarize (adaptive threshold)
    2. Use morphological operations to detect long horizontal and vertical lines
    3. Combine line masks to find rectangular intersections
    4. Find contours of combined regions
    5. Filter by minimum size (tables are >25% width, >10% height)
    6. Cluster into zones
    
    Falls back to full-image single zone if OpenCV isn't available
    or no clear table boundaries are found.
    
    Args:
        image_b64: Base64 PNG of the schedule region (or full SLD page)
        min_table_width_pct: Minimum zone width as fraction of image width
        min_table_height_pct: Minimum zone height as fraction of image height
        max_zones: Maximum number of zones to return (typically 1-4)
    
    Returns:
        List of TableZone objects, each containing a cropped image
    """
    if not HAS_OPENCV:
        return _fallback_single_zone(image_b64)
    
    try:
        # Decode image
        img_bytes = base64.b64decode(image_b64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return _fallback_single_zone(image_b64)
        
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Step 1: Adaptive threshold (handles varying contrast across page)
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=15,
            C=10,
        )
        
        # Step 2: Detect horizontal lines
        # Kernel width = 20% of image width (catches table borders)
        h_kernel_len = max(w // 5, 50)
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_kernel_len, 1))
        h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel, iterations=2)
        
        # Step 3: Detect vertical lines
        v_kernel_len = max(h // 10, 30)
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_kernel_len))
        v_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel, iterations=2)
        
        # Step 4: Combine to get grid structure
        combined = cv2.add(h_lines, v_lines)
        
        # Dilate to connect nearby line fragments
        dilate_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        combined = cv2.dilate(combined, dilate_kernel, iterations=3)
        
        # Step 5: Find contours
        contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Step 6: Filter by size
        min_w = int(w * min_table_width_pct)
        min_h = int(h * min_table_height_pct)
        
        candidate_rects: List[Tuple[int, int, int, int]] = []
        for contour in contours:
            cx, cy, cw, ch = cv2.boundingRect(contour)
            if cw >= min_w and ch >= min_h:
                candidate_rects.append((cx, cy, cx + cw, cy + ch))
        
        if not candidate_rects:
            # No clear table boundaries found — try alternative: find dense regions
            zones = _detect_by_density(gray, w, h, min_w, min_h)
            if zones:
                return _crop_zones(img, zones, image_b64)
            return _fallback_single_zone(image_b64)
        
        # Step 7: Merge overlapping rectangles
        merged = _merge_overlapping_rects(candidate_rects, overlap_threshold=0.3)
        
        # Step 8: Sort by position (top-left to bottom-right)
        merged.sort(key=lambda r: (r[1], r[0]))  # Sort by y first, then x
        
        # Limit to max_zones
        merged = merged[:max_zones]
        
        # Step 9: Create zones with cropped images
        return _crop_zones(img, merged, image_b64)
        
    except Exception as e:
        # Any OpenCV error → fall back to single zone
        return _fallback_single_zone(image_b64)


def _detect_by_density(
    gray: np.ndarray,
    w: int, h: int,
    min_w: int, min_h: int,
) -> List[Tuple[int, int, int, int]]:
    """
    Alternative detection: find regions with dense text/lines.
    Used when traditional line detection fails (some tables use dashed lines).
    """
    if not HAS_OPENCV:
        return []
    
    # Edge detection
    edges = cv2.Canny(gray, 50, 150)
    
    # Dilate heavily to create blobs
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 10))
    dilated = cv2.dilate(edges, kernel, iterations=5)
    
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    rects = []
    for contour in contours:
        cx, cy, cw, ch = cv2.boundingRect(contour)
        if cw >= min_w and ch >= min_h:
            rects.append((cx, cy, cx + cw, cy + ch))
    
    return _merge_overlapping_rects(rects) if rects else []


def _merge_overlapping_rects(
    rects: List[Tuple[int, int, int, int]],
    overlap_threshold: float = 0.3,
) -> List[Tuple[int, int, int, int]]:
    """Merge rectangles that overlap significantly."""
    if not rects:
        return []
    
    # Simple greedy merge
    merged = list(rects)
    changed = True
    
    while changed:
        changed = False
        new_merged = []
        used = set()
        
        for i in range(len(merged)):
            if i in used:
                continue
            
            current = merged[i]
            
            for j in range(i + 1, len(merged)):
                if j in used:
                    continue
                
                other = merged[j]
                
                # Check overlap
                overlap_x = max(0, min(current[2], other[2]) - max(current[0], other[0]))
                overlap_y = max(0, min(current[3], other[3]) - max(current[1], other[1]))
                overlap_area = overlap_x * overlap_y
                
                current_area = (current[2] - current[0]) * (current[3] - current[1])
                other_area = (other[2] - other[0]) * (other[3] - other[1])
                min_area = min(current_area, other_area)
                
                if min_area > 0 and overlap_area / min_area > overlap_threshold:
                    # Merge
                    current = (
                        min(current[0], other[0]),
                        min(current[1], other[1]),
                        max(current[2], other[2]),
                        max(current[3], other[3]),
                    )
                    used.add(j)
                    changed = True
            
            new_merged.append(current)
        
        merged = new_merged
    
    return merged


def _crop_zones(
    img: np.ndarray,
    rects: List[Tuple[int, int, int, int]],
    original_b64: str,
) -> List[TableZone]:
    """Create TableZone objects with cropped images."""
    zones = []
    
    for idx, (x0, y0, x1, y1) in enumerate(rects):
        # Add small padding
        h, w = img.shape[:2]
        pad = 10
        x0_padded = max(0, x0 - pad)
        y0_padded = max(0, y0 - pad)
        x1_padded = min(w, x1 + pad)
        y1_padded = min(h, y1 + pad)
        
        # Crop
        cropped = img[y0_padded:y1_padded, x0_padded:x1_padded]
        
        # Encode to base64
        success, buffer = cv2.imencode(".png", cropped)
        if success:
            zone_b64 = base64.b64encode(buffer.tobytes()).decode("utf-8")
        else:
            zone_b64 = original_b64
        
        zone = TableZone(
            x0=x0, y0=y0, x1=x1, y1=y1,
            zone_index=idx,
            confidence=0.8,
            image_b64=zone_b64,
        )
        zones.append(zone)
    
    return zones


def _fallback_single_zone(image_b64: str) -> List[TableZone]:
    """When detection fails, return the full image as a single zone."""
    return [
        TableZone(
            x0=0, y0=0, x1=0, y1=0,
            zone_index=0,
            confidence=0.5,
            image_b64=image_b64,
            db_label_hint="",
        )
    ]


def split_multi_db_by_layout(
    image_b64: str,
    expected_db_count: int = 0,
) -> List[TableZone]:
    """
    Higher-level splitter that uses layout heuristics when OpenCV detection
    gives ambiguous results.
    
    Based on real data analysis:
    - 2 DBs: Usually top/bottom split (horizontal) or left/right split (vertical)
    - 4 DBs: 2×2 quadrant grid
    
    Args:
        image_b64: Schedule region image
        expected_db_count: If known from diagram analysis (0 = unknown)
    """
    # First try OpenCV detection
    zones = detect_table_zones(image_b64)
    
    if len(zones) >= 2:
        return zones
    
    # If OpenCV found only 1 zone but we expect more, use geometric splitting
    if expected_db_count >= 2:
        img_bytes = base64.b64decode(image_b64)
        img = Image.open(io.BytesIO(img_bytes))
        w, h = img.size
        
        if expected_db_count == 2:
            # Try horizontal split (top/bottom — most common)
            return _geometric_split_horizontal(image_b64, img, w, h)
        elif expected_db_count == 4:
            # 2×2 grid
            return _geometric_split_grid(image_b64, img, w, h)
    
    return zones


def _geometric_split_horizontal(
    original_b64: str,
    img: Image.Image,
    w: int, h: int,
) -> List[TableZone]:
    """Split image into top and bottom halves."""
    mid_y = h // 2
    
    zones = []
    for idx, (y0, y1) in enumerate([(0, mid_y), (mid_y, h)]):
        cropped = img.crop((0, y0, w, y1))
        buffer = io.BytesIO()
        cropped.save(buffer, format="PNG")
        zone_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        zones.append(TableZone(
            x0=0, y0=y0, x1=w, y1=y1,
            zone_index=idx,
            confidence=0.6,
            image_b64=zone_b64,
        ))
    
    return zones


def _geometric_split_grid(
    original_b64: str,
    img: Image.Image,
    w: int, h: int,
) -> List[TableZone]:
    """Split image into 2×2 grid."""
    mid_x, mid_y = w // 2, h // 2
    
    quadrants = [
        (0, 0, mid_x, mid_y),         # Top-left
        (mid_x, 0, w, mid_y),         # Top-right
        (0, mid_y, mid_x, h),         # Bottom-left
        (mid_x, mid_y, w, h),         # Bottom-right
    ]
    
    zones = []
    for idx, (x0, y0, x1, y1) in enumerate(quadrants):
        cropped = img.crop((x0, y0, x1, y1))
        buffer = io.BytesIO()
        cropped.save(buffer, format="PNG")
        zone_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        zones.append(TableZone(
            x0=x0, y0=y0, x1=x1, y1=y1,
            zone_index=idx,
            confidence=0.55,
            image_b64=zone_b64,
        ))
    
    return zones
