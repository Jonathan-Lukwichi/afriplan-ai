"""
INGEST Stage: Document preprocessing - PDF/images to base64.

Converts uploaded files into a standardized DocumentSet structure.
Uses PyMuPDF (fitz) for PDF rendering and Pillow for image processing.
"""

import io
import base64
from typing import List, Tuple, Optional
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


def _categorize_pages(doc_set: DocumentSet) -> None:
    """
    Categorize pages based on filename patterns and text content.
    Updates page types and document set counters.

    v4.1.2: Improved detection for combined layout drawings that contain
    both lighting and socket/switch symbols on the same page.
    """
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

            # Text content-based scoring
            # SLD indicators
            if any(k in text_lower for k in ["circuit no", "wattage", "wire size", "no of point"]):
                scores["sld"] += 5
            if any(k in text_lower for k in ["distribution board", "mcb", "elcb", "breaker"]):
                scores["sld"] += 3
            if "db-" in text_lower:
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
