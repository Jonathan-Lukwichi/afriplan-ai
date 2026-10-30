# Current state (update when it changes)

Moved out of `CLAUDE.md` on 2026-10-29 to keep it a short signpost. What to work on next lives
in `context/priorities.md`.

- Reference project: **wedela** (7 billed buildings). Baselines (`reports/baselines/README.md`),
  project-level Reproduction Score (2026-09-27): **DXF 44.6 %** (45.3 % with completer),
  **PDF 27.1 %** (Opus 5, pages read in parallel, ~5 min; the Wedela PDF set has no site plan, so its feeder lengths stay assumed).
- Optional **AI symbol names** (ADR-0007): loose-line-work symbols are grouped into shapes
  (`dxf_pipeline/passes/shapes.py`, no LLM), named once by `api/assist/symbol_namer.py`
  from a fixed catalogue (`agent/shared/symbol_catalogue.py`), remembered in `symbol_names`;
  Wedela DXF 44.8 % → **46.2 %** (49.2 % with completer) for ~R 1.
- A DWG/DXF **set** runs as one project (`run_dxf_project`): feeders from every SLD are
  measured on the electrical site plan (`agent/shared/routes.py` + each pipeline's
  `passes/site_routes.py`); the PDF pipeline measures vector site-plan PDFs the same way.
- **One bill from both readers** (ADR-0008): each engine states *findings* (`agent/shared/findings.py`,
  with evidence: measured > counted > written > seen > assumed) priced by ONE pricer
  (`agent/shared/pricing.py`). `api/consolidate/combine.py` merges the two readers' findings
  (PDF pages paired with CAD sheets by shared words, `agent/shared/sheets.py`); names Python cannot
  pair go to the injected AI matcher `api/assist/finding_matcher.py`. Wedela combined **47.2 %**.
- **DOE workflow** (2026-10-02, `doe/execution/project.py` + skill `estimate-project`): PDF pages
  read by Claude Code on the subscription → Wedela PDF **47.5 %** (Claude API 27.1 %, Gemini free
  40.2 %); combined with the DWG set **55.8 % — the best so far**. Forms are saved per page so every
  result can be reproduced; a missing or invalid form stops `finish`. With the 2026-10-02 form
  boxes: **58.5 %** (CAD alone 48.7 %, PDF alone 50.6 %).
- **Accuracy report** (`docs/accuracy-metrics.md`): `finish --reference <p>` writes
  `accuracy_report.md/.json` — every reader's metrics and the missing points split by item, cause
  and kind of fix (`evaluation/gaps.py`); dated copies in `reports/accuracy/` (gitignored). Wedela's
  biggest gaps: feeder cable sizes, boards counted twice, derived material not produced, trench length.
- **Current aim = READING accuracy** (`evaluation/reading.py`, pricing judged later): only items counted or
  measured on the uploaded drawings, weighted by the real bill, our rates never enter. Wedela DOE combined
  **67.5 %** (CAD 53.2 %, PDF 59.7 %). Recheck each loss against the drawing — the reference is a priced
  bill: part of the loss is the bill differing from the drawing, not misreading. Next: a drawing ground truth.
  A person checked 20 items of Claude's own drawing reading (6 Oct): **19 correct, 0 wrong, 1 blank**. Verdict and
  data plan (5 projects from 3+ consulting firms) in `docs/accuracy-metrics.md` §2c.
- **Wiring** (2026-10-29): final-circuit wiring is billed four ways; South African bills use
  convention A (material by material), which neither engine produces yet
  (`doe/knowledge/BOQ_KNOWLEDGE.md` §6).
- **CI** (GitHub Actions, `.github/workflows/ci.yml`: Python, build, browser tests, client-data check) is on
  branches `ci/github-actions` and `chore/claude-playbook`, green,
  not yet merged into `main` (2026-10-26).
- **Take-off check** (2026-10-30, `scripts/check_takeoff.py`, skill `check-takeoff`): the synthetic
  sample PASSES (11 downlights, 13 double sockets, 1 board, 34.25 m wiring, exact, identical twice).
  Getting there fixed issue 015: Windows-saved (CRLF) DXFs were read as empty drawings, unnamed
  symbols were priced without a gap, underscore block names were not classified. Wedela DXF
  unchanged (44.8 % project-level). Next: real drawings with hand counts in `data/takeoff_tests/`.
- **Price catalogue** (2026-10-29): 13.5k dated items — Schneider 2026 list prices (excl. VAT, before trade
  discount), the AfriPlan estimates and 58 supplier names; user prices in `data/catalogue/price_overrides.csv`.
  Shown on Live Pricing as a dated "list price" supplier for breakers / earth leakage / surge (never
  auto-applied); not yet read by the pricer — that step changes every bill's rates and needs approval.
- Streamlit app retired 2026-09-26; its final state is the tag `archive/legacy-streamlit-2026-09-26`.
