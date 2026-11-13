# phase-5-draft-edit-gates — spec

Build-plan Phase 5 (`docs/DESIGN.md`). No tracker, so the slug stands in for a ticket ID.

## Problem
The chain stops at the approved outline. Nothing writes the article, nothing judges it, and the hooks that guard `draft.md`
and `final.md` (ADR-009) have no stage skill to guard. FLOW-6 (no sign-off while a marker remains) is a request in prose.

## Goal / business value
Ranked goal 1 (correct gates): a draft gate that judges structure and argument, and a final gate that checks facts against
their sources, voice, SEO and length, each in a fresh read-only context. Also resolves DESIGN open question 3 (how G4 is
split) and carries ADR-008 markers through to the final.

## Scope
- in: skills `draft` (the `draft` skill), `edit-final` (the `edit-final` skill), `check-draft` (G3, agent `gate`), `check-final` (G4, agent `fact-gate`);
  the prose-lint record gains the finding lines (so a write-free gate can read them); four guard rules: a G4 verdict is saved
  only against a current lint record; `.prose-lint.json` is written only by the script; a non-empty `Signed-off-by:` is written only
  when G4's latest verdict is a PASS on the resulting content and no marker remains; backups `draft.prev.<n>.md`
  and `final.prev.<n>.md`; tests, ADR-010, docs.
- **out (explicit):** the `article` orchestrator, the publish stage, the sync stage, the setup stage (Phases 6 and 7); reading synced comments beyond "use
  `comments/*.md` if present"; parallel fan-out of G4 (rejected, see assumptions); VOI-4 reading-level computation (a gate
  judgement, no script); client-specific content (PLG-1); any version bump.

## Acceptance criteria
- [ ] AC1 Given the plugin, when `claude plugin validate ./` and the full pytest run, then both pass.
- [ ] AC2 Given no G2 PASS, or an empty `Approved-by:`, when the `draft` skill runs, then it stops and names what is missing (FLOW-1, FLOW-2); the guard blocks the write too.
- [ ] AC3 Given an approved outline with a marker, when the `draft` skill runs, then `draft.md` carries that marker unchanged in place of the claim, every other factual sentence has an existing `[F#]`, and G3 runs and its verdict is saved by Write.
- [ ] AC4 Given a draft with a section the outline lacks, or a sentence with a statistic and no `[F#]`, when G3 runs, then BLOCK citing STR-2 or FACT-1 with the line and a fix.
- [ ] AC5 Given a G3 PASS, when the `edit-final` skill runs, then `final.md` has front matter (`title`, `meta_description`, `slug`), an empty `Signed-off-by:`, the lint run is recorded with its finding lines, and G4 runs.
- [ ] AC6 Given a fact row whose quote is not on the cited page, when G4 runs, then it opens the page and returns BLOCK citing FACT-3.
- [ ] AC7 Given a final with a marker, when G4 runs, then the verdict can PASS, line 3 is `Markers: <n>`, and a write that sets a non-empty `Signed-off-by:` is blocked by the guard (FLOW-6).
- [ ] AC8 Given a stale or missing lint record, when a G4 verdict is saved, then the guard blocks it and says to rerun the lint.
- [ ] AC8b Given a tool write to `.prose-lint.json`, or a sign-off written onto a final with no current G4 PASS (or whose body the write changes), then the guard blocks it; a shell write to `final.md` is a stated known gap.
- [ ] AC9 Given two G3 or two G4 BLOCKs on disk, when the actor is reached again, then it stops and hands over (FLOW-3).
- [ ] AC10 Given a replaced draft or final, when the actor rebuilds, then the old file is kept as `*.prev.<n>.md` and a cleared sign-off is reported.

## Edge cases
| Case | Expected behaviour | Decided by |
|------|--------------------|-----------|
| Outline approved but a marker sits in its cell | The draft keeps the marker; G3 does not block it; sign-off holds | ADR-008, FLOW-6 |
| Source cannot be opened by G4 (blocked, no web tools) | Row under Not checked, one blocking FACT-2 finding | `fact-gate` rule |
| Human edits `final.md` after PASS | Verdict is stale (sidecar hash); rerun G4 and save with Write | ADR-009 |
| `Signed-off-by:` written when the final has a marker | Guard blocks the write | FLOW-6 |
| No `comments/` folder (sync is Phase 7) | the `edit-final` skill skips it and says so once | DESIGN |
| `.claude/rules/style.md` missing or unfilled | VOI and SEO-5 checks listed under Not checked; prose-lint prints its own NOTE | prose-lint |

## Open questions
| # | Question | My assumed answer | Needs a human? |
|---|----------|-------------------|----------------|
| 1 | Can a forked gate fan out sub-checks (DESIGN OQ 3)? | Not relied on. G4 is one forked gate on `fact-gate` that checks sequentially | no |
| 2 | How does a write-free gate read prose-lint output? | The edit stage records the finding lines in `.prose-lint.json`; G4 reads them; the guard refuses a G4 verdict unless the record's hash matches `final.md` | yes: confirm over giving the agents a scoped Bash tool |
| 3 | Is `tests/test_structure.py` (ask-first) edited? | Yes, only to move four entries from `PLANNED` to `COMMANDS`; no check is changed | yes, at the ask-first prompt |
