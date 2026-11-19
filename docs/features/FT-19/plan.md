# FT-19 — implementation plan

No tracker. Branch `feat/ft-19-coverage-floor-advisory`, cut from `main`. One draft PR (A4). Spec: `spec.md`.

<!-- A human writes this line to approve. Until it is here, guard-plan-approval blocks writes to code. -->
Approved-by: Volodymyr · 2026-11-19

Pattern followed: ADR-014's own change (the checklist paragraph, the gate skill's example, the research skill sentence, `test_g1_blocks_a_dossier_below_the_coverage_floor_and_research_knows_it`).
A reversal of ADR-014, so a new ADR-021 that supersedes it.

## Contract changes
- **G1 verdict:** the coverage-floor finding moves from "Blocking" to "Advisory". The `Coverage:` line 3 is unchanged. A verdict with 0 blocking and the floor advisory is a PASS.
- data / generated output: none. No dependency (C2).

## Requirements
### R1 — G1 treats the floor as advisory (M)
- files: `skills/check-research/references/checklist.md` (paragraph at line 59), `skills/check-research/SKILL.md` (the BLOCK example at line 63 becomes a PASS example with the advisory),
  `rules/core/CLAUDE.template.md` (FACT-6, line 30), `docs/DESIGN.md` (FACT-6 row, FT-2 row stays as history)
- test: `tests/test_skills.py` line 222: rename to `test_g1_reports_a_dossier_below_the_coverage_floor_as_advisory_and_research_knows_it` and pin the advisory wording; the verdict-regex test over the gate examples must still pass with the new PASS example.
- executed how: run the changed pytest first on unchanged code to show the pin fails, then after the change; then run the real gate once on the drifity dossier copy and show its first three lines.
- risk: a PASS on a thin dossier. Mitigation: the advisory names the numbers, and research still needs a human `Approved-by:` (FLOW-2).

### R2 — the research stage reports instead of stopping (S)
- files: `skills/research/SKILL.md` (remove Step 3b; line 69 says the gate advises when fewer than half are answered; the Step 6 report lists open questions with what would answer each), `tests/test_skills.py` (line 996 test is replaced by one pinning the report sentence and the absence of "do not run the gate")
- executed how: pytest; a research run on a scratch article is not run here and goes under "Not verified".
- risk: low, skill text.

## Docs to update in this PR
- [ ] docs/features/FT-19/spec.md (acceptance criteria checked off)
- [ ] docs/decisions/ADR-021-coverage-floor-advisory.md (new; ADR-014 gets "Superseded by ADR-021")
- [ ] docs/DESIGN.md: FT-19 row, FACT-6 wording
- [ ] CHANGELOG.md; **Upgrading:** re-run `writer-plugin:setup` or edit FACT-6 in the workspace `CLAUDE.md` (the workspace copy says "at least half are answered")

## Risks
| Risk | Impact | Cheapest way to find out early |
|------|--------|-------------------------------|
| Articles reach the final with many markers and are never signed off | wasted draft work (the FT-2 finding) | the advisory at research approval; revisit if it recurs |
| The workspace constitution still says the old rule | G1 and CLAUDE.md disagree | the Upgrading note; the gate reads its own checklist, not the workspace file |
