# phase-3-vertical-slice — spec

Build-plan Phase 3 (`docs/DESIGN.md`). No ticket tracker, so the slug stands in for a ticket ID.

## Problem
The plugin has rule IDs and artifact templates (Phase 2) but nothing that runs. A user cannot turn a brief into a
researched, gated outline, and no gate exists to prove that "a gate blocks a wrong fact" works.

## Goal / business value
Ranked goal 2 (ship the vertical slice) in service of goal 1 (correct gates): the first three stages and their gates,
run on a brief, before the draft and edit stages are built on top.

## Scope
- in: skills for the brief, research and outline stages; gate skills G0, G1, G2; agents `gate` and `fact-gate`;
  structure and contract tests; docs.
- **out (explicit):** draft, edit, G3, G4 (Phase 5); the orchestrator (Phase 6); `guard-stage-order`, `prose-lint.py`,
  `verify-final`, `session-context` (Phase 4); Google Doc copies, the sync skill, setup (Phase 7); any client-specific content (PLG-1).

## Acceptance criteria
- [x] AC1 Given the plugin, when `claude plugin validate ./` and the full pytest run, then both pass.
- [x] AC2 Given a brief with no named reader, when the brief gate runs, then it returns BLOCK citing BRF-1 and a fix.
- [x] AC3 Given a complete brief, when the brief stage runs, then `brief.md` matches the template headings and G0 returns PASS.
- [x] AC4 Given a fact bank with a fabricated quote or a dead URL, when the research gate runs, then it opens the source and returns BLOCK citing FACT-3 or FACT-2.
- [x] AC5 Given an outline with a section that has no fact ID for a statistic, when the outline gate runs, then BLOCK citing FACT-1.
- [x] AC6 Given a PASS on the outline, when the outline stage ends, then `Approved-by:` is still empty and the stage tells the human to fill it.
- [x] AC7 Given a second BLOCK on the same artifact, when an actor reaches it, then it stops and hands over (FLOW-3).
- [x] AC9 Given a brief with no research questions, when the brief gate runs, then BLOCK citing BRF-6.
- [x] AC10 Given a brief question that research neither answers nor lists under Open gaps, when the research gate runs, then BLOCK citing FACT-6.
- [x] AC8 Every verdict is saved by the actor to `gates/G<n>-<stage>.r<k>.md`; no gate wrote a file.

## Edge cases
| Case | Expected behaviour | Decided by |
|------|--------------------|-----------|
| Previous gate has no PASS on disk | Actor stops and names the missing verdict (FLOW-1) | DESIGN |
| Source URL definitively gone (404, 410, DNS) | G1 BLOCK, FACT-2 | plan, FACT-2 now says the URL resolves |
| Source blocked, timed out, or web tools absent | Fact under "Not checked"; verdict BLOCK "cannot verify", never PASS | architecture, goal 1 |
| Gate invoked with no slug | Resolves the most recently modified `articles/*/` artifact, names it first | rln-agent analyze pattern |
| Web tools absent in the session | G1 BLOCKs "cannot verify", never PASSes | goal 1 |

## Open questions
| # | Question | My assumed answer | Needs a human? |
|---|----------|-------------------|----------------|
| 1 | Is there a real brief to run the slice on? | No. Verify on synthetic neutral briefs (scratchpad); Phase 4 does not start until a real one runs | yes, before Phase 4 |
| 2 | Can skill text reference `${CLAUDE_PLUGIN_ROOT}/templates/`? | Unknown; R1 verifies in the docs (D4). If not, templates are copied under each actor's `references/` with a drift test | no |
| 3 | Do actors publish a Doc copy now? | No. The publish skill is Phase 7; actors end with "Doc copy: not yet available" | no |
