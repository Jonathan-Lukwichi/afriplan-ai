"""
Outbound transactional email — one thin Resend wrapper so the email-BoQ
feature has a single provider, timeout, and failure mode. Adapted from the
HealthForecast project's api/core/notify.py (same proven pattern), extended
to support multiple attachments since a BoQ email carries both the Excel
and the PDF.

Uses the OS trust store (truststore) so it works behind TLS-inspecting
corporate networks, matching agent/pdf_pipeline/llm.py's own TLS handling.
"""

from __future__ import annotations

import base64
import os
import ssl

import httpx

try:
    import truststore
    _SSL_CONTEXT = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
except ImportError:  # pragma: no cover
    import certifi
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

_API_KEY = os.getenv("RESEND_API_KEY")
_FROM = os.getenv("NOTIFY_FROM_EMAIL", "onboarding@resend.dev")


def send_email(
    to: str,
    subject: str,
    html: str,
    attachments: list[tuple[str, bytes]] | None = None,
) -> bool:
    """Send one transactional email via Resend.

    `attachments` is a list of (filename, raw_bytes) pairs. Returns False
    (never raises) if the provider isn't configured or the send fails —
    callers decide how to degrade.
    """
    if not _API_KEY:
        return False
    payload = {"from": _FROM, "to": [to], "subject": subject, "html": html}
    if attachments:
        payload["attachments"] = [
            {"filename": name, "content": base64.b64encode(data).decode("ascii")}
            for name, data in attachments
        ]
    try:
        with httpx.Client(verify=_SSL_CONTEXT, timeout=20) as c:
            r = c.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {_API_KEY}"},
                json=payload,
            )
            return r.status_code < 300
    except Exception:
        return False
