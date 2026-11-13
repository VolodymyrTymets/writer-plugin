# Changelog

Format: **Deleted** first — a smaller plugin each release is the goal.

## Unreleased

### Deleted
- Nothing yet.

### Changed
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
