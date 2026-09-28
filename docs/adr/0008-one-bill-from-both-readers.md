# ADR-0008: One bill from both readers — findings, combining, one pricer

- **Status:** accepted
- **Date:** 2026-09-28
- **Amends:** ADR-0001 (pipelines stay independent; a new step sits above both)

## Context
The two engines are good at different things. On Wedela the DWG engine measures feeder
routes and trench on the site plan and reads boards exactly from the SLD text; the PDF
engine reads words and pictures (fitting types, notes, sheets that exist only as PDF) but
assumes feeder lengths. Each engine also prices on its own, so the same board costs
differently depending on which engine read it. A contractor who has both a DWG set and the
PDF set should get ONE bill that takes each item from the reader that saw it best.

## Decision
1. **Findings** (`agent/shared/findings.py`): what a reader found on the drawings, *unpriced*
   — boards (with their contents), feeders (with length and how it was known), items
   (fittings, outlets, allowances) and wiring lengths. Each finding says which reader
   produced it, which sheet it came from and its **evidence**.
2. **Evidence decides, not the project:** `measured > counted > written > seen > assumed`
   (measured on CAD geometry; every copy counted in CAD; exact text in the CAD file; read by
   the AI from a picture; assumed). Combining keeps the finding with the strongest evidence
   and lists disagreements as "Things to check". There is no per-project or per-item rule
   tuned on a reference project.
3. **One pricer** (`agent/shared/pricing.py`, `price_findings`): findings → `BillOfQuantities`
   using `core.rate_model`. Both engines price through it, so a board or a feeder is priced
   the same way whoever read it. An item's list price is looked up by the reader from its own
   vocabulary (Python, never the LLM) until both vocabularies are the shared catalogue.
4. **Matching, then choosing.** To combine, the step first decides which findings from the two
   readers are the *same real thing*. Python pairs what it can match exactly (the same board
   tag, the same feeder ends, the same catalogue item on the same sheet). Only the leftovers —
   "KIOSK busbar" vs "KIOSK (WD-KIOSK-01)", "Bulkhead Light" vs "24W bulkhead" — go to the
   Claude API (`api/assist/`, like ADR-0007), which answers through a strict `tool_use` schema:
   *same*, *different* or *unsure*, with a short reason. The AI never picks a quantity, a
   length or a price: once a pair is matched, Python keeps the stronger evidence, and an
   *unsure* pair or a real disagreement (DWG 7 boards, PDF 8) becomes a "Things to check" line.
   Optional and injected: without an API key, combining still runs on exact matches alone.
5. **Independence kept:** neither engine imports the other. Each produces findings; the
   combining step (outside both) takes the two sets. The staged upload is
   CAD → PDF → combine → bill; every step is optional.
6. **Rolled out in steps, each scored on every reference project:** (1) findings + pricer, DXF
   priced through them with an unchanged bill; (2) the PDF engine the same, and it skips sheets
   already read from a DWG; (3) combining with the AI matcher; (4) the staged upload screens. A combined bill must
   score at least as well as the better single engine.

## Consequences
- The PDF engine gains the DWG engine's board and feeder pricing (step 2).
- Paying the AI to read a sheet that was already read exactly from its DWG becomes avoidable.
- Findings are a public schema: changing them is an ASK-FIRST change, like `BillOfQuantities`.
