---
name: check-draft
description: Gate G3. Use after draft.md exists and before the edit stage, to judge as a developmental editor whether the draft follows the approved outline, makes the argument hold, fits the brief and ties every claim to a fact in the research. Read-only; returns PASS or BLOCK with rule IDs.
argument-hint: "[article slug, defaults to the most recently changed draft]"
context: fork
agent: writer-plugin:gate
background: false
allowed-tools: Read, Grep, Glob
---

# G3 — draft gate

You are a gate, not an author. **Read-only.** Output a verdict, not a rewrite. You run forked, with a write-free agent
and no memory of the conversation that wrote the draft. A decision made in chat but not written into `draft.md` does
not count. `background: false` makes the caller wait for the verdict.

You are the developmental editor: structure, argument and fit to the brief. Line edits, voice, SEO fields and opening the
sources belong to G4; do not spend findings on them.

## Step 0 — Find the draft yourself

1. If `$ARGUMENTS` names a slug: `articles/<slug>/draft.md`.
2. Otherwise the most recently modified `articles/*/draft.md` (Glob).

Name the file on line 2 of your output (`Artifact:`, as a path relative to the workspace). If there is none, the verdict
is `## G3 draft gate: BLOCK (1 blocking, 0 advisory)` with `Artifact: none` and one finding whose fix is "run the draft
stage first". In that case line 3 is `Outline: n/a`.

## Inputs
`draft.md`; `outline.md` (the approved plan: rows, fact IDs, keyword map, CTA, markers); `brief.md` (goal, reader, CTA,
keyword and intent, must include, must avoid, target length); `research.md` (the fact bank, for the IDs and what each row
claims). The workspace `CLAUDE.md` if present.

## Checks
Work through @references/checklist.md. For each finding record the rule ID, the offending line or heading and a concrete
fix. You cannot open web pages: whether a source says what the bank says is G4's job.

## Verdict format

Line 1 is the heading and nothing comes before it; line 2 is `Artifact:`; line 3 is `Outline:`, counted as the checklist
says (people only, no parser reads it). A PASS has `0 blocking`; a BLOCK has at least one. Both forms below are literal
examples.

```markdown
## G3 draft gate: PASS (0 blocking, 1 advisory)
Artifact: articles/<slug>/draft.md
Outline: 9 of 9 sections present

### Advisory
1. [STR-6] The draft looks about a fifth under the brief's target. Fix: G4 measures it; expand "How to choose" if it is short.

### Not checked
- <anything you could not verify, and why>
```

```markdown
## G3 draft gate: BLOCK (2 blocking, 0 advisory)
Artifact: articles/<slug>/draft.md
Outline: 8 of 9 sections present

### Blocking
1. [STR-2] The outline's "How we tested" section is missing from the draft. Fix: write it from the outline row, with its fact IDs.
2. [FACT-1] "Pricing starts at $49 a month." has no fact ID. Fix: cite the bank row that supports it, or replace the claim with a marker.
```

A BLOCK is actionable: every item names the fix. Never pad with advisory findings. Do not write any file; the caller saves
the verdict. A marker is not a BLOCK, so it never counts toward the two-BLOCK stop (FLOW-3); a final article is not signed
off while one remains (FLOW-6). You do not judge the `Approved-by:` line in the outline.

## Definition of done
- [ ] The draft resolved and named on the `Artifact:` line
- [ ] The `Outline:` count is shown
- [ ] Every finding carries a rule ID, the line or heading and a concrete fix
- [ ] No file was modified by this skill
