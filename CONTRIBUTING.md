# Contributing to writer-plugin

How the plugin is built and what a change needs before it merges. The *why* — flow, rule IDs, hooks, Google Docs
approach and the build plan — is in [docs/DESIGN.md](docs/DESIGN.md).

## Layout

| Path | Contents | Loaded by Claude Code? |
|------|----------|------------------------|
| `.claude-plugin/` | `plugin.json` (name, version), `marketplace.json` | yes |
| `skills/` | **flat**: one directory per skill, `SKILL.md` plus `references/` | yes |
| `agents/` | write-free gate agents (`gate`, `fact-gate`) | yes |
| `hooks/hooks.json` + `bin/` | hooks and the prose-lint script, stdlib-only Python 3.9+ | yes |
| `rules/core/` | the editorial constitution template with rule IDs | no — copied into a workspace by the setup skill |
| `templates/` | brief, research dossier, outline, style guide templates | no — copied or read by skills |
| `tests/` | pytest: structure guard now, hook behaviour later | no |
| `docs/` | design | no |

### Command names

A plugin skill takes its command from frontmatter `name:`, not its directory. The map is `COMMANDS` in
`tests/test_structure.py`; commands not built yet are in `PLANNED`. The test fails when a skill's `name:` drifts from
the map, when a name collides with a built-in, or when a document presents a command that does not exist. Planned
commands may appear only in `README.md`, `CHANGELOG.md` and `docs/DESIGN.md`.

### Gates are forked by construction

A gate asked to "use a fresh context" in prose is a request. `context: fork` plus a scoped, write-free `agent:` is the
mechanism, and `background: false` keeps the caller waiting for the verdict. The structure test enforces all three for
every skill in `GATE_SKILLS`.

## Testing

```bash
python -m pytest
claude plugin validate ./ --strict
```

A hook change without a test case is not accepted: a false block wastes a writer's turn, and a missed block means the
rule quietly stopped existing.

## Adding to this plugin

1. Client-specific knowledge never enters this repo (PLG-1). Generalise it, or put it in a workspace's `style.md`.
2. A new skill: add it to `COMMANDS` (and to `GATE_SKILLS` if it judges an artifact), remove it from `PLANNED`.
3. Prefer a script or a hook over a prompt rule.
4. Both checks above before opening a PR. `CHANGELOG.md` leads with what was deleted.
