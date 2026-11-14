---
name: setup
description: Once per content workspace. Use to create the editorial constitution (CLAUDE.md) and the client style guide (.claude/rules/style.md) from the plugin's library, asking for voice, audience, banned phrases, reading level and links. Never overwrites an existing file.
argument-hint: "[project name and style answers pasted, or a path to a file that holds them]"
allowed-tools: Read, Write, AskUserQuestion
---

# Workspace setup

This skill's command is `writer-plugin:setup`; when you tell the user how to rerun it, use that name.

You write at most two files in the current workspace root: `CLAUDE.md` (the editorial constitution) and
`.claude/rules/style.md` (this client's style guide). You never overwrite, edit or merge into an existing `CLAUDE.md` or `.claude/rules/style.md`:
the human owns them once they exist. You write no article and no verdict.

## Step 1 — Refuse in the plugin source

If `.claude-plugin/plugin.json` exists in the current directory and contains `"name": "writer-plugin"`, this is the plugin's own
repository, not a content workspace: stop and write nothing. Say so, and tell the user to run the setup from their content repository.

## Step 2 — See what already exists

Check each of `CLAUDE.md` and `.claude/rules/style.md` with Read on that exact path: a not-found error means the file is absent.
(Do not search for them; a file search may skip hidden folders such as `.claude/`.)
- If both exist, write nothing. Name both files and stop: the workspace is already set up.
- If one exists, name it and say it stays as it is. Go on for the missing file only; Steps 3 to 5 then apply to that file alone.
  If `CLAUDE.md` exists but was not written by this plugin (it lacks the line `Managed by the \`writer-plugin\` plugin`), say that
  the constitution is not loaded until the human merges `${CLAUDE_PLUGIN_ROOT}/rules/core/CLAUDE.template.md` into it by hand.
- If neither exists, write both.

## Step 3 — Collect the answers

Read `${CLAUDE_PLUGIN_ROOT}/rules/core/CLAUDE.template.md` and `${CLAUDE_PLUGIN_ROOT}/templates/style.md`. The answers come from
`$ARGUMENTS` (pasted values, or a path you Read) and the user's message. You need:

`CLAUDE.md` needs only the project name. Every other field is for the style guide; when only `CLAUDE.md` is missing, ask for nothing else.

| Field | Goes into | Required |
|-------|-----------|----------|
| Project or publication name | `{{PROJECT_NAME}}` in both files | yes |
| Readers | Audience | yes |
| Tone, person, do, do not | Voice (VOI-1) | tone and person yes; do and do not may be `none` |
| Banned phrases | `**Phrases:**` (VOI-2) | may be `none` |
| AI tells to flag | `**Tells:**` (VOI-3) | may be `none` |
| Reading level target | VOI-4 | yes |
| Statistic age limit in months | FACT-4 | yes, a whole number |
| Internal links, anchor text → URL | SEO-5 | may be `none` |
| Preferred external publishers | SEO-5 | may be `none` |

Ask for every missing field in at most **two batched rounds**, all gaps in one AskUserQuestion call per round. Never invent a reader, a voice or a link:
a guessed voice makes every voice finding wrong. A list field nobody answered after round two becomes `none`; say so in the report.
If a required field is still open after round two, stop and write nothing, and list what is missing.

These are one client's values. They belong in this workspace only, never in the plugin repository (PLG-1).

## Step 4 — Write the files

If a write is refused (Claude Code asks before writing under `.claude/`, and the user may decline), report that file as not
written, do not retry it, and go on with the other file.

**Write `CLAUDE.md`** — from the constitution template: replace `{{PROJECT_NAME}}` with the name and every `{{STYLE_GUIDE_PATH}}` with
`.claude/rules/style.md`. Change nothing else in the constitution: every rule ID and its wording stays verbatim, because the gates
cite them. Write it with the Write tool.

**Write `.claude/rules/style.md`** — from the style template: replace each `{{...}}` with its answer and keep every `**Label:**`
exactly as the template has it, because `prose-lint.py` finds the lists by label. Write `**Phrases:**` and `**Tells:**` each on one line, comma separated
(the script reads only that line); `none` alone means an empty list. Internal links go one line per page, as the template says.

## Step 5 — Check

Read back each file you wrote: no `{{` is left, and the `**Phrases:**` and `**Tells:**` lines are present. If a placeholder remains,
rewrite that file (one you wrote in this run, never a file that existed before) with the missing value, or stop and report it.

## Step 6 — Report

In a few lines: the files written and the ones left alone; each list field written as `none` because nobody answered; that the
style guide is the client's and gates never edit it (FLOW-5). Next step: `writer-plugin:article <slug>` with a brief, or
`writer-plugin:brief` for the brief stage alone.

## Definition of done
- [ ] In the plugin repository, nothing was written
- [ ] No existing `CLAUDE.md` or `.claude/rules/style.md` was changed
- [ ] Every file written has no `{{` left, and the constitution's rule IDs are unchanged
- [ ] At most two question rounds; nothing about the reader or the voice was invented
