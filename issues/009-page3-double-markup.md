# 009 — Page 3 applies contractor markup on top of rates that already include markup

**Priority:** P1 · **Opened:** 2026-09-23

**Evidence.** v2 assemblers bake ×1.3 material markup into every rate and set
`markup_zar = 0`. `pages/3_BOQ_Generation.py:37-42` `_reprice()` then adds `markup` %
(default 20 %) of the subtotal again.

**Acceptance.** Markup applied exactly once (decided in an ADR); a test proves it.
