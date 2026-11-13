# ADR-004 — A gate verdict is a saved file whose first line is machine-readable

- **Date:** 2026-11-12
- **Status:** accepted
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (build-plan Phase 3, `docs/features/phase-3-vertical-slice/plan.md`)

## Context
Gates are forked and write-free (FLOW-4), so the actor that called a gate saves its verdict to
`articles/<slug>/gates/G<n>-<stage>.r<k>.md`. Phase 4's `guard-stage-order` hook must read those files mechanically to
enforce FLOW-1. A format that says one thing in the prose and another to a parser would block every stage or none.

## Decision
- Line 1 of a verdict matches
  `^## (G0 brief|G1 research|G2 outline|G3 draft|G4 final) gate: (PASS \(0 blocking|BLOCK \([1-9]\d* blocking), \d+ advisory\)$`.
  The gate number and the stage are a fixed pair. A PASS carries no blockers; a BLOCK carries at least one. A fact the
  fact gate could not open counts as one blocking FACT-2 finding.
- Line 2 is `Artifact: <path relative to the workspace>`. Everything else is free text for the human and the actor.
- `k` is 1 plus the highest `r<k>` found in `gates/` and in `gates/archive/` for that gate. A count would reuse a number
  after an archive and overwrite a saved verdict. Files are never edited.
- The actor checks line 1 against the pattern before saving. No match means "no PASS", and nothing is saved.
- Only an actor-saved verdict counts for FLOW-1. A gate run on its own is not recorded. A forked gate cannot tell who
  called it, so it prints no notice about that.
- FLOW-3 is counted on disk: two BLOCK files for an artifact stop every later run of that actor. A human resumes by
  moving **every** verdict file of that gate, PASS ones too, into `gates/archive/`, so no stale PASS can unlock the next stage.
- `tests/test_skills.py` holds the pattern and asserts each gate skill's literal PASS and BLOCK examples match it and use
  that gate's own pair.

## Rejected alternatives
| Alternative | Why not |
|-------------|---------|
| Free-text verdict, hook greps for the word PASS | A BLOCK that mentions "PASS" in a finding would read as a pass |
| A gate writes its own verdict file | Gates are write-free by construction (FLOW-4) |
| Count BLOCKs within one run only | A rerun after a stop would get two more tries and skip the human hand-over |

## Consequences
- Positive: the Phase 4 hook is a short parser; contradictory counts cannot read as a PASS.
- Accepted cost: changing the first line later breaks the hook and every saved verdict.
- Follow-ups: `guard-stage-order` (Phase 4); a skill-level way to archive after a stop, if moving files by hand proves clumsy.

Refined by ADR-007: a verdict covers the artifact it judged; the actor never edits after a PASS.
Refined by ADR-009: hooks enforce the format, the numbering and immutability; a verdict counts if it was saved by the Write tool and recorded by the hook (this replaces "only an actor-saved verdict counts").

## Revisit when
A gate needs a third outcome (for example "PASS WITH CONDITIONS"), or verdicts move out of local files.
