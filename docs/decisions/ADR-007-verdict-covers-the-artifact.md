# ADR-007 — A verdict covers the artifact it judged; the actor never edits after a PASS

- **Date:** 2026-11-13
- **Status:** accepted
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (`docs/features/verdict-covers-artifact/plan.md`)
- **Refines:** ADR-004 (verdict-file contract). ADR-004's format, numbering and FLOW-3 counting are unchanged.

## Context
Running the brief stage on a real brief, the actor fixed the gate's advisory findings in `brief.md` after the PASS and did
not rerun the gate. The saved verdict described an earlier version, and FLOW-1 trusts that file.

## Decision
1. After a PASS the actor never edits the artifact. It reports the gate's advisory findings to the user and stops.
2. If the artifact has to change, the stage's written input changes and the stage runs again: a corrected input file for
   the brief stage (saved as `brief.source.md`); research and outline rebuild from their upstream artifacts. The rebuilt
   artifact is gated again and its verdict is saved as the next `r<k>`. A BLOCK from a rerun counts toward FLOW-3 like any
   other BLOCK.
3. A rebuild keeps earlier work. The brief stage carries `<field>: answered by the user, round <n>` lines forward verbatim.
   The outline stage copies any existing `outline.md` to `outline.prev.<n>.md` before replacing it (`n` is 1 plus the
   highest existing `n`, independent of verdicts, so it cannot collide after a stop or an archive), never replaces a backup,
   and says the approval was cleared when `Approved-by:` was non-empty. A replaced outline needs a new approval.
4. A rebuild stales what was built on it: the report names later artifacts as built on the replaced version.
5. The verdict covers the artifact apart from the human approval line (`Approved-by:`, later `Signed-off-by:`), which the
   human writes after the PASS by design. A human may still change the outline's direction before approving
   (`docs/DESIGN.md`, the approval row).
6. An advisory on a PASS is the human's to accept or act on. A rerun of research or outline rebuilds from upstream and does
   not target it.
- Known gap, not closed here: a human's hand edit, or an edit by the main agent outside the stage skill, is not recorded or
  enforced. The constitution carries one hygiene line as a request, not a mechanism.

## Rejected alternatives
| Alternative | Why not |
|-------------|---------|
| Let the actor fix advisories in place and rerun the gate | G0 would have to accept a field that contradicts the source on the strength of a line the actor wrote, and the gate cannot see the chat |
| Require every human edit to be re-gated | The plugin cannot record a gate rerun for a hand edit (a standalone gate run is not recorded; rerunning the stage rebuilds the file). Left as an open question for Phase 4 |
| One `outline.prev.md` slot | A second rebuild would overwrite the approved outline |

## Consequences
- Positive: a saved verdict describes what the stage wrote, and a human's outline is never silently lost.
- Accepted cost: a change after a PASS costs a rerun and a new verdict, and research and outline accept no free-text change.
- Follow-ups (Phase 4, `guard-stage-order`; DESIGN open questions 5 and 6): re-gate and record a human edit before
  approval; require content other than the approval line to be unchanged since the latest verdict, and a downstream
  verdict to be newer than the upstream verdict it relied on. A bare modification-time check would trip on the approval edit.

Refined by ADR-009: the Phase 4 hooks make the stale-verdict and hand-edit checks mechanical (open questions 5 and 6 are resolved there).

## Revisit when
The Phase 4 hook exists, or a stage needs to take a free-text change.
