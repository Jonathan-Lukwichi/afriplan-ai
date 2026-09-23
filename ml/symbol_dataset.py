"""
DWG/DXF → labelled symbol-image dataset (YOLO format) for a future CNN detector.

Why CAD is the label source: a PDF drawing is pixels, but its source DWG knows
exactly where every block symbol sits. Rendering the DXF to an image and
projecting each recognised block's extent into pixel space yields bounding-box
labels with zero human annotation. A detector trained on these images can then
read the PDFs clients actually send.

Labels come from INSERT blocks whose name the DXF pipeline's pattern table
classifies (agent.dxf_pipeline.patterns) mapped to taxonomy families. Exploded
line-work symbols (common in Revit exports) have no block and therefore no
label — the dataset card reports that coverage honestly.

Output layout (data/ml/symbols/, gitignored):
    images/<sheet>.png   labels/<sheet>.txt  (YOLO: cls cx cy w h, normalised)
    classes.txt          samples.jsonl       (one SheetSample per image)
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
from pydantic import BaseModel, Field

from evaluation.taxonomy import classify_item

try:
    import cv2
except Exception:  # noqa: BLE001
    cv2 = None

MAX_SIDE_PX = 4096           # keep images trainable (YOLO tiles larger sheets)
_SYMBOL_KINDS = ("LINE", "CIRCLE", "ARC", "LWPOLYLINE", "INSERT")


class SymbolLabel(BaseModel):
    cls: str
    x0: int
    y0: int
    x1: int
    y1: int
    source: str = "block"


class SheetSample(BaseModel):
    image_path: str
    width: int
    height: int
    source_dwg: str = ""
    labels: List[SymbolLabel] = Field(default_factory=list)


# ─── rendering ───────────────────────────────────────────────────────

def _extents(doc) -> Tuple[float, float, float, float]:
    emin = doc.header.get("$EXTMIN", (0, 0, 0))
    emax = doc.header.get("$EXTMAX", (1000, 1000, 0))
    x0, y0, x1, y1 = float(emin[0]), float(emin[1]), float(emax[0]), float(emax[1])
    if not (x1 > x0 and y1 > y0) or max(x1 - x0, y1 - y0) > 1e9:
        from ezdxf import bbox
        box = bbox.extents(doc.modelspace())
        x0, y0, x1, y1 = box.extmin.x, box.extmin.y, box.extmax.x, box.extmax.y
    return x0, y0, x1, y1


def render_sheet(doc, *, px_per_unit: Optional[float] = None, out_png: Path) -> Tuple[int, int, Callable]:
    """Render modelspace line-work (black on white). Returns (w, h, world→pixel)."""
    if cv2 is None:
        raise RuntimeError("opencv-python-headless is required to render sheets")
    x0, y0, x1, y1 = _extents(doc)
    span = max(x1 - x0, y1 - y0) or 1.0
    ppu = px_per_unit or (MAX_SIDE_PX / span)
    ppu = min(ppu, MAX_SIDE_PX / span)
    w, h = max(1, int((x1 - x0) * ppu) + 1), max(1, int((y1 - y0) * ppu) + 1)
    img = np.full((h, w), 255, np.uint8)

    def to_px(x: float, y: float) -> Tuple[int, int]:
        return int(round((x - x0) * ppu)), int(round((y1 - y) * ppu))

    def draw(e):
        k = e.dxftype()
        try:
            if k == "LINE":
                cv2.line(img, to_px(e.dxf.start.x, e.dxf.start.y), to_px(e.dxf.end.x, e.dxf.end.y), 0, 1)
            elif k == "CIRCLE":
                cv2.circle(img, to_px(e.dxf.center.x, e.dxf.center.y), max(1, int(e.dxf.radius * ppu)), 0, 1)
            elif k == "ARC":
                c = to_px(e.dxf.center.x, e.dxf.center.y)
                r = max(1, int(e.dxf.radius * ppu))
                cv2.ellipse(img, c, (r, r), 0, -float(e.dxf.end_angle), -float(e.dxf.start_angle), 0, 1)
            elif k == "LWPOLYLINE":
                pts = [to_px(p[0], p[1]) for p in e.get_points("xy")]
                if len(pts) > 1:
                    cv2.polylines(img, [np.array(pts, np.int32)], bool(e.closed), 0, 1)
            elif k == "INSERT":
                for sub in e.virtual_entities():
                    draw(sub)
        except Exception:  # noqa: BLE001 — one malformed entity must not kill a sheet
            pass

    for e in doc.modelspace():
        if e.dxftype() in _SYMBOL_KINDS:
            draw(e)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_png), img)
    return w, h, to_px


# ─── labels ──────────────────────────────────────────────────────────

def _block_family(name: str) -> Optional[str]:
    from agent.dxf_pipeline.patterns import classify_block_name   # label source = the pattern table
    spec = classify_block_name(name)
    if spec is None:
        return None
    fam = classify_item(spec.canonical_name).family
    return None if fam == "other" else fam


def labels_from_doc(doc, to_px: Callable, *, min_px: int = 3) -> List[SymbolLabel]:
    """One pixel bounding box per classified INSERT block."""
    from ezdxf import bbox
    labels: List[SymbolLabel] = []
    cache: Dict[str, Optional[str]] = {}
    for e in doc.modelspace().query("INSERT"):
        name = e.dxf.name
        if name not in cache:
            cache[name] = _block_family(name)
        fam = cache[name]
        if fam is None:
            continue
        try:
            ext = bbox.extents(e.virtual_entities())
        except Exception:  # noqa: BLE001
            continue
        if not ext.has_data:
            continue
        ax, ay = to_px(ext.extmin.x, ext.extmax.y)       # top-left in pixel space
        bx, by = to_px(ext.extmax.x, ext.extmin.y)
        x0, x1 = sorted((ax, bx))
        y0, y1 = sorted((ay, by))
        if x1 - x0 < min_px:
            x0, x1 = x0 - min_px, x1 + min_px
        if y1 - y0 < min_px:
            y0, y1 = y0 - min_px, y1 + min_px
        labels.append(SymbolLabel(cls=fam, x0=max(0, x0), y0=max(0, y0), x1=x1, y1=y1, source="block"))
    return labels


# ─── writing ─────────────────────────────────────────────────────────

def write_sample(out_dir: Path, sheet: str, w: int, h: int, labels: Sequence[SymbolLabel],
                 *, classes: Sequence[str]) -> Path:
    """Write labels/<sheet>.txt in YOLO format (class cx cy w h, all normalised)."""
    idx = {c: i for i, c in enumerate(classes)}
    lines = []
    for l in labels:
        x0, x1 = max(0, l.x0), min(w, l.x1)
        y0, y1 = max(0, l.y0), min(h, l.y1)
        if x1 <= x0 or y1 <= y0 or l.cls not in idx:
            continue
        lines.append(f"{idx[l.cls]} {(x0 + x1) / 2 / w:.6f} {(y0 + y1) / 2 / h:.6f} "
                     f"{(x1 - x0) / w:.6f} {(y1 - y0) / h:.6f}")
    p = Path(out_dir) / "labels" / f"{sheet}.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return p


def build_dataset(dxf_docs: Sequence[Tuple[str, object]], out_dir: Path) -> List[SheetSample]:
    """dxf_docs: [(sheet_name, ezdxf doc)]. Writes images, YOLO labels, classes, samples."""
    out_dir = Path(out_dir)
    samples: List[SheetSample] = []
    for sheet, doc in dxf_docs:
        png = out_dir / "images" / f"{sheet}.png"
        w, h, to_px = render_sheet(doc, out_png=png)
        samples.append(SheetSample(image_path=str(png.relative_to(out_dir)), width=w, height=h,
                                   source_dwg=sheet, labels=labels_from_doc(doc, to_px)))
    classes = sorted({l.cls for s in samples for l in s.labels})
    (out_dir / "classes.txt").write_text("\n".join(classes) + "\n", encoding="utf-8")
    for s in samples:
        write_sample(out_dir, Path(s.image_path).stem, s.width, s.height, s.labels, classes=classes)
    with (out_dir / "samples.jsonl").open("w", encoding="utf-8") as fh:
        for s in samples:
            fh.write(s.model_dump_json() + "\n")
    return samples
