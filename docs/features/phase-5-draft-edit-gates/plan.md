# phase-5-draft-edit-gates — implementation plan

Build-plan Phase 5 (`docs/DESIGN.md`): the `draft` skill, the `edit-final` skill, the `check-draft` gate (G3), the `check-final` gate (G4), and open question 3. No tracker,
so the slug stands in for a ticket ID. Branch `feat/phase-5-draft-edit-gates` off `main`, one draft PR, one commit per requirement.

## Open for the approver (your approval covers these)
1. **Lint access for G4.** I assume the record-lines route below (Contract changes), which replaces ADR-009 decision 5 ("the G4 gate calls prose-lint")
   and DESIGN's hooks row. The alternative is a scoped Bash tool on `fact-gate`; I reject it because it puts a shell in a gate (FLOW-4).
2. **`tests/test_structure.py` (ask-first)** is edited only to move four entries from `PLANNED` to `COMMANDS`; no check changes.
3. **Guard rule (2) of R3: `.prose-lint.json` is protected.** Only `prose-lint.py --record` may write it; Write, Edit and parsed Bash writes
   are blocked, with a message naming the command. This changes a pinned case (`tests/test_hooks.py:302` lists the path as allowed): that
   case moves to a new test where the write is blocked. Stricter, not weaker (B3), and recorded in ADR-010.
4. **Guard rules (3) and (4) of R3: sign-off needs G4 and no marker.** The guard blocks a tool write of a non-empty `Signed-off-by:` unless G4's latest verdict is a PASS whose
   recorded hash equals the hash of the **resulting** content (so a body change on a signed-off final is blocked) and no marker remains. A sign-off a human types in an editor
   triggers no hook: a known gap, stated in ADR-010; FLOW-6 and AC7 cover tool writes.
5. **SEO-4** (matches the search intent) is judged at G3, the one gate that sees the whole draft against the brief.

<!-- A human writes this line to approve. Until it is here, guard-plan-approval blocks writes to code. -->
Approved-by: Volodymyr Tymets, in session 2026-11-13 ("approved, go ahead", to the plan and its five approver items)

Pattern followed: `skills/outline/SKILL.md` and `skills/intake-brief/SKILL.md` (actors), `skills/check-outline/` and
`skills/check-research/` (gates, with `references/checklist.md`), `tests/test_skills.py` (`GATES`, `ACTORS`, `MUST_CITE`),
`bin/guard-stage-order.py` plus `bin/lib/writer.py` and `tests/test_hooks.py` (hooks), ADR-004, ADR-007, ADR-008, ADR-009.

## Goal
Ranked goal 1: judge the article twice by different editors (G3 structure and argument, G4 facts against sources, voice, SEO,
length), and make FLOW-6 mechanical (no sign-off while a marker remains) as ADR-008 promised for this phase.

## Contract changes (decisions go in ADR-010)
- **G4 is one forked gate on `fact-gate`, sequential, no fan-out (open question 3).** A forked gate cannot be relied on to spawn
  subagents, and one agent keeps one verdict. G3 uses `gate` (no web). `fact-gate` keeps its tools; no Bash is added to any gate.
- **The lint record carries the finding lines.** `.prose-lint.json` gains `"lines": [<printed finding lines>]` beside
  `{file, sha256, findings, at}`; old records without it are read as unknown. A gate cannot run a script or compute a hash, so it
  reads the lines. **The guard** refuses to save a `G4-final.r<k>.md` unless `.prose-lint.json` exists and its `sha256` equals
  the current hash of `final.md` (approval lines ignored): the lint it reads is current by construction (AC8).
- **The lint record is protected.** The guard blocks Write, Edit and parsed Bash writes to `articles/<slug>/.prose-lint.json`; the script
  writes it itself (a hook sees only the tool call, not the script's own file write).
- **FLOW-6 mechanical.** The guard blocks a Write or Edit whose resulting `final.md` has a non-empty `Signed-off-by:` unless G4's latest
  verdict is a PASS whose sidecar hash equals `w.text_hash` of the resulting content, with its upstream chain current (`check_gate` for
  the gates above it), or while a loose marker (`<Can.t be verified`) remains. For Edit the result is the current file with `old_string` replaced (every occurrence when `replace_all` is true); if it cannot be computed the
  write is allowed and reported (fail open, as everywhere). **A parsed shell write to `final.md` is allowed by this rule** (the parser
  returns paths, never content): a known gap, pinned by a test and listed in ADR-010.
- **Verdict lines.** G3: `## G3 draft gate: …`, line 2 `Artifact:`, line 3 `Outline: <a> of <m> sections present` (for people).
  G4: line 3 `Markers: <n>` as G2. Line 1 is ADR-004's, unchanged (`VERDICT_LINE` already knows G3 and G4).
- **Backups.** A rebuilt draft or final is first copied to `draft.prev.<n>.md` / `final.prev.<n>.md` (`n` = 1 + highest, never
  replaced), as `outline.prev.<n>.md` (ADR-007). The guard matches exact stage file names, so `*.prev.*` is already unguarded
  (a test pins it). A cleared `Signed-off-by:` is reported.
- **Rules per gate.** G3: STR-1, STR-2, STR-5, STR-6 (advisory only), SEO-4, FACT-1, FACT-5 (against the bank row), BRF-5. G4: FACT-1 to FACT-5, STR-4,
  STR-6, VOI-1 to VOI-5, SEO-1, SEO-2, SEO-3, SEO-5, FLOW-6. A marker is never a BLOCK (ADR-008); in G4 it is counted on line 3
  and listed under "Sign-off holds".
- Frontmatter names (the command comes from `name:`): `skills/draft` `name: draft`, `skills/edit-final` `name: edit`, `skills/check-draft`
  `name: check-draft`, `skills/check-final` `name: check-final`.
- `tests/test_structure.py` (ask-first): only `draft`, `edit-final`, `check-draft`, `check-final` move from `PLANNED` to `COMMANDS`,
  each in the commit that adds its skill (R1, R2, R4, R5).

## Requirements (ordered)

### R0 — Verify the tool syntax and the G4 turn budget (S)
- **Result (2026-11-13, docs via Context7):** `allowed-tools` takes space-separated rules; a `*` before the rest of the command is flagged
  by Claude Code, so the form is `Bash(python3 ${CLAUDE_PLUGIN_ROOT}/bin/prose-lint.py *)`, which is substituted in plugin skills in both
  `allowed-tools` and the body (run the command unquoted, as written in the rule). Turn budget: the test article's G1 PASSed over 25 opened
  sources inside `maxTurns: 40`, so G4 stays one gate; R4 still measures it. Original text follows.
- D4: check against the Claude Code docs (Context7 or the docs site) that a skill's `allowed-tools:` accepts `Bash(python3 ${CLAUDE_PLUGIN_ROOT}/bin/prose-lint.py *)`
  (a wildcard inside the pattern), and read `w.bash_targets` to see how `prose-lint.py --record articles/<slug>/final.md` parses (it must
  not read as a write target of the guard). If the pattern is invalid, use the form the docs show and record it in ADR-010; if the docs and
  the build disagree, stop and report (B4). No repo change unless the form differs.
- Throwaway probe, scratchpad only: run `fact-gate` over a synthetic final with ten real public sources plus voice and SEO checks and count
  turns against `maxTurns: 40`. If it does not fit, stop and report before R1 (B4): the split of G4 changes the plan, not the code.

### R1 — G3 gate, skill `check-draft` (M)
- files: `skills/check-draft/SKILL.md`, `skills/check-draft/references/checklist.md`, `tests/test_structure.py` (move `check-draft`),
  `tests/test_skills.py` (`GATES`, `MUST_CITE`, a test that G3 reads outline and research and treats a marker as not a claim)
- shape: copy `check-outline` (`context: fork`, `agent: writer-plugin:gate`, `background: false`, Read/Grep/Glob). Checks: every
  outline row present in order with its H2/H3; no section beyond the outline; intro states the promise in 100 words; the close
  delivers the CTA; length is advisory only here (STR-6 is enforced at G4 from the lint record; `gate` has no shell to count words); SEO-4 the draft matches the search intent in the brief; every sentence with a number, date,
  name or quote has a `[F#]` that exists in `research.md` and that bank row supports it; no claim stronger than its row;
  must-include and must-avoid honoured. Not line edits.
- executed how: first `.venv/bin/python -m pytest tests/test_structure.py` is green (the plan and spec name no planned command in a
  code span); then `claude -p --plugin-dir .` in a scratchpad workspace with a synthetic neutral article: a clean draft gives PASS;
  a draft missing a section and one with a bare statistic give BLOCK STR-2 and FACT-1 with the line and a fix; an over-length draft is
  only advisory.

### R2 — actor, skill `draft` (M)
- files: `skills/draft/SKILL.md` (`allowed-tools: Read, Write, Glob, Grep, Skill, Bash(python3 ${CLAUDE_PLUGIN_ROOT}/bin/prose-lint.py *)`),
  `tests/test_structure.py` (move `draft`), `tests/test_skills.py` (`ACTORS`, FLOW-2 text, markers, backup, Write-tool save)
- shape: copy `outline`: resolve slug, FLOW-1 (G2 PASS), FLOW-2 (`Approved-by:` non-empty), FLOW-3 (G3 blocks), write section by
  section from the outline, every factual sentence tagged `[F#]` with IDs from the bank only, a marker copied unchanged where the
  outline has one (never rewritten, never explained), H1 = the outline's first title option; run `prose-lint.py` without
  `--record` and fix STR-4 or FACT-1 findings before the gate; backup rule; invoke `writer-plugin:check-draft`; save the verdict
  with Write; the ADR-007 "after the gate" block. Ends with "Doc copy: not yet available".
- executed how: scratchpad workspace with a G2 PASS and an approved outline whose cells hold one exact marker: the draft is written, the
  marker is in `draft.md` verbatim, and the G3 verdict is saved as `G3-draft.r1.md` with its sidecar (AC3); with `Approved-by:` empty the
  stage stops (AC2); with two `G3-draft.r*.md` BLOCK files seeded in `gates/` it stops and names both (AC9); rerun over an existing
  `draft.md` it creates `draft.prev.1.md` (AC10).

### R3 — Lint record lines and four guard rules (M)
The four rules, one set for ADR-010 and the tests: (1) a G4 verdict is saved only against a lint record whose hash matches `final.md`;
(2) only `prose-lint.py` writes `.prose-lint.json`; (3) a non-empty `Signed-off-by:` is written only against a current G4 PASS on the
resulting content; (4) no marker may remain beside a non-empty `Signed-off-by:`.
- files: `bin/prose-lint.py` (`record` writes `lines`), `bin/guard-stage-order.py`, `bin/lib/writer.py`, `tests/test_prose_lint.py`,
  `tests/test_hooks.py`
- tests (red first): `--record` writes the lines, and a run without the flag still writes nothing; a G4 verdict save is blocked with
  no record, a stale record (final changed), and allowed with a matching record, also after a sign-off-only change; a G3 save is
  unaffected; a Write, Edit or Bash write to `.prose-lint.json` is blocked and the script's own `--record` still works (the old
  allowed case at `tests/test_hooks.py:302` moves here); a Write or Edit giving `final.md` a non-empty `Signed-off-by:` is blocked
  with a marker, with no G4, with a G4 BLOCK and with a stale G4 PASS, and allowed with a current G4 PASS and no marker; an Edit with `replace_all` is resolved the same way as without; an Edit that changes the body of an already signed-off final is blocked, a sign-off-only
  change is allowed; a `sed -i` on `final.md` is allowed (the gap); an empty
  `Signed-off-by:` is always allowed; an Edit that cannot be resolved fails open; `draft.prev.1.md` and `final.prev.1.md`
  are not guarded.
- executed how: a real `claude -p` session in the scratchpad workspace: saving G4 with no lint is blocked and the message shown;
  after `prose-lint.py --record` it is allowed; writing `Signed-off-by:` onto a final with a marker or no current G4 PASS is blocked, and a hand-written `.prose-lint.json` is blocked (AC7, AC8).

### R4 — G4 gate, skill `check-final` (L)
- files: `skills/check-final/SKILL.md`, `skills/check-final/references/checklist.md`, `tests/test_structure.py` (move `check-final`), `tests/test_skills.py` (`GATES`, `MUST_CITE`,
  reads the record, opens sources, a FLOW-6 lint line is never blocking), `agents/fact-gate.md` only if its text must name G4 (no tool change)
- shape: `context: fork`, `agent: writer-plugin:fact-gate`. Step A reads `.prose-lint.json` and reports its `lines` by rule (an
  absent `lines` or a record the gate cannot tie to `final.md` goes under Not checked and counts as one blocking finding). Step B
  opens each source behind the `[F#]` IDs used in `final.md` and compares claim and quote (FACT-2, 3, 5; FACT-4 by the style guide's
  age limit). Step C: voice against `style.md` (VOI-1, 4, 5), SEO-1 to 3 and 5 from the front matter and links. Fact IDs are still in
  `final.md` (stripped only in the Doc copy). A `FLOW-6` lint line is counted on line 3 (`Markers: <n>`) and listed under "Sign-off holds", never a blocking finding (ADR-008). A missing `style.md` puts the VOI and SEO-5 checks under Not checked **without** a blocking finding (unlike an unopened source), or
  every workspace without one would be stopped by FLOW-3; one executed case has no style guide. Three real findings beat twelve.
- executed how: scratchpad workspace with one fact whose quote is not on a real public page: BLOCK FACT-3; a clean fact: PASS with
  line 3 `Markers: 0`; a final with a marker: PASS with `Markers: 1` (AC6, AC7). Count the turns used against `maxTurns: 40` for ten sources.

### R5 — actor, skill `edit-final` (M)
- files: `skills/edit-final/SKILL.md` (`allowed-tools: Read, Write, Glob, Grep, Skill, Bash(python3 ${CLAUDE_PLUGIN_ROOT}/bin/prose-lint.py *)`),
  `tests/test_structure.py` (move `edit-final`), `tests/test_skills.py` (`ACTORS`)
- shape: FLOW-1 (G3 PASS), FLOW-3 (G4 blocks); inputs: `draft.md`, the latest G3 verdict's advisories, `comments/*.md` if present
  (say once if absent), `style.md`; writes `final.md` with front matter (`title` of 60 or fewer, `meta_description` of 120 to 155,
  `slug`), a line edit that keeps every `[F#]` and every marker verbatim, and an empty `Signed-off-by:` line; fixes
  findings using runs of `prose-lint.py` **without** `--record`, then runs it with `--record` as the **last action on `final.md`**,
  with no write between it and the gate (a later write makes the record stale and the guard refuses the G4 save; a test pins this
  order; the script path comes from `${CLAUDE_PLUGIN_ROOT}/bin/`); invokes
  `writer-plugin:check-final`, saves with Write. Reports markers, says **the final is not signed off**, never writes the sign-off.
  A rebuild backs up as above. ADR-007 block; the "FLOW-6: holds while a marker remains" sentence.
- executed how: full chain in the scratchpad workspace from a G3 PASS to a G4 verdict saved, with a seeded lint finding fixed before
  the record; `verify-final` stays silent (AC5). With two `G4-final.r*.md` BLOCK files seeded it stops and names both (AC9). Rerun over a
  `final.md` with a filled `Signed-off-by:`: `final.prev.1.md` exists and the report says the sign-off was cleared (AC10).

### R6 — Docs and ADR-010 (S)
- files: `docs/decisions/ADR-010-…md` (G4 shape, lint lines, all four guard rules and their known gaps, backups), `docs/DESIGN.md` (build plan row 5,
  open question 3 resolved, workspace tree, hooks table, the Gates bullets and the Agents table: `gate` has no prose-lint), `docs/ARCHITECTURE.md`, `docs/DOMAIN_GLOSSARY.md` (lint record, backup),
  `README.md` (status, commands available), `CONTRIBUTING.md`, `CHANGELOG.md` (Deleted section first), ADR-008 and ADR-009 "Refined by ADR-010".
- executed how: full `pytest`, `claude plugin validate ./`, `git diff` scan for client names (PLG-1).

## Docs to update in this PR
- [ ] ADR-010 · DESIGN.md · ARCHITECTURE.md · DOMAIN_GLOSSARY.md · README.md · CONTRIBUTING.md · CHANGELOG.md

## Risks
| Risk | Impact | Cheapest way to find out early |
|------|--------|-------------------------------|
| G4 runs out of turns on a long article | Sources left under Not checked, a forced BLOCK | R4 run on ten sources, count turns; if short, G4 prioritises sources behind numbers and quotes, else stop and report (B4) |
| The lint-record guard false-blocks a legitimate G4 save | A lost writer turn | table-driven tests; fail open on error; the message names the command |
| Sign-off guard misses an Edit result, a shell write or an editor | Marker or ungated final signed off | known gap in ADR-010; prose-lint FLOW-6 and G4 line 3 remain |
| Prompt-only G3/G4 checks drift | A gate passes a wrong fact | contract tests pin must-cite rules; executed runs with a seeded fault for each gate |
| Client data in evidence | PLG-1 | synthetic neutral fixtures; real public pages only for G4 source opening; scan diff and PR body |

## Assumptions
- Test workspaces mock unverifiable facts so a flow test does not stall; the plugin itself stays strict.
- `hooks/hooks.json` is not changed (the guard handles the new rules); `.claude/**` and `.claude-plugin/**` untouched; no version bump.
- Not verified in the PR: Google Doc copies and comment sync (Phase 7), the `article` orchestrator (Phase 6), shell writes the parser cannot read, and a `Signed-off-by:` a human types in an editor (no hook sees it).
