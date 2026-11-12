# phase-3-vertical-slice — implementation plan

Build-plan Phase 3 (`docs/DESIGN.md`): the brief, research and outline stages, their three gates, agents `gate` and
`fact-gate`. Spec: `spec.md`. No tracker, so the slug stands in for a ticket ID.

<!-- A human writes this line to approve. Until it is here, guard-plan-approval blocks writes to code. -->
Approved-by: Volodymyr - 2026-11-12

Pattern followed: `../rln-agent/skills/analyze-plan/SKILL.md` and `../rln-agent/agents/plan-gate.md` (forked skill,
`agent:`, `background: false`, read-only agent, verdict format, "resolve the input from disk yourself"). Actor-then-gate
chaining follows `../rln-agent/skills/develop-feature/SKILL.md` (calls the gate, fixes, stops after repeated failure).

## Contract changes
- boundary: six new slash commands (three stage commands and three gate commands, named by `COMMANDS` in
  `tests/test_structure.py` once each lands), additive. Two new agents, `writer-plugin:gate` and `writer-plugin:fact-gate`.
- data (breaking for Phase 4 hooks if changed later): the **verdict file** `articles/<slug>/gates/G<n>-<stage>.r<k>.md`.
  Line 1 matches `^## (G0 brief|G1 research|G2 outline|G3 draft|G4 final) gate: (PASS \(0 blocking|BLOCK \([1-9]\d* blocking), \d+ advisory\)$`
  (a PASS may carry advisories, never blockers; each unverifiable fact counts as one blocking FACT-2 finding). Line 2 is `Artifact: <path>`; anything else comes after.
  `guard-stage-order` (Phase 4) reads "latest `r<k>`, line 1 matches, verdict group is PASS". `k` is 1 + the count of
  existing files for that gate. Settled in `docs/decisions/ADR-004-verdict-file-contract.md`.
  Each gate skill carries a literal PASS example and a literal BLOCK example (not placeholders); `tests/test_skills.py`
  asserts (a) the regex accepts each gate's PASS and BLOCK examples, (b) each gate's examples use its own pair, and (c) it rejects `PASS (1 blocking, 0 advisory)` and `BLOCK (0 blocking, 0 advisory)`. The actor checks line 1 against the regex before saving; no match means "no PASS", not
  a saved PASS. Only an actor-saved verdict counts for FLOW-1; the caller's save is the only record. A forked gate cannot tell who called it, so it prints no notice about that.
- **FACT-2 wording (constitution and DESIGN, one word):** "has a source URL" becomes "has a source URL that resolves" (DESIGN row: "every fact has URL" becomes "every fact has a URL that resolves").
  Without it no rule covers a dead link. This strengthens a rule; `test_templates.py` shape checks are unaffected.
- **two new rule IDs (constitution, DESIGN table, brief template heading tagged):** BRF-6 the questions the research
  must answer are listed; FACT-6 every such question is answered by a fact or listed under Open gaps. G0 and G1 need
  them, since a finding without an ID is not a finding. `test_templates.py` reads IDs from DESIGN, so it follows.
- artifacts: shapes fixed in Phase 2 templates; actors write exactly those headings. Gates parse headings, not wording.
- `tests/test_structure.py` (ask-first path): only `COMMANDS` / `PLANNED` entries move. No assertion is touched (B3).

## Requirements (ordered, each independently verifiable)

### R0 — Rule IDs: FACT-2 wording, BRF-6, FACT-6 (S)
- files: `rules/core/CLAUDE.template.md`, `docs/DESIGN.md` (rule table), `templates/brief.md` (heading tagged `(BRF-6)`),
  `tests/test_templates.py` (`test_brief_has_a_section_per_brf_rule` range 1..5 becomes 1..6: stricter, B3 holds)
- test: `test_constitution_defines_every_design_rule_id` (reads DESIGN, so the two cannot drift) plus the extended brief test.
- executed how: full pytest; fill the brief template in the scratchpad and confirm the BRF-6 heading parses. Lands first,
  so later checklists cite only defined IDs. BRF-6 and FACT-6 are exercised in R2 and R3 below.
- risk: low. Phase 2 shape tests stay green.

### R1 — Agents `gate` and `fact-gate` (S)
- files: `agents/gate.md` (new, tools `Read, Grep, Glob`), `agents/fact-gate.md` (new, tools
  `Read, Grep, Glob, WebFetch, WebSearch`), `tests/test_skills.py` (new)
- layer: agent config. Body states read-only, no fixing, golden rule "artifact and constitution disagree: the artifact
  is wrong", "unverifiable goes under Not checked, never PASS". The prose-lint tool is added to `gate` in Phase 4.
- test: existing `test_agents_are_well_formed_and_gate_agents_cannot_write` (no write tool, tools listed);
  new `test_fact_gate_can_open_sources_and_gate_cannot` — `fact-gate` lists WebFetch and WebSearch, `gate` lists neither.
- **first step, before any skill text (D4):** settle from the Claude Code docs (Context7 or claude-code-guide, not
  memory) whether `${CLAUDE_PLUGIN_ROOT}` expands in skill text and whether `claude -p --plugin-dir` exists, and whether a skill invoked through the Skill tool honours `context: fork`
  and `agent:` and returns its verdict to the caller. If the docs do not confirm the last point, implementation stops
  after R1 and the chaining design goes back to a human (B4, F2); it is not worked around in skill text. Decision
  recorded in the plan's Assumptions and in a new `docs/ARCHITECTURE.md` landmine line (not DESIGN open question 2,
  which is about Drive tools). Where inputs come from, in a workspace that has had no setup:
  actors read `templates/<stage>.md` via `${CLAUDE_PLUGIN_ROOT}` if it expands, else from a copy under their own
  `references/` guarded by a drift test (ADR-005 records whichever branch is taken: where actors get templates at runtime, and why); gates take their checks and rule-ID wording from their own
  `references/checklist.md`, and read the workspace `CLAUDE.md` and `.claude/rules/style.md` (path as in DESIGN; `test_skills.py` asserts gate text names it) only if present (absent: say so under
  "Not checked", never invent a style rule). If `templates/` becomes a runtime input, ARCHITECTURE's "loaded" column changes.
- executed how: `claude plugin validate ./`; confirm both agents appear to a headless session
  (`claude -p --plugin-dir . "list agents"` in the scratchpad), if the docs confirm the flag.
- risk: headless plugin runs may not work here. If not, listed under "Not verified" with the reason.

### R2 — Brief stage and G0 (M)
- files: `skills/intake-brief/SKILL.md` (command `brief`), `skills/check-brief/SKILL.md` (+ `references/checklist.md`),
  `tests/test_structure.py` (move two entries PLANNED → COMMANDS), `tests/test_skills.py`
- layer: actor skill writes `brief.md` (+ keeps the input as `brief.source.md`), max two batched question rounds, then
  invokes G0 via the Skill tool, writes the verdict to `gates/G0-brief.r<k>.md`, on BLOCK revises once; the actor counts BLOCK verdict files on disk for the artifact, so a second BLOCK stops it
  across runs too (FLOW-3). Gate skill: `context: fork`, `agent: writer-plugin:gate`, `background: false`; checks BRF-1..6
  (only headings that carry a rule tag are checked); verdict format as in Contract changes.
- test: `test_gate_checklists_cite_only_their_stage_rules` — allowed IDs per gate: G0 BRF-1..6; G1 FACT-1..6; G2 STR-2, STR-3, STR-5, SEO-1, FACT-1; each checklist cites only its set;
  `test_actor_skills_save_verdicts_and_stop_after_two_blocks` — each actor text names `gates/` and FLOW-3.
  Structure tests (fork, agent, background, command map, planned-command mentions) run on the new skills unchanged.
- every gate skill and actor resolves its input from disk: argument slug, else the most recently modified
  `articles/*/<artifact>`, named on the `Artifact:` line. Every actor after the brief stage refuses to start without
  the previous gate's latest PASS verdict file (FLOW-1) and names that file when it stops. Tested in `test_skills.py`.
- executed how: scratch workspace outside the repo with **nothing copied in** (the R1 decision supplies templates;
  a missing `CLAUDE.md` / `style.md` is part of what is exercised). (a) a brief with no reader → the brief gate
  BLOCK with BRF-1 and a fix (AC2); a brief with no research questions → BLOCK BRF-6 (AC9); the brief gate run with no slug
  records its resolved `Artifact:` line; (b) a complete synthetic brief → the brief stage writes `brief.md`, G0 PASS, verdict file
  written (AC3, AC8).
- risk: the actor reads `templates/` from the plugin; see Risks.

### R3 — Research stage and G1 (L)
- files: `skills/research/SKILL.md`, `skills/check-research/SKILL.md` (+ `references/checklist.md`),
  `tests/test_structure.py` (entries), `tests/test_skills.py`
- layer: actor writes `research.md`: questions, sources, fact bank (seven columns), competitor coverage from WebSearch
  of the primary keyword, the gap, open gaps. Refuses to start without a G0 PASS on disk (FLOW-1, prompt only until
  Phase 4). Never invents a quote: a fact it cannot quote verbatim is not a row. G1 forks into `fact-gate`, opens
  **every** source URL, compares the quote and date, flags FACT-1..5, and FACT-6 for each brief question.
  Reachability rule, written into the G1 checklist: page fetched but the quote is not on it → BLOCK FACT-3; page
  definitively gone (404, 410, DNS failure) → BLOCK FACT-2; blocked, timed out or web tools absent → that fact is listed
  under "Not checked", cited as FACT-2 (cannot confirm the URL resolves), and the verdict is BLOCK, never PASS. The
  research actor keeps a row only if it fetched the page itself, so a blocked host is rare, not routine.
- test: `test_fact_gate_skill_uses_fact_gate_agent` — `check-research` names `writer-plugin:fact-gate`, others `gate`;
  the checklist names FACT-2, FACT-3 and FACT-5.
- executed how: (a) real WebSearch research on a neutral topic, G1 PASS or a justified BLOCK; (b) edit a copy of that
  `research.md` so one quote is fabricated and one URL is a definite 404 (`https://httpbin.org/status/404`) → G1 BLOCK citing FACT-3 and
  FACT-2 (AC4); a third row on `https://httpbin.org/status/403` (a blocked fetch) must land under "Not checked". Also a
  required run with web tools denied: BLOCK, every row under "Not checked" cited FACT-2. Save raw fetch results as evidence.
  FLOW-1 run: the research stage in a workspace with `brief.md` but no G0 verdict file must stop and name the file.
  Also: an answer-less brief question, absent from Open gaps → BLOCK FACT-6 (AC10). This is the
  check that matters most for goal 1.
- risk: G1 cost and turn budget (many fetches). Mitigation: `maxTurns` set on the agent, and G1 reports what it did not
  reach under "Not checked" rather than passing it.

### R4 — Outline stage and G2 (M)
- files: `skills/outline/SKILL.md`, `skills/check-outline/SKILL.md` (+ `references/checklist.md`),
  `tests/test_structure.py` (entries), `tests/test_skills.py`
- layer: actor writes `outline.md` with an **empty** `Approved-by:` and never fills it; ends by telling the human to.
  G2 checks STR-2, STR-3 (sums the Words column against the brief target ±10%), STR-5, SEO-1 plan, FACT-1 (every claim
  row has fact IDs that exist in the bank). G2 does not check `Approved-by:` (no rule ID covers it; the actor test and the Phase 4 hook do).
- test: `test_outline_actor_never_writes_the_approval` — the skill text says it leaves `Approved-by:` empty (FLOW-2).
- executed how: (a) full chain on the R2/R3 sample → outline, G2 PASS, `Approved-by:` empty (AC6); (b) an outline row
  citing `F99` that is not in the bank, and a budget 40% over target → BLOCK with FACT-1 and STR-3; (c) the outline stage with no G1 PASS on disk stops and names the file; (d) a row whose
  Key points carry a statistic and whose `Fact IDs` cell is empty → BLOCK FACT-1 (AC5). The G2 checklist has a line for each.

### R5 — Docs and chain run (S)
- files: `docs/DESIGN.md` (Phase 3 status "built; real-brief run pending", never "done"), `docs/ARCHITECTURE.md` (skills and
  agents rows, `tests/` row), `docs/DOMAIN_GLOSSARY.md` (verdict file), `CHANGELOG.md` (Unreleased/Added), `README.md`
  (only if it lists commands as planned), this spec's checkboxes
- test: full `pytest` incl. `test_every_documented_command_exists`; `claude plugin validate ./`
- executed how: run the whole slice once in a fresh scratch workspace (brief → G0 → research → G1 → outline → G2) and
  record each verdict file. AC7 seed: a brief with no named reader and the question round answered "unknown", so the
  brief stage reaches G0 BLOCK twice and must stop; a rerun of the stage must stop at once, naming both verdict files. Every R commit and the final tree run the full pytest green.

## Docs to update in this PR
- [x] docs/DESIGN.md — Phase 3 status (built; real-brief run pending); rule table in R0
- [x] rules/core/CLAUDE.template.md and templates/brief.md — FACT-2, BRF-6, FACT-6, heading tag
- [x] docs/decisions/ADR-004-verdict-file-contract.md — the regex and why Phase 4 depends on it
- [x] docs/ARCHITECTURE.md, CONTRIBUTING.md — skills, agents, tests rows
- [x] docs/DOMAIN_GLOSSARY.md — "Verdict file"
- [x] CHANGELOG.md — Added (Deleted: nothing yet)
- [x] docs/decisions/ADR-005-actor-template-source.md — either branch of R1; the gate pattern follows rln-agent

## Risks
| Risk | Impact | Cheapest way to find out early |
|------|--------|-------------------------------|
| `${CLAUDE_PLUGIN_ROOT}` may not expand in skill text | actors cannot find templates | R1: check docs; fallback is `references/` copies plus a drift test |
| FLOW-1 is a prompt rule until Phase 4 | an actor could skip a gate | say so in the PR; the hook is Phase 4 and not in scope |
| Skills cannot be exercised end to end in this environment | "executed" evidence is thin | R1 headless probe; otherwise run the gate prompts by hand on fixtures and mark "Not verified" |
| A gate that blocks on noise | goal 1 | checklists name only rule-ID checks; advisory capped, three real findings first |
| Planned commands named in skill text fail the doc test | red test | this plan and spec name commands by stage, never as a slash code span; each R commit runs the full pytest, green |

## Assumptions
- Settled in R1 from the docs (2026-11-12): `${CLAUDE_PLUGIN_ROOT}` expands in skill content (ADR-005); `claude -p
  --plugin-dir` exists; a forked skill called through the Skill tool returned its verdict to the calling skill in every run.
- Verification uses synthetic neutral briefs in the scratchpad, never inside this repo (`articles/` is protected, PLG-1).
- Skill directories follow the existing `PLANNED` names: `intake-brief`, `research`, `outline`, `check-*`.
- Actors do not publish Doc copies until Phase 7. One draft PR on `feat/phase-3-vertical-slice` (A4); plan ships in it.
- Gates use `model: opus`, as `plan-gate` does. `.serena/` is never committed.
- Not verified in the PR: a real client brief (needs a human), Doc copies, hook enforcement of FLOW-1/FLOW-2.
