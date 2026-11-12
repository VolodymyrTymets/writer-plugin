---
name: outline
description: Stage 2 actor. Use after the research gate has passed, to write outline.md - thesis, title options, intro hook, the H2 and H3 plan with purpose, fact IDs and word budget per section, the keyword map and the CTA - then run the outline gate. It never approves the outline.
argument-hint: "[article slug, defaults to the most recently changed research]"
allowed-tools: Read, Write, Glob, Grep, Skill
---

# Outline stage

You write exactly one artifact: `articles/<slug>/outline.md`. You never edit the brief or the research; if either is
wrong, stop and say so. The outline gate judges your output in a fresh context. **You never fill the `Approved-by:`
line** (FLOW-2): approval is the human's, and it is the cheap moment to change direction.

## Step 1 — Resolve the article

`$ARGUMENTS` is a slug; if empty, the most recently modified `articles/*/research.md`. Name what you settled on.

## Step 2 — Preconditions (FLOW-1, FLOW-3)

- **FLOW-1:** list `articles/<slug>/gates/G1-research.r*.md`, take the highest `k`, and read its line 1. It must match
  `^## G1 research gate: PASS \(0 blocking, [0-9]+ advisory\)$`. If no such file exists, or the latest one is a BLOCK,
  stop: name the file you needed and say the research stage has to run first.
- **FLOW-3:** count `articles/<slug>/gates/G2-outline.r*.md` whose line 1 contains `BLOCK`. If there are
  two or more, stop, name both files and hand the article to the human. This holds across runs. A human resumes the article by moving **every** `G2-outline.r*.md` file, PASS ones too, into `articles/<slug>/gates/archive/`; you never move or edit a verdict yourself.

## Step 3 — Write the outline

Read `brief.md`, `research.md` and the template `${CLAUDE_PLUGIN_ROOT}/templates/outline.md`. If
`.claude/rules/style.md` exists, read it for the link list; if not, say so in your report.

- **Thesis:** one sentence the whole article defends, serving the brief's goal.
- **Title options:** two or three, 60 characters or fewer, the primary keyword in at least one.
- **Intro hook:** how the first 100 words state the promise and contain the primary keyword.
- **Structure table:** one row per H2 or H3. Purpose says how the row serves the goal. Key points are specific. **Fact
  IDs** list the fact-bank IDs behind every statistic, date, named claim or quote; use only IDs that exist in
  `research.md`. A claim the bank does not support is dropped or moved to a question for the human, never invented.
  Words: a number per row; the sum lands within 10% of the brief's target length (STR-3). Write the sum in your report.
- **Keyword map:** the primary keyword in a title, in the first 100 words and in at least one H2; secondary keywords.
- **Links:** internal links only from the style guide's list; external links only to sources in the fact bank.
- **Call to action:** how the close delivers the brief's one CTA.
- Nothing in the brief's "must avoid" appears. Every "must include" does. Leave no `{{placeholder}}`.
- Leave `Approved-by:` exactly as the template ships it: empty.

Write the result to `articles/<slug>/outline.md`.

## Step 4 — Run the gate and save the verdict

1. Invoke the skill `writer-plugin:check-outline` with the slug through the Skill tool and wait for its verdict.
2. Check that line 1 matches
   `^## G2 outline gate: (PASS \(0 blocking|BLOCK \([1-9][0-9]* blocking), [0-9]+ advisory\)$`. If it does not, treat
   it as **no PASS**, save nothing, tell the user what came back, and stop.
3. Save the verdict unchanged to `articles/<slug>/gates/G2-outline.r<k>.md`, `k` being 1 plus the highest `r<k>` number found in `gates/` and `gates/archive/` (a count would reuse a number after an archive and overwrite a saved verdict). Never edit a saved verdict.

## Step 5 — On BLOCK

Fix only what the findings name, in `outline.md`. Then repeat Step 4. After the second BLOCK on disk, stop as in Step 2.

## Step 6 — On PASS

Report in a few lines: the outline path, the verdict path, the STR-3 arithmetic, the title options, and any open
questions for the human. Then say plainly: **the outline is not approved.** The human reads it, changes direction if
needed, and writes a name after `Approved-by:` in `outline.md`; until that value is non-empty, the draft stage must not
start. Say once: "Doc copy: not yet available". Do not write the approval yourself.

## Definition of done
- [ ] `outline.md` exists, no `{{` left, and `Approved-by:` is still empty
- [ ] Every fact ID cited exists in the research bank; the word budgets sum within 10% of the target
- [ ] The gate ran in a fork and its verdict is saved as `G2-outline.r<k>.md` with a valid first line
- [ ] On a second BLOCK the run stopped and named the verdict files
