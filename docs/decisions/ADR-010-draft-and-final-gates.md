# ADR-010 — The draft and final stages: one G4 gate, a lint record the gate reads, and a mechanical sign-off

- **Date:** 2026-11-13
- **Status:** accepted
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (`docs/features/phase-5-draft-edit-gates/plan.md`)
- **Refines:** ADR-008 (the marker reaches the final and stops the sign-off here) and ADR-009 (decision 5: no gate calls `prose-lint`).

## Context
Phase 5 adds the draft stage, the edit stage, G3 and G4. DESIGN open question 3 asked whether G4's fact, voice and SEO checks
must be fanned out by the orchestrator because a forked gate may not spawn subagents. ADR-008 promised that the final stages carry
markers through and refuse sign-off while one remains. G4 also needs the mechanical lint findings, and a forked gate has no
shell and cannot compute a hash.

## What was verified first (D4, 2026-11-13)
- Claude Code's docs: a skill's `allowed-tools` takes space-separated rules; a `*` before the rest of a Bash command is flagged,
  so the rule is `Bash(python3 ${CLAUDE_PLUGIN_ROOT}/bin/prose-lint.py *)`, and `${CLAUDE_PLUGIN_ROOT}` is substituted in plugin
  skills in `allowed-tools` and in the body.
- `fact-gate` opened ten public sources, checked the lint record, voice and SEO in one forked run in about a minute and a half of
  wall time, inside `maxTurns: 40`; the earlier research gate on a 25-fact bank also finished.

## Decision
1. **G3 is `check-draft` on the `gate` agent** (no web). Rules: STR-1, STR-2, STR-5, STR-6 (advisory only: it has no shell to count
   words), SEO-4, FACT-1, FACT-5 (against the bank row), BRF-5. Line 3 is `Outline: <a> of <m> sections present`. SEO-4 is judged
   here, the one gate that sees the draft against the brief; after this phase it is no longer ungated.
2. **G4 is one forked gate, `check-final`, on `fact-gate`, working sequentially; there is no fan-out** (resolves open question 3).
   Rules: FACT-1 to FACT-5, STR-4, STR-6, VOI-1 to VOI-5, SEO-1, SEO-2, SEO-3, SEO-5, FLOW-6. Line 3 is `Markers: <n>`.
   The bank's row metadata was judged by G1, so at G4 it is one advisory finding for all rows, never ten blocks. A missing style guide
   lists VOI-1, VOI-4 and SEO-5 under Not checked, non-blocking.
3. **The lint record carries the findings.** `prose-lint.py --record` writes `lines` (the printed findings) beside `file`, `sha256`,
   `findings` and `at`. G4 reads them; no gate runs the script. **This replaces ADR-009 decision 5's mention that the G4 gate calls
   prose-lint.** The alternative, a scoped Bash tool on `fact-gate`, was rejected: it puts a shell in a gate (FLOW-4).
4. **Four guard rules (`guard-stage-order`)**, one set for the tests and this record:
   (1) a G4 verdict, PASS or BLOCK, is saved only against a `.prose-lint.json` whose hash equals `final.md` (approval lines ignored), so the lint the
   gate read is current by construction; (2) no tool writes `.prose-lint.json`, only the script does (a hook sees tool calls, not the
   script's own write); (3) a Write or Edit giving `final.md` a non-empty `Signed-off-by:` (the last such line outside a code fence) needs G4's latest verdict to be a PASS
   whose recorded hash equals the hash of the **resulting** content (for Edit: the file with `old_string` replaced, every occurrence
   with `replace_all`) and its upstream chain current; paths are compared in lower case (case-insensitive filesystems); (4) no unverified-claim marker (loose pattern) may remain beside a non-empty
   `Signed-off-by:`. An unresolvable Edit is allowed and says so on stderr (fail open).
5. **The actors.** `draft` writes from the approved outline, tags facts, copies outline markers unchanged, lints without `--record`
   and fixes before the gate. `edit` (folder `edit-final`) line-edits into `final.md` with front matter, freezes fact IDs and markers,
   fixes lint findings with plain runs, then runs `--record` as its last action on `final.md`. Both back up a replaced file as
   `draft.prev.<n>.md` / `final.prev.<n>.md` and report a cleared sign-off. Neither writes `Approved-by:` or `Signed-off-by:`.
6. A marker is not a BLOCK at G3 or G4; at G4 it is counted and listed under "Sign-off holds".

## Rejected alternatives
| Alternative | Why not |
|-------------|---------|
| Fan G4 out into fact, voice and SEO subagents | Not needed: one run fits the turn budget, and one agent keeps one verdict |
| A scoped Bash tool on the gates | A shell in a gate; FLOW-4 is a mechanism, not a request |
| Block a sign-off only when the file on disk matches the verdict | A body change carried in the same write would slip through; the check uses the resulting content |
| Judge STR-6 by counting at G3 | `gate` cannot count; a miscount would be a false BLOCK. The lint record enforces it at G4 |

## Consequences
- Positive: FLOW-6 and the lint trust path are mechanical for tool writes; G4 cannot pass on a stale lint.
- Known gaps: a shell write to `final.md` (the parser sees paths, not content), a `Signed-off-by:` a human types in an editor, a
  caller who fabricates a verdict file (ADR-004's trust model), and a gate with no sidecar being trusted as legacy (ADR-009).
- Follow-ups: the orchestrator (Phase 6), Doc copies and comment sync (Phase 7).

## Revisit when
G4 runs out of turns on a long article, or a hook payload changes in a Claude Code release.
