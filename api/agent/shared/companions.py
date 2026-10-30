"""
Convention-A wiring lines derived from the route — the companion rules in
`.claude/skills/deriving-companion-items/RULES.md` (rule IDs cited in every line's assumption).

A South African bill prices final-circuit wiring material by material (doe/knowledge/BOQ_KNOWLEDGE.md
§3–5): conduit = R (horizontal route) + D (drops), then the materials that follow from the conduit.
Pure and deterministic: findings in, more findings out, priced by the one pricer (ADR-0008). Only
high-confidence rules emit lines; a companion a reader already counted wins (no double count).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from agent.shared.boq import BQSection, GapItem, ItemConfidence
from agent.shared.findings import Evidence, Findings, ItemFinding
from core import constants


@dataclass(frozen=True)
class CompanionConfig:
    ceiling_m: float = 3.0               # used when the drawing gives no ceiling height (flagged)
    socket_mount_m: float = 0.5          # BOQ_KNOWLEDGE §4: socket at 500 mm
    switch_mount_m: float = 1.3          # switches / isolators at ~1.2–1.4 m
    conduit_size: str = "20mm"


DEFAULT_COMPANIONS = CompanionConfig()


def _wall_points(findings: Findings, building: str) -> Dict[str, float]:
    """Counted wall points in one building: sockets, and switches incl. isolators (one drop each)."""
    out = {"socket": 0.0, "switch": 0.0}
    for it in findings.items:
        if it.building != building:
            continue
        name = f"{it.item} {it.description}".lower()
        if "socket" in name:
            out["socket"] += it.qty
        elif "switch" in name or "isolator" in name:
            out["switch"] += it.qty
    return out


def _counted(findings: Findings, building: str, word: str) -> bool:
    return any(word in it.description.lower() for it in findings.items if it.building == building)


def _conduit(findings: Findings, building: str, route_m: float, cfg: CompanionConfig) -> ItemFinding:
    """CO-C1 (conf H): conduit = R + D."""
    pts = _wall_points(findings, building)
    drop_socket = cfg.ceiling_m - cfg.socket_mount_m
    drop_switch = cfg.ceiling_m - cfg.switch_mount_m
    drops_m = pts["socket"] * drop_socket + pts["switch"] * drop_switch
    qty = round(route_m + drops_m, 2)
    material = constants.CONTAINMENT_PRICES.get(f"pvc_conduit_{cfg.conduit_size}", 0.0)
    item = ItemFinding(
        description=f"{cfg.conduit_size} PVC conduit with accessories — {building}".rstrip(" —"),
        section=BQSection.CONTAINMENT, unit="m", qty=qty, material_zar=material, install_zar=0.0,
        building=building, sheet="derived", evidence=Evidence.MEASURED,
        confidence=ItemConfidence.INFERRED,
        assumption=(f"CO-C1: conduit = route {route_m:g} m measured + drops {drops_m:g} m "
                    f"({pts['socket']:g} sockets × {drop_socket:g} m, {pts['switch']:g} switches × "
                    f"{drop_switch:g} m; ceiling {cfg.ceiling_m:g} m)."),
    )
    item.gaps.append(GapItem(
        section=BQSection.CONTAINMENT, building_block=building,
        description=f"Ceiling height for conduit drops in {building or 'this building'} not on the drawing",
        assumption=f"{cfg.ceiling_m:g} m assumed; drops = ceiling − mounting height.",
        suggested_action="Confirm the ceiling height; the conduit quantity follows it.",
        severity="low", drawing_ref="derived",
    ))
    item.gaps.append(GapItem(
        section=BQSection.CONTAINMENT, building_block=building,
        description=f"Conduit install labour has no rate in the rate model ({building or 'this building'})",
        assumption="Priced on material only.",
        suggested_action="Price conduit installation by hand, or add a labour rate.",
        severity="medium", drawing_ref="derived",
    ))
    return item


def companion_findings(findings: Findings, cfg: CompanionConfig = DEFAULT_COMPANIONS) -> List[ItemFinding]:
    """The derived lines for these findings, one set per building with a measured route."""
    route: Dict[str, float] = {}
    for w in findings.wires:
        if w.evidence == Evidence.MEASURED and w.route_m > 0:      # the straight route, not the drawn length
            route[w.building] = route.get(w.building, 0.0) + w.route_m
    out: List[ItemFinding] = []
    for building, route_m in route.items():
        if not _counted(findings, building, "conduit"):
            out.append(_conduit(findings, building, route_m, cfg))
    return out
