# 014 — Add a second reference project (Trichard) as ground truth

**Priority:** P1 — unlocks generalisation · **Opened:** 2026-09-23

**Evidence.** Ratios, taxonomy and scorer are validated on one project (ADR-0004). The
Trichard priced BOQ exists locally (`Electrical plan/EXCEL FILES/Revised BOQ ERF 470
TRICHARD Herve.xlsx`); its drawings need collecting.

**Acceptance.** `data/projects/trichard/` onboarded with the `add-reference-project` skill;
ratios refitted with leave-one-project-out error; baselines for both projects.
