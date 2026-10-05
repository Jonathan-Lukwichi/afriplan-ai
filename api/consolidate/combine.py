"""
Combine what the DWG reader and the PDF reader found into ONE set of findings (ADR-0008).

Two questions, answered in this order:
  1. Which findings are the same real thing?  Python pairs what it can match exactly —
     the same board tag, the same feeder ends, the same catalogue item on the same sheet
     (a PDF page is paired with the CAD sheet it prints, `agent.shared.sheets`). Only the
     names Python cannot pair go to an optional, injected `match_names` (the Claude API in
     `api/assist/finding_matcher.py`): same / different / unsure.
  2. Of a matched pair, which one to keep?  The stronger evidence (measured > counted >
     written > seen > assumed) — a rule that does not depend on the project. The AI never
     chooses a quantity, a length or a price.

What only one reader saw is kept. A real disagreement, or an "unsure" pair, becomes a
thing to check. A warning that belongs to a dropped finding is dropped with it.
Pure Python, no LLM import: the same inputs (and the same matcher answers) give the same set.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Callable, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field

from agent.shared import BQSection, GapItem
from agent.shared.findings import KIOSK_ALLOWANCE, BoardFinding, Evidence, FeederFinding, Findings, ItemFinding
from agent.shared.routes import equipment_key as _equipment_key
from agent.shared.sheets import pair_sheets

Verdict = Literal["same", "different", "unsure"]
# (kind, CAD names, PDF names) → {PDF name: (CAD name or "", verdict, reason)}
NameMatcher = Callable[[str, List[str], List[str]], Dict[str, Tuple[str, str, str]]]

_LABEL = {"dxf": "DWG", "pdf": "PDF"}


def equipment_key(name: str) -> str:
    """The equipment tag for matching: words in brackets describe it ('KIOSK (WD-KIOSK-01)'
    is the KIOSK), then spacing, hyphens and 'existing'/'new' are ignored ('Existing Mini Sub')."""
    return _equipment_key(re.sub(r"\([^)]*\)", " ", name))


class Decision(BaseModel):
    kind: str                               # board | feeder | item | wiring | name
    what: str
    kept: Literal["dxf", "pdf", "both"]
    reason: str


class Combined(BaseModel):
    findings: Findings
    decisions: List[Decision] = Field(default_factory=list)
    sheet_pairs: Dict[str, str] = Field(default_factory=dict)   # PDF page → CAD sheet
    ai_matched: int = 0                     # names the matcher paired


def combine(cad: Findings, pdf: Findings, *, match_names: Optional[NameMatcher] = None,
            count_tolerance: float = 0.2) -> Combined:
    out = Combined(findings=Findings(), sheet_pairs=pair_sheets(cad.sheet_words, pdf.sheet_words))
    alias, unsure = _equipment_aliases(cad, pdf, match_names, out)

    boards, dropped_boards = _combine_boards(cad.boards, pdf.boards, alias, unsure, out)
    feeders, dropped_feeders = _combine_feeders(cad.feeders, pdf.feeders, alias, out)
    dropped_names = dropped_boards | dropped_feeders
    items = _combine_items(cad.items, pdf.items, boards, match_names, count_tolerance, out)
    wires = _combine_wires(cad, pdf, out)

    # set-level PDF warnings about a board or feeder the DWG replaced would now mislead
    pdf_gaps = [g for g in pdf.gaps
                if not (g.section in (BQSection.DISTRIBUTION, BQSection.SUBMAIN_CABLES)
                        and g.building_block and equipment_key(g.building_block) in dropped_names)]
    out.findings = Findings(
        boards=boards, feeders=feeders, items=items, wires=wires,
        gaps=[*cad.gaps, *pdf_gaps, *_unsure_gaps(unsure)],
        sheet_words={**pdf.sheet_words, **cad.sheet_words},
    )
    return out


# ─── names: which PDF name is which CAD equipment ────────────────────

def _names(f: Findings) -> List[str]:
    seen: Dict[str, str] = {}
    for n in [*(b.name for b in f.boards), *(x for fd in f.feeders for x in (fd.from_board, fd.to_board))]:
        if n.strip():
            seen.setdefault(n, n)
    return list(seen)


def _equipment_aliases(cad: Findings, pdf: Findings, match_names: Optional[NameMatcher], out: Combined):
    """{PDF name: CAD name} for every PDF equipment name that is a CAD one; and the unsure pairs."""
    cad_names = _names(cad)
    by_key = {equipment_key(n): n for n in cad_names}
    alias: Dict[str, str] = {}
    left: List[str] = []
    for n in _names(pdf):
        if equipment_key(n) in by_key:
            alias[n] = by_key[equipment_key(n)]
        else:
            left.append(n)
    unsure: Dict[str, str] = {}
    if left and cad_names and match_names is not None:
        answers = match_names("equipment", sorted(cad_names), sorted(left))
        for pdf_name, (cad_name, verdict, reason) in answers.items():
            if pdf_name not in left or cad_name not in cad_names:
                continue                    # never trust a name that was not offered
            if verdict == "same":
                alias[pdf_name] = cad_name
                out.ai_matched += 1
                out.decisions.append(Decision(kind="name", what=f"{pdf_name} = {cad_name}", kept="both",
                                              reason=f"Matched by AI: {reason}"))
            elif verdict == "unsure":
                unsure[pdf_name] = cad_name
    return alias, unsure


def _unsure_gaps(unsure: Dict[str, str]) -> List[GapItem]:
    return [GapItem(
        section=BQSection.DISTRIBUTION, building_block=pdf_name,
        description=f"'{pdf_name}' on the PDF may be the same as '{cad_name}' on the DWG — both are priced",
        assumption="Kept both, so nothing is missed; one may be a duplicate.",
        suggested_action="Check the two drawings and remove the duplicate if they are the same.",
        severity="high", drawing_ref="Combining",
    ) for pdf_name, cad_name in sorted(unsure.items())]


# ─── boards ──────────────────────────────────────────────────────────

def _board_rank(b: BoardFinding) -> tuple:
    return (b.contents_known, b.evidence.rank, b.reader == "dxf")


def _ways(b: BoardFinding) -> int:
    return len(b.circuits) + b.spares


def _combine_boards(cad: List[BoardFinding], pdf: List[BoardFinding], alias, unsure, out: Combined):
    kept: Dict[str, BoardFinding] = {equipment_key(b.name): b for b in cad}
    extra: List[BoardFinding] = []
    dropped: set = set()                    # PDF board names the DWG replaced
    for p in pdf:
        key = equipment_key(alias.get(p.name, p.name))
        c = kept.get(key)
        if c is None:
            extra.append(p)
            out.decisions.append(Decision(kind="board", what=p.name, kept="pdf",
                                          reason="Only the PDF shows this board."))
            continue
        win, lose = (c, p) if _board_rank(c) >= _board_rank(p) else (p, c)
        if win is p:
            win = p.model_copy(update={"name": c.name})
            kept[key] = win
        else:
            dropped.add(equipment_key(p.name))
        if c.contents_known and p.contents_known and (
                c.main_breaker_a != p.main_breaker_a or _ways(c) != _ways(p)):
            win.gaps.append(GapItem(
                section=BQSection.DISTRIBUTION, building_block=win.name,
                description=(f"{win.name}: the DWG shows {c.main_breaker_a}A, {_ways(c)}-way; "
                             f"the PDF shows {p.main_breaker_a}A, {_ways(p)}-way"),
                assumption=f"Priced from the {_LABEL[win.reader]} ({win.evidence.value}).",
                suggested_action="Check the board schedule on the SLD.",
                severity="medium", drawing_ref="Combining",
            ))
        out.decisions.append(Decision(
            kind="board", what=win.name, kept=win.reader,
            reason=("Board contents shown only on the " + _LABEL[win.reader]) if not lose.contents_known
            else f"{_LABEL[win.reader]} {win.evidence.value} beats {_LABEL[lose.reader]} {lose.evidence.value}.",
        ))
    return [*kept.values(), *extra], dropped


# ─── feeders ─────────────────────────────────────────────────────────

def _feeder_key(f: FeederFinding, alias) -> Tuple[str, str]:
    return equipment_key(alias.get(f.from_board, f.from_board)), equipment_key(alias.get(f.to_board, f.to_board))


def _feeder_rank(f: FeederFinding) -> tuple:
    return (f.evidence.rank, f.reader == "dxf")


def _combine_feeders(cad: List[FeederFinding], pdf: List[FeederFinding], alias, out: Combined):
    by_key = {_feeder_key(f, {}): f for f in cad}
    by_to = {k[1]: f for k, f in by_key.items()}
    names = {equipment_key(n): n for f in cad for n in (f.from_board, f.to_board)}
    groups: Dict[Tuple[str, str], List[FeederFinding]] = defaultdict(list)
    for p in pdf:
        groups[_feeder_key(p, alias)].append(p)

    kept: Dict[Tuple[str, str], FeederFinding] = dict(by_key)
    extra: List[FeederFinding] = []
    dropped: set = set()
    for key, group in groups.items():
        best = max(group, key=_feeder_rank)
        if len(group) > 1:
            out.decisions.append(Decision(kind="feeder", what=f"{best.from_board}→{best.to_board}", kept="pdf",
                                          reason=f"The PDF showed this feeder {len(group)} times; kept once."))
        c = by_key.get(key) or by_to.get(key[1])
        if c is None:
            extra.append(best)
            out.decisions.append(Decision(kind="feeder", what=f"{best.from_board}→{best.to_board}", kept="pdf",
                                          reason="Only the PDF shows this feeder."))
            continue
        ckey = _feeder_key(c, {})
        if _feeder_rank(c) >= _feeder_rank(best):
            win, lose = c, best
            dropped.add(equipment_key(best.to_board))
        else:
            win = best.model_copy(update={"from_board": names.get(key[0], best.from_board),
                                          "to_board": c.to_board})
            lose = c
            kept[ckey] = win
        if key[0] != ckey[0]:
            win.gaps.append(GapItem(
                section=BQSection.SUBMAIN_CABLES, building_block=c.to_board,
                description=(f"{c.to_board}: the DWG says it is fed from {c.from_board}, "
                             f"the PDF says from {best.from_board}"),
                assumption=f"Priced as the {_LABEL[win.reader]} shows.",
                suggested_action="Confirm the supply arrangement with the designer.",
                severity="medium", drawing_ref="Combining",
            ))
        if c.cable_size_mm2 and best.cable_size_mm2 and c.cable_size_mm2 != best.cable_size_mm2:
            win.gaps.append(GapItem(
                section=BQSection.SUBMAIN_CABLES, building_block=c.to_board,
                description=(f"Feeder to {c.to_board}: the DWG shows {c.cable_size_mm2:g}mm², "
                             f"the PDF shows {best.cable_size_mm2:g}mm²"),
                assumption=f"Priced as the {_LABEL[win.reader]} shows ({win.cable_size_mm2:g}mm²).",
                suggested_action="Check the cable size on the SLD.",
                severity="medium", drawing_ref="Combining",
            ))
        out.decisions.append(Decision(
            kind="feeder", what=f"{win.from_board}→{win.to_board}", kept=win.reader,
            reason=f"Length {win.evidence.value} on the {_LABEL[win.reader]} beats "
                   f"{lose.evidence.value} on the {_LABEL[lose.reader]}.",
        ))
    return [*kept.values(), *extra], dropped


# ─── items: sheet by sheet ───────────────────────────────────────────

def _item_name(i: ItemFinding) -> str:
    return i.item or i.description


def _combine_items(cad: List[ItemFinding], pdf: List[ItemFinding], boards: List[BoardFinding],
                   match_names: Optional[NameMatcher], tol: float, out: Combined) -> List[ItemFinding]:
    pairs = out.sheet_pairs
    on_sheet: Dict[str, Dict[str, List[ItemFinding]]] = defaultdict(lambda: defaultdict(list))
    for c in cad:
        on_sheet[c.sheet][_item_name(c)].append(c)

    # PDF item names on paired sheets that the CAD sheet does not list by the same name
    left = sorted({p.item for p in pdf if p.sheet in pairs and p.item
                   and p.item not in on_sheet[pairs[p.sheet]]})
    unnamed = sorted({c.description for c in cad if not c.item and c.sheet in set(pairs.values())})
    alias: Dict[str, str] = {}
    if left and unnamed and match_names is not None:
        for pdf_name, (cad_name, verdict, reason) in match_names("item", unnamed, left).items():
            if verdict == "same" and pdf_name in left and cad_name in unnamed:
                alias[pdf_name] = cad_name
                out.ai_matched += 1
                out.decisions.append(Decision(kind="name", what=f"{pdf_name} = {cad_name}", kept="both",
                                              reason=f"Matched by AI: {reason}"))

    has_main_kiosk = any(b.main_kiosk and b.reader == "dxf" for b in boards)
    kept: List[ItemFinding] = list(cad)
    pdf_qty: Dict[Tuple[str, str], float] = defaultdict(float)
    pdf_items: Dict[Tuple[str, str], List[ItemFinding]] = defaultdict(list)
    for p in pdf:
        if p.item == KIOSK_ALLOWANCE and has_main_kiosk:
            out.decisions.append(Decision(kind="item", what=p.description, kept="dxf",
                                          reason="The DWG prices the main kiosk from its SLD."))
            continue
        sheet = pairs.get(p.sheet)
        name = alias.get(p.item, p.item)
        if sheet is not None and name and name in on_sheet[sheet]:
            pdf_qty[(sheet, name)] += p.qty
            pdf_items[(sheet, name)].append(p)
            continue
        kept.append(p)
    for (sheet, name), pq in sorted(pdf_qty.items()):
        found = on_sheet[sheet][name]
        cq = sum(i.qty for i in found)
        scheduled = all(p.evidence == Evidence.WRITTEN for p in pdf_items[(sheet, name)])
        if scheduled and pq > cq:
            # Symbol recognition can miss copies (exploded or unknown blocks) but never invents
            # them; a HIGHER quantity printed in the designer's own schedule means the count
            # missed some. A lower one may be out of date, so the count stands then.
            kept = [i for i in kept if not any(i is f for f in found)]
            kept += pdf_items[(sheet, name)]
            out.decisions.append(Decision(kind="item", what=f"{name} on {sheet}", kept="pdf",
                                          reason=f"The designer's schedule prints {pq:g}; the DWG count "
                                                 f"found only {cq:g} symbols."))
            pdf_items[(sheet, name)][0].gaps.append(GapItem(
                section=found[0].section, building_block=found[0].building,
                description=f"{name} on {sheet}: the legend schedule says {pq:g}, the DWG count found {cq:g}",
                assumption="Priced on the designer's schedule (the count missed some symbols).",
                suggested_action="Check that sheet: some symbols may be drawn as loose lines or other blocks.",
                severity="medium", drawing_ref=sheet,
            ))
            continue
        out.decisions.append(Decision(kind="item", what=f"{name} on {sheet}", kept="dxf",
                                      reason=f"Every symbol counted on the DWG ({cq:g}); the PDF showed {pq:g}."))
        if abs(cq - pq) >= 2 and abs(cq - pq) > tol * max(cq, pq):
            found[0].gaps.append(GapItem(
                section=found[0].section, building_block=found[0].building,
                description=f"{name} on {sheet}: the DWG counted {cq:g}, the PDF shows {pq:g}",
                assumption="Priced on the DWG count (every symbol counted).",
                suggested_action="Check that sheet; symbols may be hidden in a block or drawn on another layer.",
                severity="medium", drawing_ref=sheet,
            ))
    return kept


def _combine_wires(cad: Findings, pdf: Findings, out: Combined):
    measured = {w.sheet for w in cad.wires}
    kept = list(cad.wires)
    replaced = 0
    for w in pdf.wires:
        if out.sheet_pairs.get(w.sheet) in measured:
            replaced += 1
            continue
        kept.append(w)
    if replaced:
        out.decisions.append(Decision(kind="wiring", what=f"{replaced} PDF wiring allowances", kept="dxf",
                                      reason="Wiring measured on the DWG of the same sheet."))
    return kept
