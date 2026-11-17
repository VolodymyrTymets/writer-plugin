# ADR-018 — A skill's folder name is its command

- **Date:** 2026-11-17
- **Status:** accepted
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (`docs/features/FT-11-12/plan.md`, finding FT-11)
- **Relation:** replaces the naming rule "skill directories may differ from commands" in `docs/DOMAIN_GLOSSARY.md`.

## Context
Four skills (`intake-brief`, `edit-final`, `setup-workspace`, `sync-comments`) lived in folders that differ from their `name:`. A user ran
`/writer-plugin:setup-workspace` while the skill text says `writer-plugin:setup`. The Claude Code docs say a plugin skill's command is
`/<plugin>:<directory>` and that `name:` replaces the last segment, so the menu shows the `name:` form; they do not say what the folder form does,
and one run resolved it. A command with two names is the defect, whichever resolves.

## Decision
- Every skill's folder name equals its frontmatter `name:`, so `/<plugin>:<folder>` and `/<plugin>:<name>` are the same string.
- `tests/test_structure.py` fails when they differ. `COMMANDS` stays the list of what exists.

## Rejected alternatives
| Alternative | Why not |
|-------------|---------|
| Keep the folders, fix only the text | The folder form stays a second name that may or may not resolve; it depends on behaviour the docs do not state |
| Drop `name:` and rely on the folder | A missing `name:` hides a drift from the test; one explicit field is checked |

## Consequences
- Positive: one name per command in the menu, the skill text, the tests and the folder.
- Negative: old plans and ADR-010 name the old folders; they are history and stay as written. An installed copy keeps the old folders until updated; commands are unchanged.
