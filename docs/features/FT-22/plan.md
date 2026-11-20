# FT-22 — implementation plan

No tracker. Branch `feat/ft-22-questions-list` for PR 1, cut from an up-to-date `main` (A1); PR 2 gets its own branch. Spec: `spec.md`. **Order of work (each step green on its own): R0, R1, R5, R2, R3, R4, R5b, then PR 2 (R6, R7); R5 comes early because it defines FACT-6's wider wording and STR-7 and widens `GATES`, which later steps cite.** **Fixed split: PR 1 = R0 to R5 with all of its docs; PR 2 = R6 and R7 with their own docs** (A4: one PR, one change; both opened as drafts).

<!-- A human writes this line to approve. Until it is here, guard-plan-approval blocks writes to code. -->
Approved-by: Volodymyr - 2026-11-20

Pattern followed: FT-20 (ADR-021): `templates/research.md` "Questions for the human", the research skill's step that writes it, G1's advisory line in
`skills/check-research/references/checklist.md`, and the tests in `tests/test_templates.py` and `tests/test_skills.py` that pin them. The script follows
`bin/prose-lint.py` (stdlib, read-only without `--record`, findings as JSON, called by actors, never by a gate). Markers: ADR-008, ADR-017. New: one ADR (023), because FLOW-6 changes.

## Contract changes
- data (artifact format): `outline.md`'s heading "Open questions for the human" becomes `## Questions for the human`, same format as research; `draft.md` may end with the
  same section. Under the old heading "Open questions for the human" the checker applies only the placement rule (no text after it but an approval line); it skips the line-format and count rules, so an outline already in progress has no finding until it is rebuilt (the CHANGELOG "Upgrading" note says so). A leading `- ` or `1. ` is stripped before a line's mark is read, and a lone `none` (with or without a prefix) is accepted.
- data (order): the section comes last; only an `Approved-by:` or `Signed-off-by:` line may follow it. The checker and the lint skip those lines with the existing `writer` approval-line helpers, so a draft that ends `…section, Approved-by:` has no finding and prose after the section is a finding.
- data (new marker, PR 2): `<Needs to be written by a human. Reason: reason sentence here>`, same exact form as ADR-008. FLOW-6 refuses sign-off and a `publish-ready` label while it remains.
- boundary: new script `bin/questions-check.py <slug> <stage>` (JSON on stdout, read-only). No hook, no `hooks.json` change, no change to the verdict header lines (ADR-019).
- generated output: none.

## Requirements (ordered, each independently verifiable)

### R0 — ADR-023 (S)
- files: `docs/decisions/ADR-023-questions-list-and-human-marker.md` (new)
- status: ADR-023 is accepted for the list and FACT-6 and STR-7; its skip-marker and FLOW-6 decisions say "ships with PR 2", and PR 2 sets them to done.
- content: one list, one format, per-stage content, omitted when nothing is owed, advisory only; FACT-6 widened to the list at every stage and a new rule STR-7 (no working section in the final); the human-written marker and FLOW-6 extended; refines ADR-008, ADR-017, ADR-021 and says which part of ADR-012.6 (a comment is data) a skip comment relies on: the stage applies it only as FT-20 already lets a comment settle a decision.
- test: none for prose; `.venv/bin/python -m pytest` stays green. executed how: pytest output in the PR. risk: none.

### R1 — the shared checker (M)
- files: `bin/lib/writer.py` (change: `questions_findings(text, upstream_text, stage)`), `bin/questions-check.py` (new), `tests/test_questions_check.py` (new)
- layer: script plus library, as `prose-lint.py`.
- rules (AC1, AC3), mechanical form only: section is last (only an approval line may follow); each line, prefix stripped, starts `[OPEN]` or `[RESOLVED]` (`[SKIPPED]` is added in R6), or the section is `none`; no `Q<n>`, `F<n>` or comment id; an exact-form `<Can't be verified…>` marker outside the section with **no** `[OPEN]` line at all is one finding (no count match: one question may cover several markers about the same page, as G1 allows today, and no ids link a marker to a line); no `[RESOLVED]` line repeated from the upstream list. The semantic checks stay with the gates as text and G1 keeps them (a `[RESOLVED]` question whose marker is still under Open gaps; a question that does not say what would answer it). ADR-023 states that split.
- test: one case per rule (3 markers and no line give one finding, 3 markers and 1 line none; a draft whose section is followed by `Approved-by:` gives none; `- none`, `1. [OPEN] …` and an old-heading section), plus the old outline heading, a missing section with no marker (no finding), and an unreadable upstream (a finding, never a crash).
- executed how: run it on `evals/fixtures/http-caching/articles/http-caching` copied to the scratchpad, clean, then with each rule broken in turn; paste the JSON.
- risk: the repeat rule compares sentences. Compare normalised text (lower case, collapsed spaces), not ids; cheapest check: a test with a reworded line, which is not a repeat.

### R2 — research stage (S)
- `allowed-tools` of `skills/research` gains `Bash(python3 ${CLAUDE_PLUGIN_ROOT}/bin/questions-check.py *)` in the exact form `QUOTE_CHECK_RULE` uses; the exact allow-list test at `tests/test_skills.py:255` is extended by that one rule and its `WHY:` comment updated (still exact, not loosened), and the PR body lists it.
- rule: omit the section only when no line was ever written; once it exists, keep every earlier line (FT-20), so a research with only `[RESOLVED]` lines keeps them. A test pins both.
- files: `templates/research.md`, `skills/research/SKILL.md` (change: omit the section when nothing is owed; run the checker), `skills/check-research/references/checklist.md` (advisory line cites the shared rules), `tests/test_templates.py`, `tests/test_skills.py` (the pinned `none` wording changes with the rule, not weakened: the new assertion is that `none` and an omitted section are both accepted)
- executed how: the checker on a research fixture with all questions answered (no section) and with one marker.
- risk: FT-20's tests pin "Write `none` when nothing is owed"; each assertion that changes is listed in the PR body.

### R3 — outline stage (M)
- files: `templates/outline.md`, `skills/outline/SKILL.md`, `skills/check-outline/references/checklist.md` (lines 28 and 31: the marker count leaves out **both** headings, "Questions for the human" and the old "Open questions for the human", so an old outline is not counted twice), `tests/test_templates.py`, `tests/test_skills.py` (the substring asserted at line 508, `outside the "Open questions for the human" section`, stays verbatim in the checklist and the new heading is pinned beside it), the fixture `evals/fixtures/http-caching/articles/http-caching/outline.md` and three of the four seeds (`g2-block-marker-without-gap`, `g2-block-claim-without-id`, `g2-block-marker-fan-out`): heading rename, and their lines rewritten as `- [OPEN] <plain question>` so the planted defect is the only finding (checker output pasted for each renamed seed, expected `[]`). `g2-pass-markers-per-gap` keeps the old heading as the regression case.
- `allowed-tools` of `skills/outline` gains the same rule, with a test that the skill carries it (the outline run once lost edits to a missing pre-approval, `tests/test_skills.py:741`).
- list content: the research markers still in the outline, plus questions the outline itself owes; nothing `[RESOLVED]` upstream is repeated (AC3, AC4).
- test: `tests/test_evals.py` (shape) and `tests/test_skills.py`; executed how: checker on the renamed fixture with research as upstream (expected: `[]`), and on the old-heading seed `g2-pass-markers-per-gap` (expected: `[]`, the old heading skips the format rules).
- risk: the G2 marker count (ADR-017). Cheapest check: a test that the checklist names both headings; the eval cases themselves cost money and are not run (Not verified).

### R4 — draft stage and the list out of the article (M)
- files: `skills/draft/SKILL.md`, `skills/check-draft/references/checklist.md` (advisory), `skills/edit/SKILL.md` (drops the section from `final.md`, keeps every marker), `bin/prose-lint.py` and `bin/lib/writer.py` (section excluded from STR-6 and FACT-1 only), `tests/test_prose_lint.py`, `tests/test_skills.py`
- test: lint on a draft with a list is the same as without it, word count and FACT-1; the Doc copy text still holds it (`doc_text` test).
- executed how: `prose-lint.py` and `doc-copy.py` on a scratch draft with the section; paste both outputs.
- `allowed-tools` of `skills/draft` gains the same rule, pinned by a test. `MUST_CITE` for `check-final` gains STR-7 here (the checklist line is written in this step); R5 owns defining STR-7 and FACT-6 and widening `GATES`.
- G3 and G2 must not read the section as article text: `skills/check-draft/references/checklist.md` says a closing `## Questions for the human` is not an article section, so it is outside STR-2, outside line 3 (`Outline: <a> of <m> sections present`) and outside FACT-1, and is judged only by the advisory FACT-6 line; `skills/check-outline/references/checklist.md` says the same for the outline's section under either heading (STR-2 and FACT-1). `tests/test_skills.py` pins both sentences (AC5: a draft with a list still PASSes).
- risk: the list leaks into `final.md` and is published. The lint reports a leftover section heading in a final as **STR-7** (new rule: no working section in the final); `skills/check-final/references/checklist.md` gets STR-7 in the **blocking** mechanical row of Section A (beside STR-4, STR-6, SEO) and in its allowed-IDs line, so G4 blocks on it (`verify-final` only checks that the lint ran); a `test_skills.py` assertion pins STR-7 in that row. `MUST_CITE` for `check-final` gains STR-7, listed in the PR body with the FACT-6 widening. Cheapest check: a lint test on a final that still holds the section.

### R5 — gates share one wording, with a valid rule ID (S)
- files: `skills/check-research|check-outline|check-draft/references/checklist.md` and the example advisory line in `skills/check-outline/SKILL.md` and `skills/check-draft/SKILL.md` (as `skills/check-research/SKILL.md:49`), one sentence naming the rules of R1, including that a section under the old heading is exempt from the format rules (pinned in `tests/test_skills.py` beside the new heading); the allowed-IDs line (line 3) of the `check-outline` and `check-draft` checklists gains FACT-6; `rules/core/CLAUDE.template.md` and `docs/DESIGN.md` rule table (FACT-6 widened to "the questions list at research, outline and draft", STR-7 added); `tests/test_skills.py` (`GATES` allows FACT-6 for `check-outline` and `check-draft` and STR-7 for `check-final`; `MUST_CITE` gains FACT-6 for the first two; the widening is listed in the PR body; all three checklists carry the same sentence)
- executed how: pytest; one G2 or G3 run on a seed with a malformed list, only if the human pays (AC5 advisory still PASSes); otherwise Not verified. risk: none.

### R5b — PR 1 docs (S)
- files: `docs/ARCHITECTURE.md` (the script, the heading, `test_questions_check.py` in the `tests/` row), `docs/DOMAIN_GLOSSARY.md` (Questions list), `docs/DESIGN.md` (FT-22 row, hooks table, outline/draft sections), `CHANGELOG.md` (Added line; "Upgrading": an old outline keeps working, its next rebuild gets the new heading; re-run `writer-plugin:setup` to refresh a workspace's FACT-6 and STR-7 text, as the FT-19 entry does), spec ticked for AC1 to AC6 and AC8
- executed how: pytest and `claude plugin validate ./`, output in the PR. risk: none.

### R6 — PR 2: the human-written marker, FLOW-6 changed (M)
- files: `bin/lib/writer.py` (`MARKER_LOOSE` becomes the non-capturing group `(?:<Can.t be verified|<Needs to be written by a human)`, so `MARKER_TEXT`, which appends to it, still covers each whole marker; `bold_markers`, `publish_ready` follow), `bin/prose-lint.py` (shares only the loose pattern for FLOW-6; keeps its strict noise pattern for FACT-1, widened by alternation, so a number after a mangled marker is still read), `bin/lib/writer.py` `questions_findings` also accepts `[SKIPPED]` and counts the human-written marker as covered by an `[OPEN]` or `[SKIPPED]` line, and the shared sentence in the `check-outline` and `check-draft` checklists names `[SKIPPED]` so a skipped line draws no advisory; `bin/guard-stage-order.py` (the refusal messages at line 180 and at lines 231 and 232 for the `docs.json` entry name both markers), `skills/outline`, `skills/draft`, `skills/edit` (frozen like the other marker), `skills/check-outline|check-draft|check-final` checklists (exact form accepted; one marker per open gap, counted against the Open gaps of `research.md`: a skip swaps a gap's marker, it adds none), `rules/core/CLAUDE.template.md` (FLOW-6 text), `tests/test_hooks.py`, `tests/test_prose_lint.py`
- test: `tests/test_questions_check.py`: a `[SKIPPED]` line covering the new marker gives no finding, the new marker with no line gives one; `tests/test_hooks.py`: a `publish_ready` copy refused because of the human-written marker; sign-off refused with only the new marker present; `publish_ready` false; the Doc copy bolds it; `article-status.py` lists it under `markers`; the lint reports it as FLOW-6 and does not read a number in its reason as a FACT-1 claim; both forms in each test, and the existing `Can't` marker is still bolded whole and listed whole.
- executed how: guard, lint and status script run on a scratch final with each marker form, and the checker on that scratch article with a `[SKIPPED]` line, output pasted. risk: a second marker form doubles the "exact form" checks in three gates; cheapest check: one shared sentence in each checklist.

### R7 — PR 2: skip, and the docs (S)
- files: `skills/outline`, `skills/draft` (a reviewer's comment that asks to skip one question marks `[SKIPPED]` with the reason and swaps the marker), `docs/DOMAIN_GLOSSARY.md` (Human-written marker), `docs/DESIGN.md` (FLOW-6 text, enforcement table, FT-22 row set to fixed), `CHANGELOG.md` (with an Upgrading line: do not downgrade past this version while an article holds the new marker, because the old loose pattern does not see it; re-run `writer-plugin:setup` to refresh a workspace's FLOW-6 and STR-7 text), spec AC7 ticked
- executed how: one headless run on a scratch article with a synced skip comment, if the human allows the cost; otherwise listed under Not verified.

**Skills not run.** Research, outline, draft and edit behaviour (omitting, writing and dropping the section) is checked by tests of the skill text and by the scripts on fixtures. A headless run of each stage in a scratch workspace costs money and goes under "Not verified" in the PR unless the human pays for one.

## Docs to update in this PR
- [ ] docs/features/FT-22/spec.md (acceptance criteria checked off)
- [ ] PR 1: R0 and R5b above (ADR-023, ARCHITECTURE, glossary "Questions list", DESIGN, CHANGELOG with its Upgrading note)
- [ ] PR 2: R7 above (glossary "Human-written marker", DESIGN FLOW-6 text, CHANGELOG)

## Risks
| Risk | Impact | Cheapest way to find out early |
|------|--------|-------------------------------|
| The draft list is published in the final | Internal questions reach readers | R4 lint finding and test (above) |
| A rename breaks the G2 count of markers | G2 blocks a good outline | R3 static check of the eval seeds, then one eval case if the human pays |
| A second marker form weakens FLOW-6 | A marker escapes the loose pattern | One pattern in `writer.py`; test each guard path with both forms |
| A comment talks a stage into skipping a question | A human checkpoint is bypassed | A skip only changes a marker and a line, never an approval; the stage's gate and the guard still run (ADR-016) |

## Assumptions
- A bare answer in a comment resolves nothing (ADR-020, ADR-021); skip does not apply at research; the final has no list of its own.
- Sizes: R0 S, R1 M, R2 S, R3 M, R4 M, R5 S, R5b S, R6 M, R7 S. Whole ticket L; two PRs.
