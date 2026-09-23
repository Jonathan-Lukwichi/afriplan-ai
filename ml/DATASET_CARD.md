# Dataset card — CAD-labelled electrical symbol images (v0, 2026-09-23)

## Purpose
Training data for a future CNN symbol detector that reads client PDFs (ADR-0004).
Labels come free from CAD: every classified block in a DWG is projected into pixel
space. No model is trained yet — one project is not enough to generalise.

## How to build
```bash
python scripts/build_symbol_dataset.py wedela     # → data/ml/symbols/wedela/ (gitignored)
```
Output: `images/*.png` (line-work, black on white, ≤ 4096 px long side), `labels/*.txt`
(YOLO: `class cx cy w h`, normalised), `classes.txt`, `samples.jsonl`.

## Wedela v0 — what the CAD actually yields
| | |
|---|---|
| Sheets | 17 (5 lighting, 5 plug, 7 SLD; superseded revision excluded) |
| Labelled symbols | **44 — all class `switch`** |
| Sheets with 0 labels | 6 of 7 SLDs |
| Image size | ~4097 × 2839 px |

## Honest limitations
1. **Sparse, single-class labels.** Wedela's DWGs are Revit exports: lights and sockets
   are exploded line-work, not blocks, so they carry no label. Only switch blocks
   survive. This set cannot train a multi-class detector. Useful sources of more labels:
   block-based CAD from other consultants, and LDSE mode-3 template matches
   (`agent/dxf_pipeline/passes/template_count.py`) promoted to labels after human review.
2. **Legend glyphs are labelled as instances.** Each layout's legend table contains
   switch glyph blocks that are labelled like plan symbols (visible in the top-left
   legend box of every layout). Before training, exclude INSERTs inside the legend
   region. The same defect makes the DXF pipeline over-count switches (44 vs 20 in the
   reference BOQ) — see `issues/`.
3. **No text rendered.** TEXT/MTEXT (circuit tags, room names) are not drawn, so the
   images differ from real PDFs, which carry text. Add text rendering before training
   a PDF-facing detector, or train on PDF renders with CAD-projected boxes.
4. **One project.** Any detector must be validated leave-one-project-out; in-project
   accuracy is not evidence of generalisation.

## Next data milestones
- ≥ 5 reference projects with block-based symbols (sockets, lights, DBs, isolators).
- Legend-region exclusion + text rendering in `ml/symbol_dataset.py`.
- A held-out project reserved for detector evaluation.
