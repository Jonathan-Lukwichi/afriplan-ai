---
name: consolidating-price-catalogue
description: Use when a new supplier price list, quotation, catalogue or pricing schedule arrives (doe/knowledge/price_lists/ or Downloads), when a user wants to change, discount or date a price, when prices look stale or a BoQ line has no price, or when changing scripts/build_price_catalogue.py, api/sourcing/catalogue.py, data/catalogue/ or how the web app links prices to items.
---

# Consolidating the price catalogue

## Overview
Every price AfriPlan knows lives in ONE catalogue: one row per product with **supplier, part no.,
description, family, poles/amps/kA, list price excl. VAT, price date and price source**. Price lists
are parsed by deterministic Python (no LLM — a price is never read by AI eyes alone); a user's
own prices live in `data/catalogue/price_overrides.csv`, which a rebuild applies on top and never
overwrites. Read `data/catalogue/README.md` for the user-facing side.

## Quick reference
| Task | How |
|---|---|
| Rebuild | `$PY scripts/build_price_catalogue.py` (`--skip-pdf` for a quick rebuild without the slow Schneider PDF) |
| Change / discount / date a price | add a row to `price_overrides.csv` (`item_id`, price, `price_date`, `updated_by`, `note`, `discount_pct`), rebuild |
| Add your own item | override row with a new `item_id` (`supplier:part`), `supplier`, `description` |
| Read it in code | `sourcing.catalogue.load_catalogue(path)` → `CatalogueItem` list |
| Where it goes | `data/catalogue/` — gitignored except README (commercial prices; public repo) |

## PC — rules
| ID | Rule |
|---|---|
| PC-1 | Every row has a `price_date`. A price with no date is not used for a tender. |
| PC-2 | `price_source` says where the number came from: `price list`, `AfriPlan estimate`, `override: <who> — <note>`. |
| PC-3 | Prices are **list prices excl. VAT** in ZAR; trade discount is `discount_pct`, net = list × (1 − d/100). VAT is added once on the bill summary (CLAUDE.md rule 10). |
| PC-4 | Overrides win over price lists; a newer price-list date does **not** silently replace an override — report it so the user decides. |
| PC-5 | `item_id` = `<supplier slug>:<part no>`, permanent; AfriPlan estimates are `afriplan:<constants key>`. |
| PC-6 | `family` comes from `classify_family` (keyword rules, first match wins); `other` means "needs a rule" — log it. |
| PC-7 | A pricing *schedule* without prices (e.g. a tender's supply schedule) is an item list, not a price source — never enter zeros as prices. |
| PC-8 | A supplier directory gives supplier names and roles only — never people's names, phones or e-mails. |
| PC-9 | Commercial price files and the built catalogue stay out of git (hard rule 9 spirit); grep staged files before a push. |
| PC-10 | Spreadsheet-made PDFs: read text **spans** placed by the header's column edges (`read_schneider_pdf`, ~30 s for 193 pages), not table detection (~45 min, and it pushed description letters into the price cell). Split a glued span only where the next column has no span of its own. |
| PC-11 | Part numbers can be clipped in the PDF (Excel cuts text at the cell edge), so one printed part may be several products: keep each as `<id>~2`, `~3` with its own description — never merge or drop them; only an exact repeat (same description and price) is dropped. |
| PC-12 | After every build check the printed counts: rows without a price (≈0 is right), exact repeats, and the size of `other`. A jump in any of them means the layout changed — inspect before using. |

## Adding a new price source
1. Put the document in `doe/knowledge/price_lists/` and add it to `doe/knowledge/SOURCES.md`.
2. Look at its structure first (`page.find_tables()` for PDF tables; `openpyxl` for Excel). Note the
   columns, price format ("ZAR 1 234,00"), the price date (document metadata or cover) and the unit.
3. Failing test first (skill `tdd`) in `tests/sourcing_layer/test_catalogue.py`: a few synthetic rows in
   that layout → expected items (id, family, price, date). No real supplier rows in tests.
4. Add a pure `parse_<supplier>_rows(rows, *, source, price_date)` in `api/sourcing/catalogue.py`, plus a
   reader if the format is new; wire it into `scripts/build_price_catalogue.py` with its own `SourceDoc`.
5. Rebuild; check the printed counts (items, rows without a price, families). A large `other` family or
   many skipped rows means the parser is wrong — fix before using it.
6. Log the source and anything surprising in `FEEDBACK.md` (skill `improving-boq-skills`).

## Linking prices to BoQ lines (web app — not done yet, ask first)
The catalogue is not yet read by the pricer: `agent/shared/pricing.py` / `core/rate_model.py` still use
`core/constants.py`, and `sourcing` has a planned `price_list` channel (`sourcing/__init__.py`). Linking
changes every bill's rates and every baseline, so **ask first**, then: match a line by family + key
attributes (poles, amps, kA, mm², cores), prefer override > newest price list > estimate, write the
`item_id` and `price_date` into the line's assumption, re-run all baselines and report the change.

## Common mistakes
| Mistake | Fix |
|---|---|
| Typing a new price into `price_catalogue.csv` | it is rebuilt — use `price_overrides.csv` |
| Treating a list price as the contractor's cost | apply `discount_pct`; flag when none is set |
| Committing the catalogue or a supplier's PDF | both are gitignored; keep it so |

## Version
v1 · 2026-10-29 · Schneider 2026 list, AfriPlan estimates (Feb 2026), Sparks supplier directory (Sept 2019).

v2 · 2026-10-29 · span reader (45 min → 32 s), repeats kept, glued cells split, automation family; see FEEDBACK.md.
