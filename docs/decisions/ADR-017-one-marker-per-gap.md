# ADR-017 — The outline holds one marker per open gap, and a claim with no fact and no gap is dropped

- **Date:** 2026-11-17
- **Status:** accepted
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (`docs/features/FT-8-10/plan.md`, finding FT-10)
- **Relation:** refines ADR-008's outline decision. The two-BLOCK rule (FLOW-3, ADR-004) is unchanged.

## Context
A field test carried 6 markers out of research and 29 into the outline: the outline stage put a marker in every cell whose
claim lacked a fact, and ADR-008 told it that a statement with no fact ID "is a marker, even if `research.md` mentions it in
prose". One missing fact then needed many manual fills, and a marker stood for claims research never listed as gaps.

## Decision
- A marker is only for a point that `research.md` lists under Open gaps.
- One open gap gets at most one marker, in the one row that would carry the claim. Other rows that depend on it drop the point.
- A claim with no fact ID and no open gap is dropped from the outline. This replaces ADR-008's sentence that it is a marker.
- G2 counts the exact-form markers in the outline's cells against the exact-form markers under Open gaps. More in the outline is
  one blocking FACT-1 finding. A marker within the count is still not a BLOCK (ADR-008).
- Research is unchanged. A gap that needs two facts may therefore make G2 block; that costs one FLOW-3 strike and is accepted.

## Rejected alternatives
| Alternative | Why not |
|-------------|---------|
| Leave it to the outline skill's wording | A prompt is a request; the count is checkable, so the gate checks it (goal 1) |
| A script that counts markers | No gate runs a script (ADR-010.3), and the gate can count two lists |
| Give gaps IDs and tie each marker to one | A new format in research and every template for a count that already catches the defect |

## Consequences
- Positive: sign-off needs one fill per gap; markers always trace to a listed gap.
- Accepted cost: an outline that honestly needs a second marker for one gap is blocked until research splits the gap.

## Revisit when
A gap is seen to need two markers often, or a G2 BLOCK on this rule is seen to be wrong.
