# FT-20 — research ends with a clear list of questions for the human

No tracker; a row of the Field-test findings table in `docs/DESIGN.md`.

## Problem
When research cannot answer part of the brief, the human is asked in the research file's Open gaps and in the actor's chat report, by `Q5`, `F7` and `Comment 4` ids spread over
many bullets, some of them notes about the brief. On drifity the human could not tell what to bring, in what form, or which question a reply belongs to.

## Goal / business value
BUSINESS_MODEL goal 1 and the "human fills the gaps" flow of ADR-021: the human opens the last section of the research and sees exactly what is being asked.

## Scope
- in: a final section `## Questions for the human` in `research.md` (template, research skill). One numbered plain-text question per open gap and per decision the human owes (for example
  "the brief says X, the page says Y: which does the article state?"). No `Q<n>`, `F<n>` or comment ids in it. Each question says what would answer it: a URL a run can fetch, or a page's text
  with the date it was read, or a yes/no decision. `none` when nothing is owed. Each question starts with a status mark, `[OPEN]` or `[RESOLVED]`, so the human sees at a glance what is still owed
  and what is clear. A resolved question stays in the list (with one plain sentence saying how it was settled), so a rerun keeps the record instead of dropping it. G1 gets an advisory check that
  the section exists, carries no id, covers every marker under Open gaps with an `[OPEN]` question and has no `[RESOLVED]` question whose marker is still under Open gaps.
- **out (explicit):** one Doc updated in place (FT-21, needs its own spike and ADR); how a reviewer's answer is recorded (a comment stays a pointer note, Step 2b of the research skill);
  any change to markers, FLOW-6, FACT-6's arithmetic or the other stages' gates; a script or hook.

## Acceptance criteria
- [x] AC1 `templates/research.md` ends with `## Questions for the human`, after `## Open gaps`, with numbered placeholders that start `[OPEN]` or `[RESOLVED]` and the "no ids" rule in a comment.
- [x] AC2 The research skill tells the actor to write that section, one question per marker under Open gaps and per owed decision, with no `Q`/`F`/comment ids, to name in each what would answer it, and to mark each `[OPEN]`;
  on a rerun it keeps every earlier line, changes `[OPEN]` to `[RESOLVED]` only when a fact row now answers the question or a reviewer's comment settles a decision, and adds one plain sentence saying how. The Step 6 report gives the counts ("3 open, 2 resolved") and points to the section instead of repeating the questions.
- [x] AC3 G1 reports as an **advisory** FACT-6 finding: a missing section, a line in it with a `Q<n>`/`F<n>` id or no `[OPEN]`/`[RESOLVED]` mark, an Open gaps marker no `[OPEN]` question covers, or a `[RESOLVED]` question whose marker is still under Open gaps. It never blocks.
- [x] AC4 Tests pin AC1 to AC3 (template shape, skill text, checklist text); none is deleted or skipped.
- [x] AC5 Full pytest passes; `claude plugin validate ./` passes with only the known warning.

## Edge cases
| Case | Expected behaviour | Decided by |
|------|--------------------|-----------|
| No open gaps and no owed decision | the section says `none` | this spec |
| A marker and a decision about the same page | one question, not two | this spec |
| The sections of an existing `research.md` lack the new section | G1 advises, the next research run adds it; nothing is rewritten | AC3 |
| A reviewer answers a question in the Doc | recorded as a pointer note, never a fact (research Step 2b); a factual answer leaves the question `[OPEN]` until a fact row answers it | ADR-016 |
| A reviewer's comment settles a decision ("state 100 included credits") | the question becomes `[RESOLVED]` with the sentence "decided by the reviewer in comments/research.r<k>.md"; no fact row is made | research Step 2b |
| A resolved question's page later changes | the actor does not reopen it by itself; the human reopens by writing `[OPEN]` back in `research.md` | this spec |

## Open questions
| # | Question | My assumed answer | Needs a human? |
|---|----------|-------------------|----------------|
| 1 | Should the section sit before `Approved-by:` at the top for visibility? | No: the brief says "in the end of the research file" | no |
| 2 | Should the actor also repeat the list in chat? | One line pointing to the section and its count | no |
| 3 | A checkbox (`- [ ]`) or a word for the mark? | A word, `[OPEN]` / `[RESOLVED]`: it survives the Markdown upload to a Google Doc as plain text, which a checkbox was not checked to do, and G1 can count it like the synced comments' `· OPEN` | no |
