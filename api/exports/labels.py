"""
Plain-language labels for the exported Excel/PDF — the same words the app shows
(src/lib/plainWords.js), so a client reading the file understands every column.
"""

SOURCE_LABEL = {
    "extracted": "From the drawing",
    "inferred": "Worked out",
    "assumed": "Guessed - check",
    "provisional": "Allowance",
    "estimated": "Rough estimate - check",
    "manual": "Price you chose",
}

SEVERITY_LABEL = {
    "critical": "MUST FIX",
    "high": "MUST CHECK",
    "medium": "SHOULD CHECK",
    "low": "FOR INFO",
}

SOURCE_KEY = (
    "Where it comes from — From the drawing: counted or read off the drawings. "
    "Worked out: calculated from the drawings (e.g. cable measured on the site plan + allowance). "
    "Guessed - check: not on the drawings, a standard value was used. "
    "Price you chose: price changed by you (e.g. a supplier's price)."
)


def source_label(value: str) -> str:
    return SOURCE_LABEL.get(value, value)


def severity_label(value: str) -> str:
    return SEVERITY_LABEL.get(value, value.upper())
