# ADR-008 — What research cannot find or prove is marked for a human, and the flow goes on

- **Date:** 2026-11-13
- **Status:** accepted
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (`docs/features/human-check-marker/plan.md`)
- **Relation:** reopens no ADR. It applies FACT-1 at the outline gate to a marker and extends FLOW-6. It relies on ADR-004's
  FLOW-3 count staying unchanged: a marker is not a BLOCK.

## Context
Running the outline stage on a real brief, research could not find or prove some facts. The outline gate blocked every
unsupported claim, twice, and two BLOCKs stop the flow. With no fact to cite, the outline could not pass however it was
rewritten, so the whole flow stopped on gaps only a human can close.

## Decision
- The marker is one exact form: `<Can't be verified. Reason: reason sentence here>`. ASCII apostrophe, a required reason
  that starts with a visible character and stays on one line, and no `<`, `>` or `|` (a pipe would split a table row).
  The reason says why the claim could not be verified and what a human would need, never the claim itself.
- The research stage never turns what it cannot find or prove into a fact row. It lists it under Open gaps with the marker.
  It never invents a claim.
- The outline stage puts the marker in a cell in place of a claim no fact supports, keeps the section, and collects every
  marker in an "Open questions for the human" section. Its report lists them with the count.
- The outline gate treats a marker as not a claim, so FACT-1 does not apply to it. A claim beside a marker or inside its
  reason still blocks. A marker not in the exact form is a blocking FACT-1 finding and is not counted. A marker on a point
  the fact bank supports is a FACT-1 finding (cite the fact ID instead). Its verdict gains a fixed line 3, `Markers: <n>`,
  for people only; no parser reads it, as with G1's `Coverage:`. ADR-004's pattern for lines 1 and 2 is unchanged.
- A marker is not a BLOCK, so it never counts toward the two-BLOCK stop, and the human may approve an outline that
  still has markers.
- The research gate is unchanged: a source it cannot open stays a blocking finding, and the fix is to move the claim to Open
  gaps with the marker and drop the row.
- **Nothing unverified reaches publication.** FLOW-6: no final article is labelled publish-ready while a marker remains.
  The draft, edit and final-gate stages are built in Phase 5; they must carry markers through and refuse sign-off while one
  remains. The publication check uses a loose pattern (`<Can.t be verified`, any apostrophe), not the exact form, so a
  marker mangled by a later stage still stops sign-off.
- Precedence: the gate's checklist wins over a workspace constitution that still carries the earlier FLOW-6. Nothing
  reads FLOW-6 before Phase 5.

## Rejected alternatives
| Alternative | Why not |
|-------------|---------|
| Keep blocking unsupported claims | The flow stops on gaps only a human can close, which is what this change removes |
| Let the outline state the claim and flag it | An unverified claim would read as a finding to a reviewer; the marker replaces it |
| Treat any `<…>` text as a marker | A near-variant would be carried forward in a form the publication check cannot find |

## Consequences
- Positive: the flow reaches a human with every open item listed in one place, and unverified claims cannot be published.
- Accepted cost: an outline can be mostly markers and still pass. The `Markers:` count, the stage report and the human's
  approval are the checks. The rendering of `<…>` in a Google Doc review copy is unverified.
- Follow-ups: the Phase 4 `prose-lint` check and the Phase 5 stages (see DESIGN).

## Revisit when
The draft and final stages exist and a marker is seen to reach a signed-off article, or the marker needs another form.

Refined by ADR-010: the draft, edit and final-gate stages carry markers through; the guard refuses a `Signed-off-by:` while one remains.
