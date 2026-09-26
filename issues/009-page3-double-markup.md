# 009 — Page 3 applies contractor markup on top of rates that already include markup

> **Status:** FIXED 2026-09-26 (80e7318) — contractor_markup_pct = 0 on v2 bills; page 3 defaults to it.

**Priority:** P1 · **Opened:** 2026-09-23

**Evidence.** v2 assemblers bake ×1.3 material markup into every rate and set
`markup_zar = 0`. `pages/3_BOQ_Generation.py:37-42` `_reprice()` then adds `markup` %
(default 20 %) of the subtotal again.

**Acceptance.** Markup applied exactly once (decided in an ADR); a test proves it.
