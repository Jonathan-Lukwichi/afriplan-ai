# References

Signposts to the reference material AfriPlan already has. Most of it lives next to the code that
uses it, so nothing is copied here; this page says where to look.

| What | Where | Note |
|---|---|---|
| **How a QS measures and bills electrical work** (drawing → line, the four wiring conventions, route take-off, rate build-up) | `doe/knowledge/BOQ_KNOWLEDGE.md` | Read before changing any wiring or measuring code |
| Material prices (South African rand) | `api/core/constants.py` | Header says "updated Feb 2026"; site-lighting prices are market estimates to verify with suppliers |
| Rate model (crew × hours, consumables, transport, waste) | `api/core/rate_model.py` | Deterministic; no LLM |
| SANS / standards rules used in checks | `api/core/standards.py`, `api/agent/shared/compliance.py` | |
| Symbol legend conventions | `api/agent/shared/legend.py`, `api/agent/shared/symbol_catalogue.py` | A drawing's own legend wins (LDSE, `context.md`) |
| How the DOE brain reads a page | `doe/brain/BRAIN.md`, `doe/playbook/` | |
| Accuracy metrics and the data plan | `docs/accuracy-metrics.md` | |
| Decisions and why | `docs/adr/` | This repo's decision log |
| Connected tools and keys | `references/connections.md` | Key names only |

Supplier quote format: **unsure, not documented yet** (the suppliers in `api/sourcing/suppliers/`
are mocks).
