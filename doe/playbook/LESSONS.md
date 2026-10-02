# Lessons — what each project taught us (the playbook's memory)

Add one entry per run that surprised us. Keep it general: what would help on the NEXT
consultant's drawings? No client rand figures here (this file is committed).

## Wedela (reference project)
- Cable routes live on the electrical outline sheet (`WD-OL-001`), not on the architect's site plan.
- The PDF set is one combined file: pages are paired to DWG sheets by the words they print.
- Words in brackets describe equipment ("KIOSK (WD-KIOSK-01)" is the KIOSK).
- Solar post and high-mast lights share one legend glyph with other outdoor lights —
  the name must come from the legend text next to it, not the shape.
- Trunking, sleeves, manholes, draw wire and connection fees are never drawn: they must be
  estimated and flagged, not expected from the drawings.

## General (2026-10-02, subscription reading of the Wedela PDFs)
- **Legend QTY columns are gold.** Many consultants print the designer's own count per fitting in
  the legend. Reading them gave the best PDF result so far (47.5 % vs 27.1 % for an AI counting
  symbols); look for them first. They count the whole sheet, not rooms.
- **Scanned SLD pages are readable by vision** at full-page resolution; board headers, breaker
  ratings, spares and "fed from / incoming main cable" boxes give boards AND feeders.
- **Feeder routes vs the SLD can disagree** (site outline: DB-AB1 fed from DB-PFA; SLD: from DB-CR).
  Price the SLD's cable, flag the difference.
- **Form gaps found:** no field for DOL motor starters, master switches, single 5 ft fluorescent
  battens, prismatic battens, geysers or A/C units — they go in warnings today. Adding fields
  is a schema change (ask first).
- **Same site lights on two sheets** (an outline sheet's "outdoor pole lights" and a building
  sheet's solar posts / high masts) — the engine flags it; a person decides.
