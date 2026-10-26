---
name: structure-review
description: Evaluate a codebase's STRUCTURE and score it out of ten — layering, module sizes, test coverage, how architecture rules are enforced (tests/hooks/CI), decision records (ADRs), docs, and data-safety. Use when asked to "check the structure", "evaluate/rate the repo out of ten", "is this well architected", or for a structural health check before a milestone. Not a bug hunt and not a BOQ scorer — use code review for defects, evaluate-boq for output accuracy.
---

# structure-review

**Goal:** a reproducible, honest score out of ten for how well a repository is
*structured*, backed by evidence from the actual files — never a vibe. The score
must fall out of a fixed rubric so two runs on the same repo agree.

This skill is generic: it runs on any repo you open in VS Code. Point it at the
repo root (the working directory by default) and work top-down.

## Rules
- **Evidence before claim.** Every strength and gap names a file, a count, or a
  command output. No "feels clean" without a reason.
- **Check claims against reality.** When `README`/`CLAUDE.md`/docs assert a
  guarantee ("enforced by CI", "100% typed", "all tested"), verify it exists in
  the repo. A stated guarantee that no file backs is a gap, not a strength — this
  is the highest-value finding this skill produces.
- **Report honestly.** List regressions and gaps even when the overall score is
  high. If a category can't be measured, say so and don't award its points.

## Step 1 — Map the structure
```bash
ls -la                                   # top level
git branch --show-current 2>/dev/null; git status -s 2>/dev/null | head
# subdirectories of the main source trees (adjust names to the repo)
for d in */ ; do echo "$d"; ls -F "$d" 2>/dev/null | head; echo; done
```
Read the README and any `CLAUDE.md`, `context.md`, `docs/architecture.md`. Note
what the project *claims* its structure and guarantees are — you will test them.

## Step 2 — Measure size and shape
```bash
# lines of code per area (edit the dir list to match the repo)
for d in <dirs...>; do
  loc=$(find "$d" -name '*.py' -o -name '*.js' -o -name '*.jsx' -o -name '*.ts' -o -name '*.tsx' 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
  files=$(find "$d" -type f 2>/dev/null | wc -l)
  echo "$d: $files files, ${loc:-0} lines"
done
# the heaviest files — oversized modules are a structure smell
find . -path ./node_modules -prune -o \( -name '*.py' -o -name '*.jsx' -o -name '*.ts' \) -print | xargs wc -l 2>/dev/null | sort -rn | head -15
```
Flag any single file well above the repo's norm (rough guide: >500 lines for a
non-generated module) as a split candidate.

## Step 3 — Tests
```bash
find . -path ./node_modules -prune -o -name 'test_*.py' -print -o -name '*.spec.*' -print -o -name '*.test.*' -print | wc -l
grep -rh "def test_\|it(\|test(" --include='*.py' --include='*.js' --include='*.jsx' . 2>/dev/null | wc -l
```
Do test directories mirror the source layout (a good sign)? Are there tests that
assert *architecture* (import boundaries, layering), not just behaviour?

## Step 4 — Enforcement (the part docs usually overstate)
Find every mechanism that keeps the structure from rotting, and confirm each one
is actually wired:
```bash
find . -path ./node_modules -prune -o \( -name '*.yml' -o -name '*.yaml' \) -print   # CI, deploy
ls .github/workflows/ 2>/dev/null || echo "NO GitHub Actions CI"
cat .claude/settings.json 2>/dev/null                                                # Claude Code hooks
ls .pre-commit-config.yaml .husky 2>/dev/null                                        # git hooks
```
For each guarantee the docs state, answer: **where does it run, and what does it
cover?** A hook that only fires in local Claude Code sessions does NOT protect
`main` — say so explicitly. This usually drives the single biggest point loss.

## Step 5 — Decisions and backlog
```bash
ls docs/adr/ docs/decisions/ 2>/dev/null       # architecture decision records
ls issues/ 2>/dev/null                          # in-repo defect backlog
```
Are non-obvious choices recorded with rationale? Is known debt tracked with
evidence, or invisible?

## Step 6 — Data safety / secrets
```bash
cat .gitignore
git ls-files | grep -iE '\.env|secret|credential|reference_boq|ratio_model' || echo "no obvious secrets tracked"
```
If the repo is public (check README/ADRs), confirm client data and secrets are
excluded by `.gitignore` and not already committed.

## Step 7 — Score it (fixed rubric, 10 points)
Award each category from the evidence gathered. Do not round up to be kind.

| # | Category | Pts | Full marks when... |
|---|---|---|---|
| 1 | Layering & separation of concerns | 2 | clear boundaries (e.g. thin IO / fat core), no tangled cross-imports |
| 2 | Enforcement matches claims | 2 | every stated guarantee runs where it's needed (CI on `main`, not just local) |
| 3 | Test structure & coverage of boundaries | 1.5 | tests mirror source; architecture/boundary tests exist |
| 4 | Module size & cohesion | 1.5 | no oversized god-files; each module does one thing |
| 5 | Decision records (ADRs) & tracked backlog | 1 | key choices recorded; debt tracked with evidence |
| 6 | Documentation | 1 | architecture one-pager + glossary + honest README |
| 7 | Data/secret safety & config hygiene | 1 | secrets/client data gitignored and absent from history |

Half-points are fine. Sum to one decimal.

## Step 8 — Report
Output in this shape (concise, evidence-led):
1. **One-line structure map** — a small table of areas, paths, sizes.
2. **Strengths** — each with its evidence (file/count).
3. **Where it loses points** — each gap tied to the rubric category it cost, most
   important first. Put any "claim not backed by a file" finding at the top.
4. **Score: X / 10** with a one-sentence verdict.
5. **The one change that would raise the score most** — name it, and offer to do it.

Keep it plain. Report the number honestly even when it is lower than the author
hoped; an overstated score helps no one.
