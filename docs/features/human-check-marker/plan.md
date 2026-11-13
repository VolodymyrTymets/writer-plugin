# human-check-marker — implementation plan

Found by running the outline stage on a real brief: research could not find or prove some facts, the outline gate
blocked every unsupported claim twice, and FLOW-3 stopped the whole flow. The human's direction: where research cannot
find or prove something, leave a marker for a human and keep going; do not stop the flow. No tracker, so the slug stands
in for a ticket ID. Branch `fix/human-check-marker` off `main` (PR #5 merged).

<!-- A human writes this line to approve. Until it is here, guard-plan-approval blocks writes to code. -->
Approved-by:

Pattern followed: the Open gaps convention in `skills/research/SKILL.md` and the `Not checked` convention in the gate
skills; a new decision is recorded as ADR-008. It reopens no ADR: it applies FACT-1 at G2 to a marker and extends FLOW-6, and it relies on ADR-004's FLOW-3 count staying unchanged (a marker is not a BLOCK).

## Problem
A gate that never passes what it cannot verify is right (goal 1), but turning every unverifiable claim into a BLOCK made
the outline stage unwinnable: no fact existed to cite, so each rerun blocked on the same cells, and two BLOCKs stop the flow.

## The change
1. **The marker.** The exact text `<Need human check/decision>`, optionally with a reason after a colon, for example
   `<Need human check/decision: the vendor's pricing page blocked the fetch>`. One greppable form, no variants. **The reason names only what is needed and where a human could get it, never a claim:** a statistic, date, named claim or quote inside the reason is a blocking FACT-1 finding at G2. The reason cannot contain `|` (a pipe would split a Structure-table row and corrupt the Fact IDs and Words columns).
2. **Research stage.** Whatever the brief needs that it cannot find or prove is not a fact row. It goes under Open gaps
   with the marker, what is needed, and where a human could get it. It never invents or softens a claim.
3. **Outline stage.** Where no fact supports a cell or claim, the cell carries the marker and says what is needed, not the
   claim. The section stays. The marker replaces the claim; a claim written next to a marker is still a claim. The report
   lists every marker and the count, and the outline gets an "Open questions for the human" section (template) that
   collects them.
4. **G2 (outline gate).** A marker is not a claim, so FACT-1 does not apply to it. A claim with no fact ID, or a claim
   sitting beside a marker, still blocks. G2 prints a fixed line 3, `Markers: <n>`, in both of its examples (people only, no parser reads it, as with G1's `Coverage:`), so an outline made mostly of markers is visible. A missing artifact prints `Markers: n/a`. The count is every marker in `outline.md` outside its "Open questions for the human" section (that section only collects them, so counting it would count each twice); the checklist defines it the way G1's checklist defines Coverage, and `test_g2_prints_a_markers_line` asserts that sentence. It adds no finding and does not change line 1's counts.
5. **G1 (research gate).** Unchanged. A row the gate cannot open stays a blocking FACT-2 finding whose fix is to move the
   claim to Open gaps with the marker and drop the row (the fix the research stage already uses). Markers in Open gaps
   already satisfy FACT-6, because an open question may sit under Open gaps.
6. **The flow does not stop on markers.** A marker is not a BLOCK, so it does not count toward FLOW-3. The human may approve
   an outline that still has markers.
7. **Nothing unverified reaches publication.** FLOW-6 gains: no `final` is labelled publish-ready while a
   `<Need human check/decision>` marker remains in `final.md`. The draft, edit and final-gate stages do not exist yet
   (Phase 5); DESIGN and ADR-008 record that they must carry markers through and refuse sign-off while any remain, and
   Phase 4's `prose-lint` can grep for the one form.

## Contract changes
- Skill text (research, outline, check-outline), `templates/outline.md` (one section), `templates/research.md` (one line
  under Open gaps), the constitution's FLOW-6, `docs/DESIGN.md` (the FLOW-6 cell, §Gates, Phase 4 and 5 notes), ADR-008
  (new), glossary row, CHANGELOG. No change to the verdict format, G1, rule IDs or the other checklists.
- FLOW-6's text changes; `test_constitution_defines_every_design_rule_id` reads IDs only, so it is unaffected.

## Requirements

### R1 — Marker, research and outline stages, G2 (M)
- files: `skills/research/SKILL.md`, `skills/outline/SKILL.md`, `skills/check-outline/SKILL.md`,
  `skills/check-outline/references/checklist.md`, `templates/outline.md`, `templates/research.md`, `tests/test_skills.py`,
  `tests/test_templates.py`, `tests/conftest.py`
- tests (red before, green after): a shared `HUMAN_CHECK` regex constant in `tests/conftest.py` (`<Need human check/decision(: [^<>|]+)?>`), imported by both test files, and `test_human_check_marker_regex_accepts_the_template_and_rejects_variants`;
  `test_research_and_outline_stages_use_the_marker` (parametrised, both texts carry the exact form and the words "never
  invents"/"not a fact row" for research, "replaces the claim" for outline); `test_g2_treats_a_marker_as_not_a_claim` (the checklist says FACT-1 does not apply to a marker, that a claim beside a marker or inside its reason still blocks, and that the reason holds no pipe); `test_g2_prints_a_markers_line` (both examples carry `Markers: <n>` on line 3, and `Markers: n/a` for a missing artifact, like the Coverage test); in `tests/test_templates.py`, `test_outline_template_has_an_open_questions_section` and `test_research_template_open_gaps_carries_the_marker` (the research template's Open gaps section holds a string matching `HUMAN_CHECK`).
- The G2 checklist text about markers cites only FACT-1 (its allowed set is unchanged); the FLOW-3 and FLOW-6 explanation goes in `skills/check-outline/SKILL.md`, ADR-008 and DESIGN only.
- The outline template ships the "Open questions for the human" section with `{{… or "none"}}` (the research template's Open gaps uses the same form), and `test_outline_template_has_an_open_questions_section` asserts that wording. In step 2, the section must list exactly the markers G2 counted.
- checks before the runs, real output in the PR: `.venv/bin/python -m pytest` (green) and `claude plugin validate ./`.
- executed how (scratchpad workspaces, each a new directory; each step a separate
  `claude -p "/writer-plugin:<stage> …" --plugin-dir <this checkout> --permission-mode acceptEdits` call):
  1. the user's scenario: copy the real brief's workspace (research G1 PASS, outline stopped at two G2 BLOCKs); in the
     copy move both `G2-outline.r*.md` into `gates/archive/` (the ADR-004 resume step) and rerun the outline stage.
     Expect `G2-outline.r<k+1>` PASS, markers in the cells that lacked facts, the markers listed in the reply, and no
     stop. Report verdict line 1, marker counts and ordering only (client data, PLG-1).
  2. a neutral synthetic brief that asks for a fact no source can give (an invented product's exact price): research puts
     it under Open gaps with the marker and G1 passes; the outline carries the marker in the cell and G2 passes.
    3. negative: in copies of the step-2 outline, (a) write a claim next to a marker (a price beside the marker) and (b)
     put a price inside a marker's reason; run the outline gate on each: expect BLOCK citing FACT-1 in both.
- risk: an actor could mark everything to get a PASS. Mitigation: G2 reports the count, the stage reports every marker,
  FLOW-6 blocks publication, and the human approves the outline.

### R2 — Docs and decision (S)
- files: `rules/core/CLAUDE.template.md` (FLOW-6), `docs/DESIGN.md`, `docs/decisions/ADR-008-human-check-marker.md`,
  `docs/DOMAIN_GLOSSARY.md` (Human-check marker), `CHANGELOG.md`
- test: `test_constitution_flow_6_blocks_publication_while_a_marker_remains` in `tests/test_templates.py`.
- executed how: full pytest and `claude plugin validate ./`.

## Docs to update in this PR
- [ ] ADR-008 · DESIGN.md (FLOW-6 cell, §Gates, Phase 4 and 5 rows) · constitution FLOW-6 · DOMAIN_GLOSSARY.md · CHANGELOG.md

## Risks
| Risk | Impact | Cheapest way to find out early |
|------|--------|-------------------------------|
| An outline of mostly markers passes | a hollow outline | step 1 reports the marker count; the human approves the outline |
| A marker slips into the published article | an unverified or placeholder claim published | FLOW-6 and ADR-008 make sign-off refuse; the draft and final stages and the hook come in Phase 4 and 5 |
| Client data in evidence | PLG-1 | only verdict lines, counts and ordering; grep the PR body, `git diff` and this plan file for the real brief's client and vendor names before committing and before the PR opens |

## Assumptions
- ADR-008 carries a one-line precedence note, as ADR-006 does: the gate's checklist wins over a workspace constitution that still has the old FLOW-6.
- One draft PR; `.serena/` is never committed. Headless runs cannot answer question rounds. Not verified in the PR: the
  draft, edit and final stages and sign-off refusal (not built), a hand edit outside the skill (ADR-007 gap), and the gate's
  run-to-run variance in findings.
