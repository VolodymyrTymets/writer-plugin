---
name: brief
description: Stage 0 actor. Use to turn whatever the user supplied (pasted text, a file, a Google Doc) into a normalised brief.md for a blog post, then run the brief gate. Asks at most two batched rounds of questions.
argument-hint: "[article slug, or a path to the supplied brief]"
allowed-tools: Read, Write, Glob, Grep, Skill, AskUserQuestion
---

# Brief stage

This stage's command is `writer-plugin:brief`; when you tell the user how to rerun it, use that name.

You write exactly one artifact: `articles/<slug>/brief.md`. You never edit a later stage's artifact. When you are
done, the brief gate judges it in a fresh context, and you save its verdict.

## Step 1 — Resolve the article and its input

- Input: `$ARGUMENTS` may be a slug, a path, or empty. The brief itself is pasted text, a file path, or a Google Doc.
  Read a file with Read; for a Google Doc, use a connected Drive read tool if one exists, otherwise ask the user to paste it.
- Slug: lowercase kebab-case from the working title, unless the user gave one. Folder: `articles/<slug>/`.
- Save the input unchanged as `articles/<slug>/brief.source.md`. If that file exists and the new input differs, the human
  has supplied a correction: copy the old file to `brief.source.prev.md` (replacing any earlier one) and save the new input
  as `brief.source.md`. Then build `brief.md` from the new input. Before rebuilding, read the previous `brief.md` if
  there is one and carry its `<field>: answered by the user, round <n>` lines forward verbatim, keeping their original
  `round <n>`, unless the corrected input overrides the field: the gate cannot see the chat, so those lines are the record.

## Step 2 — Stop if the human is already owed a decision (FLOW-3)

Count the BLOCK verdict files for this artifact: `articles/<slug>/gates/G0-brief.r*.md` whose line 1 contains `BLOCK`.
If there are two or more, stop. Name both files, say what they blocked on, and hand the article to the human. Do not
try a third time; this holds across runs, not only within this one. A human resumes the article by moving **every** `G0-brief.r*.md` file, PASS ones too, into `articles/<slug>/gates/archive/`; you never move or edit a verdict yourself.

## Step 3 — Fill the template

Read `${CLAUDE_PLUGIN_ROOT}/templates/brief.md` and fill every field from the input. Rules:
- Write only what the input supports. A gap that changes the article (reader, goal, keyword, length, CTA, research
  questions) is a question, not a guess.
- Ask in at most **two batched rounds**, all open gaps in one AskUserQuestion call per round. After the second round
  state your assumption for anything still open under "Assumptions made while normalising". Record every answer the user
  gave in a round there too, as `<field>: answered by the user, round <n>`: the gate cannot see the chat. Never invent a reader or a keyword.
- Leave no `{{placeholder}}` in the file. "none" is a valid value for must include and must avoid.

Write the result to `articles/<slug>/brief.md`.

## Step 4 — Run the gate and save the verdict

1. Invoke the skill `writer-plugin:check-brief` with the slug through the Skill tool and wait for its verdict.
2. Check that line 1 of the verdict matches
   `^## G0 brief gate: (PASS \(0 blocking|BLOCK \([1-9][0-9]* blocking), [0-9]+ advisory\)$`. If it does not, the
   verdict is malformed: treat it as **no PASS**, save nothing, tell the user what came back, and stop.
3. Save the verdict text unchanged, with the Write tool, to `articles/<slug>/gates/G0-brief.r<k>.md`, where `k` is 1 plus the highest `r<k>` number found in `gates/` and `gates/archive/` (a count would reuse a number after an archive and overwrite a saved verdict). Never edit a saved verdict.

## Step 5 — On BLOCK

Fix only what the findings name, in `brief.md`; ask the user for any information you lack (it counts against the two
question rounds). Then repeat Step 4. After the second BLOCK on disk, stop as in Step 2.

## Step 6 — On PASS

Report, in a few lines: the brief path, the verdict path, the assumptions you made, and that the next stage is the
research stage. Say once: "Doc copy: not yet available" (the review copy comes with a later phase). Do not start
research yourself.

## After the gate

The verdict covers the artifact as it was when the gate ran. After a PASS you never edit the artifact: report the gate's
advisory findings to the user and stop. If the artifact has to change, change the stage's written input and run the stage
again (a corrected input file, saved as `brief.source.md` in Step 1); the rebuilt artifact is gated again and its verdict is saved as the next `r<k>`. A BLOCK from a rerun
counts toward FLOW-3 like any other BLOCK. When you replace an artifact and a later stage's artifact already exists
(`research.md` or `outline.md`), say in your report that it was built on the replaced version and must be rerun. The human approval line is the
one thing a human writes after a PASS; it does not change what the verdict covers.

## Definition of done
- [ ] `brief.source.md` and `brief.md` exist; no `{{` is left
- [ ] The gate ran in a fork and its verdict is saved as `G0-brief.r<k>.md` with a valid first line
- [ ] At most two question rounds were used; assumptions are written in the brief
- [ ] On a second BLOCK the run stopped and named the verdict files
