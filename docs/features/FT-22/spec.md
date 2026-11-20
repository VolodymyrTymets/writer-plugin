# FT-22 — one list of questions for the human, across research, outline and draft

## Problem
FT-20 gave `research.md` a closing `## Questions for the human` (plain sentences, `[OPEN]` or `[RESOLVED]`, no ids). The outline has its own older section,
"Open questions for the human", that only copies the markers (ADR-008, ADR-017); the draft has none. A reviewer of the outline or draft Doc must decode markers
again, cannot see which question was settled upstream, and a question research answered is invisible at the next stage. The flow is one chain of questions, but the
plugin writes three unrelated lists.

## Goal / business value
Goal 1 (correct gates, mechanical enforcement): one format and one checker, so a gate's advisory about the list means the same thing at every stage. Also the human
checkpoint (FLOW-2) works only if the human can see exactly what is still theirs to answer.

## Scope
- in: one section, `## Questions for the human`, in `research.md`, `outline.md` and `draft.md`, in one format; one checker (`bin/questions-check.py`) used by the three
  actors; each stage lists only what is still open in its own artifact (markers left in its text, decisions it owes) plus its own earlier lines it kept; a question
  resolved at an earlier stage is not repeated; the section is omitted when nothing is owed; the gates advise (never block) from the same rules.
- in, phase 2 (same ticket, own commits, a second PR if the first grows past review size): a human may skip a question. The outline and draft then carry
  `<Needs to be written by a human. Reason: reason sentence here>` instead of the unverified marker, and the line is marked `[SKIPPED]`.
- **out (explicit):** the final (`/edit`) gets no list of its own: it carries the draft's markers and drops the draft's section (the final is the article). Any change
  to G1's coverage floor (ADR-021), to the fact bank, to Doc copies other than the section, to `/sync` or to the approval flow. Replying to comments (BUSINESS_MODEL).

## Acceptance criteria
- [x] AC1 (`[OPEN]`/`[RESOLVED]` in PR 1; `[SKIPPED]` and the human-written marker in PR 2) Given a `research.md`, `outline.md` or `draft.md`, when `bin/questions-check.py` runs, then it prints JSON findings for: section not last; a line without
      `[OPEN]`, `[RESOLVED]` or `[SKIPPED]`; a `Q<n>`, `F<n>` or comment id in a line; an exact-form marker in the artifact with no `[OPEN]` or `[SKIPPED]` line.
- [x] AC2 Given research answered every question and the artifact holds no marker, when the stage writes the artifact, then it has no `## Questions for the human`
      section and no finding (omitted when no line was ever owed; a section holding only `[RESOLVED]` lines or `none` is also accepted, FT-20).
- [x] AC3 Given a line `[RESOLVED]` in the upstream artifact's list, when the next stage writes its list, then that line is not repeated and the checker reports
      a repeat as a finding.
- [x] AC4 Given the outline raises one question research did not, when the outline is written, then its list holds that one `[OPEN]` line and the markers that remain,
      and the draft's list holds only what the draft still has open.
- [x] AC5 Given G1, G2 or G3 reads an artifact, when the list breaks a rule of AC1 or AC3, then the verdict has one advisory FACT-6 finding (FACT-6 now covers the questions list at all three stages) and still PASSes.
- [x] AC6 Given a draft with a list, when `prose-lint.py` runs, then the section is outside the word count (STR-6) and FACT-1; the Doc copy keeps it; `final.md`
      does not contain it, and the lint reports one that does as STR-7 (new rule: no working section in the final).
- [x] AC7 (phase 2) Given a reviewer's comment asks to skip one question, when the owning stage reruns, then that question's line is `[SKIPPED]` with the reason and, at
      outline and draft, the cell holds the human-written marker; the guard refuses sign-off while the marker remains (FLOW-6).
- [x] AC8 An ADR (ADR-023) records the format, the skip marker and the sign-off rule; DESIGN.md FT-22 row, glossary and CHANGELOG match.

## Edge cases
| Case | Expected behaviour | Decided by |
|------|--------------------|-----------|
| An old outline still says "Open questions for the human" | The checker reads that heading as the same section until the outline is rebuilt; no finding for the old name | assumption |
| Research resolved a question after the outline was built | The outline is stale (ADR-009) and rerun; the line is not repeated | ADR-009, AC3 |
| A reviewer's comment only says the answer, with no source | Still a pointer note, never a fact row; the line stays `[OPEN]` (ADR-021). Only a fetchable source or a dated page text resolves it | ADR-020, ADR-021 |
| A human skips a question at research | Research keeps its open gap and marker; `[SKIPPED]` is written at the outline and draft, where text exists | assumption |
| The draft section would be counted as article words | Excluded from STR-6 and FACT-1; checked by a lint test | AC6 |

## Open questions
| # | Question | My assumed answer | Needs a human? |
|---|----------|-------------------|----------------|
| 1 | Does the human-written marker block sign-off? | **Decided by the human: yes, change the rule.** FLOW-6 covers both markers: the human writes the text in `final.md` and removes the marker, which stales G4 and reruns it. ADR-023 records it | no |
| 2 | Does a human's answer in a comment resolve a question? | Only with a fetchable source or a dated page text, as today (ADR-020, ADR-021); a bare answer stays a pointer note; ADR-023 states it as an assumption, and a human may overturn it before PR 2 | no, unless the human objects |
| 3 | Does the skip apply at research too? | No: research has no text to mark; it keeps the open gap | no |
| 4 | Script or prompt for the shared checker? | A script run by the actors; the gates apply the same rules as text, since no gate runs a script (DESIGN, Gates) | no |
