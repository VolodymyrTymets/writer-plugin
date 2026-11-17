# FT-13 — implementation plan

No tracker. Branch `fix/ft-13`, cut from `main`. One draft PR (A4). Spec: `spec.md`.

<!-- A human writes this line to approve. Until it is here, guard-plan-approval blocks writes to code. -->
Approved-by: Volodymyr · 2026-11-17

Pattern followed: `check_gates` in `bin/guard-stage-order.py` (the line-1 check beside it) with its `w.block(rule, why, fix)` messages, and
`tests/test_hooks.py` `test_a_bad_new_verdict_is_blocked` (parametrised reject cases); skill sentences pinned in `tests/test_skills.py`
as in FT-8-10. A refinement of ADR-004, so a new ADR (ADR-019), no new pattern.

## Contract changes
- **verdict file:** additive restriction: a saved verdict's line 2 starts `Artifact: ` and, for G1 to G4, line 3 starts with the gate's label.
  Gates already print this (their skills say so), so no gate output changes. Verdicts already on disk are not re-checked.
- data / generated output: none. No dependency (C2).

## Requirements (ordered, each independently verifiable)

### R1 — the guard checks lines 2 and 3 (M)
- files: `bin/lib/writer.py` (change: `VERDICT_LINE3 = {'research': 'Coverage:', 'outline': 'Markers:', 'draft': 'Outline:', 'final': 'Markers:'}`
  and `verdict_header_problem(stage, content)` returning None or a message), `bin/guard-stage-order.py` (change: call it in `check_gates` right
  after the line-1 check, `w.block('FLOW-4', ...)`)
- layer: hook plus shared library, stdlib only.
- test: `tests/test_hooks.py` (change: every verdict save that goes through the guard, blocking cases included, gets the full header inside its helper:
  `g1_save` (line 1435) `Coverage: ...` or `Coverage: n/a`, `g4_save` (line 559) `Markers: ...`, the inline G2 and G3 saves (lines 593, 1486) `Markers:` and
  `Outline:`, the two-line `Artifact: none` allow case, and `test_the_next_number_continues_past_the_archive` (line 252, a one-line G0 save expecting exit 0). The five record-check block tests (`..._blocked_when_research_changed_after_the_check`,
  `test_a_corrupt_quote_record_blocks_the_g1_save`, `test_a_g1_block_is_also_saved_only_against_a_record`, `test_a_pass_that_claims_no_artifact_cannot_skip_the_record_either` (line 1505),
  `..._claims_no_artifact_cannot_skip_the_record_while_research_exists`, `..._g4_verdict_is_blocked_when_final_changed_after_the_lint`) also assert their
  own stderr text (`quote-check` or `prose-lint`), so a header block cannot stand in for them; new parametrised rejects, each
  also asserting stderr names `line 2`, or `line 3` plus the wanted label: blank line 2, `leading-space-line-2`, `bom-line-2` (`\ufeffArtifact: x`), `empty-artifact-value`, blank line 3,
  wrong label, two-line G1; allows: G0 with free line 3, CRLF). `tests/test_skills.py` (new, next to line 66
  `test_verdict_regex_accepts_each_gates_own_examples_and_only_those`): `w.verdict_header_problem(stage, example)` is None for every literal PASS and
  BLOCK example in the five `skills/check-*/SKILL.md`, plus one constructed `Artifact: none` BLOCK per gate (line 3 `Coverage: n/a`, `Markers: n/a`,
  `Outline: n/a`; none for G0), since the skills describe those in prose only.
- executed how: write the new reject cases first and run them on unchanged code to show they fail (the guard exits 0); then the change, then the same
  run passing; both outputs go in the PR. Then pipe a real Write payload for each case into `bin/guard-stage-order.py` in a scratch workspace outside the repo and show exit codes
  and the stderr text; the pytest case above runs the gates' literal examples on every run.
- risk: an over-strict check blocks a legitimate verdict. Mitigation: the label prefix only, not the values; the examples test fails on any later gate-skill edit that breaks it.

### R2 — actors save the header as printed (S)
- files: `skills/brief/SKILL.md`, `skills/research/SKILL.md`, `skills/outline/SKILL.md`, `skills/draft/SKILL.md`, `skills/edit/SKILL.md`
  (change: the "Save the verdict unchanged" step adds: lines 1 to 3 exactly as printed, no blank line before them; the guard refuses otherwise; the actor checks lines 2 and 3 as it checks line 1, and when they do not match saves nothing, tells the user what came back, stops, and never edits them, as ADR-004 says for line 1),
  `tests/test_skills.py` (change: pin the sentence in all five)
- layer: skill text.
- test: `tests/test_skills.py` new case: each actor's flat text contains the sentence.
- executed how: `.venv/bin/python -m pytest tests/test_skills.py`; then `claude plugin eval` on `evals/brief-actor-http-caching` (ADR-013), reporting lines 1 and 2
  of the saved `G0-brief.r1.md`. If the eval session does not load the guard or lacks Write, say so. A G1 to G4 actor saving line 3 is never run end to end here
  unless a real research-stage run in a scratch workspace fits; otherwise it goes under "Not verified".
- risk: G0 has no line 3, so no existing eval covers the field failure; the cost of the eval is unmeasured.

## Docs to update in this PR
- [ ] docs/features/FT-13/spec.md (acceptance criteria checked off)
- [ ] docs/DESIGN.md: FT-13 row to "fixed", and the `guard-stage-order` row (FLOW-4: lines 2 and 3 of a verdict)
- [ ] docs/decisions/ADR-019-verdict-header-lines.md (new; extends ADR-004's line-1 rule to lines 2 and 3: no match, nothing saved, user told, stage stops; ADR-004 gets a "Refined by ADR-019" line)
- [ ] CHANGELOG.md (Deleted section first, then the entry under Changed, where this repo lists fixes)
- [ ] docs/ARCHITECTURE.md:30 (Gate verdict row) and docs/DOMAIN_GLOSSARY.md:15 (Verdict file): "line 1 fixed" becomes "lines 1 to 3 fixed (ADR-004, ADR-019)"; no new term

## Risks
| Risk | Impact | Cheapest way to find out early |
|------|--------|-------------------------------|
| A gate prints a header the check refuses | every save of that gate blocks | the pytest case on the literal examples of all five gate skills |
| Existing tests save one-line verdicts | red suite | update them with a full header, never loosen the check (B3) |
| Header blocks stand in for the record-check blocks in existing tests, which still pass for the wrong reason | the quote and lint record checks lose coverage | give the helpers a full header and assert each test's own stderr (R1) |
| An actor loops on the new block | wasted turns | the message states the exact fix; the R2 sentence prevents the first error |

## Assumptions
- Line 3 of G0 stays free: `check-brief` defines only lines 1 and 2.
- Only the label of line 3 is mechanical; its counts stay for people.
- ADR numbering continues at 019.
