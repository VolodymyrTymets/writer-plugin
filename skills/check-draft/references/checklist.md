# G3 checklist

Judge `draft.md` against the approved `outline.md`, `brief.md` and the fact bank in `research.md`. Rule IDs allowed at
this gate: STR-1, STR-2, STR-5, STR-6, SEO-4, FACT-1, FACT-5, BRF-5. Blocking means the edit stage would be polishing a
draft that is built wrongly; wording polish is not your work.

| ID | Blocking when | Passes when |
|----|---------------|-------------|
| STR-1 | The first 100 words do not state the promise of the article, or the reader cannot tell what they will get | The opening states the promise the outline's hook describes |
| STR-2 | An outline row has no section in the draft, a section covers something the outline does not plan or the brief says to avoid, or a section no longer serves the brief's goal | Every outline row is present with its heading, no section is added, and each section does what its Purpose says. A changed order is advisory |
| STR-5 | The close does not deliver the brief's one CTA (a different action, no URL when the brief gave one, or several CTAs) | The close states the brief's CTA where the outline places it |
| STR-6 | (never blocking at this gate) The draft is plainly far from the brief's target length, for example half or double | Within reach of the target. You cannot count words exactly, so report a gross miss as advisory; G4 enforces the length from the lint record |
| SEO-4 | The draft answers a different search intent than the brief names (a how-to where the brief says comparison) | The article's shape and promise match the intent in the brief |
| FACT-1 | A sentence with a statistic, a date, a named claim or a quote has no `[F#]`; or a cited ID is not in the bank | Every such sentence cites IDs that exist in the bank |
| FACT-5 | The sentence says more than the cited bank row's claim or quote says (a number rounded up, "may" turned into "does", one study turned into "research shows"), or a cited ID exists but does not support the sentence | Each sentence is no stronger than the row behind it. Read the row |
| BRF-5 | A "must avoid" item appears, or a "must include" item is absent | Every must-include is in the draft and nothing from must-avoid is |

## Notes
- Argument: does each section follow from the one before, and does the thesis in the outline hold at the end? A section
  that repeats another, a leap the reader cannot follow, or a thesis that is dropped is STR-2.
- A section with no facts is fine when its content is structure or advice and carries no checkable claim.
- Do not judge the voice, the title, the meta description or commas: those are G4's work. Do not open web pages.

## The marker
A marker is `<Can't be verified. Reason: reason sentence here>`. The draft carries it unchanged from the outline.
- FACT-1 does not apply to a marker: it replaces a claim, it is not one.
- A claim written beside a marker or inside its reason still blocks (FACT-1): the reason says why it could not be
  verified, never what the claim is.
- A marker not in the exact form (ASCII apostrophe; a non-empty one-line reason with no `<`, `>` or `|`) is a blocking
  FACT-1 finding with the fix "rewrite it in the exact form".
- A marker the outline does not contain, or on a point the bank supports, is a FACT-1 finding: the draft invents an
  unverified point, or should cite the fact ID instead.

## Outline line
Line 3 of your verdict is `Outline: <a> of <m> sections present`, with `m` the number of rows in the outline's Structure
table and `a` the number of those rows whose heading appears in the draft. Count it the same way every run.

## Not checked
List what you could not judge: whether the thesis is the best angle (a human decided at approval), whether the sources
say what the bank says (G4 opens them), the draft's exact word count, and a missing `outline.md`, `brief.md` or
`research.md`.
