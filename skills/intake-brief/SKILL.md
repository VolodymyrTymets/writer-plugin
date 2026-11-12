---
name: brief
description: Stage 0 actor. Use to turn whatever the user supplied (pasted text, a file, a Google Doc) into a normalised brief.md for a blog post, then run the brief gate. Asks at most two batched rounds of questions.
argument-hint: "[article slug, or a path to the supplied brief]"
allowed-tools: Read, Write, Glob, Grep, Skill, AskUserQuestion
---

# Brief stage

You write exactly one artifact: `articles/<slug>/brief.md`. You never edit a later stage's artifact. When you are
done, the brief gate judges it in a fresh context, and you save its verdict.

## Step 1 — Resolve the article and its input

- Input: `$ARGUMENTS` may be a slug, a path, or empty. The brief itself is pasted text, a file path, or a Google Doc.
  Read a file with Read; for a Google Doc, use a connected Drive read tool if one exists, otherwise ask the user to paste it.
- Slug: lowercase kebab-case from the working title, unless the user gave one. Folder: `articles/<slug>/`.
- Save the input unchanged as `articles/<slug>/brief.source.md`, unless that file already exists.

## Step 2 — Stop if the human is already owed a decision (FLOW-3)

Count the BLOCK verdict files for this artifact: `articles/<slug>/gates/G0-brief.r*.md` whose line 1 contains `BLOCK`.
If there are two or more, stop. Name both files, say what they blocked on, and hand the article to the human. Do not
try a third time; this holds across runs, not only within this one.

## Step 3 — Fill the template

Read `${CLAUDE_PLUGIN_ROOT}/templates/brief.md` and fill every field from the input. Rules:
- Write only what the input supports. A gap that changes the article (reader, goal, keyword, length, CTA, research
  questions) is a question, not a guess.
- Ask in at most **two batched rounds**, all open gaps in one AskUserQuestion call per round. After the second round
  state your assumption for anything still open under "Assumptions made while normalising". Never invent a reader or a keyword.
- Leave no `{{placeholder}}` in the file. "none" is a valid value for must include and must avoid.

Write the result to `articles/<slug>/brief.md`.

## Step 4 — Run the gate and save the verdict

1. Invoke the skill `writer-plugin:check-brief` with the slug through the Skill tool and wait for its verdict.
2. Check that line 1 of the verdict matches
   `^## G0 brief gate: (PASS \(0 blocking|BLOCK \([1-9][0-9]* blocking), [0-9]+ advisory\)$`. If it does not, the
   verdict is malformed: treat it as **no PASS**, save nothing, tell the user what came back, and stop.
3. Save the verdict text unchanged to `articles/<slug>/gates/G0-brief.r<k>.md`, where `k` is 1 plus the number of
   `G0-brief.r*.md` files already there. Never edit a saved verdict.

## Step 5 — On BLOCK

Fix only what the findings name, in `brief.md`; ask the user for any information you lack (it counts against the two
question rounds). Then repeat Step 4. After the second BLOCK on disk, stop as in Step 2.

## Step 6 — On PASS

Report, in a few lines: the brief path, the verdict path, the assumptions you made, and that the next stage is the
research stage. Say once: "Doc copy: not yet available" (the review copy comes with a later phase). Do not start
research yourself.

## Definition of done
- [ ] `brief.source.md` and `brief.md` exist; no `{{` is left
- [ ] The gate ran in a fork and its verdict is saved as `G0-brief.r<k>.md` with a valid first line
- [ ] At most two question rounds were used; assumptions are written in the brief
- [ ] On a second BLOCK the run stopped and named the verdict files
