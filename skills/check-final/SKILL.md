---
name: check-final
description: Gate G4. Use after final.md exists and before a human signs it off, to line-edit judge it - every fact against its source page, voice against the style guide, SEO fields, headings, length and the recorded prose-lint findings. Opens the sources. Read-only; returns PASS or BLOCK with rule IDs.
argument-hint: "[article slug, defaults to the most recently changed final]"
context: fork
agent: writer-plugin:fact-gate
background: false
allowed-tools: Read, Grep, Glob, WebFetch, WebSearch
---

# G4 — final gate

You are a gate, not an author. **Read-only.** Output a verdict, not a rewrite. You run forked, with a fact-checking agent
that has web tools and no write tools, and no memory of the conversation that wrote the final. A decision made in chat but
not written into `final.md` does not count. `background: false` makes the caller wait for the verdict.

You are the line editor and the fact checker: G3 already judged structure and argument, so spend no findings on those.

## Step 0 — Find the final yourself

1. If `$ARGUMENTS` names a slug: `articles/<slug>/final.md`.
2. Otherwise the most recently modified `articles/*/final.md` (Glob).

Name the file on line 2 of your output (`Artifact:`, as a path relative to the workspace). If there is none, the verdict is
`## G4 final gate: BLOCK (1 blocking, 0 advisory)` with `Artifact: none` and one finding whose fix is "run the edit stage first".
In that case line 3 is `Markers: n/a`.

## Inputs
`final.md` (front matter, then the article with its `[F#]` tags); `.prose-lint.json` beside it (the recorded lint run);
`brief.md`; `research.md` (the fact bank); the workspace `.claude/rules/style.md` if present; the workspace `CLAUDE.md` if present.

## Checks
Work through @references/checklist.md. **Open every source URL behind a fact ID that `final.md` cites** and compare; never
judge a fact from memory or from the bank row alone. You cannot run the lint script: you read the findings it recorded. For
each finding record the rule ID, the offending line or row and the concrete fix.

## Verdict format

Line 1 is the heading and nothing comes before it; line 2 is `Artifact:`; line 3 is `Markers: <n>`, counted as the
checklist says (people only, no parser reads it). A PASS has `0 blocking`; a BLOCK has at least one. Every source you could
not open counts as one blocking FACT-2 finding. Both forms below are literal examples.

```markdown
## G4 final gate: PASS (0 blocking, 1 advisory)
Artifact: articles/<slug>/final.md
Markers: 1

### Advisory
1. [VOI-5] The sentence "It is worth noting that..." in "Steeping time" is filler. Fix: delete the first clause.

### Sign-off holds
- One marker remains, in "Steeping time". A human supplies the fact or removes the claim; the final is not signed off while it remains (FLOW-6).

### Not checked
- <anything you could not verify, and why>
```

```markdown
## G4 final gate: BLOCK (2 blocking, 0 advisory)
Artifact: articles/<slug>/final.md
Markers: 0

### Blocking
1. [FACT-3] F2: the quote "..." is not on the page at the URL. Fix: quote the page's real wording or drop the sentence.
2. [SEO-3] The meta description is 112 characters, the limit is 120 to 155 (recorded lint). Fix: lengthen it.
```

A BLOCK is actionable: every item names the fix. Never pad with advisory findings. List the sources you opened and the ones you
did not under Not checked. Do not write any file; the caller saves the verdict. A marker is not a BLOCK (ADR-008): it is counted
on line 3 and listed under "Sign-off holds", and it never counts toward the two-BLOCK stop (FLOW-3). You do not judge the
`Signed-off-by:` line.

## Definition of done
- [ ] The final resolved and named on the `Artifact:` line
- [ ] The recorded lint findings were read, or their absence is a blocking finding
- [ ] Every cited fact's URL was opened, or listed under Not checked and counted as blocking
- [ ] Every finding carries a rule ID, the line or row and a concrete fix
- [ ] No file was modified by this skill
