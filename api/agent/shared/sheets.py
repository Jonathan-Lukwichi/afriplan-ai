"""
Which PDF page is a print of which CAD sheet (ADR-0008) — by the words both show.

A drawing set often arrives as DWGs AND as one combined PDF. To combine what the two
readers found without counting a sheet twice, each PDF page is paired with the CAD sheet
that prints the same words: room names, the drawing number, the title. Words every sheet
shows (legend, notes) weigh little; rare words weigh a lot. No naming convention assumed.
A page with no text layer (a scan), or no clear match, stays unpaired.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, Iterable, List

_WORD = re.compile(r"[A-Z0-9]+")
_CODE = re.compile(r"[A-Z]{1,4}(?:[-_/.]?[A-Z0-9]{1,4}){1,3}")


def sheet_words(texts: Iterable[str]) -> List[str]:
    """Distinctive words on a sheet: words of 3+ characters with a letter, plus codes
    written with separators joined up ('WD-AB-01' → 'WDAB01', 'DB-AB1' → 'DBAB1')."""
    out = set()
    for t in texts:
        up = (t or "").upper()
        out.update(w for w in _WORD.findall(up) if len(w) >= 3 and any(c.isalpha() for c in w))
        for code in _CODE.findall(up):
            c = re.sub(r"[-_/.]", "", code)
            if len(c) >= 4 and any(ch.isdigit() for ch in c) and any(ch.isalpha() for ch in c):
                out.add(c)
    return sorted(out)


def pair_sheets(cad: Dict[str, Iterable[str]], pdf: Dict[str, Iterable[str]],
                min_score: float = 0.5) -> Dict[str, str]:
    """{pdf page: cad sheet}. Score = the share of the page's (rarity-weighted) words that the
    sheet also shows. Each CAD sheet is used once; the page with the clearest winner is
    paired first, so two look-alike pages settle on different sheets."""
    cad_w = {k: set(v) for k, v in cad.items()}
    pdf_w = {k: set(v) for k, v in pdf.items() if v}
    df = Counter(w for words in (*cad_w.values(), *pdf_w.values()) for w in words)
    n = len(cad_w) + len(pdf_w)
    idf = {w: math.log(1 + n / c) for w, c in df.items()}

    def score(page: str, sheet: str) -> float:
        words = pdf_w[page]
        total = sum(idf[w] for w in words)
        return sum(idf[w] for w in words & cad_w[sheet]) / total if total else 0.0

    scores = {p: {s: score(p, s) for s in cad_w} for p in pdf_w}
    pairs: Dict[str, str] = {}
    free = set(cad_w)
    todo = set(pdf_w)
    while todo and free:
        best = None
        for p in sorted(todo):
            ranked = sorted(((scores[p][s], s) for s in free), reverse=True)
            top, sheet = ranked[0]
            margin = top - (ranked[1][0] if len(ranked) > 1 else 0.0)
            if best is None or (margin, top) > best[0]:
                best = ((margin, top), p, sheet)
        (_, top), page, sheet = best
        todo.discard(page)
        if top >= min_score:
            pairs[page] = sheet
            free.discard(sheet)
    return pairs
