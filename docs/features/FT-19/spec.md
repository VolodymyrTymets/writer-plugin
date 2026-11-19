# FT-19 — a thin research dossier no longer blocks; the gaps travel as markers

No tracker; a row of the Field-test findings table in `docs/DESIGN.md`.

## Problem
G1 blocks a dossier that answers fewer than half of the brief's questions (FACT-6 floor, ADR-014). On drifity, 4 of 12 questions were answered and the rest need
a human (G2 and Capterra pages, Reply.io pricing, hands-on tests). Two BLOCKs stopped the article (FLOW-3), so the draft and the final were never reached,
although the human wanted to carry the gaps forward as markers and fill them later.

## Goal
The flow continues past a thin dossier. Each unanswered question stays a `<Can't be verified. Reason: ...>` marker (ADR-008, one per gap, ADR-017) through the
outline and the draft into the final, where a human fills them. The final cannot be signed off while a marker remains (FLOW-6), which is what protects publication.

## Scope
- in: G1 reports the coverage floor as an **advisory** finding (still on the `Coverage:` line, same arithmetic), not a blocking one. The research stage
  tells the human the numbers and what would answer each open question, and no longer stops before the gate (FT-17 Step 3b is removed). The human sees it
  when approving the research.
- **out (explicit):** a waiver line or a `style.md` setting; any change to the markers, FLOW-6 or the outline/draft/final gates; per-question findings;
  the human approval of research (still required, FLOW-2).

## Acceptance criteria
- [x] AC1 Given a dossier with `answered x 2 < m` and no other defect, G1 returns PASS with the floor as an advisory finding naming the numbers.
- [x] AC2 The `FACT-6` rule text in the checklist, the gate skill, the constitution template and DESIGN says "at least half is advised", not blocking.
- [x] AC3 The research skill has no "do not run the gate" step; it reports the coverage and the open questions after the gate.
- [x] AC4 The existing tests that pinned the block are changed to pin the advisory (a deliberate contract change, rule B3), none deleted or skipped.
- [x] AC5 Full pytest passes; `claude plugin validate ./` passes with only the known warning.

## Edge cases
| Case | Expected behaviour | Decided by |
|------|--------------------|-----------|
| 0 of 12 answered | G1 PASS with the advisory; the human decides at approval | this spec |
| A question is neither answered nor under Open gaps | still a blocking FACT-6 finding (unchanged) | ADR-008 |
| Final holds markers | G4 may PASS it; sign-off is refused (FLOW-6) | ADR-008, ADR-012 |

## Open questions
| # | Question | Assumed answer | Needs a human? |
|---|----------|----------------|----------------|
| 1 | Advisory, or a typed waiver the human must write? | Advisory: the research approval is already the human checkpoint and shows the numbers | yes |
| 2 | Should the outline stage warn when the research was thin? | No, the markers already show in its Open questions section | no |
