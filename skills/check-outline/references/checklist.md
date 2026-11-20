# G2 checklist

Judge `outline.md` against `brief.md` and the fact bank in `research.md`. Rule IDs allowed at this gate: STR-2, STR-3,
STR-5, SEO-1, FACT-1, FACT-6. Blocking means the draft would be built on it wrongly; wording polish is advisory and rare.

| ID | Blocking when | Passes when |
|----|---------------|-------------|
| STR-2 | A section's purpose does not trace to the brief's goal, or the section covers something the brief says to avoid | Every row's Purpose names how it serves the goal, and no row contradicts "must avoid" |
| STR-3 | The Words column does not sum to the brief's target within plus or minus 10% | The sum is inside the range. Write the arithmetic: `target 1400 → 1260 to 1540; sum 520+...=1480` |
| STR-5 | The Call to action section does not deliver the brief's one CTA (a different action, no URL when the brief gave one, or several CTAs) | The section states the brief's CTA and where the close places it |
| SEO-1 | The keyword map does not place the primary keyword in a title option, in the intro hook (first 100 words) and in at least one H2 heading, or the structure table's headings contradict the map | All three places are named, and an H2 in the Structure table really contains the keyword or a direct form of it |
| FACT-1 | A Key points cell has a statistic, a date, a named claim or a quote and its Fact IDs cell does not cover it; or a cited fact ID is not in the bank of `research.md` | Every such claim has fact IDs, and every ID cited exists in the bank |

## Notes
- FACT-1 applies to the intro hook and the keyword map text too: a number there needs an ID.
- A fact ID that exists but does not support the key point it is attached to is a FACT-1 finding. Read the bank row.
- A section with no facts is fine when its key points are structure or advice and carry no checkable claim.

## The marker
A marker is `<Can't be verified. Reason: reason sentence here>`. It stands in for a claim the research could not support.
- FACT-1 does not apply to a marker: it replaces a claim, it is not one.
- **The second form (ADR-023).** `<Needs to be written by a human. Reason: reason sentence here>` replaces a gap's marker when a reviewer asked to skip that question. It has the same exact-form rules, it is not a claim, and a skip swaps a marker for it, so the one-marker-per-open-gap count below covers both forms together. Its question line in the list is `[SKIPPED]`; a skipped marker with no `[SKIPPED]` line is a FACT-6 advisory.
- A claim written beside a marker or inside its reason still blocks (FACT-1): the reason says why it could not be verified,
  never what the claim is.
- A marker not in the exact form (ASCII apostrophe; a non-empty one-line reason with no `<`, `>` or `|`) is a blocking
  FACT-1 finding with the fix "rewrite it in the exact form". It is not counted.
- A marker on a point the bank supports is a FACT-1 finding; the fix is "cite the fact ID instead".
- **One marker per open gap (ADR-017).** Count the exact-form markers under "## Open gaps" in `research.md`. If the exact-form
  markers counted for line 3 (outside the "Questions for the human" section and the older "Open questions for the human" section) outnumber them, that is one blocking FACT-1 finding with the fix "keep one marker per open gap,
  in one row, and drop the claim from the other rows". Name both counts. Do not guess which marker is the extra one: say the
  count and quote two that look like the same gap.
- Line 3 of your verdict is `Markers: <n>`: the exact-form markers in `outline.md` outside the "Open questions for the human" section and outside the "Questions for the human" section (the older
  section collected the markers, so counting it would count each twice; the newer one lists plain questions and is not article text, so STR-2 and FACT-1 skip it). Count it the same way every run.

The closing `## Questions for the human` (or the older `## Open questions for the human`) is not a section of the plan: it is outside STR-2 and FACT-1, and only the FACT-6 advisory below judges it.

**Questions for the human (FACT-6, ADR-023).** The same advisory at research, outline and draft: the closing `## Questions for the human` follows one form, which the actor checks with `bin/questions-check.py`. It is the last section (only an approval line may follow it); each line starts `[OPEN]`, `[RESOLVED]` or `[SKIPPED]` (a skipped question is one a reviewer asked to leave for the human, ADR-023; a leading `- ` or `1. ` is ignored); no line carries a `Q<n>` or `F<n>` id or a comment number; a line the previous stage's list marks `[RESOLVED]` is not repeated, as `[OPEN]` or in any form; a marker in the text has at least one `[OPEN]` or `[SKIPPED]` line somewhere in the list (one question may cover several markers about the same page); and the section is `none`, or absent, when nothing is owed. A section under the old heading `Open questions for the human` is exempt from every rule but placement. Add one advisory FACT-6 finding naming the lines. It never blocks.

## Do not

- Judge the voice, the title's appeal or the draft prose; there is no draft yet.
- Judge the `Approved-by:` line.

## Not checked
List what you could not judge: for example, whether the thesis is the best angle (a human decides at approval), or a
missing `brief.md` or `research.md`.
