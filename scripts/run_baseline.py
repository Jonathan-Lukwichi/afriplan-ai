"""
Run a pipeline over a reference project and score it — the reproducible baseline.

    python scripts/run_baseline.py --project wedela --pipeline dxf
    python scripts/run_baseline.py --project wedela --pipeline pdf          # paid: uses ANTHROPIC_API_KEY
    python scripts/run_baseline.py --project wedela --pipeline pdf --from-runs <run_id>   # re-score, R 0
    ... --out reports/baselines/2026-09-23-wedela-dxf.md

Scores every run twice with the frozen scorer:
  per building  — lines attributed to the reference building they belong to
  project-level — all buildings merged, so building attribution errors don't hide
                  what was (or was not) quantified at all
and again after the BOQ completer (audit.completer) adds fitted derived items.
Runs are persisted under runs/<pipeline>/ for later re-scoring.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))
sys.stdout.reconfigure(encoding="utf-8")

from agent.shared import BillOfQuantities, ProjectMetadata  # noqa: E402
from audit.completer import complete_boq  # noqa: E402
from evaluation.dataset import load_manifest, project_dir, uploaded_from_manifest, verify_manifest  # noqa: E402
from evaluation.metrics import PredLine, Scorecard, pred_lines_from_boq, score  # noqa: E402
from evaluation.network import DrawingType  # noqa: E402
from evaluation.ratios import load_ratio_model  # noqa: E402
from evaluation.reference import RefBuilding, ReferenceBoq, load_reference  # noqa: E402

PROJECT = "Project (all buildings)"


# ─── running the pipelines ───────────────────────────────────────────

_DXF_ROLES = ("sld", "lighting_layout", "plug_layout", "site_plan")


def _attribute_dxf(boq: BillOfQuantities, manifest) -> Dict[str, BillOfQuantities]:
    """Project-run lines → buildings, by the drawing each line came from (its drawing_ref)."""
    building_of = {Path(f.path).stem: f.building for f in manifest.files}
    per_building: Dict[str, BillOfQuantities] = {}
    for ln in boq.line_items:
        bld = building_of.get(ln.drawing_ref) or "(unattributed)"
        per_building.setdefault(bld, BillOfQuantities(pipeline="dxf", project_name=bld)).line_items.append(ln)
    return per_building


def run_dxf(project: str, manifest, ref: ReferenceBoq) -> Tuple[Dict[str, BillOfQuantities], List[str]]:
    """The whole DWG set as ONE project run — exactly what a user uploading the set gets:
    boards/feeders from every SLD, feeder routes measured on the site plan, fittings from
    every layout. Lines are attributed to buildings by the drawing they came from."""
    from agent.dxf_pipeline.passes.run import run_dxf_project
    files = [f for f in manifest.files
             if f.path.lower().endswith(".dwg") and not f.superseded and f.role in _DXF_ROLES]
    t = time.perf_counter()
    run = run_dxf_project([((project_dir(project) / f.path).read_bytes(), Path(f.path).name) for f in files],
                          project=ProjectMetadata(project_name=project), persist=True)
    log = [f"DWG set ({len(files)} drawings) | run {run.run_id} | "
           f"{len(run.boq.line_items) if run.boq else 0} lines | site plan: {run.site_plan_file or 'none'} | "
           f"feeders measured on it: {run.routes_measured} | "
           f"{'ok' if run.success else 'FAILED: ' + str(run.error)[:60]} | {time.perf_counter() - t:.0f}s"]
    log += [f"  {n.role or '?'}: {n.file_name}" + ("" if n.ok else f" (FAILED: {n.error[:60]})") for n in run.files]
    return (_attribute_dxf(run.boq, manifest) if run.boq else {}), log


def _db_tokens(ref: ReferenceBoq) -> Dict[str, str]:
    """DB name token → building, learned from the reference DB lines ('DB CR:' → Swimming Pool)."""
    out: Dict[str, str] = {}
    for b in ref.billed_buildings():
        for l in b.lines:
            if l.key_family == "db":
                m = re.match(r"\s*((?:main\s+)?db[\s\-]*[a-z0-9]*(?:\s*\d)?)", l.description, re.I)
                if m:
                    out[re.sub(r"[\s\-]+", "", m.group(1).lower())] = b.name
    return out


def load_dxf_runs(run_ids: List[str], ref: ReferenceBoq, manifest=None) -> Tuple[Dict[str, BillOfQuantities], List[str]]:
    """Re-score saved DXF runs (free, reproducible). A project run (several drawings) is
    attributed by drawing; an older single-drawing run's project_name is its building."""
    import json
    per_building: Dict[str, BillOfQuantities] = {}
    log: List[str] = []
    for rid in run_ids:
        raw = json.loads((Path("runs/dxf") / f"{rid}.json").read_text(encoding="utf-8"))
        bld = raw.get("project_name", "")
        boq = BillOfQuantities.model_validate(raw["boq"]) if raw.get("boq") else None
        log.append(f"{bld} | {raw.get('input_file')} | saved run {rid} | {len(boq.line_items) if boq else 0} lines")
        if boq and manifest is not None and len(raw.get("files") or []) > 1:
            for b, part in _attribute_dxf(boq, manifest).items():
                per_building.setdefault(b, BillOfQuantities(pipeline="dxf", project_name=b)).line_items.extend(part.line_items)
            continue
        if boq and ref.building(bld) is not None:
            merged = per_building.setdefault(bld, BillOfQuantities(pipeline="dxf", project_name=bld))
            merged.line_items.extend(boq.line_items)
            merged.gaps.extend(boq.gaps)
    return per_building, log


def _attribute_pdf(boq: BillOfQuantities, ref: ReferenceBoq) -> Dict[str, BillOfQuantities]:
    tokens = _db_tokens(ref)
    per_building: Dict[str, BillOfQuantities] = {}
    for ln in boq.line_items:
        blk = re.sub(r"[\s\-]+", "", (ln.building_block or "").lower())
        bld = next((b for t, b in tokens.items() if t and (t in blk or blk in t) and blk), None)
        bld = bld or "(unattributed)"
        per_building.setdefault(bld, BillOfQuantities(pipeline="pdf", project_name=bld)).line_items.append(ln)
    return per_building


def load_pdf_run(run_id: str, ref: ReferenceBoq) -> Tuple[Dict[str, BillOfQuantities], List[str]]:
    """Re-score a saved PDF run without paying for the LLM again."""
    import json
    raw = json.loads((Path("runs/pdf") / f"{run_id}.json").read_text(encoding="utf-8"))
    boq = BillOfQuantities.model_validate(raw["boq"])
    log = [f"saved PDF run {run_id} | pages {raw.get('page_count')} | {len(boq.line_items)} lines | "
           f"original cost R {raw.get('cost_zar', 0):.2f} (re-scored at R 0)"]
    for fc in raw.get("files", []):
        log.append(f"  classified {fc['file_name']} → {fc['sheet_type']} ({fc['confidence']:.0%})")
    return _attribute_pdf(boq, ref), log


def run_pdf(project: str, manifest, ref: ReferenceBoq) -> Tuple[Dict[str, BillOfQuantities], List[str]]:
    """One PDF run over the whole set; lines attributed to buildings via DB names."""
    from agent.pdf_pipeline.passes.run import run_pdf_estimator
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        try:
            import tomllib
            key = tomllib.load(open(".streamlit/secrets.toml", "rb")).get("ANTHROPIC_API_KEY")
        except Exception:  # noqa: BLE001
            key = None
    if not key:
        raise SystemExit("No ANTHROPIC_API_KEY (env or .streamlit/secrets.toml) — PDF baseline needs it.")
    files = [(project_dir(project) / f.path).read_bytes() for f in manifest.files if f.role.startswith("pdf_")]
    names = [Path(f.path).name for f in manifest.files if f.role.startswith("pdf_")]
    t = time.perf_counter()
    run = run_pdf_estimator(list(zip(files, names)), api_key=key,
                            project=ProjectMetadata(project_name=project), persist=True)
    log = [f"PDF set ({', '.join(names)}) | run {run.run_id} | pages {run.page_count} | "
           f"{len(run.boq.line_items) if run.boq else 0} lines | cost R {run.cost_zar:.2f} | "
           f"{'ok' if run.success else 'FAILED: ' + str(run.error)[:80]} | {time.perf_counter() - t:.0f}s"]
    for fc in run.files:
        log.append(f"  classified {fc.file_name} → {fc.sheet_type.value} ({fc.confidence:.0%})")
    if not run.boq:
        return {}, log
    return _attribute_pdf(run.boq, ref), log


# ─── scoring ─────────────────────────────────────────────────────────

def _project_ref(ref: ReferenceBoq) -> ReferenceBoq:
    lines = [l.model_copy(update={"building": PROJECT}) for b in ref.billed_buildings() for l in b.lines]
    return ReferenceBoq(project=ref.project, buildings=[RefBuilding(name=PROJECT, sheet="*", lines=lines, in_summary=True)])


def score_runs(per_building: Dict[str, BillOfQuantities], ref: ReferenceBoq, manifest, source: str,
               pipeline: str, *, completed: bool, model) -> Tuple[Scorecard, Scorecard]:
    billed = [b.name for b in ref.billed_buildings()]
    pred: List[PredLine] = []
    all_lines: List[PredLine] = []
    uploaded = {}
    for name in billed:
        uploaded[name] = uploaded_from_manifest(manifest, name, source=source)
    for name, boq in per_building.items():
        if name == PROJECT:
            continue
        b = complete_boq(boq, model, building=name) if completed and name in billed else boq
        lines = pred_lines_from_boq(b, building=name)
        pred += lines
        all_lines += [p.model_copy(update={"building": PROJECT}) for p in lines]
    per_b = score(pred, ref, uploaded=uploaded, pipeline=pipeline, buildings=billed)
    union = set().union(*uploaded.values()) if uploaded else set()
    proj = score(all_lines, _project_ref(ref), uploaded={PROJECT: union}, pipeline=pipeline, buildings=[PROJECT])
    return per_b, proj


def _row(label: str, c: Scorecard) -> str:
    s = c.scoped
    return (f"| {label} | **{c.reproduction_score:.1%}** | {c.coverage:.1%} | {c.precision:.1%} | "
            f"{c.qty_accuracy:.1%} | {c.rate_accuracy:.1%} | {s.get('reproduction_score', 0):.1%} | "
            f"R {c.predicted_value:,.0f} |")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--pipeline", choices=["dxf", "pdf"], required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--from-runs", nargs="+", metavar="RUN_ID",
                    help="re-score saved runs under runs/<pipeline>/ instead of running the pipeline")
    args = ap.parse_args()

    manifest = load_manifest(args.project)
    problems = verify_manifest(manifest, project_dir(args.project))
    if problems:
        raise SystemExit("Raw inputs do not match the manifest:\n" + "\n".join(problems))
    ref = load_reference(args.project)
    model = load_ratio_model(args.project)

    if args.pipeline == "dxf":
        per_building, log = (load_dxf_runs(args.from_runs, ref, manifest) if args.from_runs
                             else run_dxf(args.project, manifest, ref))
        source = "dwg"
    else:
        per_building, log = (load_pdf_run(args.from_runs[0], ref) if args.from_runs
                             else run_pdf(args.project, manifest, ref))
        source = "pdf"

    from evaluation.report import render_markdown
    raw_b, raw_p = score_runs(per_building, ref, manifest, source, args.pipeline, completed=False, model=model)
    cmp_b, cmp_p = score_runs(per_building, ref, manifest, source, args.pipeline, completed=True, model=model)

    md = [f"# Baseline — {args.project} · {args.pipeline.upper()} pipeline", "",
          f"Reference: {ref.source_file} · scored value R {raw_b.reference_value:,.0f} "
          "(billed buildings' priced lines; excl. contingency, VAT, P&Gs). "
          "Scorer: `evaluation/metrics.py` (frozen).", "",
          "| Scoring view | RS | Coverage | Precision | Qty acc | Rate acc | RS scoped | Predicted value |",
          "|---|---:|---:|---:|---:|---:|---:|---:|",
          _row("Per building — pipeline as-is", raw_b),
          _row("Per building — + completer", cmp_b),
          _row("Project-level — pipeline as-is", raw_p),
          _row("Project-level — + completer", cmp_p),
          "", "**RS** = Reproduction Score (value-weighted share of the reference reproduced, "
          "discounted by quantity error). **Scoped** = only items the uploaded drawings can "
          "support (see `reports/audits/wedela-drawing-sufficiency.md`).", "",
          "## Run log", "", *[f"- {l}" for l in log], "",
          "---", "", "# Detail — project-level, pipeline as-is", "",
          render_markdown(raw_p, title="Project-level scorecard").split("\n", 1)[1],
          "---", "", "# Detail — per building, + completer", "",
          render_markdown(cmp_b, title="Per-building scorecard").split("\n", 1)[1]]
    text = "\n".join(md)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"Wrote {args.out}")
    for label, c in (("per-building raw", raw_b), ("per-building +completer", cmp_b),
                     ("project raw", raw_p), ("project +completer", cmp_p)):
        print(f"{label:26} RS {c.reproduction_score:6.1%}  coverage {c.coverage:6.1%}  "
              f"precision {c.precision:6.1%}  qty {c.qty_accuracy:6.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
