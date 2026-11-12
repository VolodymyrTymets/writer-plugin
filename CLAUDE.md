# CLAUDE.md

Guidance for Claude Code when working **on this repository**.

## What this repo is

The **source of the `writer-plugin` Claude Code plugin**, not a content workspace. It is also its own marketplace
(`.claude-plugin/marketplace.json`, marketplace `writer`, plugin `source: "./"`). No build step: Markdown, JSON and
stdlib-only Python 3.9+ scripts. Maintainers install `requirements-dev.txt` (pytest) to run the tests.

Do not write articles here, and do not run the plugin's setup skill here — that is for content workspaces.

- `docs/DESIGN.md` — the flow, rule IDs, hooks, Google Docs approach, open questions and the build plan. Read it first.
- `README.md` — user-facing. `CONTRIBUTING.md` — how the repo is built and what a change needs.

## Commands

```bash
python -m pytest                       # structure guard (and hook tests once hooks exist)
claude plugin validate ./ --strict     # one warning is expected: this file is not loaded as plugin context
```

## Architecture in one paragraph

Actors write one artifact each; gates judge one artifact each, **read-only, forked**, and return PASS or BLOCK with
rule IDs. Local Markdown in the content workspace is the source of truth; Google Docs are review copies. A human
approves the outline (`Approved-by:`) and signs off the final (`Signed-off-by:`). Claude Code loads only `skills/`,
`agents/`, `hooks/hooks.json` and `.claude-plugin/`; `rules/` and `templates/` are an inert library that the setup
skill copies into a workspace.

## Conventions

- Skills are flat (`skills/<dir>/SKILL.md` plus `references/` only). A skill's command comes from frontmatter `name:`;
  the map is `COMMANDS` in `tests/test_structure.py`, and planned ones are in `PLANNED`.
- Every gate skill carries `context: fork`, `background: false` and a scoped write-free agent (`writer-plugin:<agent>`).
- A hook change needs a test case. Prefer a script or hook over a prompt rule.
- Client-specific knowledge never enters this repo (PLG-1); it belongs in a workspace's `style.md`.
- `CHANGELOG.md` leads with a "Deleted" section; the version lives in `.claude-plugin/plugin.json`.
- Default branch `main`. Branch before committing.
