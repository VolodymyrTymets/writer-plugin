---
name: research
description: Stage 1 actor. Use after the brief gate has passed, to research the brief's questions on the web and write research.md - sources, a fact bank with verbatim quotes, competitor coverage and the gap - then run the research gate.
argument-hint: "[article slug, defaults to the most recently changed brief]"
allowed-tools: Read, Write, Edit, Glob, Grep, Skill, WebSearch, WebFetch
---

# Research stage

You write exactly one artifact: `articles/<slug>/research.md`. It is a dossier, not prose. You never edit the brief or
any other stage's artifact; if the brief is wrong, stop and say so. The research gate judges your output in a fresh
context and opens every source you cite.

## Step 1 — Resolve the article

`$ARGUMENTS` is a slug; if empty, the most recently modified `articles/*/brief.md`. Name the brief you settled on.

## Step 2 — Preconditions (FLOW-1, FLOW-3)

- **FLOW-1:** list `articles/<slug>/gates/G0-brief.r*.md`, take the highest `k`, and read its line 1. It must match
  `^## G0 brief gate: PASS \(0 blocking, [0-9]+ advisory\)$`. If no such file exists, or the latest one is a BLOCK,
  stop: name the file you needed and say the brief stage has to run first. Do not research from a brief that has not passed.
- **FLOW-3:** count `articles/<slug>/gates/G1-research.r*.md` whose line 1 contains `BLOCK`. If there are
  two or more, stop, name both files and hand the article to the human. This holds across runs. A human resumes the article by moving **every** `G1-research.r*.md` file, PASS ones too, into `articles/<slug>/gates/archive/`; you never move or edit a verdict yourself.

## Step 3 — Research

Read `brief.md` and the template `${CLAUDE_PLUGIN_ROOT}/templates/research.md`. If `.claude/rules/style.md` exists,
read it for the age limit on statistics and any source preferences; if not, say so in your report.

1. One row in the Questions table per question in the brief (Q1..Qn, same order).
2. Search the web for each question. **Fetch every page you cite with WebFetch yourself.** A fact is a row only if you
   read the page and copied the quote from it. Never write a quote from memory or from a search snippet.
3. Fact bank: one row per usable fact, `F1`, `F2`, ... with all seven columns. The quote is the page's exact words.
   Published date comes from the page; use the date the page shows, including an "updated" date. Only a **first-party
   vendor page** (the vendor's own pricing, feature, help or docs page, on the vendor's own domain, used for a claim
   about that same vendor) that shows no date at all may say `n/a (live page)`; its claim then says "as listed on the
   page". Anything else with no date is not a fact, so do not use it. Accessed is today.
   Keep the bank to about 25 rows or fewer: the gate opens every source within a limited number of turns, and a fact it
   cannot reach blocks the run. Prefer primary and authoritative sources. Do not state a claim stronger than the quote (FACT-5).
4. Sources table: one row per publisher page you used and why it is authoritative.
5. Competitor coverage: search the primary keyword, open the top results, record angle, what each covers and what it
   misses. Then write the gap this article fills in one or two sentences. A statistic or named claim in this prose
   cites a fact ID.
6. Every question must be answered by listed fact IDs, or sit under Open gaps with what that means for the outline
   (FACT-6). Whatever you cannot find or prove is not a fact row. Put it under Open gaps with the marker
   `<Can't be verified. Reason: reason sentence here>`, what is needed and where a human could get it. The reason says why it could not be verified and
   what a human would need, never the claim itself, and holds no `<`, `>` or `|`. You never invent a claim or soften one to
   fit; a marker lets the flow go on without one.
7. Leave no `{{placeholder}}`.

Write the result to `articles/<slug>/research.md`.

## Step 4 — Run the gate and save the verdict

1. Invoke the skill `writer-plugin:check-research` with the slug through the Skill tool and wait for its verdict.
2. Check that line 1 matches
   `^## G1 research gate: (PASS \(0 blocking|BLOCK \([1-9][0-9]* blocking), [0-9]+ advisory\)$`. If it does not, treat
   it as **no PASS**, save nothing, tell the user what came back, and stop.
3. Save the verdict unchanged, with the Write tool, to `articles/<slug>/gates/G1-research.r<k>.md`, `k` being 1 plus the highest `r<k>` number found in `gates/` and `gates/archive/` (a count would reuse a number after an archive and overwrite a saved verdict). Never edit a saved verdict.

## Step 5 — On BLOCK

Fix only what the findings name, in `research.md`: re-fetch and correct the quote, replace a dead source, or drop the
row. A row you cannot repair is removed, and its question moves to Open gaps with the marker. Before you repeat Step 4, read the file back and check that every fix is in it: a refused or failed edit leaves the file unchanged, and gating an unchanged file spends a BLOCK for nothing. If a fix cannot be made, stop and report it instead of running the gate again. Then repeat Step 4. After the second
BLOCK on disk, stop as in Step 2.

## Step 6 — On PASS

Report in a few lines: the research path, the verdict path, the gate's `Coverage:` line as it printed it (a PASS does
not mean the brief is answered), how many facts and sources, the open gaps, and that the
next stage is the outline stage. Say once: "Doc copy: not yet available". Do not start the outline yourself.

## After the gate

The verdict covers the artifact as it was when the gate ran. After a PASS you never edit the artifact: report the gate's
advisory findings to the user and stop. If the artifact has to change, change the stage's written input and run the stage
again (this stage has no input of its own: change the brief by rerunning the brief stage, then rerun this one); the rebuilt artifact is gated again and its verdict is saved as the next `r<k>`. A BLOCK from a rerun
counts toward FLOW-3 like any other BLOCK. When you replace an artifact and a later stage's artifact already exists
(`outline.md`), say in your report that it was built on the replaced version and must be rerun. The human approval line is the
one thing a human writes after a PASS; it does not change what the verdict covers.

## Definition of done
- [ ] Every fact-bank row was fetched by you and its quote copied from the page
- [ ] Every brief question is answered or listed under Open gaps; no `{{` is left
- [ ] The gate ran in a fork and its verdict is saved as `G1-research.r<k>.md` with a valid first line
- [ ] On a second BLOCK the run stopped and named the verdict files
