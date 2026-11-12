---
name: check-research
description: Gate G1. Use after research.md exists and before any outline is written, to judge whether the sources are real and say what the fact bank claims, and whether every question in the brief is answered. Opens every source URL. Read-only; returns PASS or BLOCK with rule IDs.
argument-hint: "[article slug, defaults to the most recently changed research.md]"
context: fork
agent: writer-plugin:fact-gate
background: false
allowed-tools: Read, Grep, Glob, WebFetch, WebSearch
---

# G1 — research gate

You are a gate, not an author. **Read-only.** Output a verdict, not a rewrite. You run forked, with a fact-checking
agent that has web tools and no write tools, and no memory of the conversation that wrote the research. A decision
made in chat but not written into `research.md` does not count. `background: false` makes the caller wait.

## Step 0 — Find the research yourself

1. If `$ARGUMENTS` names a slug: `articles/<slug>/research.md`.
2. Otherwise the most recently modified `articles/*/research.md` (Glob).

Name the file on line 2 of your output (`Artifact:`, as a path relative to the workspace). If there is none, the verdict is `BLOCK: no research found`, and
the fix is "run the research stage first".

## Inputs
`research.md`; `brief.md` next to it (for the questions); the workspace `.claude/rules/style.md` if present (for the
statistic age limit); the workspace `CLAUDE.md` if present. If the style guide is absent, say so under Not checked.

## Checks
Work through @references/checklist.md. **Open every source URL in the fact bank** and compare; never judge a fact from
memory. For each finding record the rule ID, the offending row and the concrete fix.

## Verdict format

Line 1 is the heading and nothing comes before it; line 2 is `Artifact:`. A PASS has `0 blocking`; a BLOCK has at
least one. Every fact you could not open counts as one blocking FACT-2 finding. Both forms below are literal examples.

```markdown
## G1 research gate: PASS (0 blocking, 1 advisory)
Artifact: articles/<slug>/research.md

### Advisory
1. [FACT-4] F3 cites a 2021 statistic and the style guide's limit is 36 months. Fix: replace it or mark it as dated.

### Not checked
- <anything you could not verify, and why>
```

```markdown
## G1 research gate: BLOCK (2 blocking, 0 advisory)
Artifact: articles/<slug>/research.md

### Blocking
1. [FACT-3] F2: the quote "..." is not on the page at the URL. Fix: quote the page's real wording or drop the row.
2. [FACT-2] F5: the URL returns 404. Fix: find a live source for the claim or drop the row.
```

A BLOCK is actionable: every item names the fix. Never pad with advisory findings. List the sources you opened and
the ones you did not under Not checked. Do not write any file; the caller saves the verdict.

## Definition of done
- [ ] The research resolved and named on the `Artifact:` line
- [ ] Every fact-bank URL was opened, or listed under Not checked and counted as blocking
- [ ] Every finding carries a rule ID, the row and a concrete fix
- [ ] No file was modified by this skill
