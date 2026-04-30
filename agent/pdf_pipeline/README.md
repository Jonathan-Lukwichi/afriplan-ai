# `agent.pdf_pipeline` — vision-LLM PDF → BoQ

Anthropic-powered pipeline. **Never imports from `agent.dxf_pipeline`.** **Never uses `parse_json_safely(`** — every model call goes through `tool_use` with a strict JSON schema, so the SDK validates structure for us. CI grep-checks both rules.

## Stages

```
PDF bytes ─▶ ingest ─▶ classify ─▶ extract ─▶ evaluate ─▶ generate ─▶ BoQ
                       (Haiku)    (Sonnet/Opus)
```

| Stage | File | Model | Purpose |
|---|---|---|---|
| `P1` Ingest    | [`stages/ingest.py`](stages/ingest.py)     | — | PyMuPDF rasterises pages at 200 DPI, hashes input, caps at 30 pages |
| `P2` Classify  | [`stages/classify.py`](stages/classify.py) | Haiku 4.5 | One PageClassification per page (register / sld / lighting / plugs / schedule / notes) |
| `P3` Extract   | [`stages/extract.py`](stages/extract.py)   | Sonnet 4.5 + Opus 4.6 escalation | Per-page-type tool with retry-with-error-feedback |
| `P4` Evaluate  | [`stages/evaluate.py`](stages/evaluate.py) | — | Confidence aggregation, cross-page consistency, baseline MAPE, SANS compliance |
| `P5` Generate  | [`stages/generate.py`](stages/generate.py) | — | Aggregate to a `BillOfQuantities` |

## Why `tool_use` instead of free-form JSON

The blueprint forbids hand-rolled JSON parsing (no `parse_json_safely`, no markdown-fence stripping, no trailing-comma fixes). Every extraction goes through a strict tool schema in [`prompts/tool_schemas.py`](prompts/tool_schemas.py). The Anthropic SDK validates the response against the schema; if invalid, our wrapper retries with the validation error appended to the next user turn ([`llm.py`](llm.py)).

If retry fails too, we escalate Sonnet → Opus before giving up.

## Prompt caching

The system prompt in [`prompts/system_prompt.py`](prompts/system_prompt.py) is **frozen** — no timestamps, no per-request data. Each call sends `cache_control: ephemeral` on the system block, so the ~1500-token SA-domain prefix caches across every page in a session. Verify with `usage.cache_read_input_tokens` on the response.

## Acceptance criteria (blueprint §3.4)

- Wedela MAPE ≤ 20 % vs baseline
- Trichard MAPE ≤ 20 % vs baseline
- Three repeat runs produce grand totals within ±5 %
- `parse_json_safely` does not appear anywhere under this directory
- Mean cost per run ≤ R 8.00
- Mean wall-clock ≤ 60 s for 10-page PDFs

## Testing

```bash
pytest tests/pdf_pipeline/        # ~12 s, no network
```

Tests use a `MockAnthropic` client (see [`tests/pdf_pipeline/conftest.py`](../../tests/pdf_pipeline/conftest.py)) that returns canned tool_use responses keyed by `tool_choice.name`. No real API calls in CI.

## Cost telemetry

Every stage records a `StageCost` (input tokens, output tokens, cache hits, ZAR cost, retry count, duration). The orchestrator returns these in `PdfPipelineRun.stage_costs`, and `PdfPipelineRun.cost_zar` is their sum. The UI shows it next to the result; persisted runs in `runs/pdf/<run_id>.json` retain it for analysis.
