# FT-11, FT-12 — implementation plan

No tracker. Branch `fix/ft-11-12`, cut from `main`. One draft PR (A4). Spec: `spec.md`.

<!-- A human writes this line to approve. Until it is here, guard-plan-approval blocks writes to code. -->
Approved-by: Volodymyr · 2026-11-17

Pattern followed: FT-8-10 (`docs/features/FT-8-10/plan.md`): skill text pinned by `tests/test_skills.py`, the structure map in
`tests/test_structure.py` (ask-first path). Skill folders already equal their command for 10 of 14 skills; this makes it 14 of 14.
Slug handling: `skills/article/SKILL.md` lines 21-24 and `bin/article-status.py` (read-only). No missing precedent. Retiring the
glossary rule "directories may differ" is a change of convention, so it gets `ADR-018`.

## Contract changes
- **command surface:** none. `name:` is unchanged, so `/writer-plugin:brief|edit|setup|sync` stay; the folder-name forms stop being the folder.
- **paths:** `skills/{intake-brief,edit-final,setup-workspace,sync-comments}` move to `skills/{brief,edit,setup,sync}` (`git mv`, history kept).
- data / generated output: none. No dependency (C2).

## Requirements (ordered, each independently verifiable)

### R1 — FT-11: folder name = command (M)
- files: `git mv` the four folders; `tests/test_structure.py` (`COMMANDS` keys, line 14 comment; new check), `tests/test_skills.py`
  (every `intake-brief`, `edit-final`, `setup-workspace`, `sync-comments` string, lines 44-899), `tests/test_hooks.py:2189` (docstring path),
  `docs/DOMAIN_GLOSSARY.md` (naming rule, line 38), `docs/ARCHITECTURE.md` if it names a folder, `docs/DESIGN.md` (FT-11 status), `CONTRIBUTING.md` ("Command names", line 22), `CHANGELOG.md`,
  `docs/decisions/ADR-018-folder-is-the-command.md` (new)
- layer: plugin layout and structure guard.
- test: new case in `tests/test_structure.py`: for every `skills/<d>/SKILL.md`, `name:` equals `<d>`. It is added, nothing weakened (B3);
  `COMMANDS` stays as the list of what exists.
- executed how: `.venv/bin/python -m pytest` (full); `claude plugin validate ./`; `grep -rnE "intake-brief|edit-final|setup-workspace|sync-comments" . --exclude-dir=.git --exclude-dir=.venv`
  lists only history files, `ADR-018` and the FT-11 row of `docs/DESIGN.md` (which quotes the old names on purpose); then load the plugin from the repo (`claude -p --plugin-dir /Users/work/Documents/projects/ai/agents/writer-plugin --disallowedTools "mcp__claude_ai_Google_Drive__* mcp__claude_ai_Google_Docs__*"`,
  run from a scratch workspace outside the repo, since `.` would be the workspace) and run `/writer-plugin:setup` and `/writer-plugin:brief` to see them resolve.
  A headless run can have the Drive connector (ADR-016.10), so the disallow is what keeps it off Drive. If the plugin cannot be loaded this way, say so under "Not verified".
- risk: the ask-first `tests/test_structure.py` edit needs a human confirmation in the session; a missed string in `test_skills.py` fails loudly.

### R2 — FT-12: a missing slug in `sync` and `publish` (S)
- files: `skills/sync/SKILL.md` (Step 1 and `allowed-tools`: add `Glob`, `AskUserQuestion`), `skills/publish/SKILL.md` (line 20 and `allowed-tools`),
  `tests/test_skills.py`
- layer: skill text. A script would be sturdier (hook over prompt, rule T1) but `article-status.py` prints one article's state; a lister is a new
  script surface for a two-line rule, so the plan keeps it in text (see risks).
- text, identical in both: list `articles/*/brief.md` with Glob; one → take it and name it in the report; 2 to 4 → one `AskUserQuestion`, one option per
  folder (the tool takes 2 to 4); more → print the folders and ask for the slug in plain text; none → "no articles in this workspace", stop.
  "Never guess it from the newest folder" stays. A lone argument that is one of `brief`, `research`, `outline`, `draft`, `final` is the stage and the
  slug is missing (the FT-12 case, `/sync research`).
- test: both skills' flat text pins "one article", "AskUserQuestion", "more than four", "never guess" and the lone-stage-argument line; `allowed-tools` contains `Glob` and `AskUserQuestion`.
- executed how: scratch workspace outside this repo with one article folder and a `docs.json`: run `claude -p --plugin-dir <absolute plugin path> --disallowedTools "mcp__claude_ai_Google_Drive__* mcp__claude_ai_Google_Docs__*"` with `/writer-plugin:sync research` (slug missing).
  With Drive disallowed the run reaches Step 2 and stops on its "no Google Drive connection" line, which proves Step 1 took the slug; that line is the evidence.
  Then add a second folder and run again: expect the question with two options. Report both outputs.
- risk: the question is interactive, so the headless run can show only the one-article path; the two-folder path is then "Not verified" unless run interactively.

## Docs to update in this PR
- [ ] docs/features/FT-11-12/spec.md (acceptance criteria checked off)
- [ ] docs/ARCHITECTURE.md — only if it names an old folder
- [ ] CONTRIBUTING.md — the command-name rule and what the structure test fails on
- [ ] docs/DOMAIN_GLOSSARY.md — naming rule
- [ ] docs/DESIGN.md — FT-11 and FT-12 rows to "fixed"
- [ ] docs/decisions/ADR-018 — folder is the command

## Risks
| Risk | Impact | Cheapest way to find out early |
|------|--------|-------------------------------|
| The rename leaves a stale path in a test or doc | red suite, or a wrong pointer | the grep in R1, run first and last |
| Installed copies of the plugin keep the old folders until updated | none for commands (`name:` unchanged) | CHANGELOG line |
| Plain-text prompt for slugs is less reliable than a script | a wrong slug is still possible if the actor ignores the text | pinned wording plus the executed run; a lister script is the follow-up if it recurs |

## Assumptions
- The docs' `/<plugin>:<directory>` rule is current (Context7, code.claude.com/docs/en/plugins/components, 2026-11-17).
- "An article" is a folder under `articles/` with a `brief.md`.
- `AskUserQuestion` accepts 2 to 4 options (its own schema).
