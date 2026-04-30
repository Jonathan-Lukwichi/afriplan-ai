"""
Stage D1 — Ingest.

Open the DXF, detect units, hash inputs, return a DxfIngestResult plus
the live ezdxf document. The doc is passed by reference to subsequent
stages (no re-parsing).
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Tuple

import ezdxf
from ezdxf.document import Drawing

from agent.dxf_pipeline.models import DxfIngestResult


# AutoCAD INSUNITS values → SI factor to metres
_INSUNITS_TO_METRES = {
    0: ("unitless", 1.0),
    1: ("inches", 0.0254),
    2: ("feet", 0.3048),
    4: ("mm", 0.001),
    5: ("cm", 0.01),
    6: ("metres", 1.0),
}


def _sha256(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def ingest(
    file_bytes: bytes,
    file_name: str = "input.dxf",
) -> Tuple[DxfIngestResult, "Drawing"]:
    """
    Read the DXF and return (ingest_result, ezdxf_document).

    Raises nothing — errors are captured into DxfIngestResult.error.
    """
    sha = _sha256(file_bytes)
    size = len(file_bytes)

    # ezdxf wants a path; write to a temp file so it can stream.
    tmp = tempfile.NamedTemporaryFile(prefix="afp_dxf_", suffix=".dxf", delete=False)
    try:
        tmp.write(file_bytes)
        tmp.flush()
        tmp.close()

        try:
            doc = ezdxf.readfile(tmp.name)
        except (ezdxf.DXFStructureError, IOError, ValueError) as e:
            return (
                DxfIngestResult(
                    file_name=file_name,
                    file_size_bytes=size,
                    file_sha256=sha,
                    open_ok=False,
                    error=f"{type(e).__name__}: {e}",
                ),
                None,  # type: ignore[return-value]
            )

        # Detect units
        insunits = doc.header.get("$INSUNITS", 0)
        unit_label, factor = _INSUNITS_TO_METRES.get(insunits, ("unknown", 1.0))

        layer_count = len(doc.layers)
        entity_count = sum(1 for _ in doc.modelspace())

        return (
            DxfIngestResult(
                file_name=file_name,
                file_size_bytes=size,
                file_sha256=sha,
                drawing_units=unit_label,
                units_to_metre_factor=factor,
                dxf_version=str(doc.dxfversion),
                layer_count=layer_count,
                entity_count=entity_count,
                open_ok=True,
            ),
            doc,
        )
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def ingest_path(file_path: str | Path) -> Tuple[DxfIngestResult, "Drawing"]:
    """Convenience wrapper for tests."""
    p = Path(file_path)
    return ingest(p.read_bytes(), p.name)
