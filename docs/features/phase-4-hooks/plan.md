# phase-4-hooks — implementation plan

Build-plan Phase 4 (`docs/DESIGN.md`): `guard-stage-order`, `prose-lint.py`, `verify-final`, `session-context`, hook tests;
and the two Phase 4 open questions (5: a human's hand edit before approval; 6: stale downstream verdicts). No tracker, so
the slug stands in for a ticket ID. Branch `feat/phase-4-hooks` off `main`.

<!-- A human writes this line to approve. Until it is here, guard-plan-approval blocks writes to code. -->
Approved-by: Volodymyr Tymets, in session 2026-11-13 ("approved", to the plan as committed at 1e80f73)

Pattern followed: `../rln-agent/bin/guard-plan-approval.py`, `session-context.py`, `verify-dod.py`, `bin/lib/util.py` and
`tests/test_hooks.py` (stdin JSON payload, stderr plus exit 2 to block, a small shared `lib/`, fixture repos).

## Goal
Ranked goal 1 and "a hook is a mechanism, a prompt is a request": FLOW-1, FLOW-2, FLOW-4 (verdicts are immutable, ADR-004),
FLOW-6 (no marker in a final) and a lint run before a final is done stop depending on the stage skills following their text.

## Contract changes (decisions go in ADR-009)
- **Verdict sidecar.** When a verdict file is written, a PostToolUse hook writes `gates/G<n>-<stage>.r<k>.json` beside it:
  `{"artifact_sha256": <hash of the artifact it judged>, "upstream": <file name of the latest verdict of the previous gate>}`.
  The hash ignores `Approved-by:` and `Signed-off-by:` lines (the human writes them after the PASS by design, ADR-007).
- **Guard (PreToolUse).** Writing `articles/<slug>/<stage>.md` for stage research, outline, draft or final is blocked unless
  the latest verdict (highest `r<k>` in `gates/`) of the previous gate (`G0-brief`, `G1-research`, `G2-outline`,
  `G3-draft`) is a PASS whose first line matches ADR-004 (FLOW-1); `draft.md` also needs a non-empty `Approved-by:` in
  `outline.md` (FLOW-2). Walking the chain back: each verdict's recorded `upstream` must equal the current latest verdict of
  its upstream gate (open question 6: a rebuilt upstream makes downstream verdicts stale), and each PASS's recorded hash must
  equal the current hash of its artifact (open question 5: a hand edit makes the verdict stale). The rule for a missing sidecar is
  **per gate**: a gate none of whose verdicts has a sidecar is legacy (it predates this phase) and its links are skipped; once
  any verdict of a gate has a sidecar, that gate's latest verdict must have one, or the write is blocked with a message to
  re-gate. Deleting or forging a sidecar is blocked (below), so a missing one means legacy or a hook failure. No file
  modification times are used. **Migration:** an article in flight keeps working (legacy gates are skipped, and a new verdict's
  recorded `upstream` is a file name, which a legacy verdict has too); hand-edit protection starts for a gate at its first recorded
  verdict, so a legacy gate gains it when re-gated. **Rollback:** reverting the plugin leaves the sidecars as ignored files. FLOW-3 is mechanical too: writing a stage's artifact is blocked while its own gate has two or
  more BLOCK verdict files in `gates/` (a human resumes by archiving, ADR-004).
- **Re-gating a hand edit (OQ5).** Any caller (an actor, or the main agent on a human's request) may save a rerun of the gate
  on the edited artifact as the next verdict by Write; the hooks validate it and record its hash. ADR-009 states which ADR-004
  clause this replaces: "only an actor-saved verdict counts" becomes "a verdict counts if it was saved by Write, validated and
  recorded by the hook"; "a gate run on its own is not recorded" stays (its printed output counts only once saved). A re-gate
  saves its verdict whether PASS or BLOCK and follows the existing two-BLOCK check; that a caller saves a BLOCK is still on the
  caller, the same trust model as today, and is listed as a known gap. ADR-004 and ADR-007 get a "Refined by ADR-009" line.
  The outline skill's Step 6 says how. No new skill.
- **FLOW-4 / ADR-004, made hard to get around.** An existing `gates/G*.r*.md` cannot be edited or overwritten; a new one may be
  created only by the Write tool (so the PostToolUse hook always fires), must have a valid line 1 and must be numbered
  `k` = 1 + the highest `r<k>` across `gates/` and `gates/archive/` (so an archive collision or a skipped number is blocked); every Bash write, `mv`,
  `rm` or `cp` into or out of `gates/` is blocked; no tool may write `gates/*.json` (only `record-verdict`, as a script, does).
- `brief.source*.md`, `outline.prev.*.md`, `.prose-lint.json` and everything outside `articles/` are never guarded; `brief.md` is
  guarded for the FLOW-3 check only (it has no predecessor gate).
- **`final.md` front matter** (needed by `prose-lint`, written by the edit stage in Phase 5): first lines `---`, `title:`,
  `meta_description:`, `slug:`, `---`.
- **`prose-lint`** is a script, not a hook: `python3 bin/prose-lint.py <file>` prints `RULE path:line message`, exits 0 or 1,
  and, only with `--record` (used by the edit stage), writes `articles/<slug>/.prose-lint.json` (`{file, sha256, findings, at}`; the hash is the same approval-line-stripped hash from `bin/lib/writer.py`, so writing `Signed-off-by:`
  does not make the record stale).
  Without the flag it writes nothing, so a gate that calls it stays write-free (FLOW-4).
- Stdlib only, Python 3.9. A hook that hits an unexpected error allows the action and says so on stderr (a false block costs
  a writer's turn). Tool matcher `Edit|Write|MultiEdit|Bash`: `mcp__.*` is dropped from DESIGN's row (an MCP read tool with a
  path argument would be blocked) and recorded as a known gap, as are shell writes the parser cannot read.
- `hooks/hooks.json` and `tests/test_structure.py` are ask-first paths: the first gets the new entries; the second is not edited.

## Requirements (ordered)

### R0 — Probe the real hook payloads (S)
- files: none in the repo. A throwaway probe plugin in the scratchpad logs stdin and exits 2 for a chosen path.
- executed how: `claude -p … --plugin-dir <probe>`: ask for an Edit, a Write, a MultiEdit and a Bash `echo > file`; record the
  payloads, whether the Edit/Write matcher fires for the Bash write, whether MultiEdit exists, and that exit 2 plus stderr
  blocks and the message reaches the agent. Also a Stop and a SessionStart event. Results go into ADR-009 (D4); if the docs
  and the build disagree the plan stops and is reported (B4).

### R1 — Shared lib, `guard-stage-order`, `record-verdict` (L)
- files: `bin/lib/writer.py` (new: payload, block, ADR-004 regex, artifact hash, verdict listing, chain check),
  `bin/guard-stage-order.py`, `bin/record-verdict.py`, `hooks/hooks.json`, `tests/test_hooks.py` (new)
- tests (red first), one for each of: an archive collision and a skipped verdict number blocked; a tool write to `gates/*.json` blocked; a Bash write of a new verdict blocked and a Write allowed; Bash `mv`/`rm`/`cp` in `gates/` blocked; a verdict without a sidecar blocked once any sidecar exists and allowed when none does; two BLOCK files block a stage write (FLOW-3); plus: table-driven over a throwaway workspace built in `tmp_path` (neutral synthetic articles): each stage allowed
  with a PASS and blocked with none, a BLOCK or a malformed line 1; FLOW-2 empty and non-empty `Approved-by:`; a stale upstream
  verdict; a hash mismatch; an approval-line-only edit allowed; verdict immutability; a new verdict with a bad line 1 blocked;
  a Bash redirect and `tee`/`cp`/`mv`/`sed -i` onto a guarded file, with reads still allowed (`ls`, `cat` and `grep` on `gates/`, `git status`);
  a legacy chain (no sidecars) plus one new G2 verdict allows the next stage; a gate whose r1 has a sidecar and whose r2 has none
  blocks; a legacy G2 verdict with a hand edit is allowed (documented); the block message for a move out of `gates/` says to
  archive by hand (ADR-004); a path outside `articles/`; bad JSON and an internal error
  fail open; `record-verdict` writes the sidecar with the right hash and `upstream`; the regex equals the one in `test_skills.py`.
- executed how: a real `claude -p` session in a scratchpad workspace with `--plugin-dir`: a write of `draft.md` with no
  approval is blocked with the message shown; with a G2 PASS and an approval it goes through; an edit of an existing verdict
  is blocked; a rebuilt brief makes a later write blocked as stale. Evidence: the block text and exit behaviour, not content.

### R2 — `prose-lint.py` (M)
- files: `bin/prose-lint.py`, `tests/test_prose_lint.py` (new), `tests/test_hooks.py` unchanged
- checks, all with rule IDs: STR-6 (new rule, added to `rules/core/CLAUDE.template.md` and the DESIGN table in this PR: the article's length is within the
  brief's target ±10%; a range uses its bounds), STR-4 one H1 and no skipped
  level, SEO-1/2/3 (final only: keyword in title, first 100 words and one H2; title at most 60; meta 120 to 155), VOI-2 and VOI-3
  from `.claude/rules/style.md` (skipped with one note when it is absent or the value is a `{{placeholder}}`), a number with no
  `[F#]` in the same sentence (FACT-1, heuristic: headings, URLs, list numbers ignored) and a marker left in `final.md`
  (FLOW-6, loose pattern `<Can.t be verified`).
- tests: one parametrised case per rule (a hit and a clean text), front matter parsing, the run record only with `--record`, exit codes.
- executed how: run it on a synthetic neutral draft and final: findings and exit 1, then a clean file and exit 0.

### R3 — `verify-final` and `session-context` (M)
- files: `bin/verify-final.py`, `bin/session-context.py`, `hooks/hooks.json`, `tests/test_hooks.py`
- `session-context` (SessionStart `startup|resume|clear|compact`): at most 30 lines on stdout, one per article in flight with its
  stage and what it waits for; records the session start in a temp-dir state file keyed by `session_id`, only if none exists yet (so `resume`, `clear` and
  `compact` do not move it).
- `verify-final` (Stop): a `final.md` written this session (modification time after the recorded session start) whose
  `.prose-lint.json` hash differs from its current hash blocks once, quoting the command with the script's absolute path (resolved from the hook's own location, since `bin/`
  is not in a workspace: ADR-005) and `--record`; a test asserts the quoted path exists; `stop_hook_active` or a second
  attempt allows (no loop).
- tests: output shape and the 30-line cap; the session start is not overwritten by a second SessionStart; a sign-off-only change to
  `final.md` allows Stop; a block once, then allow; `stop_hook_active`; a clean lint record allows; a
  `final.md` not touched this session is ignored.
- executed how: a headless session that writes `final.md` without linting is held once at Stop and quotes the command; a
  fresh session in a workspace with articles shows the summary.

### R4 — Docs, the outline text, and an end-to-end run (S)
- files: `docs/decisions/ADR-009-mechanical-stage-order.md` (D4 results, the sidecar, the guard rules, the open-question
  decisions and the known gaps), `docs/DESIGN.md` (hooks table, `final.md` shape, workspace tree, open questions 5 and 6
  resolved, the Phase 4 status), `rules/core/CLAUDE.template.md` (STR-6), `docs/decisions/ADR-004` and `ADR-007` ("Refined by ADR-009" lines), `docs/ARCHITECTURE.md`, `docs/DOMAIN_GLOSSARY.md`, `README.md`, `CONTRIBUTING.md`,
  `CHANGELOG.md`, `skills/outline/SKILL.md` Step 6 (how to re-gate a hand edit) and Step 4.3 of the brief, research and outline stage skills
  ("save the verdict with the Write tool", since a Bash save is now blocked), with text tests; ADR-009 lists those three skills as
  consumers of the changed verdict contract
- executed how: full `pytest` and `claude plugin validate ./`, then the real brief's approved outline (scratchpad copy): the
  sequence (1) the draft write is allowed (the Phase 3 verdicts are legacy, so the checks are skipped); (2) a G2 re-gate is saved by Write,
  which records the first sidecar, and the draft write is still allowed; (3) after a one-word hand edit it is blocked; (4) after
  a saved rerun verdict it is allowed again. Counts and block text only (client data, PLG-1).

## Docs to update in this PR
- [ ] ADR-009 · DESIGN.md · ARCHITECTURE.md · DOMAIN_GLOSSARY.md · README.md · CONTRIBUTING.md · CHANGELOG.md

## Risks
| Risk | Impact | Cheapest way to find out early |
|------|--------|-------------------------------|
| A guard false-blocks a legitimate write | a lost writer turn | fail open on errors; table-driven tests; R1's real session |
| The hook payload differs from the docs (MultiEdit, Bash) | a hole or a false block | R0 probes the real build first |
| Shell writes the parser cannot read | the guard is bypassed | stated as a known gap; the stage skills still follow their text |
| `prose-lint` noise (number heuristic) | findings writers learn to ignore | tests pin the ignored forms; the run record only needs a run, not zero findings |
| Client data in evidence | PLG-1 | neutral fixtures in tests; for the real brief only counts and block text; scan the diff, plan and PR body for its names |

## Assumptions
- One draft PR with one commit per requirement; `.serena/` is never committed. No version bump (the maintainer decides at release).
- Not verified in the PR: the draft, edit and final-gate stages (Phase 5), shell writes beyond the parsed forms, `mcp__` tools, and a
  caller who saves only a PASS and not a BLOCK from a re-gate (the same trust model as ADR-004).
