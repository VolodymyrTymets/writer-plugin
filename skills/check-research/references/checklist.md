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
| Publisher, published date or accessed date is empty or still a `{{placeholder}}` (a published date of `n/a (live page)` is judged by the section below) | blocking | FACT-2 |

## `n/a (live page)` in the published column
Allowed only when **all** of these hold; if any fails, the `n/a` is blocking (FACT-2):
1. The publisher column names the vendor, and the claim's subject is that vendor (not another vendor).
2. The URL's registrable domain is the vendor's own, the domain of its product site. Docs on a third-party domain or a
   reseller mirror fail this; so does a vendor page used for a claim about another vendor.
3. The page shows no published or updated date. Open it and look. If it shows one, the row must carry that date.
4. The claim says "as listed on the page".
Articles, statistics from other publishers and regulator pages never qualify. The same rule applies to the Sources table.

## Other checks
- **FACT-1** A statistic, date, named claim or quote in the competitor-coverage or gap prose that has no fact ID next
  to it is a finding. The fact bank is where claims live; prose around it cites them.
- **FACT-3** A quote must also be attributed: the publisher column names who said it.
- **FACT-4** A statistic older than the age limit in the workspace style guide is a **blocking** finding unless the row
  says it is dated (in the claim, for example "as of 2021"). "As listed on the page" is not a date. For an
  `n/a (live page)` row, age is the accessed date. If there is no style guide, you cannot judge age: say so under Not
  checked, and do not invent a limit.
- **FACT-6** For every question in `brief.md`, the Questions table lists fact IDs that exist in the bank and support
  the question, or the question appears under Open gaps with what that means for the outline. A question in neither
  place is blocking. A listed fact ID that is not in the bank is blocking, and so is a listed ID that exists but does
  not support its question. A fact supports a question if its claim answers at least part of it; read the bank row to
  decide. The unanswered part goes under Open gaps.

## Do not
- Judge style, structure or the quality of the gap statement; those are other gates' work.
- Pass a row because the source "is surely right". If you did not open it, it is Not checked.

## Not checked
List every URL you did not open and why, whether competitor-coverage rows were verified (they are not facts; do not
block on them), and whether a style guide was present.
