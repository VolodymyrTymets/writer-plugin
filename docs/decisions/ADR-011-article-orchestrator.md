# ADR-011 — The article orchestrator dispatches from a status script and writes nothing

- **Date:** 2026-11-14
- **Status:** accepted
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (`docs/features/phase-6-article-orchestrator/plan.md`)
- **Refines:** ADR-009 (the session briefing now comes from the same state function the orchestrator reads).

## Context
Phase 6 adds one command that runs brief → research → outline → (approval) → draft → final → (sign-off). Each stage already
works on its own: an actor writes one artifact, runs its forked gate, fixes a BLOCK and stops after a second (FLOW-3). No skill in
the plugin dispatched other skills yet, so the orchestrator is a new kind of skill. Picking the next stage needs the same rules the
guard enforces (FLOW-1 to FLOW-3, stale verdicts, FLOW-6), and the session briefing already worked out "where an article is" in
`describe_article`, in its own way.

## What was verified first (D4, 2026-11-14)
A throwaway probe plugin in a headless session (`claude -p --plugin-dir`, default permission mode):
- A skill invoked through the Skill tool can itself invoke a skill that forks (`context: fork`, `background: false`); the forked
  verdict comes back to the inner skill and then to the outer one.
- The inner skill's own `allowed-tools` (a scoped `Bash(...)` rule and `Write`) are pre-approved while it runs under the outer one.
- `allowed-tools` **pre-approves; it does not restrict.** A skill that lists only `Read` still attempted `Write`, and permissions,
  not the skill, refused it. So the orchestrator's empty write list is a statement, not a mechanism.

## Decision
1. **A skill, `article` (`skills/article/`), runs the actors inline through the Skill tool**, in order. Inline, not in subagents:
   the brief actor asks the user questions (AskUserQuestion) and each actor already forks its gate.
2. **Every step comes from `bin/article-status.py <slug>`**, a stdlib script (the ADR-010 pattern: a skill runs it through a scoped
   `Bash(python3 ${CLAUDE_PLUGIN_ROOT}/bin/article-status.py *)` rule). It prints one JSON object, `slug`, `stage`, `next`,
   `reason`, `markers` (a list), `stale`, always exits 0, and writes no file. The skill runs it again after every actor and decides only
   from `next`.
3. **Precedence of `next`, first match wins:** `unknown` (the script failed, or the slug is not one folder name); `stopped` (a gate
   with two BLOCKs, whatever its latest verdict, the guard's FLOW-3 rule); `stale` (`check_gate` on the last passed stage gives a
   reason); then the walk down the chain: a stage to run (`brief` … `final`), `approve`, `sign-off`, `done`.
4. **One function decides both.** `article_state()` in `bin/lib/writer.py` computes the state; `describe_article` (the session
   briefing) and the script both use it. It reads sign-off with the guard's fence-aware `is_signed`, the approval with `APPROVED`, and
   markers with a pattern built from the guard's `MARKER_LOOSE`, taken from the artifact at the article's current stage (final, else
   draft, else outline), so a leftover final cannot speak for a rebuilt outline.
5. **The orchestrator writes nothing.** No artifact, verdict, backup or human line; it never moves a verdict. At `approve` and
   `sign-off` it stops and names the file and line a human writes, then the human reruns the command. A decision given in chat does
   not count.
6. **It never invokes the same actor twice in a row**, and calls at most five actors per run. A BLOCK loop stays inside the actor;
   if the status does not move past the stage just run, the orchestrator stops and reports. On `stopped`, `stale` and `unknown` it
   quotes `reason` and stops: rebuilding, re-gating or archiving is the human's call.
7. **Three deliberate changes to the briefing line**, each pinned by an exact-string case with a `WHY:` comment: markers are counted
   in the final once the article is there; a commit trailer quoted in a code fence is not a sign-off; a gate with two BLOCKs reads as
   STOPPED even when its latest verdict is a PASS.

## Rejected alternatives
| Alternative | Why not |
|-------------|---------|
| The skill reads the verdict files and decides in prose | A prompt is a request; the guard's rules would be restated a second, weaker time |
| The orchestrator writes `Approved-by:` / `Signed-off-by:` when the user says so in chat | A decision made in chat does not count; it would weaken the actors' "never fill it yourself" |
| Actors run in subagents to save the orchestrator's context | The brief actor needs AskUserQuestion; state on disk already lets a new session resume with the same command |
| The orchestrator archives verdicts after FLOW-3 to keep going | Two BLOCKs hand the article to a human by design (ADR-004) |

## Consequences
- Positive: the briefing, the orchestrator and the guard agree by construction; the orchestrator adds no judgement and no write path.
- Accepted cost: a whole chain runs in one context; a long run that ends early is resumed by running the command again.
- Accepted cost: the empty write list in the skill's `allowed-tools` restricts nothing (verified above); the hooks stay the enforcement.
- Follow-ups: in a headless run the outline actor fixed a BLOCK with Edit, which its `allowed-tools` does not pre-approve; the edit
  was refused and the unchanged file was re-gated. Fix in the actors (pre-approve `Edit`, or rewrite with Write), separately.

## Revisit when
Claude Code gives skills a real tool restriction, or a stage needs to run without a human between sessions (then subagents and
an explicit context budget become worth it).
