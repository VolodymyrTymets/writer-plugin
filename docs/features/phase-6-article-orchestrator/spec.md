# phase-6-article-orchestrator — spec

Build-plan Phase 6 (`docs/DESIGN.md`). No tracker, so the slug stands in for a ticket ID.

## Problem
Each stage works on its own, but a writer has to know the chain, read the verdict files and pick the next stage by hand.
Nothing runs brief → research → outline → (approval) → draft → final → (sign-off) as one command, and nothing tells a
writer, from the files, exactly where a half-done article stopped and why.

## Goal / business value
Ranked goal 1 (correct gates, mechanical enforcement): the orchestrator adds no new judgement. It decides the next step from
the files on disk, with a tested script, and never writes an artifact, a verdict, `Approved-by:` or `Signed-off-by:`. The hooks
(ADR-009, ADR-010) stay the only enforcement; the orchestrator must never need to get past one.

## Scope
- in: the `article` skill (the orchestrator, command `article`); `bin/article-status.py`, a stdlib script that prints an
  article's state and next step as JSON; `describe_article` in `bin/lib/writer.py` rebuilt on the same structured state, so the
  session briefing and the orchestrator can never disagree; tests; ADR-011; docs.
- **out (explicit):** the publish, sync and setup stages (Phase 7); evals on the test briefs (Phase 7); any change to the five
  actors, the five gates, the guard or `hooks/hooks.json`; the orchestrator writing either human line; auto-archiving verdicts after
  FLOW-3; running several articles in one call; parallel stages; a version bump.

## Acceptance criteria
- [x] AC1 Given the plugin, when `claude plugin validate ./` and the full pytest run, then both pass.
- [x] AC2 Given a workspace with no `articles/<slug>/`, when the orchestrator runs with a slug and a brief (path or pasted text), then it
      runs the brief, research and outline stages in order, each through its own actor (which runs its own gate), and stops after
      the G2 PASS saying a human writes a name after `Approved-by:` in `outline.md`. It writes nothing itself.
- [x] AC3 Given an approved outline, when the orchestrator runs again with the slug, then it starts at the draft stage (no earlier stage is
      rerun), runs draft and edit, and stops after the G4 PASS saying the final is not signed off, listing each marker (the `markers` list).
- [x] AC4 Given two BLOCK verdicts on any gate (FLOW-3), when the orchestrator runs, then it stops before calling any actor, names both
      files and says how a human resumes (archive every verdict of that gate).
- [x] AC5 Given a stale verdict (an artifact changed after its PASS, or an upstream re-gated), when the orchestrator runs, then it stops
      and quotes the reason the status script gives; it does not rebuild anything by itself.
- [ ] AC6 (partly verified: the rule is pinned by a contract test and the orchestrator re-read the status after every actor in
      every run, but no run returned from an actor with its stage unchanged, so the stop itself has not executed) Given an actor that ends without a new PASS (one BLOCK fixed and re-gated is the actor's own loop), when control returns, then
      the orchestrator reads the status again and continues only if the script says the next stage is unblocked.
- [x] AC7 Given a signed-off final, when the orchestrator runs, then it reports the article as done and calls nothing.
- [x] AC8 Given any state, `bin/article-status.py <slug>` prints one JSON object with `slug`, `next`, `stage`, `reason`, `markers`
      and the session briefing line for that article says the same thing (one function decides both).

## Edge cases
| Case | Expected behaviour | Decided by |
|------|--------------------|-----------|
| Artifact written, its gate never run (session died) | `next` is that stage's actor again; the actor backs up and rebuilds | assumption 3 |
| One BLOCK on disk, no second | `next` is that stage's actor (it fixes and re-gates) | actors' Step 5 |
| Outline passed with markers | Stops for approval and lists the markers; approval is allowed with markers (ADR-008) | ADR-008 |
| Final passed with a marker | Stops; says sign-off is refused while the marker remains (FLOW-6) | ADR-008, ADR-010 |
| Orchestrator called with no slug | Same rule as the actors: the most recently changed `articles/*/`, named | actors' Step 1 |
| Brief stage asks the user questions | Allowed: the brief actor runs inline and uses AskUserQuestion (not executed headless; listed as not verified) | `intake-brief` |
| A guard block during an actor | The orchestrator stops and reports it; it never works around a hook | FLOW-1..6 |
| Status script errors | Prints `next: "unknown"` with the error; the orchestrator stops (never guesses a stage) | assumption 4 |

## Open questions
| # | Question | My assumed answer | Needs a human? |
|---|----------|-------------------|----------------|
| 1 | May the orchestrator write `Approved-by:` / `Signed-off-by:` when the human says so in chat? | No. It stops; the human writes the line in the file and reruns. A decision made in chat does not count (BUSINESS_MODEL non-negotiable) | yes: confirm at approval |
| 2 | Dispatch from a script or from skill prose? | A script (`article-status.py`) that reuses the session-context logic: "a hook is a mechanism, a prompt is a request" | no |
| 3 | Do actors run inline or in subagents? | Inline through the Skill tool, as actors call gates today; the brief actor needs AskUserQuestion, which a subagent lacks | no, R0 checks it works |
| 4 | Is `tests/test_structure.py` (ask-first) edited? | Yes, only to move `article` from `PLANNED` to `COMMANDS`; no check changes | yes, at the ask-first prompt |
