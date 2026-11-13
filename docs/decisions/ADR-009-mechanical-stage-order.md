# ADR-009 — Stage order, verdict immutability and the final lint are enforced by hooks

- **Date:** 2026-11-13
- **Status:** accepted
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (`docs/features/phase-4-hooks/plan.md`)
- **Refines:** ADR-004 (verdict file) and ADR-007 (a verdict covers its artifact). One ADR-004 clause is replaced, named below.

## Context
FLOW-1 (a stage starts after the previous gate's PASS), FLOW-2 (no draft without an approval), FLOW-3 (two BLOCKs stop a stage),
FLOW-4 (gates never edit; saved verdicts are never edited) and FLOW-6 (no marker in a final) were requests made in skill text.
Two open questions were left for this phase: what a human's hand edit before approval does to a verdict (DESIGN question 5)
and what a rebuilt upstream artifact does to the verdicts after it (question 6).

## What was verified first (D4, 2026-11-13)
A throwaway probe plugin logged real hook payloads in a headless session (`claude -p --plugin-dir`):
- `Write` has `file_path` and `content`; `Edit` has `file_path`, `old_string`, `new_string`, `replace_all`; `Bash` has `command`.
  **`MultiEdit` does not exist in this build.** A Bash redirect fires only a Bash event: no Write event, so the guard parses Bash.
- Exit 2 with the reason on stderr blocks the call and the message reaches the agent. `PostToolUse` fires after a successful Write.
- `CLAUDE_PROJECT_DIR` and `CLAUDE_PLUGIN_ROOT` are set for hooks and `cwd` is the workspace. SessionStart has `source`
  (`startup`, and `resume`, `clear`, `compact`); Stop has `stop_hook_active`.

## Decision
1. **A verdict sidecar.** When the Write tool saves `gates/G<n>-<stage>.r<k>.md`, a PostToolUse hook (`record-verdict`) writes
   `gates/G<n>-<stage>.r<k>.json` beside it: `{"artifact_sha256": …, "upstream": <file name of the latest verdict of the gate before it>}`.
   The hash is taken with the `Approved-by:` and `Signed-off-by:` lines removed (the human writes them after the PASS, ADR-007).
2. **The guard (`guard-stage-order`, PreToolUse on Edit, Write and Bash)** blocks:
   - FLOW-1: writing research, outline, draft or final unless the previous gate's latest verdict (highest `r<k>` in `gates/`) is a PASS
     on ADR-004's line 1, and, walking up the chain, each verdict's recorded `upstream` is still the latest verdict of its upstream
     gate (question 6) and each recorded hash is still the artifact's hash (question 5);
   - FLOW-2: a draft while `Approved-by:` in the outline has no value;
   - FLOW-3: a stage whose own gate has two BLOCK verdict files (`brief.md` is guarded for this alone);
   - FLOW-4: editing or overwriting a saved verdict; creating one by any tool but Write; a number other than one past the highest
     in `gates/` and `gates/archive/`; a bad line 1 or a gate that does not match the file name; any tool writing a sidecar or
     anything else in `gates/`; every shell write, move, copy or delete in `gates/`.
   No file modification time is used.
3. **Legacy and migration.** A gate none of whose verdicts has a sidecar predates the hooks: its hash and upstream checks are skipped.
   Once any verdict of a gate has a sidecar, that gate's latest verdict must have one. An article in flight keeps working; a gate gains
   hand-edit protection at its first recorded verdict. Rolling the plugin back leaves the sidecars as ignored files.
4. **Re-gating a hand edit (question 5)** needs no new skill: any caller (an actor, or the main agent on a human's request) saves a
   rerun of the gate on the edited artifact with the Write tool as the next verdict, and the hook records its hash.
   **This replaces ADR-004's "only an actor-saved verdict counts for FLOW-1"** with "a verdict counts if it was saved by the Write
   tool, validated by the guard and recorded by the hook". "A gate run on its own is not recorded" stays: its printed output counts only once saved.
   A re-gate saves its verdict whether PASS or BLOCK and a BLOCK counts toward FLOW-3. The three stage skills' save step and the
   outline skill's Step 6 say so.
5. **`prose-lint.py` is a script, not a hook.** It prints `RULE path:line message`, exits 0 or 1, and writes `.prose-lint.json`
   (`{file, sha256, findings, at}`, the same approval-ignoring hash) only with `--record`, so a gate that calls it stays write-free.
   Checks: STR-4, STR-6 (new rule: the article's length is within the brief's target ±10%), FACT-1 (a number with no `[F#]`, a heuristic)
   and, for a final, SEO-1, SEO-2, SEO-3, VOI-2, VOI-3 and FLOW-6 (a marker left in the text, with the loose pattern). A `final.md` begins with
   front matter: `title:`, `meta_description:`, `slug:`.
6. **`verify-final` (Stop)** blocks once per article and session when `final.md` was written after the session started and no
   `.prose-lint.json` matches its hash. The session start comes from `session-context` (SessionStart), which records it once in a
   temp-dir file keyed by session id and prints at most 30 lines on where each article is. Both are silent outside a workspace.
7. A hook that hits an unexpected error allows the action and says so on stderr: a false block costs a writer a turn.

## Rejected alternatives
| Alternative | Why not |
|-------------|---------|
| Compare file modification times for staleness | A copy or a checkout reorders them; the approval edit would also trip it (ADR-007) |
| Match `mcp__.*` tools too | A read tool with a path argument would be blocked; MCP writes into `articles/` are not expected |
| Let the guard also match `MultiEdit` | It does not exist in this build; the matcher lists only tools that exist |
| Record the lint run on every `prose-lint` call | A gate that calls it would change the workspace (FLOW-4) |

## Consequences
- Positive: stage order, verdict immutability and the final lint stop depending on the skills following their text; a stale or hand-edited
  upstream is caught before the next stage; ADR-007's rule is now partly mechanical.
- Accepted cost and known gaps: shell writes the parser cannot read (`python -c`, command substitution), MCP tools, a caller who saves only a
  PASS from a re-gate (the same trust model as ADR-004), and a gate with no verdict sidecars is trusted as legacy.
- Follow-ups: the draft, edit and final-gate stages (Phase 5) carry markers through and use `--record`.

## Revisit when
A hook payload changes in a Claude Code release, or a sidecar is seen to be wrong or missing for a verdict saved by Write.

Refined by ADR-010: no gate runs `prose-lint` (decision 5); the recorded run also keeps the finding lines, and the guard gains four rules for the G4 save, the record and the sign-off.
