---
name: check-brief
description: Gate G0. Use after a brief exists and before any research starts, to judge whether the brief is complete and unambiguous enough to research. Read-only; returns PASS or BLOCK with rule IDs.
argument-hint: "[article slug, defaults to the most recently changed brief]"
context: fork
agent: writer-plugin:gate
background: false
allowed-tools: Read, Grep, Glob
---

# G0 — brief gate

You are a gate, not an author. **Read-only.** Output a verdict, not a rewrite.

This skill runs **forked** with a write-free agent and no memory of the conversation that wrote the brief. A decision
made in chat but not written into `brief.md` does not count. `background: false` makes the caller wait for the verdict.

## Step 0 — Find the brief yourself

1. If `$ARGUMENTS` names a slug: `articles/<slug>/brief.md`.
2. Otherwise the most recently modified `articles/*/brief.md` (Glob).

Name the file you settled on on line 2 of your output (`Artifact:`, as a path relative to the workspace). If there is none, the verdict is
`## G0 brief gate: BLOCK (1 blocking, 0 advisory)` with `Artifact: none` and one finding whose fix is "run the brief stage first". Do not judge a chat summary instead.

## Inputs
`brief.md`; `brief.source.md` next to it (the brief as supplied); the workspace `CLAUDE.md` if present. The style guide
is not needed at this gate.

## Checks
Work through @references/checklist.md. Record for each finding: the rule ID, the offending line of `brief.md`, and the
concrete fix.

## Verdict format

Line 1 is the heading and nothing comes before it; line 2 is `Artifact:`. The heading's counts must agree with the
verdict: a PASS has `0 blocking`, a BLOCK has at least one. Both forms below are literal examples.

```markdown
## G0 brief gate: PASS (0 blocking, 1 advisory)
Artifact: articles/<slug>/brief.md

### Advisory
1. [BRF-3] A secondary keyword repeats the primary keyword. Fix: drop it from the secondary list.

### Not checked
- <anything you could not verify, and why>
```

```markdown
## G0 brief gate: BLOCK (1 blocking, 0 advisory)
Artifact: articles/<slug>/brief.md

### Blocking
1. [BRF-1] Reader is "marketers". Fix: name a role and a context, for example "head of growth at a 50-person SaaS".
```

A BLOCK is actionable: every item names the fix. Never pad with advisory findings; three real findings beat twelve
stylistic ones. If the brief is fine, say PASS in one line and stop. Your whole output returns to the caller as one
message, so the verdict goes in it. Do not write any file; the caller saves the verdict.

## Definition of done
- [ ] The brief resolved and named on the `Artifact:` line
- [ ] Every finding carries a rule ID and a concrete fix
- [ ] No file was modified by this skill
