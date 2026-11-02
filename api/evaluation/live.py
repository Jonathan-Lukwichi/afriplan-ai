"""
Extraction accuracy on a run in the app. Read-only, no LLM; prices play no part.

Accuracy needs a truth to compare with, so it exists only for a reference project: an upload that
IS that project's drawing set, with its human-priced bill on this machine. The bill is client data
and never reaches git or the deployed app, so elsewhere there is simply no accuracy to show. A
partial upload is not judged either: it would be measured against a whole project's bill.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Optional

from agent.shared.boq import BillOfQuantities
from evaluation.dataset import DATA_ROOT, load_manifest, uploaded_from_manifest
from evaluation.metrics import pred_lines_from_boq, score
from evaluation.reading import reading_accuracy
from evaluation.reference import RefBuilding, ReferenceBoq, load_reference

PROJECT = "Project (all buildings)"
_MIN_MATCH = 0.8                 # share of the upload that is the project's, and of the set uploaded
_NOT_DRAWINGS = ("reference_boq", "architectural")
_BIGGEST_MISSES = 5
_FAMILY_NAMES = {"db": "Distribution boards"}


def _name(file_name: str) -> str:
    return " ".join(Path(file_name).stem.lower().split())


def find_reference_project(file_names: Iterable[str], *, root: Optional[Path] = None) -> Optional[str]:
    """The reference project this upload is, or None."""
    root = DATA_ROOT if root is None else Path(root)
    if not root.is_dir():
        return None
    uploaded = {_name(n) for n in file_names if n}
    if not uploaded:
        return None
    for folder in sorted(p for p in root.iterdir() if (p / "reference_boq.json").is_file()):
        try:
            files = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))["files"]
        except (OSError, ValueError, KeyError):
            continue
        drawings = {_name(f["path"]): f["role"].startswith("pdf_") for f in files if f["role"] not in _NOT_DRAWINGS}
        matched = uploaded & set(drawings)
        if not matched:
            continue
        same_kind = {n for n, is_pdf in drawings.items() if is_pdf == drawings[next(iter(matched))]}
        if len(matched) >= _MIN_MATCH * len(uploaded) and len(matched) >= _MIN_MATCH * len(same_kind):
            return folder.name
    return None


def project_reference(ref: ReferenceBoq) -> ReferenceBoq:
    """The real bill as one building: reading is judged on the project, not on attribution."""
    lines = [l.model_copy(update={"building": PROJECT}) for b in ref.billed_buildings() for l in b.lines]
    return ReferenceBoq(project=ref.project, buildings=[RefBuilding(name=PROJECT, sheet="*", lines=lines, in_summary=True)])


def _bill_queries(project: str) -> List[dict]:
    """Items where the bill looks wrong against the drawings, unconfirmed: [{key, note}], in the
    project's local bill_queries.json (client data, never in git). They give a second number
    beside the scorer's; the reference and the scorer's own number never change."""
    path = DATA_ROOT / project / "bill_queries.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []


def _miss_name(key: str, label: str) -> str:
    """The whole item's name. A label is one bill line, so a family like `db` needs its own word:
    'DB Large Guard House' would read as if that one board were the difference."""
    return _FAMILY_NAMES.get(key) or label.split(" — ")[0][:70]


def reading_summary(boq: BillOfQuantities, project: str, *, pipeline: str) -> dict:
    """What the page shows: how much of what is drawn was read, and the biggest misses. No money."""
    ref = load_reference(project)
    manifest = load_manifest(project)
    source = "pdf" if pipeline == "pdf" else "dwg"
    uploaded = set().union(*(uploaded_from_manifest(manifest, b.name, source=source) for b in ref.billed_buildings()))
    lines = pred_lines_from_boq(boq, building=PROJECT)
    card = score(lines, project_reference(ref), uploaded={PROJECT: uploaded}, pipeline=pipeline, buildings=[PROJECT])
    r = reading_accuracy(card)
    misses: List[dict] = [{"item": _miss_name(i["key"], i["label"]), "verdict": i["verdict"],
                           "points_lost": i["points_lost"]}
                          for i in r["items"][:_BIGGEST_MISSES] if i["points_lost"] > 0]
    queries = _bill_queries(project)
    queried = {q["key"] for q in queries}
    return {
        "if_queries_confirmed": ({
            "score": r["reading_score"] + sum(i["points_lost"] for i in r["items"] if i["key"] in queried),
            "items": [q["note"] for q in queries],
        } if queries else None),
        "project": project, "reading_score": r["reading_score"], "coverage": r["coverage"],
        "qty_accuracy": r["qty_accuracy"], "items_judged": r["items_judged"], "items_found": r["items_found"],
        "items_within_10pct": r["items_within_10pct"], "item_precision": r["item_precision"],
        "biggest_misses": misses,
    }
