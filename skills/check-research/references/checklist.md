# G1 checklist

Judge `research.md`. Rule IDs allowed at this gate: FACT-1 to FACT-6. Everything here is checked against the page you
opened, not against memory.

## How to check a fact row
For each row of the fact bank, fetch the source URL, then decide in this order:

| What you find | Finding | Rule |
|---------------|---------|------|
| The page is definitively gone: 404, 410, DNS failure | blocking | FACT-2 |
| The fetch is blocked, times out, or you have no web tools | the row goes under Not checked; **one blocking finding per row** | FACT-2 |
| The page loads but the verbatim quote is not on it, or has been reworded | blocking | FACT-3 |
| The quote is real but the claim says more than the quote does (a number rounded up, "may" turned into "does", one study turned into "research shows") | blocking | FACT-5 |
| The page's published date differs from the row's published column | blocking when it changes the age check, otherwise advisory | FACT-2 |
| Publisher, published date or accessed date is empty or still a `{{placeholder}}` | blocking | FACT-2 |

## Other checks
- **FACT-1** A statistic, date, named claim or quote in the competitor-coverage or gap prose that has no fact ID next
  to it is a finding. The fact bank is where claims live; prose around it cites them.
- **FACT-3** A quote must also be attributed: the publisher column names who said it.
- **FACT-4** A statistic older than the age limit in the workspace style guide is a **blocking** finding unless the row
  says it is dated (in the claim, for example "as of 2021"). If there is no style guide, you cannot judge age: say so under Not checked, and do not invent a limit.
- **FACT-6** For every question in `brief.md`, the Questions table lists fact IDs that exist in the bank, or the
  question appears under Open gaps with what that means for the outline. A question in neither place is blocking. A
  listed fact ID that is not in the bank is blocking.

## Do not
- Judge style, structure or the quality of the gap statement; those are other gates' work.
- Pass a row because the source "is surely right". If you did not open it, it is Not checked.

## Not checked
List every URL you did not open and why, whether competitor-coverage rows were verified (they are not facts; do not
block on them), and whether a style guide was present.
