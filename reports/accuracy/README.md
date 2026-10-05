# Accuracy reports (local only)

Each scored DOE run writes `<stamp>-<reference>-doe-accuracy.md` + `.json` here
(`doe/execution/project.py finish ... --reference <project>`). They quote the real bill's
items and rand values — client data — so everything in this folder except this README is
gitignored (ADR-0005). How to read them: [`docs/accuracy-metrics.md`](../../docs/accuracy-metrics.md).
Progress over time, as percentages only: [`reports/baselines/README.md`](../baselines/README.md).
