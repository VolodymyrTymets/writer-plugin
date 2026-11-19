# FT-20 — implementation plan

No tracker. Branch `feat/ft-20-human-questions-list`, cut from `main`. One draft PR (A4). Spec: `spec.md`.

<!-- A human writes this line to approve. Until it is here, guard-plan-approval blocks writes to code. -->
Approved-by: Volodymyr · 2026-11-19

Pattern followed: the Open gaps section of `templates/research.md` and its shape test (`test_research_template_open_gaps_carries_the_marker`); the advisory FACT-6 wording
added in FT-19 (`skills/check-research/references/checklist.md`) and its pin `test_g1_advises_on_a_dossier_below_the_coverage_floor_and_research_knows_it`. No new pattern, so no new ADR; a one-line note under ADR-021.

## Contract changes
- **research.md:** one more last section, `## Questions for the human`. Additive; an existing `research.md` without it still passes G1 (advisory only).
- **G1 verdict:** a new advisory FACT-6 finding. Lines 1 to 3 unchanged.
- data / generated output: none. No dependency (C2).

## Requirements (ordered, each independently verifiable)

### R1 — the template ends with the section (S)
- files: `templates/research.md` (add the section after `## Open gaps`), `docs/DOMAIN_GLOSSARY.md` (no new term; skip unless the test reads it)
- layer: template, read at run time by the research stage (ADR-005).
- test: `tests/test_templates.py` new case next to line 122: the last `##` heading of the template is `Questions for the human`, it follows `Open gaps`, its comment says no `Q`/`F` ids, and its numbered placeholders start `[OPEN]` and `[RESOLVED]`.
- executed how: pytest on unchanged template (fails), then after the change (passes); then render a research file from the template in a scratch directory and show its last 10 lines.
- risk: other tests read the template's headings. Mitigation: run the full `tests/test_templates.py` first.

### R2 — the research stage writes the list, keeps its marks and points to it (S)
- files: `skills/research/SKILL.md` (Step 3 item 6: one question per marker and per owed decision, plain text, no ids, what would answer it, each marked `[OPEN]`; when `research.md` already exists the earlier lines are kept, and one becomes `[RESOLVED]` only when a fact row now answers it or a reviewer's comment settles a decision, with one plain sentence saying how; Step 6: the report gives the open and resolved counts and names the section, and does not repeat the questions)
- layer: skill text.
- test: `tests/test_skills.py` new case near the FT-19 research case: the flat research text carries the sentences.
- executed how: pytest red then green. A real research run is not run here and goes under "Not verified".
- risk: the actor writes ids anyway. Mitigation: R3.

### R3 — G1 advises when the section is missing, carries an id or a bad mark, or leaves a marker uncovered (S)
- files: `skills/check-research/references/checklist.md` (one paragraph under the FACT-6 coverage paragraph), `skills/check-research/SKILL.md` (an advisory example line)
- layer: gate checklist text; the gate stays read-only and forked.
- test: `tests/test_skills.py`: the checklist carries "Questions for the human" and says advisory; the existing verdict-example regex test still passes with the extra example line; the checklist cites only its own rule IDs (FACT-6).
- executed how: pytest red then green; then run the real gate (forked) once on a scratch research file that lacks the section and show lines 1 to 3 and the new advisory finding.
- risk: a gate that nags on every old dossier. Mitigation: advisory only, one finding.

## Docs to update in this PR
- [ ] docs/features/FT-20/spec.md (acceptance criteria checked off)
- [ ] docs/DESIGN.md: FT-20 row to "fixed" (the FT-21 row stays open)
- [ ] docs/decisions/ADR-021-coverage-floor-advisory.md: one line under Decision 3 pointing to the list
- [ ] CHANGELOG.md (Deleted section first, then Changed). **Upgrading:** none needed; the next research run adds the section.

## Risks
| Risk | Impact | Cheapest way to find out early |
|------|--------|-------------------------------|
| The list repeats the Open gaps and the human reads two lists | confusion stays | R2 says one question per marker and nothing else; the gate checks coverage, not wording |
| A reviewer answers inside the Doc, not in a comment | the answer is lost | out of scope; FT-21 and the research Step 2b |
