---
name: draft
description: Stage 3 actor. Use after a human has approved the outline, to write draft.md section by section from it, every factual claim tagged with its fact ID and every unverified marker carried through unchanged, then run the draft gate. It never edits the outline or the research.
argument-hint: "[article slug, defaults to the most recently changed outline]"
allowed-tools: Read, Write, Glob, Grep, Skill, Bash(python3 ${CLAUDE_PLUGIN_ROOT}/bin/prose-lint.py *)
---

# Draft stage

You write exactly one artifact: `articles/<slug>/draft.md`. You never edit the brief, the research or the outline; if one
of them is wrong, stop and say so. The draft gate judges your output in a fresh context.

## Step 1 — Resolve the article

`$ARGUMENTS` is a slug; if empty, the most recently modified `articles/*/outline.md`. Name what you settled on.

## Step 2 — Preconditions (FLOW-1, FLOW-2, FLOW-3)

- **FLOW-1:** list `articles/<slug>/gates/G2-outline.r*.md`, take the highest `k`, and read its line 1. It must match
  `^## G2 outline gate: PASS \(0 blocking, [0-9]+ advisory\)$`. If no such file exists, or the latest one is a BLOCK,
  stop: name the file you needed and say the outline stage has to run first.
- **FLOW-2:** `articles/<slug>/outline.md` must have a non-empty value after `Approved-by:`. An empty line is not approval.
  If it is empty, stop and say a human reads the outline and writes their name there. Never fill it yourself.
- **FLOW-3:** count `articles/<slug>/gates/G3-draft.r*.md` whose line 1 contains `BLOCK`. If there are
  two or more, stop, name both files and hand the article to the human. This holds across runs. A human resumes the article by moving **every** `G3-draft.r*.md` file, PASS ones too, into `articles/<slug>/gates/archive/`; you never move or edit a verdict yourself.

## Step 3 — Write the draft

Read `brief.md`, `outline.md` and `research.md`. If `.claude/rules/style.md` exists, read it for voice and the link list; if not,
say so in your report. Write the article from the outline's Structure table, row by row, in order.

- **Headings:** the H1 is the outline's first title option; each row becomes a heading at its level with the outline's heading text.
- **Opening:** the first 100 words state the promise and contain the primary keyword, as the intro hook plans.
- **Each section:** do what its Purpose says, cover its Key points, aim at its word budget. The whole draft lands within 10% of the
  brief's target length (STR-6).
- **Fact IDs (FACT-1):** every sentence with a statistic, a date, a named claim or a quote ends with `[F#]`, using only IDs in the
  outline row's Fact IDs cell that exist in `research.md`. The sentence says no more than the bank row's claim does (FACT-5). A
  quote is the row's verbatim quote. The IDs stay in the draft; they are stripped only in the Doc copy.
- **No new facts.** Your own knowledge, the brief and Open gaps are not sources. A claim the bank does not support is dropped, or it is
  an outline marker (below). Never invent a number, a name, a quote or a price.
- **Markers:** where the outline holds `<Can't be verified. Reason: reason sentence here>` in a cell, write that exact marker in the
  draft in place of the claim, character for character, and keep the section. Never rewrite it, never explain it, never state the
  claim beside it. Add none of your own. Your report lists every marker and the count.
- **Links:** internal links only from the style guide's list; external links only to sources in the fact bank.
- **The close** delivers the brief's one CTA as the outline's Call to action section says. Nothing from the brief's "must avoid"
  appears; every "must include" does. Leave no `{{placeholder}}`.

Before you write, if `draft.md` already exists, read it and copy it to `articles/<slug>/draft.prev.<n>.md`, where `n` is 1 plus
the highest `n` among existing `draft.prev.*.md` files (1 if there are none). Never replace an earlier backup: a human's
hand-edited draft must not be lost. Then write the result to `articles/<slug>/draft.md`.

## Step 4 — Check mechanically, then run the gate and save the verdict

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/prose-lint.py articles/<slug>/draft.md` (no `--record`; it writes nothing). Fix what it
   reports on STR-4, STR-6 and FACT-1 in `draft.md` now; a FACT-1 hit may be a false positive (a number that is not a claim), and
   then you leave it and say so. This is before the gate: after a PASS you never edit.
2. Invoke the skill `writer-plugin:check-draft` with the slug through the Skill tool and wait for its verdict.
3. Check that line 1 matches
   `^## G3 draft gate: (PASS \(0 blocking|BLOCK \([1-9][0-9]* blocking), [0-9]+ advisory\)$`. If it does not, treat
   it as **no PASS**, save nothing, tell the user what came back, and stop.
4. Save the verdict unchanged, with the Write tool, to `articles/<slug>/gates/G3-draft.r<k>.md`, `k` being 1 plus the highest `r<k>` number found in `gates/` and `gates/archive/` (a count would reuse a number after an archive and overwrite a saved verdict). Never edit a saved verdict.

## Step 5 — On BLOCK

Fix only what the findings name, in `draft.md`. Then repeat Step 4. After the second BLOCK on disk, stop as in Step 2.

## Step 6 — On PASS

Report in a few lines: the draft path, the verdict path, the markers (each, and the count), and the gate's advisory findings.
Say once: "Doc copy: not yet available". The next stage is the edit stage.

## After the gate

The verdict covers the artifact as it was when the gate ran. After a PASS you never edit the artifact: report the gate's
advisory findings to the user and stop. If the artifact has to change, change the stage's written input and run the stage
again (a different draft needs a changed outline: rerun the outline stage, which clears its approval); the rebuilt artifact is gated again and its verdict is saved as the next `r<k>`. A BLOCK from a rerun
counts toward FLOW-3 like any other BLOCK. When you replace an artifact and a later stage's artifact already exists
(`final.md`), say in your report that it was built on the replaced version and must be rerun. If the human changed `draft.md` by hand, the verdict no longer covers it: ask for the draft gate to be rerun on the edited file and its verdict saved with the Write tool as the next verdict. A re-gate saves its verdict whether PASS or BLOCK, and a BLOCK counts toward FLOW-3.

## Definition of done
- [ ] `draft.md` exists, no `{{` left, every outline row is a section, every factual sentence carries an `[F#]` that exists
- [ ] Every marker is the outline's, unchanged; the report lists them
- [ ] `prose-lint.py` ran without `--record` before the gate
- [ ] The gate ran in a fork and its verdict is saved as `G3-draft.r<k>.md` with a valid first line
- [ ] On a second BLOCK the run stopped and named the verdict files
