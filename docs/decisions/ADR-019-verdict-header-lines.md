# ADR-019 — Lines 2 and 3 of a saved verdict are checked

- **Date:** 2026-11-17
- **Status:** accepted
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (`docs/features/FT-13/plan.md`, finding FT-13)
- **Relation:** refines ADR-004, whose line-1 rule said "everything else is free text".

## Context
Gates print `Artifact: <path>` on line 2 and, for G1 to G4, a count line on line 3 (`Coverage:`, `Markers:`, `Outline:`). In the field test actors saved
verdicts with blank lines added, so the count line left line 3. Only line 1 was checked, so the save went through unnoticed.

## Decision
- `guard-stage-order` refuses a new verdict whose line 2 is not `Artifact: ` followed by a value, or, for G1, G2, G3 and G4, whose line 3 does not
  start with that gate's label (`Coverage:`, `Markers:`, `Outline:`, `Markers:`). G0 has no line 3. The check is `writer.verdict_header_problem`.
- Only the labels are checked, never the counts: no parser reads them, and a value check would block on noise.
- The five actor skills extend ADR-004's line-1 rule: lines 1 to 3 are saved as printed; if the gate printed them otherwise, it is no PASS: nothing is saved, the user is told what came back and the stage stops
  (no rerun loop: a gate that prints an off-contract header every time would cost a rerun each, with no FLOW-3 strike). The actor never edits them.
- `tests/test_skills.py` runs the check on every literal example in the five gate skills and on a constructed `Artifact: none` BLOCK per gate.

## Rejected alternatives
| Alternative | Why not |
|-------------|---------|
| A prompt sentence only ("save byte for byte") | It is a request, not a mechanism; the field test already showed it was not kept |
| Check in `record-verdict` (PostToolUse) | It runs after the file exists and cannot refuse the save |
| Check the count values | Not parsed by anything; a mismatch would be noise |

## Consequences
- Positive: a saved verdict is the gate's verdict in its first three lines.
- Accepted cost: a gate that changes its header format must change `VERDICT_LINE3` in the same PR; the examples test fails otherwise.
- Verdicts already on disk are not re-checked.

## Revisit when
A gate gets a different line 3, or a parser starts reading the counts.
