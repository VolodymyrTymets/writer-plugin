# FT-15 — implementation plan

No tracker. Branch `feat/ft-15-publish-on-stop`, cut from `main`. One draft PR (A4). Spec: `spec.md`.

<!-- A human writes this line to approve. -->
Approved-by: Volodymyr · 2026-11-19

Pattern followed: the Step 6 sentence in each actor skill, and `test_actor_makes_its_doc_copy_through_the_copy_skill_after_a_pass`. A refinement of ADR-012.7, so ADR-020, no new pattern.

## Requirements
### R1 — actors make a copy on the second BLOCK (S)
- files: `skills/{brief,research,outline,draft,edit}/SKILL.md`, `skills/publish/SKILL.md` (description), `skills/article/SKILL.md` (`stopped` row), `tests/test_skills.py`
- test: two new cases; shown failing on the unchanged skills (6 failed), then passing (6 passed).
- not verified here: an end-to-end run on a real article that gets two BLOCKs (needs a live Drive session).

## Docs to update
- [x] ADR-020, spec, this plan
- [x] `docs/DESIGN.md` FT-15 row, `CHANGELOG.md`, ADR-012 "Refined by"
