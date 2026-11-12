# Architecture

> What the plugin **is** and where things belong. Structure only; the flow, rule IDs and build plan are in `DESIGN.md`.
> Update in the same PR as any structural change (rule E1).

## Repo layout
| Path | What lives here | Loaded by Claude Code? |
|------|-----------------|------------------------|
| `.claude-plugin/` | `plugin.json` (name, version), `marketplace.json` (marketplace `writer`, `source: "./"`) | yes |
| `skills/` | flat: `skills/<dir>/SKILL.md` plus `references/`. None yet (Phase 3 onward) | yes |
| `agents/` | write-free gate agents `gate` and `fact-gate`. None yet | yes |
| `hooks/hooks.json`, `bin/` | hooks and prose-lint, stdlib-only Python 3.9+. `hooks.json` is empty today | yes |
| `rules/core/`, `templates/` | inert library the setup skill copies into a content workspace. `rules/core/CLAUDE.template.md` (editorial constitution) and `templates/` (brief, research, outline, style) | no |
| `tests/` | pytest structure guard (`test_structure.py`), shape guard for the library (`test_templates.py`), `conftest.py` | no |
| `docs/` | `DESIGN.md`, this file, glossary, business model, `decisions/` | no |
| `.claude/` | this repo's own agent config (settings, rules). Not part of the plugin | no |

## Where truth lives
- Per article, **local Markdown** in the user's content workspace (`articles/<slug>/`). Google Docs are review copies (ADR-001).
- Command names: `COMMANDS` and `PLANNED` in `tests/test_structure.py`.
- Version: `.claude-plugin/plugin.json`.

## Boundaries and contracts
| Boundary | Format | Source of truth | Generated output |
|----------|--------|-----------------|------------------|
| Plugin manifest | JSON | `.claude-plugin/plugin.json` | none |
| Skill command name | frontmatter `name:` | `COMMANDS` in `tests/test_structure.py` | none |
| Gate verdict | `PASS` or `BLOCK` with rule IDs | gate skill checklists | saved by the caller in the workspace `gates/` |

Nothing in this repo is generated.

## Environments
There is no deployment. The plugin is installed from the `writer` marketplace by users. Local only; the agent never publishes it (rule C4).

## Key flows
1. **Article chain:** brief → research → outline → human approval → draft → final → human sign-off, each actor followed by its gate.
   Detail: `DESIGN.md`.
2. **Gate:** a forked, write-free agent reads artifacts from disk and returns a verdict; the caller writes it to disk.
3. **Hook:** a stdlib-only script reads the hook event and blocks mechanically (stage order, prose-lint run). Every hook has a pytest case.

## External integrations
| Service | Purpose | Failure mode | Sandbox |
|---------|---------|--------------|---------|
| Google Drive connector | review copies of artifacts | absent in some sessions; the workflow continues on local files | n/a |
| WebFetch / WebSearch | `fact-gate` opens sources | gate cannot verify; reports it rather than passing | n/a |

## Known constraints and landmines
- Gate skills must carry `context: fork`, `background: false` and a write-free agent; the structure test enforces it.
- Planned commands may be named only in `README.md`, `CHANGELOG.md` and `docs/DESIGN.md`, or the structure test fails.
- `claude plugin validate ./ --strict` fails on one expected warning, so CI and the command map use the non-strict form.
