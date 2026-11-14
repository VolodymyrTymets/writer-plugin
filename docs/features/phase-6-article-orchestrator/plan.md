# phase-6-article-orchestrator — implementation plan

Build-plan Phase 6 (`docs/DESIGN.md`): the `article` skill, which runs the whole chain with the two human checkpoints. No
tracker, so the slug stands in for a ticket ID. Branch `feat/phase-6-article-orchestrator` off `main`, one draft PR, one commit
per requirement.

## Open for the approver (your approval covers these)
1. **The orchestrator never writes a human line.** At each checkpoint it stops and the human writes `Approved-by:` or
   `Signed-off-by:` in the file, then reruns the `article` skill. Rejected: asking in chat and writing the name, because a
   decision made in chat does not count and the outline actor's rule ("never fill it yourself") would get a second, weaker form.
2. **Dispatch comes from a new script, `bin/article-status.py`,** that reuses `describe_article`'s logic as a structured
   `article_state()` in `bin/lib/writer.py`. This changes a shared hook helper; the session briefing text stays identical except two deliberate changes,
   pinned first by exact-string characterisation cases (R1). Recorded in ADR-011.
3. **`tests/test_structure.py` (ask-first)** is edited only to move `article` from `PLANNED` to `COMMANDS`; no check changes.

<!-- A human writes this line to approve. Until it is here, guard-plan-approval blocks writes to code. -->
Approved-by: Volodymyr - 2026-11-14

Pattern followed: `skills/edit-final/SKILL.md` and `skills/draft/SKILL.md` (resolve the slug, read preconditions from disk, call a
skill through the Skill tool, stop and name files), `bin/prose-lint.py` (a stdlib script a skill runs via a scoped `Bash(...)`
rule, ADR-010), `bin/lib/writer.py:describe_article` and `bin/session-context.py` (state read from files, never from memory),
`tests/test_hooks.py` (`ws` fixture, the parametrised session-context states), `tests/test_skills.py` (contract text tests).
No skill dispatches other skills yet: that is the new pattern ADR-011 records.

## Contract changes (decisions go in ADR-011)
- **New CLI surface, additive:** `python3 bin/article-status.py <slug>` (run from the workspace root, or with `--root <dir>`) prints one
  JSON object `{"slug", "stage", "next", "reason", "markers", "stale"}` and exits 0. `next` is one of: `brief`, `research`,
  `outline`, `draft`, `final` (run that stage's actor), `approve` (wait for `Approved-by:`), `sign-off` (wait for
  `Signed-off-by:`), `stopped` (FLOW-3), `stale` (a verdict no longer covers its artifact), `done`, `unknown` (the script failed;
  `reason` says why). `stale` is a boolean that is true exactly when `next` is `stale`. `markers` is the **list** of markers found with
  the guard's own loose pattern `w.MARKER_LOOSE` (each entry matched by `re.compile(MARKER_LOOSE.pattern + r'[^>\n]*>?')`, built from the guard's pattern, never a second one, so a
  malformed marker the guard would refuse is listed too), from the artifact at the article's current stage, falling back final → draft → outline (refined in R1: a rule of
  "`final.md` once it exists" let a leftover final speak for a rebuilt outline); empty list when none.
  The briefing count is `len(markers)`.
  Read-only: it writes no file, so the guard needs no rule for it.
- **Precedence of `next`, first match wins:** (1) `unknown` (the script failed); (2) `stopped` (any gate with two BLOCKs);
  (3) `stale` (whenever `check_gate` on the last passed stage returns a reason, whatever else holds); (4) a single BLOCK or an
  artifact with no verdict → that stage's actor; (5) `approve`, `sign-off`, `done`, or the next missing stage's actor.
  `article_state` uses the guard's own helpers, `w.APPROVED` and `w.is_signed` (fence-aware), never a second regex, so the
  orchestrator cannot call an article done that the guard treats as unsigned.
- **Shared helper refactor:** `article_state(root, slug) -> dict` in `bin/lib/writer.py`; `describe_article` formats it. Marker
  count reads `final.md` once it exists, else `outline.md` (today only the outline is read; the briefing line for a final with a
  marker gains the count, deliberate change 1, pinned by its own exact-string case with a `WHY:` line). Sign-off detection moves
  from a raw regex to `w.is_signed` (a fenced trailer in the body no longer reads as signed): deliberate change 2, pinned the same way.
- **Stage → actor map** lives in the skill and is pinned by a test against `ACTORS`: `brief` → `writer-plugin:brief`,
  `research` → `writer-plugin:research`, `outline` → `writer-plugin:outline`, `draft` → `writer-plugin:draft`,
  `final` → `writer-plugin:edit`. The test maps `ACTORS` (keyed by directory) through `COMMANDS` to these command names.
- Frontmatter: `skills/article` `name: article`, `allowed-tools: Read, Glob, Grep, Skill, AskUserQuestion,
  Bash(python3 ${CLAUDE_PLUGIN_ROOT}/bin/article-status.py *)`. No Write: the orchestrator itself writes nothing. (`allowed-tools`
  pre-approves; it does not remove tools from the actors it loads. R0 checks this, so the plan claims no mechanism from it.)

## Requirements (ordered)

### R0 — Verify nesting and permissions (S)
- **Result (2026-11-14, throwaway probe plugin in the scratchpad, `claude -p --plugin-dir`, default permission mode):** a skill A
  (`allowed-tools: Read, Skill`) invoked skill B through the Skill tool; B ran its scoped `Bash(python3 ${CLAUDE_PLUGIN_ROOT}/bin/hello.py *)`
  rule and a `Write`, both pre-approved while nested (`permission_denials: []`), then invoked forked skill C (`context: fork`,
  `background: false`, a Read/Glob agent), whose verdict line came back to B and then to A. So nested actor → forked gate works, and
  the actor's own `allowed-tools` apply under the orchestrator. A second skill with `allowed-tools: Read` still attempted `Write`; it
  was refused by permissions (`permission_denials: [Write]`), not removed: **`allowed-tools` pre-approves, it does not restrict.** The
  plan claims no mechanism from the orchestrator's `allowed-tools`, as written. No repo change. Original text follows.
- D4, docs via Context7, then a throwaway probe plugin in the scratchpad (`claude -p --plugin-dir`): a skill A calls skill B through
  the Skill tool, B calls a forked skill C with `background: false`. Check that C's verdict comes back to B, that B's
  `allowed-tools` (a scoped `Bash(...)` rule) applies while B runs inside A, and how `allowed-tools` behaves (pre-approval vs
  restriction). If nested Skill calls do not work, stop and report before R1 (B4): actors would have to run differently, which
  changes the plan. Record the result here, as Phase 5 did.

### R1 — `article_state()` and the status script (M)
- **Done note (2026-11-14):** a third deliberate briefing change, found while writing the tests: a gate with two BLOCKs is
  `stopped` whatever its latest verdict, as the guard's FLOW-3 rule already does (`bin/guard-stage-order.py:85`); before, the
  briefing only said STOPPED when the latest verdict was a BLOCK. Pinned as state `two-blocks-then-pass` with a `WHY:` line.
  Slugs that are not one folder name (`..`, `/`) give `unknown`: the slug becomes a path.
- files: `bin/lib/writer.py` (change: `article_state`, `describe_article` built on it), `bin/article-status.py` (new),
  `tests/test_hooks.py` (new cases)
- layer: hook library + stdlib script
- test, step 1 (before any refactor): a characterisation case per state below asserting the **full string** `describe_article`
  returns on today's `main`; commit it green. The existing substring cases stay as they are (B3).
- test, step 2 (red first): one parametrised table over the states the session-context test already builds (no slug folder, brief only,
  each gate missing, one BLOCK, two BLOCKs, stale, approved, unapproved, final passed unsigned, signed, markers in outline, marker in
  final, stale + unapproved → `stale`, stale + next artifact missing → `stale`, fenced `Signed-off-by:` in the body → `sign-off` not
  `done`, a malformed marker in `final.md` → listed in `markers` and `next` is `sign-off`) asserting `next`, `stage` and `markers`, plus `reason` for
  `stopped` names both verdict files and says "archive", and `reason` for `stale` equals what `check_gate` returns; the step-1 strings still hold except the two deliberate changes; the script prints valid JSON and exits 0, prints `next: "unknown"` with a `reason` when the listing fails (`articles` made a regular file in `tmp_path`, not `chmod`, so it
  holds under root in CI), and writes no file
  (directory listing before and after).
- executed how: run `python3 bin/article-status.py <slug>` on a scratchpad workspace at each of five states (empty, after G2 unapproved,
  approved, G4 PASS unsigned, two G3 BLOCKs) and paste the JSON; start a `claude -p --plugin-dir .` session there and confirm the
  briefing text matches the script.
- risk: the refactor changes briefing output; the step-1 exact-string cases catch it.

### R2 — The `article` skill (M)
- files: `skills/article/SKILL.md` (new), `tests/test_structure.py` (move `article`), `tests/test_skills.py` (new `ORCHESTRATOR`
  contract tests)
- layer: skill
- shape: Step 1 resolve slug (and the brief input when there is no `brief.md`, passed through to the brief actor). Step 2 loop:
  run the status script; on `brief|research|outline|draft|final` invoke the mapped actor with the slug and wait; after it returns, run
  the script again; if `next` did not move past the stage it just ran, stop and report the actor's outcome (never call the same actor
  twice in a row, so a BLOCK loop stays inside the actor and FLOW-3 is never raced). On `approve` / `sign-off` stop with the exact
  human instruction (file, line, rerun the `article` skill), listing markers; on `sign-off` with markers, say FLOW-6 refuses the
  sign-off until they are resolved. On `stopped`, `stale`, `unknown` stop and quote `reason`. On `done` say so. Never write a file,
  a verdict or a human line; never move a verdict; on a guard block, stop and report it. Final report: stages run this call, verdict
  paths, markers, what the article waits for. "Doc copy: not yet available".
- test: the skill names each actor in the map and the map matches `ACTORS`; it calls the status script by `${CLAUDE_PLUGIN_ROOT}`;
  it says it never writes `Approved-by:` or `Signed-off-by:`; it stops on `approve`, `sign-off`, `stopped`, `stale`, `unknown`; it
  never calls the same actor twice in a row; frontmatter has no Write or Edit in `allowed-tools`.
- executed how: scratchpad workspace with a synthetic neutral brief complete enough that the brief actor asks nothing (headless
  `claude -p` cannot answer AskUserQuestion), `claude -p --plugin-dir .`: run the `article` skill → brief,
  research, outline run and it stops at approval (AC2); write `Approved-by:` by hand, rerun → draft and edit run, it stops at sign-off
  (AC3); seed two G3 BLOCKs → it stops and names them (AC4); hand-edit a passed outline → it stops on stale (AC5); sign off → `done`
  (AC7). Capture each transcript's final report.
- risk: a full chain in one context is long; resumability from disk means a new session continues with the same command.

### R3 — Docs and ADR-011 (S)
- files: `docs/decisions/ADR-011-article-orchestrator.md` (orchestrator dispatches from the status script, writes nothing, never
  writes a human line, actors inline, no auto-archive), `docs/DESIGN.md` (build plan row 6, Mechanical enforcement table gains
  `article-status.py`, the paragraph on the article command), `docs/ARCHITECTURE.md` (skills and `bin/` rows, a key flow line),
  `docs/DOMAIN_GLOSSARY.md` (Orchestrator, Status script), `README.md` (built commands line), `CONTRIBUTING.md` (its "Adding to this
  plugin" section gains the orchestrator kind), `CHANGELOG.md` (Deleted section first).
- executed how: full `pytest`, `claude plugin validate ./`, `git diff` scan for client names (PLG-1).

## Docs to update in this PR
- [ ] spec.md (ACs ticked) · ADR-011 · DESIGN.md · ARCHITECTURE.md · DOMAIN_GLOSSARY.md · README.md · CONTRIBUTING.md · CHANGELOG.md

## Risks
| Risk | Impact | Cheapest way to find out early |
|------|--------|-------------------------------|
| Nested Skill calls (orchestrator → actor → forked gate) do not behave like a direct actor call | The design falls over | R0 probe before any code |
| The `article_state` refactor shifts the session briefing | Writers see a different status line | existing session-context cases stay untouched and must pass |
| A long chain exhausts context mid-run | Run ends partway | state is on disk; the same command resumes; the executed run spans two sessions anyway (approval) |
| The orchestrator loops on an actor that keeps failing | Wasted turns, FLOW-3 raced | "never the same actor twice in a row" rule, pinned by a test |
| Client data in evidence | PLG-1 | synthetic neutral brief; scan diff and PR body |

## Assumptions
- `hooks/hooks.json`, the guard, the five actors and the five gates are not changed; `.claude/**` and `.claude-plugin/**` untouched; no version bump.
- An artifact whose gate never ran sends `next` back to that stage's actor (it backs up and rebuilds) rather than re-gating alone.
- Not verified in the PR: the brief actor asking questions under the orchestrator (needs an interactive session), Google Doc copies and comment sync (Phase 7), evals on the test briefs (Phase 7), a run on a real client brief (PLG-1).
- Estimate: R0 S, R1 M, R2 M, R3 S.
