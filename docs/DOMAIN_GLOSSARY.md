# Domain glossary

> One meaning per term. A new term means a line here, in the same PR (rule E1).

| Term | Means exactly | Not to be confused with |
|------|---------------|-------------------------|
| Actor | A skill that writes exactly one artifact and then invokes its gate | A gate: actors write, gates never do |
| Orchestrator | The `article` skill: runs the actors in order from the status script's `next` and stops at the two human checkpoints; writes nothing (ADR-011) | An actor: it writes no artifact and runs no gate itself |
| Status script | `bin/article-status.py <slug>`: prints an article's `next` step, `reason` and `markers` as JSON from the files and verdicts; read-only (ADR-011) | The session briefing, which prints the same state as one line |
| Gate (G0–G4) | A forked, read-only skill that judges one artifact and returns `PASS` or `BLOCK` with rule IDs | A hook: a hook enforces mechanically, a gate judges |
| Artifact | One stage's output file: `brief.md`, `research.md`, `outline.md`, `draft.md`, `final.md` | The Google Doc copy, which is a review copy only |
| Fact bank | Rows `F# \| claim \| source URL \| publisher \| published \| accessed \| verbatim quote` in `research.md` | A source list: each row is one usable fact |
| Fact ID | `[F7]`, the inline tag in `draft.md` linking a claim to its fact-bank row | A footnote number |
| Content workspace | The user's repo where articles live and where the setup skill writes `CLAUDE.md` and `style.md` | This repo, which is plugin source |
| Verdict file | `gates/G<n>-<stage>.r<k>.md`, saved by the actor, line 1 fixed by ADR-004. It covers the artifact as gated, apart from the human approval line (ADR-007) | The gate's chat output: only the saved file counts for FLOW-1 |
| Backup (`*.prev.*`) | `brief.source.prev.md`, `outline.prev.<n>.md`, `draft.prev.<n>.md`, `final.prev.<n>.md`: a copy kept before a rebuild replaces a file. Not an artifact and not gated | Artifact: an actor still writes exactly one artifact |
| Unverified marker | `<Can't be verified. Reason: reason sentence here>`: stands in for a claim research could not find or prove, so the flow goes on; the reason never states the claim (ADR-008) | A BLOCK: a marker does not stop the flow, but it stops a final article from being signed off |
| Sidecar (verdict) | `gates/G<n>-<stage>.r<k>.json`, written by the `record-verdict` hook when a verdict is saved: the hash of the artifact it judged (approval lines ignored) and the upstream verdict it relied on (ADR-009) | The verdict itself, which a gate returns and an actor saves |
| Lint record | `.prose-lint.json` beside a final, written only by `prose-lint.py --record` (hash, count and the finding lines); `verify-final` checks it, the G4 gate reads its lines and the guard refuses a G4 verdict unless its hash matches (ADR-010) | A verdict: it records that a run happened, not that it was clean |
| Live page | A first-party vendor page that shows no published or updated date; its fact row says `n/a (live page)` and is aged by its accessed date (ADR-006) | Any undated page: only the vendor's own page about itself qualifies |
| Archive (verdicts) | `gates/archive/`, where a human moves every verdict of a gate to resume a stopped article; numbering continues past it | Deleting a verdict, which is never done |
| Style guide (`style.md`) | A client's voice, banned phrases, link lists and SEO targets, in the workspace | Plugin rules, which are generic |
| Approved-by / Signed-off-by | The human lines in `outline.md` / `final.md` that unlock the next stage | Gate PASS verdicts |
| Rule ID | `BRF`, `FACT`, `STR`, `VOI`, `SEO`, `FLOW`, `PLG` prefix plus number, cited by every finding | This repo's agent-config rules (A–G in `CLAUDE.md`) |

## Naming rules
- Skill directories may differ from commands; the command comes from frontmatter `name:` (`COMMANDS` in `tests/test_structure.py`).
- Gate verdict files: `gates/G<n>-<stage>.r<k>.md`.
