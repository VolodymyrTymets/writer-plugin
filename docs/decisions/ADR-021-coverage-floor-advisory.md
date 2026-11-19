# ADR-021 — The coverage floor is an advisory finding, not a BLOCK

- **Date:** 2026-11-19
- **Status:** accepted
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (`docs/features/FT-19/plan.md`, finding FT-19)
- **Supersedes:** ADR-014.

## Context
ADR-014 made G1 block a dossier that answers fewer than half of the brief's questions, after a run that passed with 1 of 10 answered and carried 29 to 31
markers into the final. On drifity, 4 of 12 questions were answered and the rest need a human (sources behind a 403, hands-on tests). Two BLOCKs stopped the
article (FLOW-3), so nothing reached the draft or the final, although the human wanted the gaps carried forward as markers and filled later.

## Decision
1. G1 reports the floor (`answered x 2 < m`, same counting rule) as an **advisory** FACT-6 finding that names the numbers and the open questions. It never blocks.
2. The open questions stay under Open gaps as one marker each (ADR-008, ADR-017) and travel to the outline, draft and final. The final cannot be signed off while
   a marker remains (FLOW-6), so a thin article cannot be published by accident.
3. The human sees the floor when approving the research (FLOW-2). The questions are the last section of `research.md`, each marked `[OPEN]` or `[RESOLVED]`, with no Q or F ids (FT-20). The research stage reports each open question with what would answer it, and no longer stops before the gate (the FT-17 stop is removed).
4. A question that is neither answered nor under Open gaps is still a blocking FACT-6 finding.

## Rejected
| Alternative | Why not |
|-------------|---------|
| A typed waiver the human must write (`Waived-by:`) | A new line, hook rule and state, for a checkpoint the research approval already is |
| A floor value in `style.md` | Still blocks below the value; the problem is the block, not the number |
| Keep the BLOCK and ask for more sources | Cannot work for questions that need hands-on tests or pages an agent cannot fetch |

## Consequences
- A thin dossier now passes G1. The cost is the FT-2 outcome: an article with many markers that waits for a human. The advisory and the research approval are the only guards.
- A workspace `CLAUDE.md` made before this change still says "at least half are answered"; the gate reads its own checklist, so it is not affected, but the text disagrees until the workspace re-runs `writer-plugin:setup`.

## Revisit when
Articles repeatedly reach the final with most claims as markers and are never signed off.
