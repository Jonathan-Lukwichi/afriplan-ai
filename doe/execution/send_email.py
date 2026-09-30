"""
LAYER 3 — EXECUTION: e-mail a run's BoQ (Excel + PDF) and evaluation to the owner.

    python doe/execution/send_email.py runs/doe/<stamp>          # to OWNER_EMAIL in api/.env

Uses, in order, whatever is set in api/.env:
  RESEND_API_KEY                       (free at resend.com; from NOTIFY_FROM_EMAIL)
  SMTP_USER + SMTP_PASSWORD [+ SMTP_HOST, default smtp.gmail.com:465]
                                       (for Gmail: an "app password", not your password)
Exit code 4 = no mail credentials — the brain then uses its Gmail connector instead.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_MIME = {".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
         ".pdf": "application/pdf"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--to", help="default: OWNER_EMAIL in api/.env")
    args = ap.parse_args()
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / "api" / ".env")
    except ImportError:
        pass
    args.to = args.to or os.environ.get("OWNER_EMAIL", "")
    if not args.to:
        print("no recipient: pass --to or set OWNER_EMAIL in api/.env")
        return 6

    summary = json.loads((args.run_dir / "summary.json").read_text(encoding="utf-8"))
    subject = f"AfriPlan BoQ — {summary['project']} — {summary['stamp']}"
    body = (args.run_dir / "email_body.txt").read_text(encoding="utf-8")
    files = [Path(summary["xlsx"]), Path(summary["pdf"])]

    if os.environ.get("RESEND_API_KEY"):
        import httpx
        r = httpx.post("https://api.resend.com/emails", timeout=60, headers={
            "Authorization": f"Bearer {os.environ['RESEND_API_KEY']}"}, json={
            "from": os.environ.get("NOTIFY_FROM_EMAIL", "onboarding@resend.dev"),
            "to": [args.to], "subject": subject, "text": body,
            "attachments": [{"filename": f.name, "content": base64.b64encode(f.read_bytes()).decode()}
                            for f in files]})
        if r.status_code >= 300:
            print(f"Resend refused: {r.status_code} {r.text[:300]}")
            return 5
        print(f"sent via Resend to {args.to}")
        return 0

    user, password = os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASSWORD")
    if user and password:
        msg = EmailMessage()
        msg["Subject"], msg["From"], msg["To"] = subject, user, args.to
        msg.set_content(body)
        for f in files:
            maintype, subtype = _MIME[f.suffix].split("/", 1)
            msg.add_attachment(f.read_bytes(), maintype=maintype, subtype=subtype, filename=f.name)
        host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        port = int(os.environ.get("SMTP_PORT", "465"))
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context()) as s:
            s.login(user, password)
            s.send_message(msg)
        print(f"sent via SMTP ({host}) to {args.to}")
        return 0

    print("no mail credentials (RESEND_API_KEY or SMTP_USER/SMTP_PASSWORD) in api/.env")
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
