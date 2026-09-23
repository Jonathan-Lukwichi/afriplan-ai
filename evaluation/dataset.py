"""
Reference-project datasets under data/projects/<project>/.

    data/projects/<project>/
        manifest.json          committed — every input file with its SHA-256
        raw/                   gitignored — the client's drawings and BOQ
        reference_boq.json     committed — parsed ground truth (evaluation.reference)
        ratio_model.json       committed — fitted derived-item ratios (evaluation.ratios)

The manifest is what makes an evaluation reproducible: anyone re-running a
baseline first verifies they hold byte-identical inputs.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel, Field

DATA_ROOT = Path(__file__).resolve().parent.parent / "data" / "projects"


class DatasetFile(BaseModel):
    path: str                 # relative to the project dir, e.g. "raw/Wedela SLD 260525.pdf"
    sha256: str
    role: str                 # reference_boq | sld | lighting_layout | plug_layout | site_plan | architectural | pdf_sld | pdf_layouts
    building: str = ""        # canonical building name ("" = whole project)
    superseded: bool = False  # an older revision of another file in the set — never use


class ProjectManifest(BaseModel):
    project: str
    description: str = ""
    buildings: List[str] = Field(default_factory=list)
    building_codes: Dict[str, str] = Field(default_factory=dict)   # drawing code -> building
    files: List[DatasetFile] = Field(default_factory=list)

    def files_for(self, *, building: str = "", role: str = "") -> List[DatasetFile]:
        """Current (non-superseded) files matching the filters."""
        return [
            f for f in self.files
            if not f.superseded
            and (not building or f.building == building)
            and (not role or f.role == role)
        ]


def project_dir(project: str) -> Path:
    return DATA_ROOT / project


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(project: str) -> ProjectManifest:
    raw = json.loads((project_dir(project) / "manifest.json").read_text(encoding="utf-8"))
    return ProjectManifest.model_validate(raw)


def verify_manifest(manifest: ProjectManifest, root: Path) -> List[str]:
    """Return a list of problems (missing file / checksum mismatch). [] means OK."""
    problems: List[str] = []
    for f in manifest.files:
        p = Path(root) / f.path
        if not p.exists():
            problems.append(f"missing: {f.path}")
        elif sha256_file(p) != f.sha256:
            problems.append(f"checksum mismatch: {f.path}")
    return problems


_DRAWING_ID = re.compile(r"^(WD-[A-Z]+-\d+)-?\s*([A-Z]+)\s+(\d{2})(\d{2})(\d{2})", re.I)


def mark_superseded(files: List[DatasetFile]) -> List[DatasetFile]:
    """
    Flag older revisions. Two files with the same drawing id + role
    (e.g. 'WD-PB-01-LIGHTING 100225' and '... 100425', dates ddmmyy) are the
    same drawing: only the latest is current. Using both would double-count.
    """
    groups: Dict[tuple, List[tuple]] = {}
    for i, f in enumerate(files):
        m = _DRAWING_ID.match(Path(f.path).name)
        if not m:
            continue
        dd, mm, yy = m.group(3), m.group(4), m.group(5)
        groups.setdefault((m.group(1).upper(), m.group(2).upper()), []).append((yy + mm + dd, i))
    out = [f.model_copy() for f in files]
    for members in groups.values():
        if len(members) < 2:
            continue
        latest = max(members)[1]
        for _, i in members:
            out[i].superseded = i != latest
    return out


_ROLE_TO_DRAWINGS = {
    "sld": ["sld"], "lighting_layout": ["lighting_layout"], "plug_layout": ["plug_layout"],
    "architectural": ["architectural"], "site_plan": ["site_plan"], "pdf_sld": ["sld"],
    "pdf_layouts": ["lighting_layout", "plug_layout"],
}


def uploaded_from_manifest(manifest: ProjectManifest, building: str, *, source: str = "all"):
    """
    Drawing types available for one building. `source`: 'dwg' (CAD only),
    'pdf' (PDF set only — project-wide files count for every building), 'all'.
    """
    from evaluation.network import DrawingType
    out = set()
    for f in manifest.files:
        if f.superseded:
            continue
        is_pdf = f.role.startswith("pdf_")
        if (source == "dwg" and is_pdf) or (source == "pdf" and not is_pdf):
            continue
        if f.building and f.building != building:
            continue
        for d in _ROLE_TO_DRAWINGS.get(f.role, []):
            out.add(DrawingType(d))
    return out


def raw_available(project: str) -> bool:
    """True when the gitignored raw inputs are present locally."""
    return (project_dir(project) / "raw").is_dir()
