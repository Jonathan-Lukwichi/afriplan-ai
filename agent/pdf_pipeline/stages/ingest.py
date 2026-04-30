"""
Stage P1 — Ingest.

PyMuPDF rasterises every page at the configured DPI, returns base64
PNGs, hashes the input bytes, caps total pages at the configured
ceiling. This stage makes ZERO API calls.
"""

from __future__ import annotations

import base64
import hashlib
import io
import logging
from dataclasses import dataclass
from typing import List

import fitz  # PyMuPDF
from PIL import Image

from core.config import PDF_THRESHOLDS

log = logging.getLogger(__name__)


@dataclass
class IngestedPage:
    page_index: int                 # 0-based
    width_px: int
    height_px: int
    image_b64: str                  # base64-encoded PNG, ready for vision API


@dataclass
class IngestResult:
    file_name: str
    file_size_bytes: int
    file_sha256: str
    page_count_total: int           # total pages in the source PDF
    pages_processed: List[IngestedPage]
    truncated: bool = False         # True if we capped at PDF_THRESHOLDS.max_pages


def _sha256(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _render_page_to_png_b64(page: "fitz.Page", dpi: int) -> tuple[str, int, int]:
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    png_bytes = pix.tobytes("png")

    # Sanity: keep the image under a reasonable byte ceiling to avoid
    # very large vision-API requests. 2576px long edge is the Opus 4.7
    # max; we render below that on purpose.
    img = Image.open(io.BytesIO(png_bytes))
    max_edge = max(img.width, img.height)
    if max_edge > 2200:
        scale = 2200.0 / max_edge
        img = img.resize(
            (int(img.width * scale), int(img.height * scale)),
            Image.LANCZOS,
        )
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        png_bytes = buf.getvalue()

    return (
        base64.b64encode(png_bytes).decode("ascii"),
        img.width,
        img.height,
    )


def ingest(
    file_bytes: bytes,
    file_name: str = "input.pdf",
    *,
    dpi: int = None,
    max_pages: int = None,
) -> IngestResult:
    """
    Open the PDF, rasterise up to `max_pages` pages at `dpi`, return them
    as base64 PNGs ready for the Anthropic vision API.
    """
    dpi = dpi or PDF_THRESHOLDS.raster_dpi
    max_pages = max_pages or PDF_THRESHOLDS.max_pages

    sha = _sha256(file_bytes)
    size = len(file_bytes)

    pages: List[IngestedPage] = []
    truncated = False

    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        total = doc.page_count
        page_limit = min(total, max_pages)
        if total > max_pages:
            truncated = True

        for i in range(page_limit):
            try:
                b64, w, h = _render_page_to_png_b64(doc.load_page(i), dpi)
            except Exception as e:  # noqa: BLE001
                log.warning("Failed to rasterise page %d: %s", i, e)
                continue
            pages.append(IngestedPage(page_index=i, width_px=w, height_px=h, image_b64=b64))

    return IngestResult(
        file_name=file_name,
        file_size_bytes=size,
        file_sha256=sha,
        page_count_total=total if "total" in dir() else len(pages),
        pages_processed=pages,
        truncated=truncated,
    )
