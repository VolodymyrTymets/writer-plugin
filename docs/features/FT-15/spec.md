# FT-15 — a stopped stage still gives reviewers a Doc

No tracker; a row of the Field-test findings table in `docs/DESIGN.md`.

## Problem
A stage that gets two BLOCKs stops (FLOW-3) with no Google Doc, so the blockers cannot be discussed where reviewers work (drifity, research stage).

## Scope
- in: the five actor skills make one ungated copy on their second BLOCK before stopping; the orchestrator's `stopped` row says where it is; ADR-020.
- out: any script or hook change; a copy after a first BLOCK; resuming a stopped stage from `sync`; Docs for articles already stopped.

## Acceptance criteria
- [x] AC1 Each of the five actors names `writer-plugin:publish <slug> <its stage>` in its second-BLOCK step, before "stop as in Step 2" (`tests/test_skills.py`).
- [x] AC2 The orchestrator's `stopped` row names the ungated copy and the archive step.
- [x] AC3 Full pytest passes; `claude plugin validate ./` passes with only the known warning.

## Open questions
| # | Question | Assumed answer | Needs a human? |
|---|----------|----------------|----------------|
| 1 | May a name typed in an ungated Doc be carried in by `sync`? | Harmless: the next stage needs a PASS, and a rerun clears the approval | yes, if it confuses reviewers |
