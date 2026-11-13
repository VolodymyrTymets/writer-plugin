# G4 checklist

Judge `final.md`. Rule IDs allowed at this gate: FACT-1 to FACT-5, STR-4, STR-6, VOI-1 to VOI-5, SEO-1, SEO-2, SEO-3, SEO-5,
FLOW-6. Structure and argument were G3's work. Blocking means the article would publish a wrong fact, a broken field or the
style guide's bans; polish is advisory and rare.

## A. The recorded lint run
Read `articles/<slug>/.prose-lint.json`. Its `lines` are the findings `prose-lint.py` printed on this final, one per line as
`RULE path:line message`.

| What you find | Finding |
|---------------|---------|
| The file or its `lines` key is missing (an older record has only a count) | one blocking finding, rule STR-6, fix "run `prose-lint.py --record` on the final"; list the lint under Not checked |
| A STR-4, STR-6, SEO-1, SEO-2, SEO-3, VOI-2 or VOI-3 line | blocking, same rule ID, the line quoted. These are mechanical |
| A FACT-1 line | read the sentence in `final.md`. A number that is a claim with no `[F#]` is blocking; a number that is not a claim (a step number, "two things") is not a finding, and you say you discarded it |
| A FLOW-6 line | never a finding: count it for line 3 and list it under "Sign-off holds" |

If the record's lines name text that is not in `final.md` (check one with Grep), the record is stale: one blocking finding,
rule STR-6, fix "rerun `prose-lint.py --record`".

## B. Facts: open the sources
Collect every `[F#]` in `final.md`. For each distinct ID find its row in `research.md`, then fetch the row's URL and decide in
this order:

| What you find | Finding | Rule |
|---------------|---------|------|
| The ID is not in the bank | blocking | FACT-1 |
| A sentence with a statistic, date, named claim or quote has no `[F#]` | blocking | FACT-1 |
| The page is definitively gone: 404, 410, DNS failure | blocking | FACT-2 |
| The fetch is blocked, times out, or you have no web tools | the row goes under Not checked; **one blocking finding per row** | FACT-2 |
| The page loads but the quote is not on it, or the final's quote differs from the row's | blocking | FACT-3 |
| The final's sentence says more than the page does (a number rounded up, "may" turned into "does", one study turned into "research shows") | blocking | FACT-5 |
| The page's published date differs from the row's, or a row says `n/a (live page)` and the page shows a date | advisory, **one finding for all such rows**; blocking only when it changes the age check (then FACT-4) | FACT-2 |
| A statistic is older than the style guide's age limit and the sentence does not date it | blocking | FACT-4 |

The bank's row metadata (publisher, published, accessed, the `n/a (live page)` label) was judged by G1 and is not re-judged
here: it is never a blocking finding on its own, and you report it once for all rows. What blocks here is a source that does not
resolve, a quote that is not on the page, a sentence stronger than the page, and an age the guide forbids; for a live-page row age is
the accessed date. Open the rows behind numbers and quotes first. If you run short of turns, the unopened rows go under Not
checked and each is one blocking FACT-2 finding; you never pass a row you did not open. Without a style guide you cannot judge
age: say so under Not checked, and do not invent a limit.

## C. Voice and links
Read `.claude/rules/style.md`. If it is absent or still `{{placeholder}}`, list VOI-1, VOI-4 and SEO-5 under Not checked as
**non-blocking**: a missing style guide must not stop every workspace without one.
- **VOI-1** The voice (tone, person, do and do not) differs from the style guide in a way a reader would notice: blocking when
  it is pervasive, advisory when it is one paragraph.
- **VOI-4** The reading level is plainly above the guide's target (long sentences, stacked clauses, unexplained jargon):
  advisory unless it is pervasive. You cannot compute a grade; say what you saw.
- **VOI-5** Filler or stacked hedges ("it is worth noting that", "may possibly perhaps"): advisory, blocking only when they
  fill whole paragraphs.
- **SEO-5** An internal link that is not in the style guide's list, or an external link that is not a source in the fact bank:
  blocking. A missing internal link the outline planned: advisory.

## Markers
A marker is `<Can't be verified. Reason: reason sentence here>`.
- FACT-1 does not apply to a marker: it replaces a claim, it is not one.
- A claim written beside a marker or inside its reason still blocks (FACT-1).
- A marker not in the exact form (ASCII apostrophe; a non-empty one-line reason with no `<`, `>` or `|`) is a blocking FACT-1
  finding with the fix "rewrite it in the exact form", and is not counted.
- Line 3 of your verdict is `Markers: <n>`: the exact-form markers in the article body, counted the same way every run.
  Under "Sign-off holds" list each with its section. A marker never makes the verdict a BLOCK (FLOW-6 stops the sign-off, not
  the gate).

## Do not
- Judge structure, the outline, the argument or the title's appeal; G3 did.
- Judge the `Signed-off-by:` line.
- Pass a row because the source "is surely right". If you did not open it, it is Not checked.

## Not checked
List every URL you did not open and why, whether a style guide was present, and whether the lint record was usable.
