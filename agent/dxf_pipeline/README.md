# `agent.dxf_pipeline` — deterministic DXF → BoQ

Pure-Python pipeline. **Never imports an LLM SDK.** **Never imports from `agent.pdf_pipeline`.** CI grep-checks both rules on every run; see [`tests/architecture/test_independence.py`](../../tests/architecture/test_independence.py).

## Stages

```
DXF bytes ─▶ ingest (ezdxf) ─▶ layers ─▶ extract ─▶ evaluate ─▶ generate ─▶ BoQ
```

| Stage | File | Purpose |
|---|---|---|
| `D1` Ingest    | [`stages/ingest.py`](stages/ingest.py)     | Open DXF, detect units, hash, return `(IngestResult, Drawing)` |
| `D2` Layers    | [`stages/layers.py`](stages/layers.py)     | Index every layer; mark electrical layers via `core.layer_aliases` |
| `D3` Extract   | [`stages/extract.py`](stages/extract.py)   | Walk modelspace, classify each `INSERT` via [`patterns.py`](patterns.py) |
| `D4` Evaluate  | [`stages/evaluate.py`](stages/evaluate.py) | Coverage, baseline regression, anomalies (orphan circles, ultra-long polylines) |
| `D5` Generate  | [`stages/generate.py`](stages/generate.py) | Aggregate to a `BillOfQuantities` |

## Acceptance criteria (blueprint §4.4)

- Block counts on a reference DXF match a hand-counted baseline exactly
- `coverage_score >= 0.80` (≥ 80 % of `INSERT` blocks recognised)
- Polyline lengths match annotated cable lengths within ±5 %
- No imports from any LLM SDK
- End-to-end run < 5 s on the largest reference DXF

## Extending the pattern dictionary

If `coverage_score` drops on a real project, the answer is almost always to add entries to [`patterns.py`](patterns.py). The evaluator emits the unrecognised block names directly:

```python
result = run_dxf_pipeline(dxf_bytes)
print(result.extraction.raw_block_names_unrecognised)
# → ['Lampe_LED_Encastree_24W', 'Prise_Double_Schuko']
```

Add them to `EXACT_BLOCK_MAP` (or `REGEX_BLOCK_PATTERNS` if a regex captures a family), commit, re-run CI, watch coverage rise.

## Testing

```bash
pytest tests/dxf_pipeline/        # ~3 s on a laptop, no network, no Anthropic
```

Test fixtures synthesise DXFs in memory via `ezdxf`, so the suite has no on-disk dependencies.
