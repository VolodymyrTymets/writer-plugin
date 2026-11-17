# FT-8-10 — implementation plan

No tracker. Branch `fix/ft-8-10`, cut from `main`. One draft PR (A4). Spec: `spec.md`.

<!-- A human writes this line to approve. Until it is here, guard-plan-approval blocks writes to code. -->
Approved-by: Volodymyr - 2026-11-17

Pattern followed: FT-4 and FT-7 fixes (`docs/DESIGN.md` FT-4, `bin/prose-lint.py` + `tests/test_prose_lint.py`) for the lint check;
the marker contract in `skills/outline/SKILL.md` and `skills/check-outline/references/checklist.md` (ADR-008) for FT-10; skill text pinned by
`tests/test_skills.py` for the rest. No precedent is missing, but the marker-count rule changes ADR-008's outline decision, so it gets an ADR.

## Contract changes
- **rule ID (additive):** `SEO-6` (the final's `slug:` is lowercase kebab-case and is not the folder name's job). Constitution template, DESIGN table, G4 checklist.
- **gate rule (tightened):** G2 blocks markers in the outline above the Open-gaps markers in the research (refines ADR-008). Needs `ADR-017`.
- **front matter:** `slug:` meaning changes from "the article's slug" to "the SEO slug". Format of the file is unchanged; existing finals are not migrated.
- **brief source:** `brief.source.md` of a PDF starts with `<!-- extracted from <file name> by the Read tool -->`.
- generated output: none. No new dependency (C2).

## Requirements (ordered, each independently verifiable)

### R1 — FT-8: read a PDF brief without a shell (S)
- files: `skills/intake-brief/SKILL.md` (Step 1), `tests/test_skills.py`
- layer: skill text; `allowed-tools` stays without Bash.
- test: the skill names `.pdf`, `pages`, the origin comment line and the no-text-layer stop; frontmatter `allowed-tools` has no `Bash`.
- executed how: in a scratch workspace outside this repo (headless runs disallow `mcp__claude_ai_Google_Drive__*` and `mcp__claude_ai_Google_Docs__*`, ADR-016.10), run `writer-plugin:brief` on: a small synthetic text PDF; a 25-page one; an image-only PDF (expected: the stage stops and asks for text, no `brief.source.md` written); and a different PDF over an existing `brief.source.md` (expected: `brief.source.prev.md` backup). Report each result. If Read cannot take a PDF there, stop and report (D4, B4).
- risk: long PDFs; the cheapest check is the 25-page run.

### R2 — FT-9: folder slug and SEO slug (M)
- files: `skills/intake-brief/SKILL.md` (Step 1 slug line), `skills/edit-final/SKILL.md` (front matter, line ~58), `bin/prose-lint.py` (front-matter `slug:` check), `skills/check-final/references/checklist.md`, `rules/core/CLAUDE.template.md`, `docs/DESIGN.md` rule table, `tests/test_prose_lint.py`, `tests/test_skills.py`, `tests/test_templates.py` if it lists rule IDs
- layer: script plus skill text; the lint is the mechanism, the skill is the request.
- test: `tests/test_skills.py` pins in `intake-brief` the kebab pattern, "the change is named in the report" and "an existing folder is never renamed"; `SEO-6` is added on purpose to the `check-final` allow-lists (`GATES`, the set at line 55, and the checklist's "Rule IDs allowed" line), an intended widening, not a narrowed test. Lint cases: `slug: Acme-Review` (SEO-6), `slug: two words`, `slug: ok-slug` (none), no `slug:` line (existing behaviour kept); skill text pins "never copied from the folder name".
- executed how: run `prose-lint.py` on the eval fixture final (`evals/fixtures/http-caching/`) as is, then with its slug changed in a scratch copy; report both outputs. Headless `writer-plugin:brief` runs in scratch workspaces: slug `Acme Review` (expected folder `articles/acme-review/`, change named in the report), and a workspace that already has `articles/Acme Review/` (expected: not renamed). Rerun the three `brief-actor-*` eval cases. The checklist change reruns G4's cases (ADR-013.5): `claude plugin eval` on `g4-pass`, `g4-block-long-title`, `g4-block-misquote`; report each score and cost, and any score below 1.0 as it is, without retrying.
- risk: the fixture and eval cases may carry a slug the new check flags; run `.venv/bin/python -m pytest tests/test_evals.py` before and after.

### R3 — FT-10: one marker per gap (M)
- files: `skills/outline/SKILL.md` (marker bullet, lines 53-60: also rewrite the ADR-008 sentence "a statement about a vendor, a price, a plan or a page that has no fact ID is a marker": a claim with no fact ID and no Open-gaps entry is dropped, not marked), `skills/check-outline/references/checklist.md` and `SKILL.md` (count rule, `Markers:` line), `templates/outline.md` (hint under "Open questions"), `docs/decisions/ADR-017-one-marker-per-gap.md` (states the change to ADR-008's outline decision; ADR-008 gains "Refined by ADR-017"; `skills/check-outline/SKILL.md:63` is reworded, since an excess marker now blocks), `tests/test_skills.py` (pins the rewritten sentence), two new eval cases under `evals/`
- layer: skill text and gate checklist; no script (gates run none, ADR-010.3).
- test: the outline skill says a gap gets one marker, in one row, other rows drop the point; the checklist names the count and FACT-1; `Markers:` still line 3.
- executed how: add and run by `claude plugin eval`: a BLOCK case where one gap fans out (2 gaps, 5 markers), a BLOCK case where the extra marker is a non-gap claim, and a PASS case (2 and 2). Also rerun `g2-pass` and `g2-block-claim-without-id` (ADR-013.5). Report each score and cost; a seeded `research.md` needs its own `.quote-check.json` (`tests/test_evals.py`).
- risk: a gap that spans two claims; handled by research recording two gaps (spec edge case), with no change to the research skill (marker policy is out of scope). A gap that needs two facts may make G2 block, which costs one FLOW-3 strike; accepted.

### R4 — Docs and changelog (S)
- files: `docs/DESIGN.md` (FT-8, FT-9, FT-10 status "fixed: …"; rule table), `docs/DOMAIN_GLOSSARY.md` (SEO slug), `docs/ARCHITECTURE.md` only if layout changes (it does not), `CHANGELOG.md` (Deleted first), with an **Upgrading:** line (re-run `writer-plugin:setup` for SEO-6; no version bump, `CHANGELOG` stays under Unreleased).
- test: `.venv/bin/python -m pytest` whole suite; `claude plugin validate ./`.

## Risks
1. Read on a PDF inside a skill may not behave as in the main session; R1's sample run is the cheapest experiment, run first.
2. G2's count rule could block a legitimate outline and cost one of two FLOW-3 strikes; mitigated by the research-gap split and by the R3 PASS eval case.
3. SEO-6 flags old finals with a capitalised folder slug; accepted, one lint line, fixed on the next edit run.

## Out of scope
Guard or status rejecting non-kebab folders; OCR or external converters; marker-form or FLOW-6 changes; migrating existing articles.

## Docs (E1)
DESIGN (rule table, FT rows), glossary (SEO slug), ADR-017, CHANGELOG. Estimate: R1 S, R2 M, R3 M, R4 S.
