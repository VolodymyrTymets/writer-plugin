# FT-13 — a saved verdict keeps its header lines

No tracker; a row of the Field-test findings table in `docs/DESIGN.md`.

## Problem
Gates print a verdict whose line 1 is the ADR-004 heading, line 2 `Artifact: <path>`, and (G1, G2, G3, G4) line 3 a count line
(`Coverage:`, `Markers:`, `Outline:`). The actor saves it with Write. In the field test actors added blank lines, so the count line moved off line 3.
Only line 1 is checked today (`bin/guard-stage-order.py` `check_gates`), so a changed header is saved without a word, and the next reader
(the human, a later gate run, the `article` skill quoting the `Coverage:` line) finds the header not where the contract says.

## Goal / business value
BUSINESS_MODEL goal 1 (mechanical enforcement over a prompt rule): a verdict that is saved is the verdict the gate gave.

## Scope
- in: `guard-stage-order` refuses a new verdict whose line 2 is not `Artifact: <non-empty>` or whose line 3 (G1 `Coverage:`, G2 and G4 `Markers:`,
  G3 `Outline:`) is not that label; G0 has no line 3. The block names the line and the fix. The five actor skills say "save lines 1 to 3 as printed,
  no blank line before them". ADR-004 is refined (new ADR-019).
- **out (explicit):** the body of a verdict (findings, `Not checked`); the counts' values (no parser reads them); an actor that edits text inside the
  body; verdicts already saved; FT-14; any change to the gate skills' own text, except `check-brief`'s "say PASS in one line", which contradicted the `Artifact:` line the guard now requires.

## Acceptance criteria
- [x] AC1 Given a new G1/G2/G3/G4 verdict whose line 3 is blank or another line, when written with Write, the guard exits 2 naming "line 3" and the label wanted.
- [x] AC2 Given a new verdict of any gate whose line 2 is not `Artifact: <something>`, the guard exits 2 naming "line 2".
- [x] AC3 Given a verdict exactly as a gate prints it (the literal examples in the five gate skills, including the `Artifact: none` BLOCKs with `Coverage: n/a` / `Markers: n/a`), the guard allows it.
- [x] AC4 CRLF line endings do not trip it (the existing line-1 check strips `\r`).
- [x] AC5 Existing hook tests that save a verdict with only line 1 are updated to a full header, none deleted or skipped (B3); new cases cover AC1 to AC4.
- [x] AC6 The five actor skills carry the "save lines 1 to 3 as printed" sentence, pinned in `tests/test_skills.py`.
- [x] AC7 Full pytest passes; `claude plugin validate ./` passes with only the known warning.

## Edge cases
| Case | Expected behaviour | Decided by |
|------|--------------------|-----------|
| G0 verdict, line 3 blank (the contract has no line 3) | allowed: line 3 of G0 is free text | check-brief format section |
| `Artifact: none` BLOCK for a missing artifact | allowed, line 3 `Coverage: n/a` / `Markers: n/a` | gate skills |
| Content has fewer than 3 lines (a G1 verdict of 2 lines) | blocked at line 3 for G1 to G4 | AC1 |
| Verdict body mentions "Coverage:" lower down | irrelevant: only line 3 is read | AC1 |
| Leading BOM or space before `Artifact:` | blocked: line 2 starts with `Artifact: ` | AC2 |

## Open questions
| # | Question | My assumed answer | Needs a human? |
|---|----------|-------------------|----------------|
| 1 | Hook or byte-for-byte prompt text? DESIGN offers both | Hook plus one sentence in the actors: a hook is a mechanism (BUSINESS_MODEL judgement table) | no |
| 2 | Also check the count values? | No: "no parser reads it"; a value check would block on noise | no |
| 3 | Enforce on an actor's retry loop cost: a block spends one more turn | Accepted; the message gives the exact fix | no |
