# Changelog

Format: **Deleted** first — a smaller plugin each release is the goal.

## Unreleased

### Deleted
- Nothing yet.

### Changed
- A reviewer's comment can ask to skip a question: the outline or draft marks its list line `[SKIPPED]` and swaps that gap's `<Can't be verified…>` marker for `<Needs to be written by a human. Reason: …>`, which adds no marker and stops sign-off and the publish-ready label like the first form (FLOW-6 now covers both; the lint, the guard, the status script and Doc copies see both). A bare answer in a comment still resolves nothing. `questions-check.py` accepts `[SKIPPED]` (FT-22, ADR-023). **Upgrading:** do not downgrade past this version while an article holds the new marker, because the older loose pattern does not see it and would allow a sign-off; re-run `writer-plugin:setup` to refresh a workspace `CLAUDE.md`'s FLOW-6 text (the gates and guard read their own rules).
- The research, outline and draft stages end with the same `## Questions for the human`: plain-text questions, `[OPEN]` or `[RESOLVED]`, no ids, built per stage from what is still open in that artifact, never repeating a question the previous stage resolved, and left out when nothing was ever owed. `bin/questions-check.py <slug> <stage>` checks its form (read-only, advisory) and G1, G2 and G3 advise on it with one wording (FACT-6 now covers the list at all three stages). The draft's list is outside the word count and the number check, `/edit` drops it from the final, and a new rule STR-7 makes the lint report and G4 block a final that still holds it (FT-22, ADR-023). **Upgrading:** an outline with the older "Open questions for the human" keeps working (placement is the only rule checked and G2 leaves it out of its marker count) until its next rebuild writes the new heading; re-run `writer-plugin:setup` to refresh a workspace `CLAUDE.md`'s FACT-6 and STR-7 text (the gates read their own checklists).
- ADR-022 records a spike of the Google Docs connector's `update_doc` and decides NO-GO on one Doc per artifact: a new Doc per revision stays (FT-21, ADR-012). No code changes.
- `research.md` ends with `## Questions for the human`: one plain-text question per open marker and per decision the human owes, each marked `[OPEN]` or `[RESOLVED]`, with no `Q`, `F` or comment ids and a line saying what would answer it. A rerun keeps earlier lines and resolves one only when a fact row answers it or a reviewer's comment settles a decision; the report gives the counts. G1 advises, never blocks, when the section is missing, a line has an id or no mark, or a marker has no `[OPEN]` question (FT-20, ADR-021). **Upgrading:** none; an existing `research.md` gets the section on its next research run.
- G1's coverage floor (fewer than half of the brief's questions answered) is an advisory finding, not a BLOCK, so a thin research dossier passes with its gaps as markers that travel to the final, where sign-off is still refused while one remains. The research stage no longer stops before the gate and reports what would answer each open question (FT-19, ADR-021; supersedes ADR-014 and removes the FT-17 stop). **Upgrading:** a workspace `CLAUDE.md` still says FACT-6 needs at least half answered; re-run `writer-plugin:setup` or edit that line (the gate reads its own checklist, so it already advises).
- `doc-copy.py` no longer skips an unchanged copy whose Doc the create hook never logged in `.docs-created.json`: such a Doc can never carry an approval, so the next copy is a new revision, and an unreadable log stops the copy with an error (FT-18, ADR-012.3, ADR-016). **Upgrading:** an article whose Docs were made without the hooks gets one new Doc on its next copy; the old ones stay in `docs.json`.
- The research stage no longer runs a gate it expects to fail: when fewer than half of the brief's questions are answered by fact rows, it makes the ungated review copy, says which questions need the human and what would answer each (a fetchable URL, or a page's text with its date), and stops before G1, so no FLOW-3 strike is spent (FT-17, ADR-020). A reviewer's comment is still only a pointer note, so a Doc comment alone does not raise coverage. The outline, draft and edit stages are not changed.
- A stage that finds its article already stopped (FLOW-3, two BLOCKs on disk from an earlier run) makes the same ungated review copy before it stops, or reports the one already recorded (FT-16, ADR-020). **Upgrading:** this replaces the manual `writer-plugin:publish` step the FT-15 entry below asks for.
- A stage that stops on its second BLOCK first makes one review copy of the blocked artifact (title ends `· ungated`), so reviewers can comment on the blockers in a Google Doc (FT-15, ADR-020; refines ADR-012). The stage still runs again only after a human archives its verdicts. **Upgrading:** an article already stopped has no such Doc; run `writer-plugin:publish <slug> <stage>` once.
- A `<Can't be verified. Reason: …>` marker is bold in every Doc copy, so a reviewer can find the gaps to fill (FT-14). The Doc text changes for an article with markers, so its next copy is a new revision. A highlight colour is not attempted.
- A saved verdict keeps its header: the guard refuses a new verdict whose line 2 is not `Artifact: <path>` or whose line 3 (G1 `Coverage:`, G2 and G4 `Markers:`, G3 `Outline:`) lacks the gate's label, and the five actor skills say to save lines 1 to 3 as printed or rerun the gate (FT-13, ADR-019; refines ADR-004). **Upgrading:** verdicts already saved are not re-checked.
- `sync` and `publish` with no slug (or only a stage name, as in `/sync research`) take the workspace's only article, offer two to four as options, list more than four, and never guess (FT-12).
- Four skill folders are renamed to their command, so each command has one name: `intake-brief` → `brief`, `edit-final` → `edit`, `setup-workspace` → `setup`, `sync-comments` → `sync`. The commands (`writer-plugin:brief` and so on) do not change, and the structure test now fails if a folder and its `name:` differ (FT-11, ADR-018).
- A PDF brief is read with the Read tool, never a shell: `brief.source.md` holds the text Read returned under an "extracted from" line, and a scanned PDF stops the stage with a request for text (FT-8).
- The brief stage normalises the folder slug to lowercase kebab-case and names the change; the final's `slug:` is the SEO slug, its own value, and `prose-lint.py` reports one that is not kebab-case as the new rule SEO-6 (FT-9).
  **Upgrading:** re-run `writer-plugin:setup` (or add SEO-6 to your `CLAUDE.md`) so a G4 verdict that cites it is defined; a final whose `slug:` is a capitalised folder name gets one lint line on its next edit run.
- The outline holds at most one marker per open gap of the research, drops a claim that has no fact and no gap, and G2 blocks more markers than gaps as FACT-1 (FT-10, ADR-017; refines ADR-008).
  **Upgrading:** an outline already approved with extra markers is not re-gated until it is rebuilt.
- `prose-lint.py` STR-6 applies the 10% tolerance to both ends of a range target: 3,500 to 4,000 words allows 3,150 to 4,400, where it used to flag 3,493. The draft and edit
  skills say not to pad to clear a length flag (FT-7). **Upgrading:** a brief with a range target now passes at a few words under its low end; re-record the lint on a final you already linted.
- Reviewer comments reach the stage they are about (FT-5, ADR-016). The status script lists `comments` waiting for a stage; research, outline, draft and the edit stage read them as data, back the
  artifact up (research now keeps `research.prev.<n>.md`), rebuild with them, clear the approval and are gated again; a rerun that applies nothing writes nothing and runs no gate. `/sync` restarts the owning
  stage once when comments are waiting and no approval came in. A reviewer's answer to a research question is recorded as a pointer note, never as a fact, so it does not clear a marker.
- Approval happens in the Google Doc (FT-6, ADR-016). Every Doc copy is unapproved and says where to approve; a name typed after `Approved-by:` (the final's is `Signed-off-by:`) is
  recorded by the new `record-approval` hook and carried into the local artifact by `/sync`; a stage is closed when the local file has it, and the next stage is blocked until then
  (FLOW-2 now covers the brief, research, outline and draft). The guard refuses any other way for a tool to fill an approval line, a filled upload, and any call that edits, shares,
  copies or removes a Doc the copy skill created. `article-status.py` reports `approve` for every stage and carries an empty `comments` list.
  **Upgrading:** an article already in progress shows `approve` at a passed stage until its line is added; re-run `writer-plugin:setup` (or edit FLOW-2 in your `CLAUDE.md`) for
  the new rule text. **Downgrading:** `approvals/` and `.docs-created.json` are inert and safe to delete, and the old FLOW-2 checks only the outline.
- `prose-lint.py` FACT-1 no longer flags numbers that make no claim: marker reasons ("HTTP 403"), image paths, numbered labels ("Screenshot 2",
  "Step 3"), "checked in <month year>", and names with a digit (G2, B2B). A fact list `[F5, F14]` counts as one tag, here and in the word count;
  the lint and the Doc copy now share one tag pattern (FT-4).
- New script `quote-check.py` checks each fact-bank quote against the raw text of its source page. The research stage records the result in
  `.quote-check.json`; G1 reads it and blocks a `not-found` quote as FACT-3 without a model's judgement; the guard refuses a G1 verdict
  without a matching record (FT-3, ADR-015). No gate gets a shell. The two G1 eval cases carry a record.
- The research stage tries a fallback for a blocked source (retry, then another page that states the claim) before a question becomes an
  Open gap, asks WebFetch for quotes word for word, and reports the sources that stayed blocked (FT-3).
- G1 blocks a research dossier that answers fewer than half of the brief's questions (FACT-6 coverage floor, ADR-014). Before, nine of ten
  questions could sit under Open gaps and pass. The research stage is told the floor.
- `prose-lint.py` SEO-1 reads the keyword as the phrase before the first `(`, `;` or `. ` on the brief's `**Primary keyword:**` line, so
  volumes and usage notes on that line no longer cause false findings (FT-1). The brief template says to keep the phrase bare.
- `docs/DESIGN.md` records a field test on one real brief (FT-1 to FT-14, all open) and updates the Phase 5 and 6 rows.
  No plugin behaviour changed.
- Each stage actor makes its Google Doc copy after its gate passes, through the copy skill, instead of saying "Doc copy: not yet
  available". The guard also runs on the Drive create call (ADR-012).
- `prose-lint.py` reads a style-guide `**Phrases:**` or `**Tells:**` value of exactly `none` as an empty list. Before, it banned the
  word "none" itself, so a workspace with no banned phrases would have had G4 block on noise.
- The five stage actors pre-approve `Edit` as well as `Write`, and after a BLOCK they read the file back to check every fix
  landed before running the gate again; a fix that cannot be made stops the stage instead. A headless run had spent an
  actor's second BLOCK re-gating a file whose edits had been refused.
- Where research cannot find or prove something, the stages leave a marker `<Can't be verified. Reason: reason sentence here>`
  instead of stopping the flow (ADR-008). The outline gate treats a marker as not a claim, blocks an inexact one or a
  claim beside it, and prints `Markers: <n>` on line 3. FLOW-6: no final is publish-ready while a marker remains.

- After a PASS the stage never edits its artifact: a change means rerunning the stage, and the rebuild is gated again
  (ADR-007). The brief stage carries earlier answers forward; the outline stage keeps the outline it replaces as
  `outline.prev.<n>.md` and clears the approval. One hygiene line in the constitution template asks the same of any agent.
- FACT-2: a first-party vendor page that shows no published or updated date may say `n/a (live page)` instead of a
  date (ADR-006); FACT-4 ages such a fact by its accessed date.
- G1 blocks a Questions-table fact ID that exists but does not support its question (FACT-6).
- G1 prints `Coverage: <a> answered, <o> open (of <m>)` on line 3 of its verdict.

### Added
- Phase 7c (ADR-013): `evals/`, a `claude plugin eval` suite of 16 cases on three synthetic public-topic briefs and one sourced
  article: a PASS and a seeded BLOCK per gate G0–G4, G0 on each brief, and the brief stage on each brief. `tests/test_evals.py`
  pins its shape and the PLG-1 domain allowlist. Local only, never in CI.
- Phase 7b (ADR-012):
  - The copy skill (`/publish`) uploads an artifact as a new Markdown Google Doc revision and appends it to `docs.json`.
    `bin/doc-copy.py` computes the text (fact IDs stripped), the hash, the revision and the title with its label.
  - The sync skill (`/sync`) writes a Doc's comments, quoted verbatim with their anchors, to `comments/<stage>.r<k>.md`.
  - The guard enforces FLOW-6 on the copies. `docs.json` is append-only and FLOW-6-true, and no Doc is titled publish-ready unless
    the final is signed off on a current G4 PASS with no marker.
  - Open questions 1–2 are resolved by a Drive spike.
- Phase 7a: the setup skill (`/setup`) writes a content workspace's `CLAUDE.md` from `rules/core/CLAUDE.template.md` and its
  `.claude/rules/style.md` from `templates/style.md`, asking at most two rounds of questions. It never overwrites an existing file,
  writes only a missing one, and refuses in the plugin's own repository.
- Phase 6 (ADR-011): the orchestrator (`/article`) runs the chain, calling each stage's actor in order and stopping at the outline
  approval and the final sign-off, on two BLOCKs, on a stale verdict, or when done; it writes nothing. `bin/article-status.py` prints an
  article's next step as JSON; the session briefing is built on the same `article_state()` and now counts markers in the final, ignores a
  `Signed-off-by:` quoted in a code fence, and reads a gate with two BLOCKs as stopped.
- Phase 5 (ADR-010): the draft stage (`/draft`), the edit stage (`/edit`), gate G3 (`/check-draft`, developmental) and gate G4
  (`/check-final`, one forked gate that opens the sources and reads the recorded lint). `prose-lint.py --record` keeps the finding
  lines. The guard gains four rules: a G4 verdict needs a matching lint record, only the script writes `.prose-lint.json`, and a
  `Signed-off-by:` needs a current G4 PASS on the resulting text and no marker (FLOW-6). Rebuilds keep `draft.prev.<n>.md` and
  `final.prev.<n>.md`.
- Phase 4 hooks (ADR-009): `guard-stage-order` (FLOW-1 to FLOW-4, stale and hand-edited verdicts), `record-verdict` (the sidecar),
  `verify-final` and `session-context`; the `prose-lint.py` script; rule STR-6 (article length within the brief's target); the
  `final.md` front matter. A verdict is now saved with the Write tool.
- ADR-006 (live vendor pages in the fact bank).
- Phase 3 vertical slice: the brief, research and outline stages, gates G0 to G2 (`/check-brief`, `/check-research`,
  `/check-outline`), and the `gate` and `fact-gate` agents. Verdict files have a fixed first line (ADR-004); the stage
  skills read `templates/` at run time through `${CLAUDE_PLUGIN_ROOT}` (ADR-005).
- Rules BRF-6 (research questions are listed) and FACT-6 (every brief question is answered or listed under Open gaps).
- Phase 2 library: editorial constitution template (`rules/core/CLAUDE.template.md`, all rule IDs) and the brief,
  research, outline and style templates under `templates/`. `tests/test_templates.py` pins their shape.
- FACT-2 now requires the source URL to resolve.
- FLOW-2 now says an outline is approved only when `Approved-by:` has a non-empty value.

## 0.0.1 — 2026-11-12 · skeleton

### Deleted
- Nothing yet.

### Added
- Design (`docs/DESIGN.md`): actor → gate flow from brief to final, five gates, two human checkpoints, rule IDs
  (BRF, FACT, STR, VOI, SEO, FLOW, PLG), hooks plan, Google Doc copies, build plan.
- Plugin manifest and marketplace (`writer`), an empty `hooks/hooks.json`, and the structure test with the command
  map. Planned commands (`/article`, `/brief`, `/research`, `/outline`, `/draft`, `/edit`, the five `/check-*` gates,
  `/publish`, `/sync`, `/setup`) are listed but not built.
