# phase-2-templates — implementation plan

Build-plan Phase 2 (`docs/DESIGN.md`): the editorial constitution template and the four artifact templates. No ticket
tracker, so the slug stands in for a ticket ID.

<!-- A human writes this line to approve. Until it is here, guard-plan-approval blocks writes to code. -->
Approved-by: Volodymyr Tymets, in session 2026-11-12 (plan, gate fixes, deletion of the root design copy)

Pattern followed: `../rln-agent/rules/core/CLAUDE.template.md` (same placeholder style, lettered rule groups, under 200
lines, pointer section); templates are plain Markdown with `{{PLACEHOLDER}}` fields, as in `../rln-agent/templates/`.

## Goal
Ranked goal 1 (correct gates): gates can only cite rules that exist and read artifacts whose shape is fixed. Phase 3
skills cannot be written until the rule IDs and the artifact shapes are on disk.

## Scope
- in: `rules/core/CLAUDE.template.md`; `templates/{brief,research,outline,style}.md`; one new test file; docs.
- **out:** any skill, agent or hook (Phase 3+); `draft.md` / `final.md` templates (not in the Phase 2 scope line;
  their shape is defined by the actors in Phase 5); the setup skill that copies these (Phase 7); client-specific
  content (PLG-1).

## Contract changes
- boundary: none loaded by Claude Code. `rules/` and `templates/` are an inert library.
- data: this fixes the on-disk shape of `brief.md`, `research.md`, `outline.md` (headings, fact-bank columns,
  `Approved-by:` line). Phase 3 gates and Phase 4 hooks will parse these, so later changes are breaking for them.
- **approval contract (FLOW-2):** an outline is approved only when `Approved-by:` is followed by a non-empty value. The
  template ships the line empty. A guard that checks the line exists would pass every unapproved outline. The rule is
  written into `docs/DESIGN.md` next to FLOW-2 in this PR, for `guard-stage-order` (Phase 4) to implement.
- SEO-2 (title ≤ 60) and SEO-3 (meta 120–155) stay fixed. The style template does not expose them.
- generated output: none.
- structure test side effect: once `rules/core/CLAUDE.template.md` exists, `test_cited_rule_ids_are_defined` takes
  defined IDs from it instead of `DESIGN.md`. It therefore has to define every ID in the DESIGN table, or any later
  citation fails.

## Requirements (ordered, each independently verifiable)

### R1 — Editorial constitution template (M)
- files: `rules/core/CLAUDE.template.md` (new)
- content: placeholders `{{PROJECT_NAME}}`, `{{STYLE_GUIDE_PATH}}`; command-free (a workspace has no build); rule
  groups BRF, FACT, STR, VOI, SEO, FLOW exactly as the DESIGN table, with a one-line gate-facing statement each;
  workspace hygiene (never edit gates/ verdicts by hand, secrets, no client data in the plugin); where-things-live
  pointers; a marker line for client-specific rules. PLG-1 is kept as a short "this plugin" note so the ID stays defined.
- test: `tests/test_templates.py::test_constitution_defines_every_design_rule_id` — reads the rule table in
  `docs/DESIGN.md` and asserts every ID found there appears in the template (no hardcoded list, so the two cannot
  drift); file under 200 lines.
- FLOW-2 wording: the constitution's FLOW-2 line carries the same words as the changed DESIGN cell (R6): "no draft
  unless `Approved-by:` in the outline has a non-empty value".
- executed how: run the test, run the existing `test_cited_rule_ids_are_defined` with the template present, then copy
  the template to the scratchpad, fill `{{PROJECT_NAME}}` and `{{STYLE_GUIDE_PATH}}`, and confirm no `{{` is left and
  it is under 200 lines.
- risk: low.

### R2 — Brief template (S)
- files: `templates/brief.md` (new)
- content: one section per BRF rule: reader (BRF-1), goal and single CTA (BRF-2), primary keyword and search intent
  (BRF-3), length and format (BRF-4), must-include and must-avoid (BRF-5); plus questions the research must answer.
- test: `test_templates.py::test_brief_has_a_section_per_brf_rule`.
- executed how: fill a sample brief in the scratchpad from the template and parse it with the test's helper.
- risk: none.

### R3 — Research dossier template (M)
- files: `templates/research.md` (new)
- content: questions, sources, **fact bank** table with the glossary columns `F# | claim | source URL | publisher |
  published | accessed | verbatim quote`, competitor coverage, the gap this article fills, open gaps.
- test: `test_templates.py::test_research_fact_bank_columns_match_glossary` — header columns equal the glossary row.
- executed how: parse a filled sample's fact-bank rows; confirm every row has all seven columns.
- risk: the column set is parsed by G1 and the prose-lint script later. Mitigation: the test reads the glossary, so
  the two cannot drift.

### R4 — Outline template (M)
- files: `templates/outline.md` (new)
- content: an **empty** `Approved-by:` line; a comment above it says a human fills it, that non-empty means approved,
  and that FLOW-2 and `guard-stage-order` (Phase 4) read it,
  thesis, title options, intro hook, H2/H3 table with purpose, key points, fact IDs, word budget (STR-3: sum is
  checked against the brief), keyword map (SEO-1), CTA (STR-5).
- test: `test_templates.py::test_outline_has_empty_approval_line_and_budget_column` — the line exists **and its value
  is empty** (a shipped template must never be pre-approved); the budget column exists.
- executed how: filled sample; sum the budget column and compare to the sample brief's target.
- risk: none.

### R5 — Style guide template (S)
- files: `templates/style.md` (new)
- content: the placeholders a client fills: voice (VOI-1), banned phrases (VOI-2), AI tells to flag (VOI-3), reading
  level (VOI-4), statistic age limit in months (FACT-4), internal link list (SEO-5), audience. Title and meta limits
  are not here: SEO-2/3 are fixed rules. All values are `{{...}}` placeholders; no real client text.
- test: `test_templates.py::test_style_template_has_no_filled_client_values` — a value line is a bullet `- **Label:** value`; every one must start with `{{`.
- executed how: as above; plus grep the tree for anything that reads as a client name.
- risk: PLG-1 slip. The test and my own grep cover it.

### R6 — Docs (S)
- files: `docs/DESIGN.md` (Phase 2 status `done`; the FLOW-2 table cell itself reads "no draft unless `Approved-by:` in the outline has a non-empty value", not a side note), `docs/ARCHITECTURE.md` (the
  `rules/core/, templates/` row no longer "not built yet"; the `tests/` row lists `test_templates.py`),
  `CHANGELOG.md` (an `Unreleased` section: Deleted "Nothing yet", Added the library). No version bump, so
  `.claude-plugin/plugin.json` is not touched.
- test: `test_every_documented_command_exists` stays green. Templates must not put planned commands in code spans.
- executed how: full pytest and `claude plugin validate ./`.

## Docs to update in this PR
- [ ] docs/DESIGN.md — Phase 2 status
- [ ] docs/ARCHITECTURE.md — `rules/` and `templates/` row
- [ ] docs/DOMAIN_GLOSSARY.md — only if a new term appears (none expected)
- [ ] no ADR: no new pattern

## Risks
| Risk | Impact | Cheapest way to find out early |
|------|--------|-------------------------------|
| Template shape later needs to change after Phase 3 gates parse it | rework in gates | keep headings minimal and stable; Phase 3 runs on a real brief before going further |
| Planned commands named in a template fail the doc-command test | red test | write "the brief stage", not the slash command; run pytest after each file |
| New `tests/test_templates.py` stricter than needed | brittle | assert shape (headings, columns), never wording |

## Assumptions
- `writer-plugin-design.md` at the repo root is an untracked, newer copy of `docs/DESIGN.md`. It fails the existing
  `test_every_documented_command_exists` (39 hits, run by the gate), because the test scans every `.md` in the tree.
  **A human moves it out of the repo before R1** (deleting or moving a file is C4). I do not weaken the test. The Phase 2
  status is set only in `docs/DESIGN.md`.
- `draft.md` and `final.md` templates are out of scope (not in the Phase 2 line).
- `tests/test_templates.py` is a new file; `tests/test_structure.py` stays untouched. A new check ships with a test
  (CLAUDE.md: "A hook change needs a test case"; same spirit for the library).
- Ships as a single draft PR (A4), branch `feat/phase-2-templates`. Files are staged by explicit path. This plan ships
  in the PR (it is the record of the approval). `.serena/` is never committed; ignoring it is a separate chore.
- The PR's "Not verified" lists: placeholder filling by the setup skill (Phase 7), and parsing of these templates by the
  G0–G2 gates and `guard-stage-order` (Phases 3–4). Phase 2 only checks shape with tests and a sample fill.
