"""
Build the CNN symbol-detection dataset from a reference project's CAD drawings.

    python scripts/build_symbol_dataset.py wedela          # → data/ml/symbols/wedela/

Every current electrical DWG is converted to DXF (LibreDWG), rendered to PNG,
and labelled from its classified blocks (YOLO format). Prints per-class counts
for ml/DATASET_CARD.md.
"""

from __future__ import annotations

import argparse
import io
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

import ezdxf  # noqa: E402

from agent.dxf_pipeline.dwg import ensure_dxf_bytes  # noqa: E402
from evaluation.dataset import load_manifest, project_dir  # noqa: E402
from ml.symbol_dataset import build_dataset  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def _read_dxf(data: bytes):
    """Text read first; LibreDWG output with odd binary chunks needs ezdxf's recover mode."""
    try:
        return ezdxf.read(io.StringIO(data.decode("utf-8", "ignore")))
    except Exception:  # noqa: BLE001
        pass
    import tempfile
    from ezdxf import recover
    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tf:
        tf.write(data)
    try:
        doc, _auditor = recover.readfile(tf.name)
        return doc
    except Exception:  # noqa: BLE001
        return None
    finally:
        Path(tf.name).unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project")
    args = ap.parse_args()

    manifest = load_manifest(args.project)
    docs = []
    for role in ("lighting_layout", "plug_layout", "sld"):
        for f in manifest.files_for(role=role):
            path = project_dir(args.project) / f.path
            conv = ensure_dxf_bytes(path.read_bytes(), path.name)
            if not conv.ok:
                print(f"skip {path.name}: {conv.error[:80]}")
                continue
            doc = _read_dxf(conv.dxf_bytes)
            if doc is None:
                print(f"skip {path.name}: unreadable DXF after conversion")
                continue
            docs.append((path.stem.replace(" ", "_"), doc))
            print(f"converted {path.name}")

    out = ROOT / "data" / "ml" / "symbols" / args.project
    samples = build_dataset(docs, out)
    per_class = Counter(l.cls for s in samples for l in s.labels)
    print(f"\n{len(samples)} sheets, {sum(per_class.values())} labelled symbols → {out}")
    for cls, n in per_class.most_common():
        print(f"  {cls:24} {n}")
    for s in samples:
        print(f"  {s.source_dwg:40} {s.width}x{s.height}px  {len(s.labels)} labels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
