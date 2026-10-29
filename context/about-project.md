# About the project

Words follow `context.md` (the glossary). Anything not known from the repo is written "unsure",
never guessed. Last reviewed: 2026-10-29.

## The problem
Manual take-off is the slow, least valuable part of pricing an electrical tender: counting
symbols, measuring cable runs and retyping schedules into a spreadsheet. AfriPlan reads the
drawings (DWG, DXF, PDF), counts and measures, prices at South African rates, and produces the
BoQ and tender document. It also audits bills that already exist.

## Who it is for
- Electrical contractors and estimators pricing a tender.
- Consulting engineers checking a bill ("Audit a BoQ").

## The flow (as the app shows it, `src/pages/Landing.jsx`)
1. Upload the drawings: DXF/DWG, a PDF set, or both.
2. Watch the take-off: symbols counted, cable measured, legend resolved.
3. Review the BoQ: every line labelled extracted, inferred or assumed.
4. Send the quotation: margin, markup and letterhead, as Excel and PDF.

The second route, the DOE workflow in Claude Code, is described in `CLAUDE.md`.

## Target and "done"
- Number we want to move: hours of take-off per tender → minutes.
- Today: see `context/current-state.md` (Wedela reading accuracy, Reproduction Score).
- Done for the pilot: **unsure, owner to set.** The MAPE threshold is also open:
  15 % in the blueprint vs 0.20 in code (`CLAUDE.md`, open item).
- Not in this version: real user accounts (login is demo-only by decision).

## Data rules
- Client drawings and bills are confidential. The repo is public, so client files, parsed
  bills, fitted ratios and client figures never enter git (hard rule 9, ADR-0005).
- No real client files in a test set without the client's permission.
- What may be sent to an AI: drawing pages go to the Claude API or Gemini (web app), or are read
  by Claude Code (DOE). Whether clients must be told or must agree: **unsure, owner to set.**
- POPIA notice: **unsure, open item.**
- Before anything goes to a client, a qualified person signs it off. Who counts as qualified
  (e.g. ECSA-registered): **unsure, owner to set.**

## People
| Name | Role | What they need |
|---|---|---|
| Hervé / Jonathan Lukwichi (JLWanalytics) | Owner, developer | unsure |

## Tools and data the project uses
See `references/connections.md`.
