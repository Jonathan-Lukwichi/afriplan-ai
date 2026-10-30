"""
Build the AfriPlan price catalogue (CSV + Excel) from the price lists in the knowledge folder.

    python scripts/build_price_catalogue.py                       # → data/catalogue/price_catalogue.{csv,xlsx}
    python scripts/build_price_catalogue.py --out-dir some/dir    # elsewhere
    python scripts/build_price_catalogue.py --skip-pdf            # quick: estimates + overrides only

Sources: the Schneider list (doe/knowledge/price_lists/), the AfriPlan estimates (api/core/constants.py)
and the supplier names of the Sparks buyer's guide. Your own prices: data/catalogue/price_overrides.csv
(created empty on the first run) — applied on top on every rebuild, never overwritten.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))
sys.stdout.reconfigure(encoding="utf-8")

from sourcing import catalogue as cat  # noqa: E402

PRICE_LISTS = ROOT / "doe" / "knowledge" / "price_lists"
SCHNEIDER_PDF = PRICE_LISTS / "Schneider Electric Price List 2026.pdf"
SPARKS_TXT = PRICE_LISTS / "Buyers_Guide_Sparks_September_2019.txt"
ESTIMATES_DATE = "2026-02-01"  # api/core/constants.py: "updated Feb 2026"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "data" / "catalogue")
    ap.add_argument("--overrides", type=Path, help="default: <out-dir>/price_overrides.csv")
    ap.add_argument("--skip-pdf", action="store_true", help="do not re-read the Schneider PDF (slow)")
    args = ap.parse_args()
    overrides_path = args.overrides or args.out_dir / "price_overrides.csv"

    items, sources, suppliers = [], [], []
    if not args.skip_pdf and SCHNEIDER_PDF.exists():
        print(f"Reading {SCHNEIDER_PDF.name}…")
        rows, price_date = cat.read_schneider_pdf(SCHNEIDER_PDF)
        stats: dict = {}
        found, skipped = cat.parse_schneider_rows(rows, source=SCHNEIDER_PDF.name, price_date=price_date, stats=stats)
        print(f"  {stats['exact_duplicates']} exact repeats dropped; "
              f"{stats['same_part_other_price']} part numbers listed again at another price kept as <id>~2")
        items += found
        sources.append(cat.SourceDoc(SCHNEIDER_PDF.name, cat.SCHNEIDER, price_date, len(found), skipped))
        suppliers.append(cat.Supplier(cat.SCHNEIDER, "manufacturer", SCHNEIDER_PDF.name, price_date))
    elif not args.skip_pdf:
        print(f"Not found, skipped: {SCHNEIDER_PDF}")

    estimates = cat.items_from_constants(price_date=ESTIMATES_DATE)
    items += estimates
    sources.append(cat.SourceDoc("api/core/constants.py", cat.AFRIPLAN, ESTIMATES_DATE, len(estimates), 0))

    if SPARKS_TXT.exists():
        suppliers += cat.parse_sparks_directory(SPARKS_TXT.read_text(encoding="utf-8"),
                                                source=SPARKS_TXT.with_suffix(".pdf").name, source_date="2019-09-01")

    if not overrides_path.exists():
        overrides_path.parent.mkdir(parents=True, exist_ok=True)
        with overrides_path.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(cat.OVERRIDE_COLUMNS)
        print(f"Created an empty overrides file: {overrides_path}")
    items, problems = cat.apply_overrides(items, cat.read_overrides(overrides_path))
    n_over = sum(1 for i in items if i.price_source.startswith("override"))

    csv_path, xlsx_path = args.out_dir / "price_catalogue.csv", args.out_dir / "price_catalogue.xlsx"
    cat.write_csv(items, csv_path)
    cat.write_xlsx(items, suppliers, sources, xlsx_path)

    print(f"\n{len(items)} items · {len(suppliers)} suppliers · {n_over} overridden")
    for s in sources:
        print(f"  {s.document}: {s.items} items, price date {s.price_date or '?'}, {s.skipped} rows without a price")
    families: dict = {}
    for i in items:
        families[i.family] = families.get(i.family, 0) + 1
    print("  families: " + ", ".join(f"{k} {v}" for k, v in sorted(families.items(), key=lambda kv: -kv[1])))
    for p in problems:
        print(f"  override problem: {p}")
    print(f"\nWrote {csv_path}\n      {xlsx_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
