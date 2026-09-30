"""
LAYER 3 — EXECUTION. One deterministic command: drawings in, priced BoQ + evaluation out.

    python doe/execution/estimate.py --project wedela --pdf-run 41c02f9505b0

Steps (no step invents a number; the same inputs always give the same files):
  1. DWG/DXF set → findings (geometry, SLD text, site-plan routes; saved AI symbol names
     are reused for free — no new AI call).
  2. PDF set → findings: a saved PDF run's facts re-priced (R 0), or a fresh PDF run with
     --pdf-fresh (uses the AI provider in api/.env: Claude or free Gemini).
  3. Combine the two readers (api/consolidate) — no AI matcher unless --ai-match.
  4. Price once (agent/shared/pricing.py: crew×hours rate model + price lists).
  5. Documents: tender Excel + PDF (api/exports — the same style as the web app).
  6. Evaluation against the project's real priced bill (frozen scorer): DWG alone,
     PDF alone and combined, with a verdict against the playbook's reliability levels.

Outputs go to runs/doe/<stamp>/ — gitignored, because they contain client figures.
Reuses the app's modules read-only; it changes nothing in the web app.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8")

# Reliability levels — the playbook's definition (doe/playbook/PLAYBOOK.md §5).
LEVELS = [
    ("Near-estimator quality", 0.85, 0.90, 0.10),
    ("Reliable assistant", 0.75, 0.90, 0.15),
    ("Useful draft", 0.60, 0.90, None),
]


def verdict(rs: float, precision: float, total_err: float) -> str:
    for name, rs_min, p_min, tot_max in LEVELS:
        if rs >= rs_min and precision >= p_min and (tot_max is None or total_err <= tot_max):
            return name
    return "Not yet reliable — a person must check every line"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default="wedela")
    ap.add_argument("--pdf-run", default="41c02f9505b0", help="saved PDF run whose facts are re-priced (R 0)")
    ap.add_argument("--pdf-fresh", action="store_true", help="read the PDFs again with the AI (see api/.env)")
    ap.add_argument("--ai-match", action="store_true", help="match leftover names with the AI when combining")
    ap.add_argument("--out", type=Path, help="output folder (default runs/doe/<stamp>)")
    args = ap.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / "api" / ".env")
    except ImportError:
        pass
    import os
    os.chdir(ROOT)

    import run_baseline as rb
    from agent.dxf_pipeline.passes.run import run_dxf_project
    from agent.pdf_pipeline.passes.assemble import findings_from_facts
    from agent.pdf_pipeline.passes.facts import PdfFacts
    from agent.pdf_pipeline.passes.run import ingest_files, page_sheets_and_words, run_pdf_estimator
    from agent.pdf_pipeline.passes.site_routes import read_pdf_site_routes
    from agent.shared import ProjectMetadata
    from agent.shared.pricing import price_findings
    from consolidate.combine import combine
    from db.symbol_names import load_symbol_names
    from evaluation.dataset import load_manifest, project_dir, verify_manifest
    from evaluation.ratios import load_ratio_model
    from evaluation.reference import load_reference
    from exports.excel_boq import export_boq_to_excel
    from exports.pdf_boq import export_boq_to_pdf

    started = time.perf_counter()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = args.out or ROOT / "runs" / "doe" / stamp
    out.mkdir(parents=True, exist_ok=True)
    log = []

    def say(msg: str) -> None:
        print(msg, flush=True)
        log.append(msg)

    manifest = load_manifest(args.project)
    problems = verify_manifest(manifest, project_dir(args.project))
    if problems:
        say("STOP: raw drawings do not match the manifest:\n" + "\n".join(problems))
        return 2
    ref = load_reference(args.project)
    model = load_ratio_model(args.project)
    meta = ProjectMetadata(project_name=args.project)

    # 1 — DWG set (free). Saved AI symbol names only: no AI call.
    remembered = load_symbol_names()
    namer = lambda groups, legend: ({g.signature: remembered[g.signature] for g in groups     # noqa: E731
                                     if g.signature in remembered}, 0.0)
    dwg_files = [f for f in manifest.files
                 if f.path.lower().endswith(".dwg") and not f.superseded and f.role in rb._DXF_ROLES]
    dxf = run_dxf_project([((project_dir(args.project) / f.path).read_bytes(), Path(f.path).name)
                           for f in dwg_files], project=meta, name_shapes=namer)
    say(f"1. DWG: {len(dwg_files)} drawings, {len(dxf.boq.line_items)} lines, site plan "
        f"'{dxf.site_plan_file or 'none'}', {dxf.routes_measured} feeders measured")

    # 2 — PDF set
    pdf_files = [((project_dir(args.project) / f.path).read_bytes(), Path(f.path).name)
                 for f in manifest.files if f.role.startswith("pdf_")]
    if args.pdf_fresh:
        run = run_pdf_estimator(pdf_files, project=meta, persist=True)
        if not run.success:
            say(f"STOP: fresh PDF run failed: {run.error}")
            return 3
        facts, pdf_note = run.facts, f"fresh PDF run {run.run_id} (R {run.cost_zar:.2f})"
    else:
        raw = json.loads((ROOT / "runs" / "pdf" / f"{args.pdf_run}.json").read_text(encoding="utf-8"))
        facts, pdf_note = PdfFacts.model_validate(raw["facts"]), f"saved PDF run {args.pdf_run} re-priced (R 0)"
    _, ingests = ingest_files(pdf_files)
    page_sheets, words = page_sheets_and_words(pdf_files, ingests)
    routes, _ = read_pdf_site_routes(pdf_files)
    pdf = findings_from_facts(facts, routes=routes, page_sheets=page_sheets)
    pdf.sheet_words = words
    pdf_boq = price_findings(pdf, pipeline="pdf", project_name=args.project)
    say(f"2. PDF: {pdf_note}, {len(pdf_boq.line_items)} lines")

    # 3 — combine
    matcher = None
    if args.ai_match:
        from agent.pdf_pipeline.llm import make_ai_client
        from assist.finding_matcher import make_name_matcher
        matcher = make_name_matcher(client=make_ai_client())
    c = combine(dxf.findings, pdf, match_names=matcher)
    say(f"3. Combined: {len(c.sheet_pairs)} PDF pages paired with their DWG sheet, "
        f"{c.ai_matched} names matched by AI, {len(c.decisions)} decisions")

    # 4 — price once
    boq = price_findings(c.findings, pipeline="combined", project_name=args.project, run_id=stamp)
    say(f"4. Priced: {len(boq.line_items)} lines, {len(boq.gaps)} things to check")

    # 5 — documents
    base = f"AfriPlan_BoQ_{args.project}_{stamp}"
    xlsx, pdfp = out / f"{base}.xlsx", out / f"{base}.pdf"
    xlsx.write_bytes(export_boq_to_excel(boq, project=meta))
    pdfp.write_bytes(export_boq_to_pdf(boq, project=meta))
    say(f"5. Documents: {xlsx.name} ({xlsx.stat().st_size // 1024} KB), {pdfp.name} ({pdfp.stat().st_size // 1024} KB)")

    # 6 — evaluation (frozen scorer), project level
    scored = {}
    for label, per_building, source in (
        ("DWG alone", rb._attribute_dxf(dxf.boq, manifest), "dwg"),
        ("PDF alone", rb._attribute_pdf(pdf_boq, ref), "pdf"),
        ("Combined (delivered)", rb._attribute_combined(boq, manifest, ref), "all"),
    ):
        _, p = rb.score_runs(per_building, ref, manifest, source, label, completed=False, model=model)
        total_err = abs(p.predicted_value - p.reference_value) / p.reference_value if p.reference_value else 1.0
        scored[label] = {"rs": p.reproduction_score, "coverage": p.coverage, "precision": p.precision,
                         "qty": p.qty_accuracy, "rate": p.rate_accuracy, "total_err": total_err,
                         "verdict": verdict(p.reproduction_score, p.precision, total_err)}
    say("6. Evaluation: " + "; ".join(f"{k} RS {v['rs']:.1%}" for k, v in scored.items()))

    rows = "\n".join(
        f"| {k} | **{v['rs']:.1%}** | {v['coverage']:.1%} | {v['precision']:.1%} | {v['qty']:.1%} | "
        f"{v['rate']:.1%} | {v['total_err']:.1%} | {v['verdict']} |" for k, v in scored.items())
    top_gaps = sorted(boq.gaps, key=lambda g: {"high": 0, "medium": 1, "low": 2}[g.severity])[:10]
    report = f"""# AfriPlan DOE run — {args.project} — {stamp}

| Source | Reproduction Score | Coverage | Precision | Qty accuracy | Rate accuracy | Total off by | Level |
|---|---:|---:|---:|---:|---:|---:|---|
{rows}

Scored with the frozen scorer against the project's real priced bill (project level).
Reliability levels: see doe/playbook/PLAYBOOK.md §5 — one project is not proof.

## Run log
""" + "\n".join(f"- {l}" for l in log) + "\n\n## Top things to check\n" + \
        "\n".join(f"- [{g.severity}] {g.description}" for g in top_gaps) + "\n"
    (out / "evaluation.md").write_text(report, encoding="utf-8")

    # e-mail material for the brain (layer 2)
    comb = scored["Combined (delivered)"]
    body = (f"AfriPlan estimate - {args.project} - run {stamp}\n\n"
            f"Attached: the combined BoQ (Excel + PDF), priced by the deterministic rate model.\n\n"
            "How close to the real priced bill (Reproduction Score, frozen scorer):\n"
            + "\n".join(f"  {k}: {v['rs']:.1%}  (found {v['coverage']:.0%} of the bill's value, "
                        f"{v['precision']:.0%} of what was priced belongs in it)  -> {v['verdict']}"
                        for k, v in scored.items())
            + f"\n\nDelivered level: {comb['verdict']}.\n"
            f"Things to check in the bill: {len(boq.gaps)} (top items in evaluation.md).\n\n"
            "Run log:\n" + "\n".join(f"  {l}" for l in log)
            + f"\n\nFiles on disk: {out}\n")
    (out / "email_body.txt").write_text(body, encoding="utf-8")
    att = out / "attachments"
    att.mkdir(exist_ok=True)
    for p in (xlsx, pdfp):                      # base64 in 1000-character lines, for the mail tool
        b = base64.b64encode(p.read_bytes()).decode()
        (att / f"{p.name}.b64").write_text("\n".join(b[i:i + 1000] for i in range(0, len(b), 1000)),
                                           encoding="ascii")
    summary = {"stamp": stamp, "project": args.project, "out": str(out), "xlsx": str(xlsx), "pdf": str(pdfp),
               "scores": scored, "lines": len(boq.line_items), "gaps": len(boq.gaps),
               "subtotal_zar": boq.subtotal_zar, "duration_s": round(time.perf_counter() - started, 1)}
    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    say(f"Done in {summary['duration_s']}s -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
