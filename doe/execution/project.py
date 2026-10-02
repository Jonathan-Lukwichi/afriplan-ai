"""
LAYER 3 — EXECUTION: any electrical project folder in, a professional BoQ out.

    python doe/execution/project.py prepare "<project folder>"
    #   → the brain (Claude Code, subscription) reads <folder>/AfriPlan_Output/work/pages/*
    #     and writes one form per PDF page in .../work/forms/  (skill: estimate-project)
    python doe/execution/project.py finish  "<project folder>" [--reference wedela]

prepare  finds every .dwg/.dxf/.pdf under the folder (older revisions of a sheet are set
         aside), renders each PDF page (whole page + 4 zoomed quarters + the legend /
         quantity table at high zoom + its text layer) and writes the forms' instructions
         and strict schemas. Deterministic: the same folder always gives the same pages.
finish   checks every form against the strict schemas (a bad or missing form STOPS the run),
         reads the DWG/DXF set (geometry, SLD text, site-plan routes; remembered symbol names,
         no AI call), merges the PDF forms like the API engine does, combines both readers
         (stronger evidence wins, nothing counted twice), prices once with the rate model and
         writes into <folder>/AfriPlan_Output/:
             <Project>_BoQ_<stamp>.xlsx   tender Excel
             <Project>_BoQ_<stamp>.pdf    tender PDF
             things_to_check.md           every doubt, most serious first
             summary.json                 counts, totals, decisions (+ scores with --reference)
         --reference <project>: also score against that reference project's real bill.
         --pdf-reader api: read the PDFs with the AI provider in api/.env instead of forms.
         --pdf-reader none: DWG/DXF only.

No step invents a number: the brain only reports what is drawn; Python validates, merges,
measures and prices. Reuses the app's engines read-only; nothing in the web app changes.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8")

OUT_DIR = "AfriPlan_Output"
CAD = (".dwg", ".dxf")


# ─── discovery ───────────────────────────────────────────────────────

def discover(folder: Path):
    """(cad files, pdf files, {older file: newer file}) — sorted, outputs excluded."""
    from agent.dxf_pipeline.passes.revisions import pick_latest_revisions
    files = sorted(p for p in folder.rglob("*") if p.is_file() and OUT_DIR not in p.parts
                   and p.suffix.lower() in (*CAD, ".pdf"))
    _, superseded = pick_latest_revisions([p.name for p in files])
    keep = [p for p in files if p.name not in superseded]
    return ([p for p in keep if p.suffix.lower() in CAD], [p for p in keep if p.suffix.lower() == ".pdf"],
            superseded)


def work_dir(folder: Path) -> Path:
    return folder / OUT_DIR / "work"


# ─── prepare: pages for the brain's eyes ─────────────────────────────

def prepare(folder: Path, dpi: int = 200) -> int:
    import fitz
    from PIL import Image

    from agent.pdf_pipeline.prompts.pass_prompts import PROMPT_BY_PASS_TOOL
    from agent.pdf_pipeline.prompts.pass_schemas import PASS_TOOLS

    cad, pdfs, superseded = discover(folder)
    wd = work_dir(folder)
    (wd / "pages").mkdir(parents=True, exist_ok=True)
    (wd / "forms").mkdir(exist_ok=True)
    pages = []
    index = 0                                   # global page index, as the PDF engine numbers pages
    for pdf in pdfs:
        doc = fitz.open(pdf)
        for local, page in enumerate(doc):
            tag = f"p{index:02d}"
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            whole = img.copy()
            whole.thumbnail((2200, 2200))
            whole.save(wd / "pages" / f"{tag}.png", optimize=True)
            w, h = img.size
            ox, oy = int(w * 0.06), int(h * 0.06)
            for q, box in enumerate([(0, 0, w // 2 + ox, h // 2 + oy), (w // 2 - ox, 0, w, h // 2 + oy),
                                     (0, h // 2 - oy, w // 2 + ox, h), (w // 2 - ox, h // 2 - oy, w, h)], 1):
                part = img.crop(box)
                part.thumbnail((2200, 2200))
                part.save(wd / "pages" / f"{tag}_q{q}.png", optimize=True)
            legend = _legend_crops(page, wd / "pages", tag)
            text = page.get_text()
            (wd / "pages" / f"{tag}.txt").write_text(text, encoding="utf-8")
            pages.append({"index": index, "file": str(pdf.relative_to(folder)), "page": local,
                          "sheet": f"{pdf.stem} p{local}", "image": f"pages/{tag}.png",
                          "quarters": [f"pages/{tag}_q{q}.png" for q in range(1, 5)],
                          "legend": legend, "text_chars": len(text.strip())})
            index += 1
    (wd / "manifest.json").write_text(json.dumps({
        "folder": str(folder), "cad": [str(p.relative_to(folder)) for p in cad],
        "pdfs": [str(p.relative_to(folder)) for p in pdfs], "superseded": superseded, "pages": pages,
    }, indent=1), encoding="utf-8")
    readme = ["# Forms — one per PDF page: forms/pNN.json", "",
              '{"page_type": <register|notes|sld|lighting_layout|plugs_layout|layout|unknown>,',
              ' "tool": <read_project_context|read_power_spine|read_layout_takeoff|none>, "input": {...}}',
              "`input` must match the tool's schema below exactly (it is checked). Report what is DRAWN:",
              "0 / false / empty when not shown. Never estimate a length, a count or a price.", ""]
    for name, tool in PASS_TOOLS.items():
        readme += [f"## {name}", "", PROMPT_BY_PASS_TOOL[name], "", "```json",
                   json.dumps(tool["input_schema"], indent=1), "```", ""]
    (wd / "forms" / "README.md").write_text("\n".join(readme), encoding="utf-8")
    print(f"{len(cad)} CAD drawings, {len(pdfs)} PDFs ({len(pages)} pages), "
          f"{len(superseded)} older revisions set aside -> {wd}")
    for p in pages:
        extra = f", legend table: {len(p['legend'])} crops" if p["legend"] else ""
        print(f"  p{p['index']:02d}  {p['sheet']}  (text {p['text_chars']} chars{extra})")
    return 0


def _legend_crops(page, out: Path, tag: str) -> list:
    """The legend / quantity table (found by its 'QTY' heading), cropped at 5x zoom."""
    import fitz
    from PIL import Image
    hits = page.search_for("QTY")
    if not hits:
        return []
    rot, r, zoom = page.rotation_matrix, page.rect, 5
    top = min((fitz.Rect(h) * rot).y0 for h in hits)
    words = [fitz.Rect(w[:4]) * rot for w in page.get_text("words")]
    words = [w for w in words if top - r.height * 0.03 <= w.y0 <= top + r.height * 0.08]
    if not words:
        return []
    x0, x1 = min(w.x0 for w in words) - 10, max(w.x1 for w in words) + 10
    full = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    img = Image.frombytes("RGB", (full.width, full.height), full.samples)
    img = img.crop((int(max(0, x0) * zoom), int(max(0, top - r.height * 0.03) * zoom),
                    int(min(r.width, x1) * zoom), int(min(r.height, top + r.height * 0.08) * zoom)))
    w, h = img.size
    names = []
    for i, part in enumerate([img.crop((0, 0, w // 2 + 40, h)), img.crop((w // 2 - 40, 0, w, h))], 1):
        part.thumbnail((2200, 2200))
        part.save(out / f"{tag}_legend{i}.png")
        names.append(f"pages/{tag}_legend{i}.png")
    return names


# ─── finish: forms + CAD → combined, priced BoQ in the project folder ─

def read_forms(wd: Path):
    """PDF facts from the brain's forms. Raises SystemExit on a missing or invalid form."""
    import jsonschema

    from agent.pdf_pipeline.passes import orchestrator as orch
    from agent.pdf_pipeline.passes.facts import PdfFacts
    from agent.pdf_pipeline.prompts.pass_schemas import PASS_TOOLS

    manifest = json.loads((wd / "manifest.json").read_text(encoding="utf-8"))
    facts, problems, report = PdfFacts(), [], []
    for p in manifest["pages"]:
        path = wd / "forms" / f"p{p['index']:02d}.json"
        if not path.exists():
            problems.append(f"p{p['index']:02d} ({p['sheet']}): no form — the page was not read")
            continue
        form = json.loads(path.read_text(encoding="utf-8"))
        tool = form.get("tool", "none")
        if tool not in PASS_TOOLS:
            report.append(f"p{p['index']:02d}: {form.get('page_type')} (nothing billable)")
            continue
        try:
            jsonschema.validate(form["input"], PASS_TOOLS[tool]["input_schema"])
            orch.VALIDATOR_BY_TOOL[tool](**form["input"])
        except Exception as e:  # noqa: BLE001 — a bad form is reported, never half-used
            problems.append(f"p{p['index']:02d}: form rejected ({tool}): {str(e).splitlines()[0][:200]}")
            continue
        orch._merge(facts, tool, form["input"], page=p["index"])
        report.append(f"p{p['index']:02d}: {form.get('page_type')} -> {tool}")
    if problems:
        raise SystemExit("STOP — fix these forms, then run finish again:\n  " + "\n  ".join(problems))
    facts.extraction_gaps.extend(orch._site_lighting_gaps(facts.takeoff))
    facts.extraction_gaps.extend(orch._check_spine_orphans(facts.spine))
    facts.extraction_gaps.extend(orch._check_source_alignment(facts.spine))
    return facts, manifest, report


def finish(folder: Path, *, name: str = "", reference: str = "", pdf_reader: str = "forms",
           ai_match: bool = False) -> int:
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / "api" / ".env")
    except ImportError:
        pass
    from agent.dxf_pipeline.passes.run import run_dxf_project
    from agent.pdf_pipeline.passes.assemble import findings_from_facts
    from agent.pdf_pipeline.passes.site_routes import read_pdf_site_routes
    from agent.shared import ProjectMetadata
    from agent.shared.findings import Findings
    from agent.shared.pricing import price_findings
    from agent.shared.sheets import sheet_words
    from consolidate.combine import combine
    from db.symbol_names import load_symbol_names
    from exports.excel_boq import export_boq_to_excel
    from exports.pdf_boq import export_boq_to_pdf

    started = time.perf_counter()
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    project = name or folder.name
    out = folder / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    meta = ProjectMetadata(project_name=project)
    log = []

    def say(msg: str) -> None:
        print(msg, flush=True)
        log.append(msg)

    cad, pdfs, superseded = discover(folder)
    say(f"Inputs: {len(cad)} CAD drawings, {len(pdfs)} PDFs, {len(superseded)} older revisions set aside")

    # 1 — CAD (free; remembered symbol names, no AI call)
    cad_findings, dxf = Findings(), None
    if cad:
        remembered = load_symbol_names()
        namer = lambda groups, legend: ({g.signature: remembered[g.signature] for g in groups     # noqa: E731
                                         if g.signature in remembered}, 0.0)
        dxf = run_dxf_project([(p.read_bytes(), p.name) for p in cad], project=meta, name_shapes=namer)
        cad_findings = dxf.findings or Findings()
        say(f"1. CAD: {len(dxf.boq.line_items) if dxf.boq else 0} lines; site plan "
            f"'{dxf.site_plan_file or 'none'}', {dxf.routes_measured} feeders measured on it")

    # 2 — PDF
    pdf_findings = Findings()
    pdf_pairs = [(p.read_bytes(), p.name) for p in pdfs]
    if pdfs and pdf_reader != "none":
        routes, _ = read_pdf_site_routes(pdf_pairs)
        if pdf_reader == "api":
            from agent.pdf_pipeline.passes.run import run_pdf_estimator
            run = run_pdf_estimator(pdf_pairs, project=meta)
            if not run.success:
                raise SystemExit(f"STOP — the AI could not read the PDFs: {run.error}")
            facts, how = run.facts, f"AI provider (R {run.cost_zar:.2f})"
            page_sheets = {}
        else:
            facts, manifest, report = read_forms(work_dir(folder))
            page_sheets = {p["index"]: p["sheet"] for p in manifest["pages"]}
            how = f"brain's forms ({len(report)} pages)"
        pdf_findings = findings_from_facts(facts, routes=routes, page_sheets=page_sheets)
        import fitz
        for data, fname in pdf_pairs:
            with fitz.open(stream=data, filetype="pdf") as doc:
                for i, page in enumerate(doc):
                    pdf_findings.sheet_words[f"{Path(fname).stem} p{i}"] = sheet_words([page.get_text()])
        say(f"2. PDF: read by the {how}; {len(facts.spine.distribution_boards)} boards, "
            f"{len(facts.spine.feeders)} feeders, {len(facts.takeoff.rooms)} rooms")

    # 3 — combine, 4 — price once
    matcher = None
    if ai_match:
        from agent.pdf_pipeline.llm import make_ai_client
        from assist.finding_matcher import make_name_matcher
        matcher = make_name_matcher(client=make_ai_client())
    c = combine(cad_findings, pdf_findings, match_names=matcher)
    boq = price_findings(c.findings, pipeline="combined", project_name=project, run_id=stamp)
    say(f"3. Combined: {len(c.sheet_pairs)} PDF pages paired with their CAD sheet, {len(c.decisions)} decisions")
    say(f"4. Priced: {len(boq.line_items)} lines, subtotal R {boq.subtotal_zar:,.2f} excl. VAT, "
        f"{len(boq.gaps)} things to check")

    # 5 — documents in the project folder
    base = f"{_safe(project)}_BoQ_{stamp}"
    xlsx, pdfp = out / f"{base}.xlsx", out / f"{base}.pdf"
    xlsx.write_bytes(export_boq_to_excel(boq, project=meta))
    pdfp.write_bytes(export_boq_to_pdf(boq, project=meta))
    order = {"high": 0, "medium": 1, "low": 2}
    gaps = sorted(boq.gaps, key=lambda g: order.get(g.severity, 3))
    (out / "things_to_check.md").write_text(
        f"# Things to check — {project} — {stamp}\n\n" + "\n".join(
            f"- **{g.severity.upper()}** — {g.description}"
            + (f" *(assumed: {g.assumption})*" if g.assumption else "")
            + (f" → {g.suggested_action}" if g.suggested_action else "") for g in gaps) + "\n",
        encoding="utf-8")
    say(f"5. Documents: {xlsx.name}, {pdfp.name}, things_to_check.md")

    # 6 — optional evaluation against a reference project's real bill
    scores = {}
    if reference:
        scores = _evaluate(reference, boq, dxf.boq if dxf else None,
                           price_findings(pdf_findings, pipeline="pdf", project_name=project) if pdfs else None)
        say("6. Evaluation vs the real bill: " + "; ".join(f"{k} {v['rs']:.1%}" for k, v in scores.items()))

    (out / "summary.json").write_text(json.dumps({
        "project": project, "stamp": stamp, "xlsx": str(xlsx), "pdf": str(pdfp),
        "lines": len(boq.line_items), "gaps": len(boq.gaps), "subtotal_zar": boq.subtotal_zar,
        "total_incl_vat_zar": boq.total_incl_vat_zar, "superseded": superseded,
        "decisions": [d.model_dump() for d in c.decisions], "scores": scores, "log": log,
        "duration_s": round(time.perf_counter() - started, 1),
    }, indent=1), encoding="utf-8")
    say(f"Done in {time.perf_counter() - started:.0f}s -> {out}")
    return 0


def _safe(text: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in text).strip("_") or "Project"


def _evaluate(reference: str, combined, cad_boq, pdf_boq) -> dict:
    import os
    import run_baseline as rb
    from evaluation.dataset import load_manifest
    from evaluation.ratios import load_ratio_model
    from evaluation.reference import load_reference
    os.chdir(ROOT)
    manifest, ref, model = load_manifest(reference), load_reference(reference), load_ratio_model(reference)
    out = {}
    for label, boq, attribute, source in (
            ("CAD alone", cad_boq, lambda b: rb._attribute_dxf(b, manifest), "dwg"),
            ("PDF alone", pdf_boq, lambda b: rb._attribute_pdf(b, ref), "pdf"),
            ("Combined (delivered)", combined, lambda b: rb._attribute_combined(b, manifest, ref), "all")):
        if boq is None:
            continue
        _, p = rb.score_runs(attribute(boq), ref, manifest, source, label, completed=False, model=model)
        out[label] = {"rs": p.reproduction_score, "coverage": p.coverage, "precision": p.precision,
                      "qty": p.qty_accuracy, "rate": p.rate_accuracy,
                      "total_off": abs(p.predicted_value - p.reference_value) / p.reference_value
                      if p.reference_value else None}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["prepare", "finish"])
    ap.add_argument("folder", type=Path, help="the project folder holding the drawings")
    ap.add_argument("--name", default="", help="project name for the documents (default: folder name)")
    ap.add_argument("--reference", default="", help="score against this reference project's real bill")
    ap.add_argument("--pdf-reader", choices=["forms", "api", "none"], default="forms")
    ap.add_argument("--ai-match", action="store_true", help="AI pairs leftover names when combining (paid/free API)")
    args = ap.parse_args()
    folder = args.folder.resolve()
    if not folder.is_dir():
        raise SystemExit(f"STOP — not a folder: {folder}")
    if args.step == "prepare":
        return prepare(folder)
    return finish(folder, name=args.name, reference=args.reference, pdf_reader=args.pdf_reader,
                  ai_match=args.ai_match)


if __name__ == "__main__":
    raise SystemExit(main())
