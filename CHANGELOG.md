# Changelog

Format: **Deleted** first — a smaller plugin each release is the goal.

## Unreleased

### Deleted
- Nothing yet.

### Changed
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
