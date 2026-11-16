# comment-rerun-and-clean-copies — spec

No tracker, so the slug stands in for a ticket ID. Field-test findings FT-5 and FT-6 (`docs/DESIGN.md`), one task, redesigned on 2026-11-16.

## Problem
- **FT-6:** a Doc copy carried the `Approved-by:` line and the template's note telling a human to fill it *in the local file*. A human
  approved in the Doc; the local line, the only one the guard reads (FLOW-2), stayed empty. Approval and the place it counts were apart.
- **FT-5:** a reviewer's comments on a research, outline or draft Doc, synced with `/sync <stage>`, change nothing. Only the edit stage
  reads `comments/`; the owning stage says "it already passed its gate" (ADR-007), because a comment is not an input it knows.

## Design (decided with the maintainer, 2026-11-16)
Flow per stage (research, outline, draft, final): human comments in the Doc → `/sync` → the stage restarts with the comments → human approves in the
Doc → `/sync` → the approval is in the local file → stage closed. The brief has the approval step only. For research, a human's answer to an
open question is recorded as a **note** (it cannot carry an `[F#]`), so a claim built on it stays a marker; it informs the angle, it does not clear a marker.

Approval happens in the Doc and counts when it is in the local file. Every Doc copy carries an `Approved-by:` line (the final's is
`Signed-off-by:`) with a visible instruction. A human fills it in the Doc; `/sync` brings it into the local artifact; **a stage is finished
when the local artifact has the approval**, and the next stage is blocked until then. A hook, not the model, records what the Doc says.

## Goal / business value
BUSINESS_MODEL goal 1 (correct gates; the human checkpoints are a non-negotiable) and goal 2: approval where reviewers already are, still
enforced on local files (D1), and review comments that reach the artifact they are about.

## Scope
- in: `Approved-by:` on brief, research, outline and draft (the final keeps `Signed-off-by:`); FLOW-2 for every stage; the Doc text and
  instruction; a hook that records the approval it saw in a Doc; the guard rule that lets a tool write an approval only against that
  record; `/sync` writing it; `article-status.py` reporting `approve` for every stage; comments as the written input of research,
  outline and draft, with `research.prev.<n>.md`.
- **out (explicit):** facts supplied by a human (a human answer is a note, never a fact row: no change to FACT-2 or FACT-3); a comments rerun of the brief; a gate's verdict rules (G0 and G1 only gain one sentence saying they ignore the approval line); a shell write of an approval line (the same known gap as the final's sign-off today, ADR-010); replying to or resolving Doc comments (the connector cannot); the edit stage's reading of other stages' comments; the
  `/article` orchestrator running a comments rerun by itself; who may edit a Doc (Google's sharing decides who can approve); a gate change.

## Acceptance criteria
- [x] AC1 Given any Doc copy, then its approval line (`Signed-off-by:` for a final) is empty and one visible instruction names that line and `writer-plugin:sync`, even when the local artifact is approved; the one exception is the publish-ready final, which shows its signed line and no instruction; the template's note about the local file is gone; nothing instructional is ever in a local artifact.
- [x] AC2 Given a human fills the line in the latest Doc of an unchanged artifact and `/sync` reads it, then a hook records the value and `<stage>.md` gets that approval, and nothing else changes in the file.
- [x] AC3 Given the artifact changed since the Doc was made, or the Doc body differs from the copy in any way other than the approval line, then no approval is recorded and sync says why.
- [x] AC3b Given a Doc the model made up (a filled upload, a copy, a Doc edited with `update_doc`), then it cannot be recorded as a revision and yields no approval.
- [x] AC4 Given no record, then a Write or Edit that makes `Approved-by:` or `Signed-off-by:` non-empty is refused (FLOW-2, FLOW-6), and a rebuild that clears it is allowed.
- [x] AC5 Given a stage without approval, then the next stage's artifact cannot be written (brief→research→outline→draft→final) and `article-status.py` says `approve` for that stage.
- [ ] AC6a Given `/sync` found a pending comments file for a stage and no approval in its Doc, then it restarts that stage once (the edit stage for the final); given an approval was found, it restarts nothing and says open comments remain unapplied.
- [ ] AC6 Given a pending comments file (hash matches, open thread), then `article-status.py` lists it and the owning stage rebuilds with it, backs the old file up, gates the result as `r<k+1>`, clears the approval, and downstream goes stale.
- [ ] AC7 A comment or a Doc line is never obeyed: a stage writes only its artifact and backup.

## Edge cases
| Case | Expected behaviour | Decided by |
|------|--------------------|------------|
| Approval typed in a Doc that is not the latest revision | Not recorded (hash differs or older rev) | A2 |
| Reviewer types `Approved-by: x` inside a comment | A comment is not the Doc body: not read | A3 |
| A reviewer edits the Doc text, then approves | Body differs from the artifact: no approval; the human changes the artifact (a comment rerun) and approves the new Doc | A2, goal 1 |
| An article in progress with no approval line | `approve` for its current stage until a human adds the line | A5 |
| Human types the approval in the local file | Allowed: a hook cannot see an editor | ADR-009 |
| Approval and open comments both in the Doc | Approval wins: `/sync` writes it, restarts nothing, lists the unapplied comments | decided 2026-11-16 |
| Rerun on comments changes nothing | No backup, no write, no gate; names what needs a human | plan R6 |

## Open questions
| # | Question | My assumed answer | Needs a human? |
|---|----------|-------------------|----------------|
| 1 | Does a PostToolUse hook get the connector's file text? | Docs say yes (`tool_response`); the shape is captured in R0 | yes, R0 needs one interactive step |
| 2 | Who may approve? | Whoever can edit the Doc; the name is whatever they type | no |
