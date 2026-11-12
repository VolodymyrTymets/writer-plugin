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

| Task | Command |
|------|---------|
| install | `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt` |
| lint | `none` (no linter configured) |
| unit tests | `.venv/bin/python -m pytest` (structure guard, and hook tests once hooks exist) |
| affected tests | `.venv/bin/python -m pytest <path>` |
| validate | `claude plugin validate ./` (passes with one expected warning: this file is not loaded as plugin context; `--strict` fails on it) |
| build / dev / e2e | `none` |

Dependency manager: **pip** into `.venv`. Runtime: Python **3.9+** (no version pin file; CI uses 3.9).

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

## Rules for working here

Hard rules only; depth is in `.claude/rules/` and `docs/`.

- **T1** Run tasks through the command map above; never invent a script name. Install only into `.venv`
  (`.venv/bin/pip`), never a bare `pip install`. Python is pinned at 3.9+; if the local interpreter is older, stop and report.
- **A1** Never commit or push to `main`. Branch as `feat|fix|chore/<slug>` (no tracker, so no ticket ID).
- **A2** No `git push --force` to a shared branch; no rewriting pushed history.
- **A4** One PR = one change, opened as a **draft**. A human marks it ready; you never approve or merge.
- **A5** Conventional Commits, imperative mood. **A6** Never commit secrets, `.env*`, tokens or client data.
- **A7** The PR body follows `.github/PULL_REQUEST_TEMPLATE.md`: what, why, verification (commands and output), not verified.
- **B1** Done means the checks pass **and** the change was executed: the skill, hook or script actually run on a sample.
  What cannot run here goes under "Not verified". Report exact commands and real output (B2).
- **B3** Never make a check pass by weakening it: no skipped or narrowed tests, no deleted assertions, no `# noqa` /
  `# type: ignore` without a human-approved `WHY:`.
- **B4** If the right fix is bigger than the task, stop and report.
- **C1** Change only what the task needs. **C2** No new dependency without approval; hooks and scripts are stdlib-only.
- **C3** Never hand-edit generated or protected paths (`.claude/rules/protected-paths.md`).
- **C4** No destructive or irreversible command (publishing the plugin, `rm -rf`, force push) without explicit confirmation.
- **D1** Read the neighbouring skill, hook or test before writing; follow its pattern. A new pattern needs an ADR.
- **D4** Never invent a Claude Code plugin API; check Context7 or the docs. Never state that a connector tool can do something unverified.
- **D6** Comments explain why. No commented-out code; no `TODO` without an owner and date.
- **E1** Docs update in the same PR: `docs/DESIGN.md` for flow, rule-ID or build-plan changes, `docs/ARCHITECTURE.md`
  for layout changes, `docs/DOMAIN_GLOSSARY.md` for new terms, an ADR for a settled decision.
- **F1** Ask only gaps you cannot resolve from the repo; max two rounds, then state assumptions. **F3** Say "not sure" plainly.
- **G2** Nothing client-specific enters this repo (PLG-1).

Project rules above (`PLG-1`, gates read-only and forked) outrank this list when they conflict.

## Where things live

- Python rules: `.claude/rules/` (auto-loaded by path). Protected paths: `.claude/rules/protected-paths.md`.
- Architecture: @docs/ARCHITECTURE.md · Goals and tie-breakers: @docs/BUSINESS_MODEL.md · Terms: @docs/DOMAIN_GLOSSARY.md
- Settled decisions: `docs/decisions/` · Design and build plan: `docs/DESIGN.md`
