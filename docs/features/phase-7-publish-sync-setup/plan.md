# phase-7-publish-sync-setup — implementation plan

Build-plan Phase 7 (`docs/DESIGN.md`). Three draft PRs, one commit per requirement, each branched off `main` after the previous merges:
`feat/phase-7a-setup`, `feat/phase-7b-publish-sync`, `feat/phase-7c-evals`.

## Open for the approver (your approval covers these)
1. **Split into 7a / 7b / 7c** (you chose this, 2026-11-14). 7b starts only after 7a merges; 7c after 7b.
2. **The 7b spike (R4) runs on your Drive.** You authenticate the Google Drive connector when R4 reaches it. The spike creates at most
   six throwaway Docs named `writer-plugin spike · <n>` from synthetic text, and you delete them afterwards.
3. **FLOW-6 becomes mechanical on the Doc title as well as on `docs.json` (R8).** It changes `bin/guard-stage-order.py` and its tests,
   and **`hooks/hooks.json` (ask-first)**: the guard's PreToolUse matcher gains the Drive create tool name that R4 records. It blocks a
   create whose title contains `publish-ready` unless `w.publish_ready(root, slug)` holds. If you decline the hooks.json change, ADR-012
   says the Doc title is prompt-enforced only and FLOW-6 is mechanical only for `docs.json`.
4. **`prose-lint.py` changes (R1):** a style-guide value of exactly `none` becomes an empty list.
5. **`tests/test_structure.py` (ask-first)** changes only to move `setup`, `publish` and `sync` from `PLANNED` to `COMMANDS`.
6. **Eval runs cost money**: each case is a full `claude` child. Dev runs use `--runs 1 --ablation none --no-publish` (the report stays local),
   with `--max-cost-usd` set from one measured case. I report the measured figure to you before the full suite runs. You answer the
   first run's plugin-trust prompt yourself; I never pass `--trust-plugin`.

<!-- A human writes this line to approve. Until it is here, guard-plan-approval blocks writes to code. -->
Approved-by: Volodymyr 2026-11-14

Pattern followed: `skills/intake-brief/SKILL.md` (fill a library template from user input in at most two batched rounds, no `{{` left;
the setup skill has the same shape), `skills/article/SKILL.md` + `bin/article-status.py` (a skill reads state from a read-only stdlib script,
never from memory: `bin/doc-copy.py` follows it), `bin/guard-stage-order.py` + `tests/test_hooks.py` (`ws` fixture) for the new guard rule,
and Phase 6 R0 (a throwaway probe before any code) for both spikes. `claude plugin eval` has no precedent here: ADR-013.

## Contract changes
- **Workspace files (7a), additive:** setup writes `CLAUDE.md` (from `rules/core/CLAUDE.template.md`, filling `{{PROJECT_NAME}}` and
  `{{STYLE_GUIDE_PATH}}` = `.claude/rules/style.md`) and `.claude/rules/style.md` (from `templates/style.md`). It never overwrites either file.
  Labels stay byte-identical to the template, because `prose-lint.py:style_list` parses `**Phrases:**` / `**Tells:**`.
- **`prose-lint.py` (7a), behaviour:** `style_list` returns `[]` for a value that is exactly `none` (case-insensitive), not `['none']`.
- **One definition of publish-ready (7b):** `w.publish_ready(root, slug)` is true exactly when `article_state(...)["next"] == "done"` **and**
  `final.md` has no `w.MARKER_LOOSE` match (a G4 PASS does not exclude markers, ADR-008, and a hand sign-off skips the guard).
  `bin/doc-copy.py` and the guard both call it; neither has its own copy.
- **`articles/<slug>/docs.json` (7b), new persisted format:** `{"revisions": [{"stage", "rev", "id", "url", "sha256", "title", "at",
  "publish_ready"}]}`, append-only. Written by the publish skill with Write, copying the script's fields unchanged. `rev` is per stage, 1 + the
  highest recorded. `sha256` is `w.artifact_hash(root, slug, stage)`: the on-disk artifact before fact IDs are stripped, approval lines
  ignored. It is never the hash of the uploaded text.
- **New CLI surface, read-only:** `python3 bin/doc-copy.py <slug> <stage> [--root DIR]` prints one JSON object
  `{text, sha256, rev, publish_ready, title, skip, existing_url}`. `text` is the artifact with fact IDs stripped, in the format R4 picks.
  `title` is `<slug> · <stage> · r<k>`, plus `· publish-ready` (final, `publish_ready`) or `· ungated` (no current PASS for that stage).
  `skip` is true when `sha256` and `title`, minus its `r<k>`, both equal the stage's last entry. So a sign-off or a later PASS on unchanged
  text still makes a new Doc, because `artifact_hash` ignores approval lines.
- **`articles/<slug>/comments/<stage>.r<k>.md` (7b):** a header (Doc id, revision, sha256, synced-at), then one block per comment: author,
  quoted anchor, text. Written by sync, and overwritten on a re-sync of the same revision.
- **Guard (7b), additive:** a Drive create call whose title contains `publish-ready` → block unless `w.publish_ready(root, slug)`, with the
  slug parsed from the title's `<slug> · final ·` prefix (no parsable slug → block). This is checked before the Doc exists, so no
  mislabelled Doc is ever created. For a Write or Edit to `articles/<slug>/docs.json`: a result that is not valid `{"revisions": [...]}` →
  block; an existing entry that is changed or removed → block. A new final
  entry with `publish_ready: true` needs `w.publish_ready(root, slug)` and `sha256 == w.artifact_hash(root, slug, 'final')`. A Bash write
  to `docs.json` → block, as for `.prose-lint.json`.
- **Actors (7b):** the step-6 line "Doc copy: not yet available" becomes: invoke `writer-plugin:publish <slug> <stage>` after a PASS, and
  report its URL or its "no Drive tool" line. Five actor files, one line each. The orchestrator's line (`skills/article/SKILL.md`) becomes
  "Doc copies: as each actor reported", and on `done` it tells the human to run the publish skill on the final for the publish-ready
  copy (README documents the same step). All six are pinned by one contract test.

## Requirements (ordered)

### 7a — setup
#### R1 — prose-lint reads `none` as an empty list (S)
- files: `bin/prose-lint.py` (`style_list`), `tests/test_prose_lint.py`
- test (red first): a style guide with `**Phrases:** none` and a final containing the word "none" gives no VOI-2 finding and no "no filled
  style guide" note; `None`/`NONE` behave the same; `none, foo` still lists both. G4's reading of `Internal links: none` is prompt-side
  (SEO-5); R2's run shows whether it needs a change, and if it does, I report it rather than widening this PR.
#### R2 — The setup skill (M)
- files: `skills/setup-workspace/SKILL.md` (new, `name: setup`, `allowed-tools: Read, Write, Glob, AskUserQuestion`),
  `tests/test_structure.py` (move `setup`), `tests/test_skills.py` (contract tests)
- shape: refuse in the plugin repo (AC4); list what exists and never overwrite it, writing only a missing file (AC3); read both library
  files through `${CLAUDE_PLUGIN_ROOT}`; take answers from `$ARGUMENTS` or a file, and ask any gap in at most two rounds; write both
  files; check for `{{`; report and point to the brief stage.
- test: the skill reads both library paths through `${CLAUDE_PLUGIN_ROOT}`; it says it never overwrites; it refuses on the plugin manifest;
  no Edit in `allowed-tools`; it names `.claude/rules/style.md` exactly as `prose-lint.py:find_style` does.
- executed how: a scratchpad workspace with `claude -p --plugin-dir . --permission-mode acceptEdits` (a `.claude/` write may need it; the run
  records which mode was needed), every answer in the prompt. Then: `grep -c '{{'` gives 0 on both files, and a one-line Python
  compares the template's rule-ID set with the written `CLAUDE.md` and prints equal (AC1); `prose-lint.py` on a seeded final reports
  VOI-2 for the banned phrase (AC2); a rerun leaves both sha256 unchanged, and deleting `style.md` then rerunning writes only that file
  (AC3); a run in a copy of this repo writes nothing (AC4); a second workspace answered `none` for phrases and links, with "none" seeded
  in its final, gives no VOI-2 finding. Paste the output.
#### R3 — Docs (S)
- `README.md` (built commands, status), `docs/DESIGN.md` (row 7: 7a done), `docs/ARCHITECTURE.md` (skills row; `rules/core` "will copy" →
  "copies"), `CHANGELOG.md`, `CONTRIBUTING.md` if it lists skills.
- executed how: full `pytest` and `claude plugin validate ./` (AC12); a `git diff` scan for client names (PLG-1).

### 7b — publish and sync
#### R4 — Spike: open questions 1–2 (S, on your Drive; first, before any 7b code)
- **Result (2026-11-14, claude.ai Google Drive connector in this Claude Code session, after `/mcp` sign-in; one spike Doc):**
  - **Q2, tools present:** yes, once signed in, as `mcp__claude_ai_Google_Drive__*`. Before sign-in only an authenticate tool exists, so
    publish must treat "no create tool" as the normal unsigned case (AC7). Real names and arguments:
    - `create_file(title, textContent | base64Content, contentMimeType, parentId?, disableConversionToGoogleType?)`. It returns
      `id`, `viewUrl` and `mimeType`; text converts to `application/vnd.google-apps.document` by default.
    - `read_file_content(fileId, includeComments)`.
    - `update_file` changes metadata only (title, parent, lock), never content. `trash_file` also exists.
  - **Q1, fidelity:** `contentMimeType: text/markdown` keeps H1/H2/H3, bulleted and numbered lists, bold, and both links (inline and
    autolink), checked by HTML export and by read-back. Inline code loses its monospace and stays as plain text. So `doc-copy.py` puts
    Markdown in `text`; no HTML or `.docx` converter is needed, and HTML was not tried.
  - **Comments:** `includeComments: true` returns `commentThreads[]`: `commentId`, `headPost` {`authorName`, `content`,
    `modifiedTime`}, `replies[]` and `status`. Anchors are inline in `fileContent` as `<comment_start id=X>anchor<comment_end id=X>`.
    An instruction-shaped comment arrives as ordinary `content`. Sync writes it as quoted data.
  - **Folder:** `create_file` takes `parentId`. A configurable folder stays a follow-up (Assumptions).
- **Added 2026-11-14 at the approver's request (review of PR #13):** Docs go into `articles/<workspace folder name>/<slug>/` in My
  Drive (an `articles` top folder keeps every workspace in one place; the approver's second remark), and titles stay full. Spike, same session:
  - `create_file(title, contentMimeType: application/vnd.google-apps.folder, parentId?)` makes a folder, and folders nest.
  - A Doc created with `parentId` lands in that folder.
  - `search_files` with `title = '<name>' and mimeType = 'application/vnd.google-apps.folder' and parentId = '<id or root>' and
    trashed = false` finds a just-created folder.
  - So `doc-copy.py` prints `folder_path` and the recorded `folder_id`; the skill finds or creates the two folders once and
    records the slug folder in `docs.json` (`"folder": {"id", "path"}`). Revisions stay append-only; the folder record is not FLOW-6.
- Authenticate; record the real tool names and arguments (rule D4). Upload one synthetic Markdown article as `text/markdown`, then
  `text/html`, read each back, and compare headings, lists and links. If neither keeps the structure, try a stdlib `.docx` (zipfile + XML).
  Check `read_file_content(includeComments: true)` on a Doc with one hand-added comment, and whether create takes a parent folder.
  Record the result here, as Phase 6 R0 did. The chosen format fixes what `doc-copy.py` puts in `text`.
- **Stop rule (B4):** if only a `.docx` works and it needs more than ~150 lines of stdlib code, stop and report before R5.
#### R5 — Helpers and `bin/doc-copy.py` (M)
- files: `bin/lib/writer.py` (`publish_ready`, `strip_fact_ids`, `docs_index`, `next_rev`, plus a converter only if R4 needs one),
  `bin/doc-copy.py` (new, read-only, modelled on `bin/article-status.py`), `tests/test_hooks.py`
- test: `[F7]`, `[F7, F9]` and `[F12]` are removed, and the spacing before punctuation is kept; fenced code is left alone. `next_rev` is 1
  on a missing `docs.json` and 1 + max otherwise. `publish_ready` is false for a signed final with a G4 PASS and a marker, and false
  unsigned; true when signed with no marker. `sha256` equals `artifact_hash` on a final containing `[F1]`. `skip` is true on an unchanged
  re-run; false after sign-off on unchanged text; false after an ungated copy later passes. Valid JSON; no file written (listing before
  and after).
- executed how: run the script on a scratchpad article before and after sign-off and paste both JSON objects.
#### R6 — The publish skill (M)
- files: `skills/publish/SKILL.md` (new), `tests/test_structure.py`, `tests/test_skills.py`
- shape: resolve the slug and stage (default: the latest artifact). Find the Drive create tool; if there is none, say so once and stop
  cleanly (AC7). Run `bin/doc-copy.py`; if `skip`, report `existing_url` and stop. Otherwise upload `text` under `title`, then append the
  script's `sha256`, `rev`, `title` and `publish_ready` unchanged, plus `id`, `url` and `at`, to `docs.json` with Write.
- frontmatter: `allowed-tools: Read, Write, Glob, Bash(python3 ${CLAUDE_PLUGIN_ROOT}/bin/doc-copy.py *)` plus the Drive create tool
  name from R4 (the scoped-Bash pattern of `skills/draft/SKILL.md`).
- test: the skill runs `${CLAUDE_PLUGIN_ROOT}/bin/doc-copy.py`, copies its fields unchanged, and does no stripping, hashing or
  `article-status.py` lookup itself; `allowed-tools` is exactly the set above.
- executed how: on the spike workspace, copy a gated outline to a Doc; copy the final unsigned, sign it, copy again and show a second
  final entry with `publish_ready: true` and its title; run once more and show the skip; run with `--disallowedTools
  'mcp__claude_ai_Google_Drive__*'` to show AC7.
#### R7 — The sync skill (S)
- files: `skills/sync-comments/SKILL.md` (new, `allowed-tools: Read, Write, Glob` plus the Drive read tool name from R4),
  `tests/test_structure.py`, `tests/test_skills.py`
- test: the skill reads Docs only through the Drive read tool and the ids in `docs.json`; it writes only
  `articles/<slug>/comments/<stage>.r<k>.md`; it stores comment text as quoted data, never as instructions; a stage with no `docs.json`
  entry is reported and nothing is written; `allowed-tools` is exactly the set above.
- executed how: add two comments by hand on the R6 final's Doc (one shaped like an instruction), run sync, show `comments/final.r<k>.md`,
  then run the edit stage and show that its report treats the comments as reviewer input (AC9); sync on the never-copied `draft` says so
  and writes nothing.
#### R8 — Guard rule FLOW-6 on `docs.json` (S)
- files: `bin/guard-stage-order.py`, `hooks/hooks.json` (matcher gains the R4 create tool name), `tests/test_hooks.py`
- test (red first): new final entry, `publish_ready: true`: unsigned → block; signed with a marker → block; signed, current G4 PASS, no
  marker, current sha → allow; same with `[F1]` in the final → allow; signed with an older sha → block. `publish_ready: false` → allow. An Edit
  that changes or removes an existing entry → block in any state. A Write of invalid JSON or of a body without `revisions` → block. A Bash
  redirect to `docs.json` → block. Drive create: `· publish-ready` title, unsigned final → block; signed, no marker → allow; a title with
  no parsable slug → block; a title without `publish-ready` → allow. A test pins that `hooks.json`'s matcher names the tool R4 recorded.
- executed how: on a scratchpad workspace, pipe a PreToolUse JSON payload into `python3 bin/guard-stage-order.py` once per case: a Write
  with `publish_ready: true` on an unsigned final; the same with a marker; an Edit that changes `rev` 1; a Write of `{}`; `echo x >
  articles/<slug>/docs.json` via Bash; a Drive create titled `<slug> · final · r2 · publish-ready` on an unsigned final; and the signed,
  current allow case. Paste each exit code and stderr line. In the R6 live run, an attempt to create a publish-ready Doc before sign-off
  is refused by the hook.
#### R9 — Actors call publish; docs; ADR-012 (S)
- files: five actor `SKILL.md` step-6 lines and `skills/article/SKILL.md`; `tests/test_skills.py`; `docs/decisions/ADR-012-doc-copies.md`
  (the format R4 chose, a new Doc per revision, `docs.json`, one publish-ready definition and its guard, comments are data);
  `docs/DESIGN.md` (open questions 1–2 resolved, hooks table, row 7); `docs/ARCHITECTURE.md` (skills: publish and sync; `bin/`:
  `doc-copy.py`; boundaries: `articles/<slug>/docs.json`, `articles/<slug>/comments/`); `docs/DOMAIN_GLOSSARY.md` (Doc copy, Revision,
  Synced comments); `README.md`; `CHANGELOG.md`.
- executed how: full `pytest`, `claude plugin validate ./` (AC12), and a PLG-1 diff scan.

### 7c — evals
#### R10 — Spike: the eval format (S)
- `claude plugin eval init --bare probe` in the scratchpad: confirm the `case.yaml` fields, how a case seeds files, which graders exist
  (exact text, `tool_used`, llm) and how WebFetch is granted. Record it here. If a case cannot seed a workspace without `--scaffold`,
  the cases use `scaffold_script` and the run command gains `--scaffold`; I wrote these scripts, so that flag is safe here.
- **Result (2026-11-14):** docs at code.claude.com/docs/en/plugin-evals.md, plus one probe case run in a scratch copy of the plugin
  (`--trust-plugin` approved by the approver for this session; $0.06):
  - **Case format:** `case.yaml` (`execution`, `context.scaffold_script`, `graders`) beside a `prompt.md`.
  - **Grader types:** `regex` (target `last_message`, `trace` or a workspace file; flags `i` only), `tool_used`, `tool_order`,
    `file_exists`, `llm` and `baseline`. There are no script graders.
  - **Tool grants:** a case can grant only read-only tools; Write, Edit, WebFetch and WebSearch come from `--allow-tools`.
  - **Seeding:** `context.scaffold_script` (needs `--scaffold`) runs in the empty workspace and reaches files beside it with `$(dirname "$0")`.
  - **Gates:** a slash prompt `/writer-plugin:check-brief demo` is expanded and **forks into `writer-plugin:gate`**. The Skill tool
    is not called, so gate cases check the fork with a `trace` regex on `subagent_type`, not with `tool_used: Skill`.
  - **Hooks:** plugin hooks run (the SessionStart briefing printed).
  - **Output:** the verdict is the run's last message, line 1 first.
  - **Seeding detail:** the gate wants `brief.source.md` beside `brief.md` and the folder named after the slug, so the cases seed both.
#### R11 — Synthetic briefs and gate cases (M)
- files: `evals/briefs/` (three public-topic briefs, e.g. HTTP caching, SQLite WAL mode, CSS container queries), `evals/<case>/` per case:
  G0 PASS ×3 (one per brief) and G0 BLOCK (no reader, BRF-1); G1 PASS and G1 BLOCK (the row's verbatim quote matches the page and only
  the claim column overstates it, FACT-5); G2 PASS (a clean
  outline) and G2 BLOCK (a claim with no fact ID, FACT-1); G3 PASS (a clean draft) and G3 BLOCK (a section off the outline, STR-2); G4 PASS
  (a clean, lint-recorded final on stable RFC/MDN sources), G4 BLOCK (a 72-character title, SEO-2) and G4 BLOCK (the final's quote differs
  from the row's verbatim quote, FACT-3); the brief actor once per brief, three cases, no question asked (AC11).
- graders: line 1 of the verdict matches PASS/BLOCK exactly, the expected rule ID appears, and the seeded defect is named (llm grader).
- test: `tests/test_structure.py` passes with `evals/` present (it scans every `.md`, eval prompts and graders included); a pytest checks
  that no eval file contains a `{{` placeholder or a non-public domain outside an allowlist (PLG-1).
- `.gitignore` gains `evals/results/` (transcripts never committed, A6); runs also pass `--output-dir` and `--report` into the scratchpad.
- executed how: first one G0 case alone to measure its cost, and the ceiling is set from that. Then `claude plugin eval ./ --runs 1
  --ablation none --max-cost-usd <measured> --no-publish --allow-tools WebFetch WebSearch` for the gate cases, and the same with
  `--case 'brief-actor-*' --allow-tools Write Edit Skill` for the three actor cases → paste both score tables. `--ablation none`: a
  no-plugin baseline means nothing for a gate verdict and would double the spend. An exit 1 (a case below `--threshold 1.0`) or exit 2
  (the ceiling) is reported with the score tables, never retried to get green.
#### R12 — Docs and ADR-013 (S)
- ADR-013 (evals: synthetic briefs only, gate-first, local and not in CI, cost flags); `docs/DESIGN.md` (Phase 0 briefs done, synthetic;
  row 7 done); `CONTRIBUTING.md` (how to run evals, and that a gate change reruns its cases); `docs/ARCHITECTURE.md` (`evals/` row); `CHANGELOG.md`.
- executed how: full `pytest`, `claude plugin validate ./` (AC12), and a PLG-1 diff scan.

## Docs to update
- [ ] spec.md ACs ticked per PR · ADR-012 (7b) · ADR-013 (7c) · DESIGN · ARCHITECTURE · GLOSSARY · README · CONTRIBUTING · CHANGELOG

## Risks
| Risk | Impact | Cheapest way to find out early |
|------|--------|-------------------------------|
| Neither Markdown nor HTML keeps headings in a Doc | A `.docx` writer in stdlib, so 7b grows | R4 before any 7b code; B4 stop rule |
| Drive tool names or arguments differ from DESIGN's note (checked 2026-11-12) | The skill text is wrong | R4 records the real names before R6 is written |
| Synced comments carry injected instructions | The edit stage acts on them | stored as quoted data; the edit stage reads `comments/` as reviewer input; an injection-shaped comment in the R7 run |
| An eval gate case is flaky (LLM grading, live web for G1/G4) | Noise read as regressions | exact-text graders first; unambiguous seeded defects; stable standards sources (RFC, MDN) |
| Eval cost | Spend | `--runs 1`, `--ablation none`, a measured ceiling, `--case` to rerun one |
| Setup in a repo that already has a non-writer `CLAUDE.md` | The constitution is never loaded | AC3 names the file and does not write it; the human merges (assumption) |

## Assumptions
- Setup does not merge into an existing `CLAUDE.md`; the human merges by hand. `articles/` is not created by setup (the brief stage creates it).
- Only the edit stage reads `comments/`; the outline and draft stages reading comments is a follow-up.
- A Doc goes to My Drive root. A configurable folder (a template, setup and test change) is a follow-up, even if R4 shows create takes one.
- `hooks/hooks.json` changes only in R8 (one matcher), with your approval; no change to `.claude/**` or `.claude-plugin/**`; no version bump.
- Not verified in the PRs: publish/sync in a session without the claude.ai connectors (beyond the AC7 path); evals in CI; a real client brief (PLG-1).
- Estimate: R1 S, R2 M, R3 S · R4 S, R5 M, R6 M, R7 S, R8 S, R9 S · R10 S, R11 M, R12 S.
