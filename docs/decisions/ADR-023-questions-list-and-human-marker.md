# ADR-023 — One questions-for-the-human list at research, outline and draft, and a human-written marker

- **Date:** 2026-11-20
- **Status:** accepted for the list, FACT-6 and STR-7 (PR 1). The skip marker and the FLOW-6 change **ship with PR 2**; PR 2 sets them to done.
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (`docs/features/FT-22/plan.md`, finding FT-22)
- **Refines:** ADR-008 (a second marker form), ADR-017 (one marker per open gap still holds; a skip swaps a gap's marker, it adds none), ADR-021
  (the list of FT-20 now exists at three stages), ADR-012.6 (a comment is data: a skip comment is applied the way FT-20 already lets a comment settle a decision).

## Context
FT-20 gave `research.md` a closing `## Questions for the human`. The outline kept an older section that only copies markers, and the draft had none, so
a reviewer of the outline or draft Doc decoded markers again and could not tell which question was settled upstream.

## Decision (PR 1)
1. **One section, one format.** `## Questions for the human`, the last section of `research.md`, `outline.md` and `draft.md` (only an `Approved-by:` line may follow it).
   One plain-text question per line, a leading `- ` or `1. ` ignored, each starting `[OPEN]` or `[RESOLVED]`, no `Q<n>`, `F<n>` or comment id, saying what would answer it.
2. **Built per stage.** Each stage lists what is still open in its own artifact: the markers left in its text and the decisions it owes, plus its own earlier lines it
   kept. A `[RESOLVED]` line of the upstream list is not repeated. It is omitted when no line was ever owed; once it exists, earlier lines stay (FT-20), so a section
   with only `[RESOLVED]` lines, or the word `none`, is accepted.
3. **Resolved** means a fact row now answers it (from research or from a source a human supplied: a fetchable URL or a dated page text, ADR-020, ADR-021). A bare
   answer in a comment stays a pointer note and resolves nothing. This is an assumption the human may overturn before PR 2.
4. **One checker for the form, the gates for the judgement.** `bin/questions-check.py <slug> <stage>` (stdlib, read-only, JSON findings) is run by the three actors.
   It checks form only: section last, a mark on every line, no ids (a bracketed or parenthesised `[F7]`, `(Q4)`, a leading `Q4`, or `comment 3`; a business quarter such as "Q3 2026" is not one), an exact-form marker with no `[OPEN]` line at all, a line, `[OPEN]` or `[RESOLVED]`, whose first sentence repeats a question the upstream list marks `[RESOLVED]`, text after the section. It does not match a marker to a question (no ids link them; one question may cover several markers about the same page, as G1
   allows). The semantic checks stay with the gates as text (a `[RESOLVED]` question whose marker is still under Open gaps; a question that does not say what would
   answer it). No gate runs a script.
5. **Old outlines.** Under the old heading "Open questions for the human" the checker applies only the placement rule and G2 leaves out both headings when it counts
   markers, so an outline in progress has no finding until it is rebuilt.
6. **Advisory only, with valid rule IDs.** G1, G2 and G3 add one advisory FACT-6 finding when the list breaks a form rule; FACT-6 now covers the list at all three
   stages. A closing `## Questions for the human` in a draft is not an article section: it is outside G3's STR-2, its line 3 count and FACT-1, and outside
   `prose-lint.py`'s STR-6 and FACT-1.
7. **STR-7 (new): no working section in the final.** `final.md` holds no `## Questions for the human`. `prose-lint.py` reports one that does, and G4 blocks on it
   (it is in the blocking mechanical row), because the section would otherwise be published. `/edit` drops the draft's section and keeps every marker.

## Decision (ships with PR 2)
8. **A human-written marker.** `<Needs to be written by a human. Reason: reason sentence here>`, the exact form of ADR-008. A reviewer's comment asks to skip one
   question; the outline or draft then marks its line `[SKIPPED]` with the reason and swaps that gap's marker for this one. Research keeps its open gap.
9. **FLOW-6 changes.** Both markers stop sign-off and the `publish-ready` label. The loose pattern becomes `(?:<Can.t be verified|<Needs to be written by a human)`.
   A human writes the text in `final.md` and removes the marker, which stales G4 and reruns it.

## Rejected
| Alternative | Why not |
|-------------|---------|
| One cumulative `questions.md` for the article | Breaks "an actor writes one artifact", and the verdict hashes and approvals are per artifact |
| Match each marker to its question by meaning in the script | No ids link them; the script would guess, and the gates would disagree with it |
| Let the human-written marker stay in the final | A final with a hole for a human is not publish-ready; the owner decided FLOW-6 covers it |
| A bare comment answer resolves a question | A comment is data, never a source the gate can open (ADR-012.6, ADR-021) |

## Consequences
- A workspace `CLAUDE.md` made earlier lacks the wider FACT-6 and STR-7 text; re-running `writer-plugin:setup` refreshes it (the gates read their own checklists).
- Do not downgrade past PR 2 while an article holds the human-written marker: the old loose pattern does not see it.

## Revisit when
Reviewers repeatedly answer questions in comments with no source, or the final routinely ships with `[SKIPPED]` lines nobody fills.
