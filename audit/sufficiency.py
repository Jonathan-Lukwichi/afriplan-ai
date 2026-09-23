"""
Drawing sufficiency — can these drawings give a complete BOQ, and if not, what
exactly is missing?

Given the drawing types available for a building, the layered BOQ network
(evaluation.network) says which item families can be quantified. Against a
reference bill we can also say how much of the bill's VALUE that covers — the
honest ceiling for any pipeline working from that upload. Families that cannot
be reproduced become PROVISIONAL items in a partial BOQ, never silent omissions.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field

from evaluation.dataset import load_manifest, uploaded_from_manifest
from evaluation.network import (
    NETWORK,
    DrawingType,
    Method,
    missing_for,
    reproducible,
    requirements_matrix,
)
from evaluation.reference import ReferenceBoq


class SufficiencyReport(BaseModel):
    building: str
    source: str = ""
    uploaded: List[str] = Field(default_factory=list)
    reproducible_families: List[str] = Field(default_factory=list)
    not_reproducible: List[str] = Field(default_factory=list)
    never_from_drawings: List[str] = Field(default_factory=list)   # provisional / prelims
    coverage_possible_zar: Optional[float] = None
    coverage_possible_pct: Optional[float] = None
    reference_value_zar: Optional[float] = None
    requests: Dict[str, List[str]] = Field(default_factory=dict)  # drawing → families it unlocks
    request_value_zar: Dict[str, float] = Field(default_factory=dict)

    @property
    def complete(self) -> bool:
        return not self.not_reproducible


def sufficiency(
    uploaded: Set[DrawingType],
    *,
    building: str = "",
    ref: Optional[ReferenceBoq] = None,
    source: str = "",
) -> SufficiencyReport:
    """
    With a reference: families are those actually billed for the building, and
    coverage is value-weighted. Without: families are every drawing-derived node.
    """
    bld = ref.building(building) if ref is not None else None
    if bld is not None:
        value_by_family: Dict[str, float] = {}
        for l in bld.lines:
            value_by_family[l.key_family] = value_by_family.get(l.key_family, 0.0) + l.value
        families = sorted(value_by_family)
    else:
        value_by_family = {}
        families = sorted(f for f, n in NETWORK.items()
                          if n.method not in (Method.PROVISIONAL, Method.PRELIMS))

    never = [f for f in families if NETWORK.get(f) is None
             or NETWORK[f].method in (Method.PROVISIONAL, Method.PRELIMS)]
    drawable = [f for f in families if f not in never]
    ok = [f for f in drawable if reproducible(f, uploaded)]
    missing = [f for f in drawable if f not in ok]
    requests = {d.value: fams for d, fams in missing_for(missing, uploaded).items()}

    rep = SufficiencyReport(
        building=building, source=source, uploaded=sorted(d.value for d in uploaded),
        reproducible_families=ok, not_reproducible=missing, never_from_drawings=never,
        requests=requests,
    )
    if bld is not None:
        total = sum(value_by_family.values())
        covered = sum(value_by_family[f] for f in ok)
        rep.reference_value_zar = total
        rep.coverage_possible_zar = covered
        rep.coverage_possible_pct = covered / total if total else 0.0
        rep.request_value_zar = {d: sum(value_by_family[f] for f in fams) for d, fams in requests.items()}
    return rep


def sufficiency_for_project(project: str, ref: ReferenceBoq, *, sources=("dwg", "pdf")) -> List[SufficiencyReport]:
    """One report per billed building and input source (CAD set vs PDF set)."""
    manifest = load_manifest(project)
    out: List[SufficiencyReport] = []
    for b in ref.billed_buildings():
        for src in sources:
            up = uploaded_from_manifest(manifest, b.name, source=src)
            out.append(sufficiency(up, building=b.name, ref=ref, source=src))
    return out


def render_sufficiency(reports: List[SufficiencyReport]) -> str:
    out = ["# Drawing sufficiency — what can each upload reproduce?", "",
           "Coverage ceiling = share of the reference bill's value whose items can be "
           "quantified from the drawings available (layered BOQ network). No pipeline can "
           "score above this ceiling on that upload.", "",
           "_Source `pdf` treats project-wide PDF sets as covering every building "
           "(not yet verified page-by-page); `dwg` uses only drawings tagged to the building._", "",
           "| Building | Source | Drawings | Coverage ceiling | Not reproducible | Request next |",
           "|---|---|---|---:|---|---|"]
    for r in reports:
        ceil = f"{r.coverage_possible_pct:.1%}" if r.coverage_possible_pct is not None else "—"
        nr = ", ".join(r.not_reproducible[:6]) + ("…" if len(r.not_reproducible) > 6 else "") or "—"
        req = "; ".join(f"**{d}** (+R {r.request_value_zar.get(d, 0):,.0f})" for d in r.requests) or "—"
        out.append(f"| {r.building} | {r.source} | {', '.join(r.uploaded) or 'none'} | {ceil} | {nr} | {req} |")
    out += ["", "## Drawing requirements (layered BOQ network)", "",
            "| Item family | How it is quantified |", "|---|---|"]
    for fam, req in sorted(requirements_matrix().items()):
        out.append(f"| `{fam}` | {req} |")
    return "\n".join(out) + "\n"
