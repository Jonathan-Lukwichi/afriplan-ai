"""
INGEST Stage: Document preprocessing - PDF/images to base64.

Converts uploaded files into a standardized DocumentSet structure.
Uses PyMuPDF (fitz) for PDF rendering and Pillow for image processing.

v4.7: Enhanced page classification with:
- Drawing register parsing (maps TJM-SLD-001 -> SLD type)
- Cable specification keywords (mm², 4c, swa) for graphics-heavy SLDs
"""

import io
import re
import base64
from typing import List, Tuple, Optional, Dict
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from PIL import Image
except ImportError:
    Image = None

from agent.models import (
    DocumentSet, DocumentInfo, PageInfo, PageType, StageResult, PipelineStage
)
from agent.utils import Timer, encode_image_to_base64


# Supported MIME types
SUPPORTED_MIMES = {
    "application/pdf": "pdf",
    "image/png": "png",
    "image/jpeg": "jpeg",
    "image/jpg": "jpeg",
}


def ingest(
    files: List[Tuple[bytes, str, str]],  # (file_bytes, filename, mime_type)
    dpi: int = 150,
    max_pages: int = 50,
) -> Tuple[DocumentSet, StageResult]:
    """
    INGEST stage: Convert uploaded files to DocumentSet.

    Args:
        files: List of (file_bytes, filename, mime_type) tuples
        dpi: Resolution for PDF rendering (default 150)
        max_pages: Maximum pages to process per document

    Returns:
        Tuple of (DocumentSet, StageResult)
    """
    with Timer("ingest") as timer:
        doc_set = DocumentSet()
        errors = []
        warnings = []
        total_pages = 0

        for file_bytes, filename, mime_type in files:
            try:
                # Normalize MIME type
                mime_type = mime_type.lower().strip()
                if mime_type not in SUPPORTED_MIMES:
                    # Try to infer from filename extension
                    ext = Path(filename).suffix.lower()
                    mime_map = {".pdf": "application/pdf", ".png": "image/png",
                               ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
                    mime_type = mime_map.get(ext, mime_type)

                if mime_type not in SUPPORTED_MIMES:
                    errors.append(f"Unsupported file type: {filename} ({mime_type})")
                    continue

                file_type = SUPPORTED_MIMES[mime_type]

                if file_type == "pdf":
                    doc_info = _process_pdf(file_bytes, filename, dpi, max_pages)
                else:
                    doc_info = _process_image(file_bytes, filename, mime_type)

                if doc_info:
                    doc_set.documents.append(doc_info)
                    total_pages += doc_info.num_pages

            except Exception as e:
                errors.append(f"Error processing {filename}: {str(e)}")

        # Update document set totals
        doc_set.total_pages = total_pages
        _categorize_pages(doc_set)

        # Build stage result
        result = StageResult(
            stage=PipelineStage.INGEST,
            success=len(doc_set.documents) > 0,
            confidence=1.0 if not errors else 0.8,
            data={
                "documents": len(doc_set.documents),
                "total_pages": total_pages,
            },
            processing_time_ms=timer.elapsed_ms,
            errors=errors,
            warnings=warnings,
        )

        return doc_set, result


def _process_pdf(
    pdf_bytes: bytes,
    filename: str,
    dpi: int,
    max_pages: int,
) -> Optional[DocumentInfo]:
    """Process PDF file into DocumentInfo."""
    if fitz is None:
        raise ImportError("PyMuPDF (fitz) is required for PDF processing")

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    doc_info = DocumentInfo(
        filename=filename,
        mime_type="application/pdf",
        num_pages=min(len(doc), max_pages),
        file_size_bytes=len(pdf_bytes),
    )

    # Render each page to image
    for page_num in range(min(len(doc), max_pages)):
        page = doc[page_num]

        # Render page to image
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)

        # Convert to PNG bytes
        img_bytes = pix.tobytes("png")
        img_base64 = encode_image_to_base64(img_bytes)

        # Extract text content
        text_content = page.get_text()

        page_info = PageInfo(
            page_number=page_num + 1,
            page_type=PageType.UNKNOWN,  # Will be classified later
            image_base64=img_base64,
            text_content=text_content,
            width_px=pix.width,
            height_px=pix.height,
            source_document=filename,
        )

        doc_info.pages.append(page_info)

    doc.close()
    return doc_info


def _process_image(
    img_bytes: bytes,
    filename: str,
    mime_type: str,
) -> Optional[DocumentInfo]:
    """Process image file into DocumentInfo."""
    if Image is None:
        raise ImportError("Pillow is required for image processing")

    # Open image
    img = Image.open(io.BytesIO(img_bytes))

    # Convert to RGB if necessary
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Encode to base64
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_base64 = encode_image_to_base64(buffer.getvalue())

    doc_info = DocumentInfo(
        filename=filename,
        mime_type=mime_type,
        num_pages=1,
        file_size_bytes=len(img_bytes),
    )

    page_info = PageInfo(
        page_number=1,
        page_type=PageType.UNKNOWN,
        image_base64=img_base64,
        text_content="",  # No text extraction from images
        width_px=img.width,
        height_px=img.height,
        source_document=filename,
    )

    doc_info.pages.append(page_info)
    return doc_info


def _parse_drawing_register(doc_set: DocumentSet) -> Dict[int, str]:
    """
    Parse drawing register (typically page 1) to extract drawing number -> page type mappings.

    v4.7: Looks for patterns like:
    - "TJM-SLD-001" -> SLD
    - "TJM-GF-01-PLUGS" -> PLUGS
    - "TJM-GF-01-LIGHTS" -> LIGHTING
    - "WD-PB-01-SLD" -> SLD

    Returns:
        Dict mapping page_number -> predicted page_type string
    """
    page_type_map: Dict[int, str] = {}

    # Drawing number patterns and their types
    sld_patterns = [
        r"sld[-_\s]?\d*",           # SLD-001, SLD_001, SLD 001
        r"\w+-sld[-_]?\d*",         # TJM-SLD-001, WD-SLD-01
        r"single\s*line",           # Single Line Diagram
        r"schematic",               # Schematic
    ]

    lighting_patterns = [
        r"light(s|ing)?[-_\s]?\d*", # LIGHTS, LIGHTING, LIGHT-01
        r"\w+-\w+-light(s|ing)?",   # TJM-GF-01-LIGHTS
        r"lux\s*layout",            # Lux Layout
    ]

    plugs_patterns = [
        r"plug(s)?[-_\s]?\d*",      # PLUGS, PLUG-01
        r"power[-_\s]?\d*",         # POWER, POWER-01
        r"socket(s)?[-_\s]?\d*",    # SOCKETS
        r"\w+-\w+-plug(s)?",        # TJM-GF-01-PLUGS
    ]

    register_patterns = [
        r"register",
        r"transmittal",
        r"index",
        r"drawing\s*list",
    ]

    # Look at first 2 pages for drawing register
    for doc in doc_set.documents:
        for page in doc.pages[:2]:  # Only check first 2 pages
            text_lower = page.text_content.lower()

            # Check if this looks like a drawing register
            is_register = any(
                re.search(pat, text_lower) for pat in register_patterns
            ) or "drawing no" in text_lower or "dwg no" in text_lower

            if not is_register:
                continue

            # Parse drawing numbers from register
            # Look for patterns like "TJM-SLD-001" followed by page info
            lines = text_lower.split('\n')

            for i, line in enumerate(lines):
                # Try to extract drawing number and associate with type
                for sld_pat in sld_patterns:
                    if re.search(sld_pat, line):
                        # Try to find associated page number
                        page_match = re.search(r'(?:page|pg|p)?\s*(\d+)', line)
                        if page_match:
                            pg_num = int(page_match.group(1))
                            page_type_map[pg_num] = "sld"
                        else:
                            # Assume sequential: drawing on line i maps to page i+1
                            estimated_page = i + 2  # +2 because register is page 1
                            if estimated_page <= doc_set.total_pages:
                                page_type_map[estimated_page] = "sld"
                        break

                for light_pat in lighting_patterns:
                    if re.search(light_pat, line) and not re.search(r'sld', line):
                        page_match = re.search(r'(?:page|pg|p)?\s*(\d+)', line)
                        if page_match:
                            pg_num = int(page_match.group(1))
                            page_type_map[pg_num] = "lighting"
                        break

                for plugs_pat in plugs_patterns:
                    if re.search(plugs_pat, line) and not re.search(r'sld', line):
                        page_match = re.search(r'(?:page|pg|p)?\s*(\d+)', line)
                        if page_match:
                            pg_num = int(page_match.group(1))
                            page_type_map[pg_num] = "plugs"
                        break

    return page_type_map


def _detect_sld_from_cable_specs(text_lower: str) -> int:
    """
    Detect SLD pages from cable specification patterns that survive graphics text extraction.

    v4.7: When PyMuPDF extracts text from graphics-heavy SLD drawings, it often
    captures cable specs like "4c 16mm² pvc swa" even when circuit schedules are
    vector graphics. This function scores these patterns.

    Returns:
        Score indicating likelihood this is an SLD page (0-10)
    """
    score = 0

    # Cable size patterns (very strong SLD indicator)
    # Matches: 16mm², 16mm2, 16 mm², 2.5mm, etc.
    cable_size_pattern = r'\d+(?:\.\d+)?\s*mm[²2]?'
    cable_matches = re.findall(cable_size_pattern, text_lower)
    if len(cable_matches) >= 2:
        score += 4
    elif len(cable_matches) >= 1:
        score += 2

    # Multi-core cable patterns (4c, 3c, 2c = 4-core, 3-core, 2-core)
    core_pattern = r'\b[234]\s*c\b'
    if re.search(core_pattern, text_lower):
        score += 3

    # Cable type indicators
    cable_types = ["pvc swa", "swa pvc", "xlpe", "pilc", "surfix", "cabtyre"]
    for cable_type in cable_types:
        if cable_type in text_lower:
            score += 2
            break

    # Breaker/protection patterns that survive as text
    breaker_patterns = [
        r'\d+\s*a\b',              # 32a, 20 a
        r'\b\d+\s*amp',            # 32amp, 20 amp
        r'earth\s*leakage',
        r'surge\s*protect',
    ]
    for bp in breaker_patterns:
        if re.search(bp, text_lower):
            score += 1
            break

    # Engineering company names (often appear on SLDs)
    if "engineering" in text_lower or "electrical" in text_lower:
        score += 1

    # Multiple "x" patterns suggesting wattage formulas (5x48W, 3x1200W)
    wattage_pattern = r'\d+\s*x\s*\d+\s*w'
    if re.search(wattage_pattern, text_lower):
        score += 2

    return score


def _categorize_pages(doc_set: DocumentSet) -> None:
    """
    Categorize pages based on filename patterns and text content.
    Updates page types and document set counters.

    v4.1.2: Improved detection for combined layout drawings that contain
    both lighting and socket/switch symbols on the same page.

    v4.7: Enhanced SLD detection with:
    - Drawing register parsing (FIX 1)
    - Cable specification keywords (FIX 2)
    """
    # FIX 1: Parse drawing register to get page type hints
    register_hints = _parse_drawing_register(doc_set)

    for doc in doc_set.documents:
        filename_lower = doc.filename.lower()

        for page in doc.pages:
            text_lower = page.text_content.lower()

            # Score-based classification for better accuracy
            scores = {
                "register": 0,
                "sld": 0,
                "lighting": 0,
                "plugs": 0,
                "combined": 0,
                "outside": 0,
            }

            # FIX 1: Apply drawing register hints (very high weight)
            if page.page_number in register_hints:
                hint_type = register_hints[page.page_number]
                if hint_type == "sld":
                    scores["sld"] += 15  # Strong boost from register
                elif hint_type == "lighting":
                    scores["lighting"] += 15
                elif hint_type == "plugs":
                    scores["plugs"] += 15

            # Filename-based scoring (high weight)
            if any(k in filename_lower for k in ["register", "transmittal", "index"]):
                scores["register"] += 10
            if any(k in filename_lower for k in ["sld", "schematic", "single line"]):
                scores["sld"] += 10
            if any(k in filename_lower for k in ["lighting", "light"]) and "plug" not in filename_lower:
                scores["lighting"] += 10
            if any(k in filename_lower for k in ["plug", "power", "socket"]):
                scores["plugs"] += 10
            if any(k in filename_lower for k in ["outside", "external", "site", "perimeter"]):
                scores["outside"] += 10

            # FIX 2: Cable specification detection (graphics-heavy SLDs)
            cable_spec_score = _detect_sld_from_cable_specs(text_lower)
            scores["sld"] += cable_spec_score

            # Text content-based scoring
            # SLD indicators (enhanced v4.2)
            # Strong SLD indicators - circuit schedule tables
            if any(k in text_lower for k in ["circuit no", "circuit schedule", "load schedule",
                                              "wattage", "wire size", "no of point", "no. of points",
                                              "cable size", "breaker size", "mcb rating"]):
                scores["sld"] += 5
            # DB/board indicators
            if any(k in text_lower for k in ["distribution board", "db schedule", "single line",
                                              "mcb", "elcb", "rccb", "rcbo", "breaker", "main switch"]):
                scores["sld"] += 3
            # DB naming patterns (DB-1, DB-L1, DB-P1, etc.)
            if "db-" in text_lower or "db " in text_lower:
                scores["sld"] += 2
            # Typical SLD table headers
            if any(k in text_lower for k in ["cct", "ckt", "total load", "diversity",
                                              "phase", "neutral", "earth", "protective device"]):
                scores["sld"] += 2

            # Lighting indicators
            if any(k in text_lower for k in ["led panel", "led light", "luminaire", "lux"]):
                scores["lighting"] += 4
            if any(k in text_lower for k in ["flood light", "downlight", "bulkhead"]):
                scores["lighting"] += 3
            if any(k in text_lower for k in ["600 x 1200", "600x1200", "recessed"]):
                scores["lighting"] += 3

            # Plug/socket indicators
            if any(k in text_lower for k in ["socket outlet", "power point", "switched socket"]):
                scores["plugs"] += 4
            if any(k in text_lower for k in ["16a double", "16a single"]):
                scores["plugs"] += 3
            if any(k in text_lower for k in ["@300mm", "@1100mm", "@1200mm", "above ffl"]):
                scores["plugs"] += 2

            # Switch indicators (usually with plugs)
            if any(k in text_lower for k in ["lever", "1 way switch", "2 way switch"]):
                scores["plugs"] += 2
            if any(k in text_lower for k in ["isolator switch", "day/night", "day night"]):
                scores["plugs"] += 2

            # Combined layout indicators (has BOTH lights and plugs/switches)
            if any(k in text_lower for k in ["legend"]):
                # Legend with both light and socket descriptions = combined
                has_light_legend = any(k in text_lower for k in ["led", "light", "flood", "luminaire"])
                has_socket_legend = any(k in text_lower for k in ["socket", "switch", "isolator"])
                if has_light_legend and has_socket_legend:
                    scores["combined"] += 8

            # Room/area indicators suggest layout drawings
            room_names = ["suite", "office", "kitchen", "bathroom", "toilet", "wc",
                         "reception", "foyer", "lounge", "boardroom", "store",
                         "kitchenette", "balcony", "parking"]
            room_count = sum(1 for r in room_names if r in text_lower)
            if room_count >= 2:
                scores["combined"] += room_count
                scores["lighting"] += room_count // 2
                scores["plugs"] += room_count // 2

            # Area measurements (m2, m²) suggest layout drawings
            if "m2" in text_lower or "m²" in text_lower:
                scores["combined"] += 3
                scores["lighting"] += 1
                scores["plugs"] += 1

            # Register indicators
            if any(k in text_lower for k in ["drawing no", "drawing name", "sent date", "rev no"]):
                scores["register"] += 5

            # Determine page type based on highest score
            max_score = max(scores.values())

            if max_score == 0:
                # No clear indicators - check if it looks like a drawing at all
                page.page_type = PageType.UNKNOWN
                doc_set.num_other_pages += 1
            elif scores["register"] == max_score and scores["register"] >= 5:
                page.page_type = PageType.REGISTER
                doc_set.num_register_pages += 1
            elif scores["sld"] == max_score and scores["sld"] >= 3:
                page.page_type = PageType.SLD
                doc_set.num_sld_pages += 1
            elif scores["combined"] == max_score and scores["combined"] >= 5:
                # Combined layout with both lighting and plugs
                page.page_type = PageType.LAYOUT_COMBINED
                doc_set.num_lighting_pages += 1  # Count for both
                doc_set.num_plugs_pages += 1
            elif scores["lighting"] > scores["plugs"] and scores["lighting"] >= 3:
                page.page_type = PageType.LAYOUT_LIGHTING
                doc_set.num_lighting_pages += 1
            elif scores["plugs"] >= 3:
                page.page_type = PageType.LAYOUT_PLUGS
                doc_set.num_plugs_pages += 1
            elif scores["outside"] >= 3:
                page.page_type = PageType.OUTSIDE_LIGHTS
                doc_set.num_outside_light_pages += 1
            elif room_count >= 1 or "m2" in text_lower:
                # Has room names or areas but no clear electrical indicators
                # Treat as combined layout (AI will figure out what's there)
                page.page_type = PageType.LAYOUT_COMBINED
                doc_set.num_lighting_pages += 1
                doc_set.num_plugs_pages += 1
            else:
                page.page_type = PageType.UNKNOWN
                doc_set.num_other_pages += 1

            # Try to detect building block from text
            block_patterns = [
                "newmark", "pool block", "ablution", "community hall",
                "guard house", "retail", "office", "suite"
            ]
            for pattern in block_patterns:
                if pattern in text_lower:
                    page.building_block = pattern.title()
                    if pattern.title() not in doc_set.building_blocks_detected:
                        doc_set.building_blocks_detected.append(pattern.title())
                    break
