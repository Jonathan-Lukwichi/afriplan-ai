"""
AI cover-note for the "email the BoQ to a client" feature — new to this
rewrite (the original Streamlit app had download buttons only, no email).

Reuses the proven SUBJECT:/##section/CLOSING: contract and graceful-
fallback parsing from the HealthForecast project's report-email feature
(see engineering-webapp-skills' report-pdf-email-delivery skill) rather
than inventing a new format: real testing there showed the model reliably
skips the literal CLOSING: marker even when told not to, so the parser
recovers it from the last section's trailing paragraph instead of trusting
the prompt alone.
"""

from __future__ import annotations

import html
import logging
import re
import ssl
from datetime import datetime
from typing import Optional

log = logging.getLogger(__name__)

_SECTION_RE = re.compile(r"^##\s*(.+?)\s*$", re.MULTILINE)
_CLOSING_RE = re.compile(r"^CLOSING:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
_FIXED_ORDER = ["Overview", "Pricing", "Next steps"]


def build_prompt(context: dict) -> str:
    return (
        "You are an electrical contractor's estimator, writing a short email "
        "to a client to accompany an attached Bill of Quantities (BoQ). Plain "
        "English, no jargon, no invented numbers — use ONLY the figures given "
        "below.\n\n"
        f"Project: {context.get('project_name', 'Untitled project')}\n"
        f"Quote reference: {context.get('quote_ref', '')}\n"
        f"Line items: {context.get('total_items', 0)}\n"
        f"Total incl. VAT: R {context.get('total_incl_vat_zar', 0):,.2f}\n"
        f"Gaps flagged for verification: {context.get('gap_count', 0)}\n"
        f"Quote valid until: {context.get('valid_until', '')}\n\n"
        "OUTPUT FORMAT — follow this exactly, nothing before or after it:\n"
        "SUBJECT: <a specific one-line subject naming the project>\n"
        "## Overview\n<1-2 sentences introducing the attached BoQ>\n"
        "## Pricing\n<1-2 sentences on the total and quote validity>\n"
        "## Next steps\n<1-2 sentences — what the client should do, e.g. review the gap report, confirm to proceed>\n"
        "CLOSING: <one short natural closing sentence>\n\n"
        "RULES: use ONLY these three section names, in this order. Skip a "
        "section entirely (no '## ' line at all) if there's nothing to say — "
        "never write a placeholder like 'n/a'. Do not include a greeting "
        "('Hi ...') or a sign-off ('Kind regards...') — those are added "
        "separately. The CLOSING line is REQUIRED, its own line, never folded "
        "into 'Next steps'.\n\n"
        "TONE: write like a real contractor emailing a client directly — "
        "short, direct, no throat-clearing, no 'I hope this finds you well'."
    )


def parse_note(raw: str) -> tuple[str, list[tuple[str, str]], str]:
    """Split the model's raw reply into (subject, [(title, body), ...], closing).
    Tolerant of the model deviating from the contract."""
    lines = raw.strip().splitlines()
    subject = None
    body_start = 0
    for i, line in enumerate(lines):
        m = re.match(r"^SUBJECT:\s*(.+)$", line.strip(), re.IGNORECASE)
        if m:
            subject = m.group(1).strip()
            body_start = i + 1
            break
    if not subject:
        subject = f"Bill of Quantities — {datetime.now():%d %B %Y}"

    rest = "\n".join(lines[body_start:]).strip()

    closing = ""
    cm = _CLOSING_RE.search(rest)
    if cm:
        closing = cm.group(1).strip()
        rest = rest[:cm.start()].strip()

    matches = list(_SECTION_RE.finditer(rest))
    if not matches:
        return subject, [], (closing or rest)

    sections: list[tuple[str, str]] = []
    for idx, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(rest)
        body = rest[start:end].strip()
        if body:
            sections.append((title, body))

    if not closing and sections:
        last_title, last_body = sections[-1]
        parts = last_body.rsplit("\n\n", 1)
        if len(parts) == 2:
            sections[-1] = (last_title, parts[0].strip())
            closing = parts[1].strip()

    return subject, sections, closing


def compose_html(recipient_name: Optional[str], sections: list[tuple[str, str]], closing: str, sender_name: str) -> str:
    greeting = html.escape(f"Hi {recipient_name.strip()}," if recipient_name and recipient_name.strip() else "Hi there,")
    ordered = sorted(sections, key=lambda s: _FIXED_ORDER.index(s[0]) if s[0] in _FIXED_ORDER else 99)
    body_parts = [
        f"<h3 style='margin:18px 0 4px;font-family:sans-serif;font-size:15px;color:#0f172a'>{html.escape(title)}</h3>"
        f"<p style='margin:0 0 4px;font-family:sans-serif;font-size:14px;color:#334155;line-height:1.5'>{html.escape(body)}</p>"
        for title, body in ordered
    ]
    closing_html = (
        f"<p style='margin:18px 0 0;font-family:sans-serif;font-size:14px;color:#334155'>{html.escape(closing)}</p>"
        if closing else ""
    )
    return (
        f"<p style='font-family:sans-serif;font-size:14px;color:#0f172a'>{greeting}</p>"
        + "".join(body_parts)
        + closing_html
        + f"<p style='margin-top:22px;font-family:sans-serif;font-size:14px;color:#0f172a'>"
          f"Kind regards,<br>{html.escape(sender_name)}</p>"
    )


def _build_tls_tolerant_http_client():
    """Same rationale as agent/pdf_pipeline/llm.py's helper of the same name —
    tolerates locally-installed TLS-inspection root CAs. Returns None on any
    failure so the caller falls back to the SDK's default client."""
    try:
        import httpx
        ctx = ssl.create_default_context()
        ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
        return httpx.Client(verify=ctx)
    except Exception:  # noqa: BLE001
        log.warning("Could not build TLS-tolerant HTTP client; using SDK default.")
        return None


def generate_note(context: dict) -> Optional[str]:
    """Call Anthropic for the cover-note text. Returns None (never raises) if
    the API key is missing or the call fails — the caller falls back to a
    plain templated note."""
    import os
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic
        from core.config import HAIKU_4_5
        http_client = _build_tls_tolerant_http_client()
        kwargs = {}
        if http_client is not None:
            kwargs["http_client"] = http_client
        client = anthropic.Anthropic(**kwargs)
        resp = client.messages.create(
            model=HAIKU_4_5.model_id,
            max_tokens=500,
            messages=[{"role": "user", "content": build_prompt(context)}],
        )
        return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    except Exception as e:  # noqa: BLE001
        log.warning("BoQ cover-note generation failed: %s", e)
        return None
