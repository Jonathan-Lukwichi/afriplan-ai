"""
Verify (or write) a reference project's checksummed manifest.

    python scripts/verify_data.py wedela            # verify raw/ matches manifest.json
    python scripts/verify_data.py wedela --write    # (re)generate manifest.json from raw/

--write assigns each file a role + building from the Wedela naming convention
(WD-<CODE>-01-<ROLE>). Review the generated manifest before committing it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))
sys.stdout.reconfigure(encoding="utf-8")

from evaluation.dataset import (  # noqa: E402
    DatasetFile,
    ProjectManifest,
    load_manifest,
    mark_superseded,
    project_dir,
    sha256_file,
    verify_manifest,
)

# Wedela: drawing code -> the building sheet it is billed on.
# OL (outdoor lighting SLD) is billed on the Swimming Pool sheet (high-mast floods,
# solar post lanterns). Storage has no electrical drawings of its own.
WEDELA_CODES = {
    "AB": "Ablution Retail Block",
    "ECH": "Existing Community Hall",
    "LGH": "Large Guard House",
    "SGH": "Small Guard House",
    "PB": "Swimming Pool",
    "OL": "Swimming Pool",
    "KIOSK": "Main Kiosk",
}
WEDELA_BUILDINGS = [
    "Existing Community Hall", "Storage", "Ablution Retail Block", "Swimming Pool",
    "Small Guard House", "Large Guard House", "Main Kiosk",
]
_ARCH_HINTS = [
    ("ablution", "Ablution Retail Block"), ("community hall", "Existing Community Hall"),
    ("pool", "Swimming Pool"), ("small gaurd", "Small Guard House"),
    ("large guard", "Large Guard House"), ("gym", "Gym Entrance (not billed)"),
]


def _classify(rel: str) -> tuple[str, str]:
    name = Path(rel).name
    low = name.lower()
    if low.endswith(".xlsx"):
        return "reference_boq", ""
    if low.endswith(".pdf"):
        return ("pdf_sld" if "sld" in low else "pdf_layouts"), ""
    m = re.match(r"WD-([A-Z]+)-", name, re.I)
    if m:
        code = m.group(1).upper()
        role = "sld" if "SLD" in name.upper() else (
            "lighting_layout" if "LIGHTING" in name.upper() else "plug_layout")
        return role, WEDELA_CODES.get(code, "")
    if "site plan" in low:
        return "site_plan", ""
    for hint, bldg in _ARCH_HINTS:
        if hint in low:
            return "architectural", bldg
    return "architectural", ""


def write_manifest(project: str) -> ProjectManifest:
    root = project_dir(project)
    files = []
    for p in sorted((root / "raw").rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        role, bldg = _classify(rel)
        files.append(DatasetFile(path=rel, sha256=sha256_file(p), role=role, building=bldg))
    manifest = ProjectManifest(
        project=project,
        description=(
            "Wedela Recreation Centre — client handover 2026-08-25: priced BOQ Rev01 "
            "(14 Nov 2025), SLD + lighting/plug PDFs (26 May 2025), 18 electrical DWGs, "
            "7 architectural DWGs."
        ),
        buildings=WEDELA_BUILDINGS,
        building_codes=WEDELA_CODES,
        files=mark_superseded(files),
    )
    (root / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    if args.write:
        m = write_manifest(args.project)
        print(f"Wrote manifest — {len(m.files)} files")
        return 0
    m = load_manifest(args.project)
    problems = verify_manifest(m, project_dir(args.project))
    if problems:
        print("\n".join(problems))
        return 1
    print(f"OK — {len(m.files)} files verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
