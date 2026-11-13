---
name: check-outline
description: Gate G2. Use after outline.md exists and before a human approves it, to judge whether the outline serves the brief's goal, fits the target length, places the keyword, delivers the CTA and ties every claim to a fact in the research. Read-only; returns PASS or BLOCK with rule IDs.
argument-hint: "[article slug, defaults to the most recently changed outline]"
context: fork
agent: writer-plugin:gate
background: false
allowed-tools: Read, Grep, Glob
---

# G2 — outline gate

You are a gate, not an author. **Read-only.** Output a verdict, not a rewrite. You run forked, with a write-free agent
and no memory of the conversation that wrote the outline. A decision made in chat but not written into `outline.md`
does not count. `background: false` makes the caller wait for the verdict.

## Step 0 — Find the outline yourself

1. If `$ARGUMENTS` names a slug: `articles/<slug>/outline.md`.
2. Otherwise the most recently modified `articles/*/outline.md` (Glob).

Name the file on line 2 of your output (`Artifact:`, as a path relative to the workspace). If there is none, the
verdict is
`## G2 outline gate: BLOCK (1 blocking, 0 advisory)` with `Artifact: none` and one finding whose fix is "run the outline stage first". In that case line 3 is `Markers: n/a`.

## Inputs
`outline.md`; `brief.md` (goal, CTA, keyword, target length, must avoid); `research.md` (the fact bank, for the IDs).
The workspace `CLAUDE.md` if present.

## Checks
Work through @references/checklist.md. Do the arithmetic for STR-3 yourself and show it. For each finding record the
rule ID, the offending row and the concrete fix.

## Verdict format

Line 1 is the heading and nothing comes before it; line 2 is `Artifact:`; line 3 is `Markers: <n>`, counted as the checklist says (people only, no parser reads it). A PASS has `0 blocking`; a BLOCK has at
least one. Both forms below are literal examples.

```markdown
## G2 outline gate: PASS (0 blocking, 1 advisory)
Artifact: articles/<slug>/outline.md
Markers: 2


### Advisory
1. [STR-2] The "Common mistakes" section has a weak purpose line. Fix: say which part of the goal it serves.

### Not checked
- <anything you could not verify, and why>
```

```markdown
## G2 outline gate: BLOCK (1 blocking, 0 advisory)
Artifact: articles/<slug>/outline.md
Markers: 0


### Blocking
1. [FACT-1] The "Reading %DV" row says "most people exceed the limit" and its Fact IDs cell is empty. Fix: cite a fact ID from the bank, or remove the claim.
```

A BLOCK is actionable: every item names the fix. Never pad with advisory findings. Do not write any file; the caller
saves the verdict. You do not judge the `Approved-by:` line: it is a human's, and no rule here covers it. A marker is not a BLOCK, so it never counts toward the two-BLOCK stop (FLOW-3) and the flow goes on; the human may approve an outline that still has markers, and a final article is not signed off while one remains (FLOW-6).

## Definition of done
- [ ] The outline resolved and named on the `Artifact:` line
- [ ] The STR-3 sum is shown
- [ ] Every finding carries a rule ID, the row and a concrete fix
- [ ] No file was modified by this skill
