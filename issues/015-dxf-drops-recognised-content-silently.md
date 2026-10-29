# 015 — DXF engine read Windows-saved DXFs as empty; unnamed symbols were priced silently

> **Status:** PARTLY FIXED 2026-10-29. Parts 1–2 fixed; part 3 open (needs the owner's OK: it
> changes the symbol catalogue, and must be checked against the Wedela baseline).

**Priority:** P1 · **Opened:** 2026-10-29 by `/check-takeoff` on the synthetic sample (no client data)

## 1. Windows line endings → an empty drawing, no error (FIXED)
**Evidence.** The sample DXF (saved with CRLF line ends, as AutoCAD on Windows writes them) loaded
through `passes/run.py::_load` as an empty document: 0 of 31 entities, default units, no exception.
The run then said "No electrical content recognised in the DXF". The same file with LF line ends:
31 entities. Cause: `ezdxf.read(io.StringIO(text))` keeps the `\r`; ezdxf parses nothing and does
not raise. Wedela escaped it: its DWGs are converted by LibreDWG, which writes LF.
**Fix.** `io.StringIO(..., newline=None)` in `_load`, and the same in
`scripts/build_symbol_dataset.py::_read_dxf`. Tests: `test_dxf_assemble.py::
test_a_dxf_saved_with_windows_line_endings_is_read_not_emptied`,
`test_build_symbol_dataset.py`.
**Result on the sample.** 27 symbols and 34.25 m of wiring reach the bill; the wiring matches the
hand count exactly.

## 2. Symbols it cannot name were priced with no gap (FIXED)
**Evidence.** Unknown blocks on an electrical layer bill as one "Electrical Symbol (unclassified)"
line with no `GapItem` (hard rule 7).
**Fix.** `passes/assemble.py::_fittings` now adds a gap per group naming the blocks and their counts
("27 electrical symbols AfriPlan could not name (blocks: DB_MAIN ×1, …)"). Quantities and prices
unchanged. Test: `test_symbols_it_cannot_name_are_listed_for_the_estimator_by_block_name`.

## 3. Block names joined by underscores are not classified (OPEN)
**Evidence.** `patterns.classify_block_name` returns None for `LIGHT_DOWNLIGHT`, `SOCKET_DOUBLE`,
`DB_MAIN`. The regex fallbacks use word boundaries (`\bdownlight\b`), and `_` is a word character,
so `light_downlight` never matches; the exact map has `downlight` and `db` but is only tried on the
whole name.
**Proposed fix (needs approval).** Split the normalised name on `_ - space $` and try the exact map
per token, longest/most specific first; add a `double … socket` pattern. **Risk:** order matters,
e.g. `LIGHT_SWITCH` must stay a switch, not become a light fitting. So: tests for such pairs first,
then re-run the Wedela DXF baseline (`evaluate-boq`) and report any change in either direction.
**Done when.** `test_check_takeoff.py::test_the_sample_drawing_take_off_matches_its_hand_counts`
passes (it is a strict xfail: it will fail loudly once fixed; remove the marker) and the Wedela DXF
score does not drop.

**Where.** `api/agent/dxf_pipeline/patterns.py` (`classify_block_name`, `EXACT_BLOCK_MAP`,
`REGEX_BLOCK_PATTERNS`).
