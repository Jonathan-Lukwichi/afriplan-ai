"""
Drawing revisions in one upload — keep the newest, report the rest.

Drawing sets often travel with superseded sheets ('WD-PB-01-LIGHTING 100225' next to
'WD-PB-01-LIGHTING 100425'). Read together, the same fittings would be billed twice.
The sheet is identified from the file name; the revision from a trailing issue date
(DDMMYY, as SA consultants write it, or YYYYMMDD) or a 'Rev C' / '_R2' mark. Files
with no recognisable revision mark are always kept — never guess.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_DATE = re.compile(r"[\s_-]+(\d{6}|\d{8})$")
_REV = re.compile(r"[\s_-]+(?:REV(?:ISION)?[\s_.-]*|R)([A-Z]|\d{1,3})$", re.I)


def _as_date(token: str) -> Optional[date]:
    try:
        if len(token) == 8:                               # YYYYMMDD
            return date(int(token[:4]), int(token[4:6]), int(token[6:]))
        d, m, y = int(token[:2]), int(token[2:4]), int(token[4:])   # DDMMYY
        return date(2000 + y, m, d)
    except ValueError:
        return None


def sheet_and_revision(file_name: str) -> Tuple[str, Optional[tuple]]:
    """('WDPB01LIGHTING', (0, date)) — the sheet key and a sortable revision, or None."""
    stem = Path(file_name).stem.strip()
    rev: Optional[tuple] = None
    m = _DATE.search(stem)
    if m and _as_date(m.group(1)):
        rev, stem = (0, _as_date(m.group(1))), stem[:m.start()]
    else:
        m = _REV.search(stem)
        if m:
            tok = m.group(1).upper()
            rev = (1, int(tok)) if tok.isdigit() else (1, ord(tok) - ord("A"))
            stem = stem[:m.start()]
    return re.sub(r"[\s_\-.]+", "", stem).upper(), rev


def pick_latest_revisions(names: List[str]) -> Tuple[List[str], Dict[str, str]]:
    """(names to read, in upload order; {older file: the newer file that replaces it})."""
    newest: Dict[str, Tuple[tuple, str]] = {}
    for n in names:
        key, rev = sheet_and_revision(n)
        if rev is None:
            continue
        if key not in newest or rev > newest[key][0]:
            newest[key] = (rev, n)
    dropped: Dict[str, str] = {}
    for n in names:
        key, rev = sheet_and_revision(n)
        if rev is not None and newest[key][1] != n:
            dropped[n] = newest[key][1]
    return [n for n in names if n not in dropped], dropped
