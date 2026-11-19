# ADR-020 — A stage that stops on its second BLOCK still makes one review copy

- **Date:** 2026-11-19
- **Status:** accepted
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (`docs/features/FT-15/plan.md`, finding FT-15)
- **Relation:** refines ADR-012 decision 7 ("actors make their copy after a PASS").

## Context
In the drifity field test the research stage got two G1 BLOCKs and stopped (FLOW-3). No Doc existed for it, because the actors
make their copy only on a PASS. The human wanted to resolve the blockers in a Doc, with reviewers commenting on them.

## Decision
1. Each actor (brief, research, outline, draft, edit) invokes `writer-plugin:publish <slug> <stage>` once after its second BLOCK, then stops
   as before. Nothing else changes: the script already titles a stage with no current PASS `· ungated` (ADR-012.1), so the Doc says it is blocked.
2. A Doc is still never approval. FLOW-1 and FLOW-2 for the next stage need a PASS on the artifact, so a name typed in an ungated Doc cannot open the next stage.
3. The stage runs again only after a human archives its verdicts (FLOW-3 is unchanged). Comments synced from the ungated Doc are read by the rerun like any others (ADR-016).

## Rejected
| Alternative | Why not |
|-------------|---------|
| A copy after every BLOCK | A first BLOCK is fixed by the actor itself; a Doc per attempt is noise and a new revision each time |
| Let the sync skill resume a stopped stage | It would bypass the human decision FLOW-3 exists for |
| Make ungated Docs not approvable in the hook | More code for a case FLOW-1 and FLOW-2 already stop downstream; revisit if a name typed in an ungated Doc causes confusion |

## Consequences
- A blocked article has a Doc to review. The first rerun after archiving still needs a human.
- A stage that finds its article already stopped (FLOW-3 in Step 2, on a later run) makes the same copy before it stops (FT-16). The copy skill skips a copy that is already recorded, so a rerun reports its URL instead of making a second Doc. The first version of this ADR covered only the stop inside the run, so an article stopped before it had no Doc.

## Revisit when
A first-BLOCK review is wanted, or an approval typed in an ungated Doc is carried into a blocked artifact in practice.
