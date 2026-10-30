# .claude/ — index, in loop order

What Claude Code loads for this project, and where each piece sits in the working loop
(`rules/working-loop.md`). CLAUDE.md at the repo root is read first, every session.

## 1. Rules (read first; they say how to work)
| File | What it is |
|---|---|
| `rules/working-loop.md` | The loop, step by step: 0 Orient → A (DOE estimate) or B (develop) → back to 0 |
| `rules/three-layer-approach.md` | Instructions → agent → engines, plus a check on every result |

## 2. Skills, by loop step
| Step | Skill | Use it to |
|---|---|---|
| A1–A2 | `skills/estimate-project/` | turn a project folder into a priced BoQ (DOE) |
| A3 · B5 | `skills/evaluate-boq/` | score a bill against a reference project (frozen scorer) |
| A3 | `skills/audit-boq/` | audit a bill or a drawing set for what is wrong or missing |
| B1 (data) | `skills/add-reference-project/` | add a new reference project (ground truth) |
| B3 | `skills/tdd/` | write the failing test first |
| B4 | `skills/karpathy-coding-discipline/` | make the smallest, surgical change |
| B5 | `skills/check-takeoff/` | compare the take-off with hand counts (`scripts/check_takeoff.py`) |
| A4 · B5 | `skills/fix-and-learn/` | fix a failure at the right layer and write the lesson down |

**BoQ domain skills** (rule tables with confidence; each logs corrections in its `FEEDBACK.md`):
| Step | Skill | Use it to |
|---|---|---|
| A1–A2 | `skills/reading-scope-modifiers/` | read notes, legend, spec and scope pages first |
| A1–A2 | `skills/reading-drawing-symbols/` | read layout and SLD pages into forms; symbol naming |
| B2–B4 | `skills/deriving-companion-items/` | derived lines (conduit, GP wire, earth, boxes…); rules in `RULES.md` |
| B2–B4 | `skills/writing-sa-bill-lines/` | descriptions, units, sections and order of bill lines |
| A3 · B5 | `skills/checking-boq-completeness/` | is the bill complete and plausible before it goes out |
| B2 | `skills/consolidating-price-catalogue/` | add or change supplier prices and the catalogue |
| A4 · B6 | `skills/improving-boq-skills/` | log what a scored run or a correction taught (a hook reminds) |

General skills installed on this PC (not in this folder): `dashboard-qa-gate` (B5, UI) ·
`frontend-design`, `dashboard-ui-kit` (B4, UI) · `data-core-engine` · `data-app-deploy`.

## 3. Agents (read-only helpers)
| File | Step | Use it to |
|---|---|---|
| `agents/checker.md` | A3 | review a BoQ: every line has a source, assumptions and gaps listed |
| `agents/researcher.md` | any | search files or the web and return a short sourced summary |

## 4. Settings and hooks (`settings.json`)
- **permissions:** deny reading `.env` / `api/.env` and `rm -rf`; ask before `git push`.
- **PostToolUse hook:** after every Edit/Write of a `.py` file, `scripts/hooks/check_architecture.py`
  runs `tests/architecture` (hard rules 1–3); a violation is fed straight back.
- Personal settings go in `settings.local.json` (gitignored).

CI (`.github/workflows/ci.yml`) runs the same checks, and more, on every push.
