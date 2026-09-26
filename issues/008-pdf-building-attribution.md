# 008 — PDF lines cannot be attributed to reference buildings

**Priority:** P1 · **Opened:** 2026-09-23

**Evidence.** PDF baseline: per-building RS 10.3 % vs project-level 18.8 %; the completer
added nothing because most lines land in `(unattributed)`. `BQLineItem.building_block`
holds DB or room names; Pass 1 reads a `buildings` list and Pass 2 DB locations but they
are never joined.

**Acceptance.** Facts carry a DB → building map; every line carries its building;
per-building and project-level PDF scores converge; the completer applies.
