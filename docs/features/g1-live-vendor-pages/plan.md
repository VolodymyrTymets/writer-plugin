# g1-live-vendor-pages — implementation plan

Follow-up to PR #3 (phase 3 slice), found by running the research stage on a real brief. No tracker, so the slug stands
in for a ticket ID. Stacked on `feat/phase-3-vertical-slice`; its PR targets that branch until PR #3 merges.

<!-- A human writes this line to approve. Until it is here, guard-plan-approval blocks writes to code. -->
Approved-by: Volodymyr Tymets, in session 2026-11-12 ("yes, go with B and do all three")

Pattern followed: `skills/check-research/` and its checklist from PR #3 (same gate shape); the rule-change path is
`docs/decisions/ADR-004` (a decision that other phases depend on gets an ADR).

## Problem
The real brief says to take prices and features from each vendor's own live pages. FACT-2 requires a published date,
and those pages show none, so the research stage dropped them and fell back on competitor articles. G1 also passed
Questions-table rows whose fact IDs exist but answer a different question, and a PASS gives no sign of how many brief
questions are actually answered.

## Contract changes
- **FACT-2 (relaxed, human-approved option B):** a fact needs a source URL that resolves, a publisher and an accessed
  date; a published date too, except that a **first-party vendor page** (the vendor's own pricing, feature, help or docs
  page, used for a claim about that same vendor) **that shows no published or updated date** may carry
  `n/a (live page)` in the published column. If the page shows a date, it is used and `n/a` is blocking. Articles,
  third-party statistics, regulator pages and a vendor's page used for a claim about another vendor still need a real
  date. "Statistics" here means third-party statistical sources; a vendor's own figures about itself (prices, plan limits)
  may be `n/a`. An `n/a` row's claim says "as listed on the page", which is **not** "dated" for FACT-4: only an explicit
  "as of <date>" in the claim exempts a row. **FACT-4** judges an `n/a` row by its accessed date, and any later statement
  of it says "checked <month year>"; that duty is written into the FACT-4 text of the constitution and the DESIGN rule
  table, where the draft stage will read it. Changed in the constitution template, `docs/DESIGN.md`, the G1 checklist,
  the research stage and both published columns of the research template; recorded in ADR-006.
- **FACT-6 checklist (stricter):** a listed fact ID that exists but does not support its question is blocking.
- **Verdict body (additive):** G1 prints `Coverage: <a> answered, <o> open (of <m>)` on line 3, counted mechanically from
  `research.md`: a question is **answered** if its Questions-table row lists at least one fact ID that supports it and no
  Open gaps entry names it; otherwise it is **open**. There is no "partial". With `Artifact: none` the line is
  `Coverage: n/a`. Line 3 is for people; no parser reads it (ADR-006 says so). Lines 1 and 2 and the ADR-004 pattern are untouched.
- No new rule IDs, so `test_cited_rule_ids_are_defined` and the DESIGN table check keep working.

## Requirements (ordered, each independently verifiable)

### R1 — FACT-6 mismatch is blocking (S)
- files: `skills/check-research/references/checklist.md`
- test: `tests/test_skills.py::test_g1_checklist_blocks_ids_that_do_not_support_their_question` — the FACT-6 text says
  an ID that "does not support" its question is blocking.
- executed how: take the real dossier's Questions table (Q2 lists F10, F11), run G1 on a copy: expect BLOCK citing FACT-6.
- risk: none.

### R2 — Live first-party vendor pages (M)
- files: `rules/core/CLAUDE.template.md`, `docs/DESIGN.md` (rule table), `templates/research.md` (one note under the Sources
  table and one under the Fact bank, since both have a Published column), `agents/fact-gate.md` (one clause: compare the
  published date only when the row has one), `skills/research/SKILL.md`, `skills/check-research/references/checklist.md`,
  `docs/decisions/ADR-006-live-vendor-pages-in-the-fact-bank.md` (new), `tests/test_skills.py`
- test: `test_n_a_published_is_limited_to_first_party_vendor_pages` — constitution, research stage and G1 checklist all
  carry `n/a (live page)`; the checklist says it is blocking for any other source, for a page that shows a date, and for
  a vendor page used for a claim about another vendor; the constitution's FACT-4 line carries "checked" and the checklist's FACT-4 line names the accessed date. Existing
  `test_constitution_defines_every_design_rule_id` and `test_research_fact_bank_columns_match_glossary` stay green.
- executed how: G1 on a copy of the real dossier (the copy has no `CLAUDE.md`, see setup below) with (a) an `n/a (live page)` row on a vendor's own pricing page:
  expect no finding; (b) an `n/a` row whose source is a third-party blog: expect BLOCK FACT-2; (c) an `n/a` row on a
  vendor page that shows an "updated" date: expect BLOCK FACT-2; (d) a vendor's page used for a claim about another vendor: BLOCK FACT-2; (e) an `n/a (live page)` first-party figure (claim "as listed on the page")
  with accessed date 2023-01-01 against a style guide limit of 12 months: BLOCK FACT-4, and the same row accessed today: no finding.
- risk: a weaker rule. Mitigation: first-party only, written into the checklist, ADR-006 names what is lost.

### R3 — Coverage line (S)
- files: `skills/check-research/SKILL.md`, its checklist, `skills/research/SKILL.md` (report it)
- test: `test_g1_prints_and_the_research_stage_reports_coverage` — both texts name `Coverage:`; the SKILL examples carry it on line 3.
- executed how: G1 on the backup of the real dossier (Q1 to Q10; every question except Q10 names an Open gap): expect
  `Coverage: 1 answered, 9 open (of 10)` on line 3; and the missing-artifact run prints `Coverage: n/a`.
- risk: none.

### R4 — Rerun on the real brief and docs (S)
- files: `CHANGELOG.md`, `docs/DOMAIN_GLOSSARY.md` (live page), `docs/DESIGN.md` (Phase 3 status row), `docs/ARCHITECTURE.md` only if a row changes
- executed how: back up the real workspace, rerun the research stage with the new rules, and report which the brief's vendor and
  tool facts entered the bank and the coverage line. Full pytest and `claude plugin validate ./` after each R.

## How every run below is set up (B2)
- Plugin source: this checkout, `claude -p --plugin-dir /Users/work/Documents/projects/ai/agents/writer-plugin`, run from a
  scratchpad copy of the real workspace (`cp -R`, never edited in place). Before each run, `ls` the copy and record that it
  has **no** `CLAUDE.md` and **no** `.claude/rules/style.md` (the earlier gate runs reported exactly that), so the only
  FACT-2 text in play is the new checklist and stage text. Run (e) adds a scratchpad `style.md` with an age limit.
- **Redaction (PLG-1, A6):** the real brief and its dossier are client data. The PR body and every committed file get only
  verdict lines 1 to 3, rule IDs and row numbers (`F10`, `Q2`), finding counts, and for R4 the number of facts that came
  from first-party live pages plus the coverage line, under a placeholder slug. Full verdicts stay in the scratchpad. No
  client or vendor name appears in this repo.
- **Copy hygiene:** `ls gates/` in the copy and record the G1 verdict count. If there is one or more, move every
  `G1-research.r*.md` into the copy's `gates/archive/` first (the ADR-004 human resume step, scratchpad only), or FLOW-3
  could stop R4. If R4 still ends on a stop after a second BLOCK, R4 reports that as the result.
- **Precedence run (g):** a scratchpad `CLAUDE.md` holding the old strict FACT-2 line, run (a) again: expect no FACT-2
  finding. If the gate blocks, the precedence rule is written into `skills/check-research/SKILL.md` Inputs, not only the checklist.
- **First-party test (written into the G1 checklist):** `n/a (live page)` is allowed only if all hold: the publisher column
  names the vendor; the URL's registrable domain is the vendor's own (the domain of its product site); the claim's
  subject is that publisher; and the page shows no published or updated date. Docs on a third-party domain or a reseller
  mirror fail, so `n/a` there is blocking. Run (f): publisher is the vendor, URL on another domain: BLOCK FACT-2.
- **"Supports" (written into the FACT-6 line):** a fact supports a question if its claim answers at least part of it; a
  fact about a different question is blocking. The unanswered part goes under Open gaps, and that question then counts as
  open in Coverage.
- **Red then green:** each new test is run and shown failing before the text changes, then passing. The red and green
  pytest output, and verdict lines 1 to 3 plus rule IDs and row numbers of each G1 run (redacted as above), go in the PR
  body; the full verdict text stays in the scratchpad (PLG-1 narrows B2's "real output" here). Before the PR is opened, grep
  the PR body and `git diff` for the real brief's vendor and client names; any hit stops the PR.
- No `spec.md`: scope is the Problem and Contract sections above. Option A (keep FACT-2 strict) was rejected by the
  human; ADR-006 records it as a rejected alternative.

## Docs to update in this PR
- [ ] docs/DESIGN.md (rule table; Phase 3 status row with the R4 outcome) · rules/core/CLAUDE.template.md · ADR-006 · CHANGELOG.md · DOMAIN_GLOSSARY.md

## Risks
| Risk | Impact | Cheapest way to find out early |
|------|--------|-------------------------------|
| A bigger fact bank hits the gate's turn limit (`maxTurns: 40`) | G1 BLOCKs on "Not checked" | R4 rerun on the real brief; raise the limit in a follow-up if it happens |
| A live page changes after the access date | a stale price in the draft | the draft states "checked <month year>"; FACT-4 uses the accessed date |
| The brief's PDF text is client data | PLG-1 | the real workspace stays in the scratchpad, never in this repo |

## Assumptions
- One draft PR on `fix/g1-live-vendor-pages`, base `feat/phase-3-vertical-slice` (A4). The real brief and its dossier are
  never committed. The rerun overwrites `research.md` in a copied workspace; the first dossier is kept as a backup.
- If a workspace still holds an earlier copy of the constitution with the strict FACT-2, the gate's checklist wins, since
  it is the text the gate is run with; ADR-006 and the checklist say so. A `research.md` with real published dates stays
  valid unchanged (nothing to migrate or roll back).
- One draft PR, three commits, with the FACT-2 relaxation in its own commit so a reviewer can read it alone.
- Not verified in the PR: the constitution template's FACT-2 and FACT-4 text (checked by test only, as every run has no
  workspace constitution), the "checked <month year>" duty (no draft stage until Phase 5), other vendors' pages that block the fetch tool, and the turn limit on a large bank.
