# Domain glossary

> One meaning per term. A new term means a line here, in the same PR (rule E1).

| Term | Means exactly | Not to be confused with |
|------|---------------|-------------------------|
| Actor | A skill that writes exactly one artifact and then invokes its gate | A gate: actors write, gates never do |
| Gate (G0–G4) | A forked, read-only skill that judges one artifact and returns `PASS` or `BLOCK` with rule IDs | A hook: a hook enforces mechanically, a gate judges |
| Artifact | One stage's output file: `brief.md`, `research.md`, `outline.md`, `draft.md`, `final.md` | The Google Doc copy, which is a review copy only |
| Fact bank | Rows `F# \| claim \| source URL \| publisher \| published \| accessed \| verbatim quote` in `research.md` | A source list: each row is one usable fact |
| Fact ID | `[F7]`, the inline tag in `draft.md` linking a claim to its fact-bank row | A footnote number |
| Content workspace | The user's repo where articles live and where the setup skill writes `CLAUDE.md` and `style.md` | This repo, which is plugin source |
| Style guide (`style.md`) | A client's voice, banned phrases, link lists and SEO targets, in the workspace | Plugin rules, which are generic |
| Approved-by / Signed-off-by | The human lines in `outline.md` / `final.md` that unlock the next stage | Gate PASS verdicts |
| Rule ID | `BRF`, `FACT`, `STR`, `VOI`, `SEO`, `FLOW`, `PLG` prefix plus number, cited by every finding | This repo's agent-config rules (A–G in `CLAUDE.md`) |

## Naming rules
- Skill directories may differ from commands; the command comes from frontmatter `name:` (`COMMANDS` in `tests/test_structure.py`).
- Gate verdict files: `gates/G<n>-<stage>.r<k>.md`.
