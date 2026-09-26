---
name: karpathy-coding-discipline
description: Behavioural guidelines to reduce common LLM coding mistakes — think before coding, minimum code, surgical changes, goal-driven execution. Source multica-ai/andrej-karpathy-skills, via the Agent Workflow Kit. Use for any non-trivial coding task where correctness matters more than speed.
---

# karpathy-coding-discipline

## 1. Think before coding
State assumptions explicitly. If several interpretations exist, present them — don't
pick silently. If a simpler approach exists, say so. If something is unclear, stop and ask.

## 2. Simplicity first
Minimum code that solves the problem. No speculative features, no abstractions for
single-use code, no configurability nobody asked for. If 200 lines could be 50, rewrite.

## 3. Surgical changes
Touch only what the task needs. Don't "improve" adjacent code, comments or formatting.
Match existing style. Mention unrelated dead code — don't delete it. Remove only the
orphans your own change created.

## 4. Goal-driven execution
Turn tasks into verifiable goals ("fix the bug" → "write a test that reproduces it,
then make it pass"). For multi-step work state the plan with a check per step:
```
1. [step] → verify: [check]
2. [step] → verify: [check]
```

In this repo the verifiable goal is usually a number: the full test suite, the
architecture tests, and — for pipeline work — the Reproduction Score against a committed
baseline (`evaluate-boq` skill).
