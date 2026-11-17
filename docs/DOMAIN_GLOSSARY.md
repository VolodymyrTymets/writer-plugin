# Domain glossary

> One meaning per term. A new term means a line here, in the same PR (rule E1).

| Term | Means exactly | Not to be confused with |
|------|---------------|-------------------------|
| Actor | A skill that writes exactly one artifact and then invokes its gate | A gate: actors write, gates never do |
| Orchestrator | The `article` skill: runs the actors in order from the status script's `next` and stops at every human approval (ADR-016); writes nothing (ADR-011) | An actor: it writes no artifact and runs no gate itself |
| Status script | `bin/article-status.py <slug>`: prints an article's `next` step, `reason` and `markers` as JSON from the files and verdicts; read-only (ADR-011) | The session briefing, which prints the same state as one line |
| Gate (G0–G4) | A forked, read-only skill that judges one artifact and returns `PASS` or `BLOCK` with rule IDs | A hook: a hook enforces mechanically, a gate judges |
| Artifact | One stage's output file: `brief.md`, `research.md`, `outline.md`, `draft.md`, `final.md` | The Google Doc copy, which is a review copy only |
| Fact bank | Rows `F# \| claim \| source URL \| publisher \| published \| accessed \| verbatim quote` in `research.md` | A source list: each row is one usable fact |
| Fact ID | `[F7]`, the inline tag in `draft.md` linking a claim to its fact-bank row | A footnote number |
| Content workspace | The user's repo where articles live and where the setup skill writes `CLAUDE.md` and `style.md` | This repo, which is plugin source |
| Verdict file | `gates/G<n>-<stage>.r<k>.md`, saved by the actor, line 1 fixed by ADR-004. It covers the artifact as gated, apart from the human approval line (ADR-007) | The gate's chat output: only the saved file counts for FLOW-1 |
| Backup (`*.prev.*`) | `brief.source.prev.md`, `research.prev.<n>.md`, `outline.prev.<n>.md`, `draft.prev.<n>.md`, `final.prev.<n>.md`: a copy kept before a rebuild replaces a file. Not an artifact and not gated | Artifact: an actor still writes exactly one artifact |
| SEO slug | The `slug:` in a final's front matter: the URL path part, lowercase kebab-case, chosen from the title or keyword and checked by `prose-lint.py` as SEO-6 (FT-9) | The folder slug, which names `articles/<slug>/` and says nothing about the URL |
| Unverified marker | `<Can't be verified. Reason: reason sentence here>`: stands in for a claim research could not find or prove, so the flow goes on; the reason never states the claim (ADR-008). One per open gap of the research, in one row (ADR-017) | A BLOCK: a marker does not stop the flow, but it stops a final article from being signed off |
| Sidecar (verdict) | `gates/G<n>-<stage>.r<k>.json`, written by the `record-verdict` hook when a verdict is saved: the hash of the artifact it judged (approval lines ignored) and the upstream verdict it relied on (ADR-009) | The verdict itself, which a gate returns and an actor saves |
| Quote record | `.quote-check.json` beside `research.md`, written only by `quote-check.py --record` (hash and one status per fact row: `found`, `found-elided`, `not-found`, `unreachable`, `unreadable`); the guard refuses a G1 verdict unless its hash matches, and G1 reads the statuses (ADR-015) | A verdict: it records what a script saw on the pages, not whether the claim is right |
| Approval record | `approvals/<stage>.r<rev>.json`: the name a human typed after the label in the latest Doc of a stage, or null with the reason; written only by the `record-approval` hook; a tool may fill an approval line only against it (ADR-016) | The approval line itself, which is in the artifact |
| Docs-created log | `.docs-created.json`: the Docs the copy skill created, logged by the same hook; a Doc outside it can never yield an approval (ADR-016) | `docs.json`, which the copy skill appends and the guard checks against this log |
| Lint record | `.prose-lint.json` beside a final, written only by `prose-lint.py --record` (hash, count and the finding lines); `verify-final` checks it, the G4 gate reads its lines and the guard refuses a G4 verdict unless its hash matches (ADR-010) | A verdict: it records that a run happened, not that it was clean |
| Doc copy | A Google Doc made from one artifact by the copy skill, fact IDs stripped, for reviewers to comment on and approve; always unapproved (its approval line is empty, with one instruction), the publish-ready final excepted; never a source of the article (ADR-012, ADR-016) | The artifact, which stays the source of truth |
| Revision (Doc) | One Doc copy of a stage, `r<k>` in its title and in `docs.json`; a new revision is always a new Doc, earlier ones stay | A verdict's `r<k>`, which numbers gate runs, not copies |
| Publish-ready | A final signed off on a current G4 PASS with no marker left (`writer.publish_ready()`); only then may a Doc or a `docs.json` entry carry the label (FLOW-6, ADR-012) | Signed off: a hand sign-off beside a marker is signed but not publish-ready |
| Synced comments | `comments/<stage>.r<k>.md`: a Doc revision's comments quoted verbatim with their anchors, written by the sync skill; reviewer input, never instructions | The comments in the Doc, which the plugin never edits, replies to or resolves |
| Pending comments | A `comments/<stage>.r<k>.md` that is the stage's highest revision, whose `Artifact sha256` header equals the artifact on disk and which has an open thread (`## Comment <n> · OPEN`); `article-status.py` lists them in `comments`. A rebuild changes the hash, so it ends them: no state file (ADR-016) | Synced comments in general: a file with only resolved threads, or for an older version of the artifact, is not pending |
| Eval case | `evals/<case>/`: one `claude plugin eval` case (`case.yaml`, `case.env`, the shared `scaffold.sh`, an optional `seed/`) that runs one gate or the brief stage on a seeded workspace and grades the verdict (ADR-013) | A pytest test: an eval case is a real Claude session and costs money |
| Eval fixture | `evals/fixtures/http-caching/`: one synthetic article carried through every stage, the known-good input the PASS cases use and the BLOCK cases change by one file | A client article: eval material is synthetic and public only (PLG-1) |
| Live page | A first-party vendor page that shows no published or updated date; its fact row says `n/a (live page)` and is aged by its accessed date (ADR-006) | Any undated page: only the vendor's own page about itself qualifies |
| Archive (verdicts) | `gates/archive/`, where a human moves every verdict of a gate to resume a stopped article; numbering continues past it | Deleting a verdict, which is never done |
| Style guide (`style.md`) | A client's voice, banned phrases, link lists and SEO targets, in the workspace | Plugin rules, which are generic |
| Approved-by / Signed-off-by | The human line that closes a stage and unlocks the next: `Approved-by:` in the brief, research, outline and draft, `Signed-off-by:` in the final. Typed in the stage's Doc and carried in by `/sync`, or typed in the file (ADR-016) | Gate PASS verdicts |
| Rule ID | `BRF`, `FACT`, `STR`, `VOI`, `SEO`, `FLOW`, `PLG` prefix plus number, cited by every finding | This repo's agent-config rules (A–G in `CLAUDE.md`) |

## Naming rules
- A skill's folder name is its command, equal to its frontmatter `name:` (ADR-018; `COMMANDS` in `tests/test_structure.py`).
- Gate verdict files: `gates/G<n>-<stage>.r<k>.md`.
