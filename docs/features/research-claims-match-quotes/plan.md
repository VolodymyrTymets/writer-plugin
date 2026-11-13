# research-claims-match-quotes — implementation plan

Found by reading every research verdict that survived the test workspaces: the first research-gate pass blocked in all
five (most on FACT-5, a claim stronger than its quote; the rest on the "as listed on the page" wording of live-page rows),
and in one run two rounds blocked on two different rows, so the two-BLOCK stop (FLOW-3) fired. No tracker, so the slug
stands in for a ticket ID. Branch `fix/research-claims-match-quotes` off `main` (PR #6 merged).

<!-- A human writes this line to approve. Until it is here, guard-plan-approval blocks writes to code. -->
Approved-by: Volodymyr Tymets, in session 2026-11-13 ("yes", to "Do you want me to go ahead with the plan and tests?")


Pattern followed: the existing research stage and G1 checklist (`skills/research/SKILL.md`,
`skills/check-research/references/checklist.md`) and the `fact-gate` agent; text-assertion tests in `tests/test_skills.py`.

## Problem
The gate is right: every FACT-5 finding was a real overreach (a modal "can" turned into "does", a qualifier the quote does
not contain, two sentences summarised under one quote). Two things make it cost a stop. The research stage writes claims
as summaries of the page, so the first draft over-claims. And the gate reports about one such row per run (an overreach
present in round 1 was reported only in round 2), so a fix-one-and-rerun loop needs more rounds than FLOW-3 allows.

## The change (text only; no rule, verdict format or FLOW-3 change)
1. **Research stage, a row-by-row self-check before the gate runs.** Every part of a claim is in its quote: keep modal verbs
   ("can", "may"), numbers and scope; add no qualifier that strengthens, widens or narrows what the quote says. The date a
   claim needs for FACT-4 ("as of <year>") and "as listed on the page" on a live-page row are required, not forbidden. A third allowance: the claim may name the subject the quote refers to
   (a quote's "we" or "our" resolved to the publisher named in the publisher column, which ADR-006 requires for a live-page
   claim) and may add nothing else; a claim with two parts becomes two rows, each with
   its own quote. A row that fails the check is rewritten to the quote
   or split, never left for the gate.
2. **G1 checklist and the `fact-gate` agent, a complete pass, plus one FACT-5 sentence.** The FACT-5 row of the checklist gains: a claim that only names the publisher behind the quote's "we" or "our", adds the FACT-4 "as of <year>", or says "as listed on the page" does not say more than its quote (asserted in `test_g1_checks_every_row_and_reports_every_finding`). Check every row against its page and report every
   finding, of every rule, in the one verdict; do not stop at the first. A row the gate ran out of turns before reaching goes
   under Not checked (existing rule), so the pass stays honest.
3. **`agents/fact-gate.md` line "Three real findings beat twelve stylistic ones" is reworded** to "Report every real finding;
   never pad with stylistic ones", because the agent can read the old line as a cap on how many findings to report and
   it pulls against the complete pass. (The check-research skill keeps "never pad with advisory findings".) `docs/DESIGN.md` §Gates carries the same sentence, so it
   is changed for the fact-gate only: "The fact-gate reports every real finding in one verdict; no gate pads with stylistic
   ones". The rest of the bullet stays, so DESIGN does not describe a duty the other gates are not given.
4. The G1 checklist keeps citing only FACT-1 to FACT-6 and the verdict format is unchanged, so `test_gate_checklist_keeps_its_must_cite_rules`
   and the verdict-contract tests are unaffected.

## Requirements

### R1 — Self-check in the research stage, complete pass in the gate (S)
- files: `skills/research/SKILL.md`, `skills/check-research/references/checklist.md`, `agents/fact-gate.md`,
  `docs/DESIGN.md` (§Gates verdict bullet), `tests/test_skills.py`, `CHANGELOG.md`
- tests (red before, green after): `test_research_stage_checks_every_claim_against_its_quote` (the stage text says every part
  of the claim is in the quote, keeps modal verbs, splits a two-part claim into two rows, says a live-page claim reads
  "as listed on the page", and carries the FACT-4 date allowance and the "we"/"our" subject allowance); `test_g1_checks_every_row_and_reports_every_finding` (the checklist says it checks every row and
  does not stop at the first finding, and that rows not reached go under Not checked); `test_fact_gate_agent_does_not_stop_at_the_first_finding` (the agent text carries the complete-pass line and the reworded
  "Report every real finding; never pad with stylistic ones", and no longer carries "Three real findings beat twelve"). The
  first test also asserts the FACT-4 date allowance ("as of <year>") is still in the stage text.
- checks before the runs, real output in the PR: `.venv/bin/python -m pytest` (green) and `claude plugin validate ./`.
- executed how (scratchpad only; neutral brief, no client data; each run a separate
  `claude -p "/writer-plugin:<stage>" --plugin-dir <checkout> --permission-mode acceptEdits`):
    0. **A neutral passed dossier first:** run the brief and research stages on a neutral brief with the branch until G1
     passes (at most two resumes: if FLOW-3 stops it, the scratch fixture archives the earlier verdicts, acting as the human; if it still has no PASS after that, stop and report, because that is itself evidence about the change). That dossier is the input of step 1.
  1. **Gate completeness, A/B.** Take the step-0 dossier and plant two FACT-5 overreaches in two different rows
     (one "can" turned into "does", one added qualifier). Run the research gate three times with the plugin from `main` (a
     separate git worktree in the scratchpad, the baseline) and three times with this branch. Report for each run whether
     both planted rows are reported (rule IDs and row numbers only). Expect the branch to report both in every run; the
     baseline's rate is the comparison. No mocks.
  2. **Fewer first-round blocks.** Run the research stage on three fresh copies of the same neutral workspace (brief PASS, no
     research) with the branch. Then run the same three runs from the `main` worktree on three fresh copies of the same workspace and report both sides in
     the same shape; the five earlier first rounds are the motivation only, not the baseline. Report for each run how it ended (PASS at `r<k>`, or a FLOW-3 stop), the first G1 verdict (line 1, rule IDs, row numbers), the number of fact rows, and the number of
     rows under Not checked. With three runs per side the
     result is indicative, not proof, and is reported so. This step measures the stage change and the gate change
     together, not the self-check on its own, and the PR body says so.
- Precedent for headless web access: the same command ran the research stage and the forked gate opened sources in PR #6's runs;
  one run is checked first, and if web tools prompt the experiments are invalid and reported as such.
- Note on loading: before the A/B runs, `claude plugin list` is checked for an installed copy of the plugin; each run loads
  exactly one source through `--plugin-dir`.
- risk: the gate may still report different rows between runs (nondeterminism); step 1 measures this. More thorough passes use
  more of `maxTurns` (40): rows not reached go under Not checked, which keeps the verdict honest. If step 1 shows the
  turn limit is hit, raising it is a separate change.

The live-page wording seen in a first round was a claim written as "<vendor>'s help article says …" or "<publisher> says …"
without "as listed on the page". The stage text already requires the phrase (Step 3.3); the actor did not follow it. Item 1's
row-by-row self-check is what enforces it: a live-page row whose claim lacks the phrase fails the check and is rewritten.

## Docs to update in this PR
- [ ] CHANGELOG.md and DESIGN.md §Gates (the verdict bullet only). No ADR or rule change (text only; the G1 contract is unchanged).

## Risks
| Risk | Impact | Cheapest way to find out early |
|------|--------|-------------------------------|
| A stricter self-check makes claims too terse | thin dossier | fact counts and Not-checked counts are compared with the `main`-side runs in step 2 |
| The complete pass hits the turn limit | BLOCK on "Not checked" | step 1 reports it; the limit is a separate change |
| Client data in evidence | PLG-1 | only a neutral brief is used; grep the plan, `git diff` and the PR body for the real brief's names before committing and opening the PR |

## Assumptions
- Deliberately unchanged (C1): "Three real findings beat twelve stylistic ones" in `agents/gate.md`, `skills/check-brief/SKILL.md`
  and `docs/BUSINESS_MODEL.md`. If step 1 shows the phrase acts as a cap, a follow-up changes them.
- One draft PR; `.serena/` is never committed. The baseline worktree lives in the scratchpad and is removed with
  `git worktree remove` when done. Not verified in the PR: the real brief (not rerun here), gate run-to-run variance beyond
  six runs.
