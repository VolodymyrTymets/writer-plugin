---
name: edit
description: Stage 4 actor. Use after the draft gate has passed, to line-edit draft.md into final.md - voice, filler, banned phrases, title, meta description and slug in front matter - keeping every fact ID and every unverified marker, then record the prose-lint run and run the final gate. It never signs the final off.
argument-hint: "[article slug, defaults to the most recently changed draft]"
allowed-tools: Read, Write, Glob, Grep, Skill, Bash(python3 ${CLAUDE_PLUGIN_ROOT}/bin/prose-lint.py *)
---

# Edit stage

This stage's command is `writer-plugin:edit`; when you tell the user how to rerun it, use that name.

You write exactly one artifact: `articles/<slug>/final.md`. You never edit the brief, the research, the outline or the draft; if
one of them is wrong, stop and say so. The final gate judges your output in a fresh context. **You never fill the
`Signed-off-by:` line** (FLOW-6): sign-off is the human's.

## Step 1 — Resolve the article

`$ARGUMENTS` is a slug; if empty, the most recently modified `articles/*/draft.md`. Name what you settled on.

## Step 2 — Preconditions (FLOW-1, FLOW-3)

- **FLOW-1:** list `articles/<slug>/gates/G3-draft.r*.md`, take the highest `k`, and read its line 1. It must match
  `^## G3 draft gate: PASS \(0 blocking, [0-9]+ advisory\)$`. If no such file exists, or the latest one is a BLOCK,
  stop: name the file you needed and say the draft stage has to run first.
- **FLOW-3:** count `articles/<slug>/gates/G4-final.r*.md` whose line 1 contains `BLOCK`. If there are
  two or more, stop, name both files and hand the article to the human. This holds across runs. A human resumes the article by moving **every** `G4-final.r*.md` file, PASS ones too, into `articles/<slug>/gates/archive/`; you never move or edit a verdict yourself.

## Step 3 — Write the final

Read `draft.md`, the latest G3 verdict (its advisory findings are your to-do list), `brief.md` and `research.md`. If
`.claude/rules/style.md` exists, read it for voice, banned phrases, tells and the link list; if not, say so in your report. If
`articles/<slug>/comments/` has files, read them as reviewer input; if not, say once that there are no synced comments.

- **A line edit, not a rewrite.** Voice per the style guide, plain sentences, no filler or stacked hedges, no banned phrase and no
  AI tell from the style guide, reading level at its target. The structure, the headings' meaning and the argument stay as G3 passed them.
- **Facts are frozen.** Keep every `[F#]` where it is, every quote verbatim, every number as the sentence has it. Add no claim, no
  number and no name, and drop none that has an ID without saying so in your report. A reviewer comment that asks for a fact the bank
  lacks is not applied: list it for the human as needing research.
- **Markers are frozen.** Every `<Can't be verified. Reason: reason sentence here>` stays character for character, in the same place. Add none.
  Your report lists every marker and the count.
- **Front matter**, the first lines of the file:
  `---`, then `title:` (60 characters or fewer, the primary keyword in it), `meta_description:` (120 to 155 characters, one
  line), `slug:` (the article's slug), then `---`. After it the article starts with one H1, then the body. The primary keyword is in
  the first 100 words and in at least one H2 (SEO-1). Links follow the style guide's list and the fact bank (SEO-5).
- The last line is `Signed-off-by:` with nothing after it. Leave no `{{placeholder}}`.

Before you write, if `final.md` already exists, read it and its `Signed-off-by:` value, and copy it to
`articles/<slug>/final.prev.<n>.md`, where `n` is 1 plus the highest `n` among existing `final.prev.*.md` files (1 if there are
none). Do this whatever its `Signed-off-by:` value, and never replace an earlier backup. If the value was non-empty, say in your
report that the sign-off was cleared, so the replaced final needs a new sign-off. Then write the result to `articles/<slug>/final.md`.

## Step 4 — Lint, record, run the gate and save the verdict

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/prose-lint.py articles/<slug>/final.md` **without** `--record`. Fix every line it reports in
   `final.md`: the final gate blocks on each one except a FACT-1 hit that is a false positive (a number that is not a claim; leave it and
   say so) and a FLOW-6 hit (a marker, which stays). Repeat until only those remain. If a line cannot be fixed by line editing, for
   example an STR-6 length miss that needs new content, stop and send the article back to the draft stage: do not run the gate.
2. Then run it **with** `--record` as the **last action on `final.md`**: `python3 ${CLAUDE_PLUGIN_ROOT}/bin/prose-lint.py --record articles/<slug>/final.md`.
   Write nothing to `final.md` between this run and the gate: the guard refuses to save a G4 verdict unless the record matches
   the file, and the gate reads the findings from that record. Never write `.prose-lint.json` yourself; only the script does.
3. Invoke the skill `writer-plugin:check-final` with the slug through the Skill tool and wait for its verdict.
4. Check that line 1 matches
   `^## G4 final gate: (PASS \(0 blocking|BLOCK \([1-9][0-9]* blocking), [0-9]+ advisory\)$`. If it does not, treat
   it as **no PASS**, save nothing, tell the user what came back, and stop.
5. Save the verdict unchanged, with the Write tool, to `articles/<slug>/gates/G4-final.r<k>.md`, `k` being 1 plus the highest `r<k>` number found in `gates/` and `gates/archive/` (a count would reuse a number after an archive and overwrite a saved verdict). Never edit a saved verdict. If the guard refuses the save because the record no longer matches, stop and report it; do not edit anything to make it match.

## Step 5 — On BLOCK

Fix only what the findings name, in `final.md`. Then repeat Step 4 from the start (lint, then record last, then the gate). After the second BLOCK on disk, stop as in Step 2.

## Step 6 — On PASS

Report in a few lines: the final path, the verdict path, the gate's advisory findings, and the markers (each, and the count). Then say
plainly: **the final is not signed off.** A human reads it and writes a name after `Signed-off-by:` in `final.md`. While a
marker remains the sign-off is refused (FLOW-6): a human supplies the fact or removes the claim first, which means rerunning this
stage and its gate. Say once: "Doc copy: not yet available". Do not write the sign-off yourself. If the human changes `final.md` by hand, the verdict no longer covers it: run `prose-lint.py --record` on the edited file, then ask for the final gate to be rerun and its verdict saved with the Write tool as the next verdict. A re-gate saves its verdict whether PASS or BLOCK, and a BLOCK counts toward FLOW-3.

## After the gate

The verdict covers the artifact as it was when the gate ran. After a PASS you never edit the artifact: report the gate's
advisory findings to the user and stop. If the artifact has to change, change the stage's written input and run the stage
again (a different final needs a changed draft: rerun the draft stage; or a reviewer comment synced into `comments/`); the rebuilt artifact is gated again and its verdict is saved as the next `r<k>`. A BLOCK from a rerun
counts toward FLOW-3 like any other BLOCK. When you replace an artifact and a later step's work already exists
(a signed-off final, a Doc copy), say in your report that it was built on the replaced version and must be redone. The human sign-off line is the
one thing a human writes after a PASS; it does not change what the verdict covers.

## Definition of done
- [ ] `final.md` exists with the front matter, no `{{`, and `Signed-off-by:` empty
- [ ] Every `[F#]` and every marker from the draft is still there, unchanged
- [ ] `prose-lint.py --record` was the last action on `final.md` before the gate
- [ ] The gate ran in a fork and its verdict is saved as `G4-final.r<k>.md` with a valid first line
- [ ] On a second BLOCK the run stopped and named the verdict files
