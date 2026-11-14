# ADR-013 — Gate-first evals on synthetic briefs, run locally with `claude plugin eval`

- **Date:** 2026-11-14
- **Status:** accepted
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (`docs/features/phase-7-publish-sync-setup/plan.md`, part 7c)

## Context
Ranked goal 1 is correct gates: a gate that passes a wrong fact, or blocks on noise, defeats the plugin. Until now every gate was
checked by contract tests on its text and by one executed run each. Nothing re-checked a gate's judgement after its checklist
changed. Phase 0 asked for "2–3 real briefs to test with"; PLG-1 keeps client briefs out of this repository.

## What was verified first (D4, 2026-11-14)
From the docs (code.claude.com/docs/en/plugin-evals.md) and a probe case run once in a scratch copy of the plugin:
- **Case format:** a case is `case.yaml` and/or `prompt.md`.
- **Grader types:** `regex` (on the last message, the trace or a workspace file), `tool_used`, `tool_order`, `file_exists`, `llm` and
  `baseline`. There are no script graders.
- **Tool grants:** a case can grant only read-only tools; Write, Edit and WebFetch come from the operator's `--allow-tools`.
- **Workspace:** it starts empty. Only `context.scaffold_script` (with `--scaffold`) seeds it, and it reaches files beside the case
  through `$(dirname "$0")`.
- **Gates:** a slash prompt (`/writer-plugin:check-brief demo`) is expanded and runs the gate **forked into
  `writer-plugin:gate`**. The Skill tool is not called, so a `tool_used: Skill` grader cannot see a gate.
- **Hooks:** plugin hooks run.
- **Output:** the verdict is the run's last message, line 1 first.
- **Trust:** the first run in a directory needs the plugin to be trusted; the approver allowed `--trust-plugin` for this session.

## Decision
1. **Gates first.** Each gate G0–G4 has a PASS case and a BLOCK case that seeds exactly one defect, and the case names the rule:
   - G0: no named reader (BRF-1).
   - G1: a claim stronger than its real quote (FACT-5).
   - G2: a statistic no fact supports (FACT-1).
   - G3: an unplanned section on the brief's must-avoid list (STR-2 or BRF-5).
   - G4: two cases, a 74-character title the recorded lint reports (SEO-2), and a quote changed against its source (FACT-3).

   G0 also passes each of the three briefs, and the brief stage normalises each brief without a question and saves a G0 PASS.
2. **Synthetic, public material only.** The suite uses three briefs on public technical topics, and one short article on HTTP caching
   carried through every stage. Its fact bank quotes RFC 9111 and MDN verbatim, as extracted from the pages on 2026-11-14.
   `tests/test_evals.py` allows only `www.rfc-editor.org`, `developer.mozilla.org` and `example.com`. This closes Phase 0's
   "briefs needed" with synthetic briefs; real client briefs are run in client workspaces, never here.
3. **One fixture, one-file defects.** Every case copies the fixture (or a brief) through one shared `scaffold.sh`, then lays its own
   `seed/` on top. A BLOCK case differs from its PASS case by one file, plus a re-recorded lint record when the final changes.
4. **Graders:**
   - a `regex` on the verdict's line 1;
   - a `regex` on the trace proving the gate forked into its write-free agent;
   - for a BLOCK, a `regex` for the rule ID and an `llm` grader that the seeded defect is the one named;
   - for the actor cases, graders on the files it wrote and `AskUserQuestion` never called.
5. **Local and on demand, never in CI.** Each run is a real session on the developer's credential. Runs use `--runs 1 --ablation none
   --max-cost-usd`, web access limited to the two source domains, and output outside the repository (`evals/results/` is git-ignored).
   A gate or checklist change reruns that gate's cases. A score below 1.0 is reported, never retried until green.

## Rejected alternatives
| Alternative | Why not |
|-------------|---------|
| Real client briefs in the repo | PLG-1 |
| Full-chain cases (brief to final in one run) | Expensive, and a failure would not say which gate is wrong |
| `tool_used: Skill` to prove a gate ran | A slash prompt does not call the Skill tool (probe); the trace shows the fork instead |
| Evals in CI | Costs per run, needs a credential, and G1/G4 depend on live pages |
| The default `--ablation with-without` | A no-plugin baseline has no meaning for a gate verdict and doubles the cost |

## Consequences
- Positive: a gate's judgement is now checked on known-good and known-bad input, so a checklist edit that makes a gate pass a wrong
  fact or block a clean article shows up as a failing case.
- Accepted cost:
  - G1 and G4 cases depend on two live pages. If MDN rewords its sentence, `g1-pass` and `g4-pass` fail until the fixture's quote
    is re-extracted.
  - RFC 9111 is a long page, and WebFetch may stop before the cited §5.2.2 sentences. A PASS case failing on FACT-3 or FACT-2
    there is the first thing to check.
  - LLM-judged graders can vary between runs.
- Ground truth: the fixture prose makes no checkable claim without a fact ID, and no sentence says more than its bank row. A
  self-review found and removed sentences that broke this, including one close to the `g1-block` overclaim. `tests/test_evals.py`
  pins the citations both ways.
- Narrow coverage: the brief-actor cases start from briefs already in template form. They check that the stage asks nothing,
  writes `brief.md` and saves a G0 PASS, not that it can normalise a messy brief.
- Not yet run: at merge, only `g0-pass-http-caching` has run (score 1.00, $0.05). The approver chose not to run the full suite yet.
- Follow-ups:
  - run the full suite once;
  - one brief-actor case from a raw, unstructured brief;
  - a case per remaining BLOCK rule, as gates change;
  - more runs per case once costs are known.

## Revisit when
`claude plugin eval` gains script graders or file fixtures, or a gate is found passing something these cases do not cover.
