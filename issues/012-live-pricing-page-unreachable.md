# 012 — Live Pricing page is not registered in navigation

> **Status:** FIXED 2026-09-26 (80e7318) — Live Pricing registered in app.py.

**Priority:** P2 · **Opened:** 2026-09-23

**Evidence.** `app.py:17-22` registers only Welcome/Upload/Extraction/BOQ;
`pages/4_Live_Pricing.py` cannot be reached.

**Acceptance.** Registered (or removed) and linked from page 3.
