# FT-21 — one Google Doc per artifact: spike and decision

## Problem
Every run of a stage makes a new Google Doc (`r1`, `r2`, `r3`, ...). The Drive fills with copies and a reviewer cannot tell which Doc is current or where a
question was answered. ADR-012 chose a new Doc per revision because the Drive connector's `update_file` changes metadata only. ADR-016 records a second
connector, Google Docs, whose `update_doc` can edit body text and has a `SUGGEST` mode, but it was never connected, so nobody has called it.

## Goal / business value
Goal 1 (correct gates, mechanical enforcement). The approval checkpoint (ADR-016) and the comment sync (ADR-012.6) both hang on "one Doc revision = one
immutable text". An in-place update could break either one silently. The cheapest way to avoid that is to measure first (D4: never state that a connector
tool can do something unverified), then decide in an ADR. Nothing is built until the ADR says go.

## Scope
- in: a spike with the Google Docs connector (R0); an ADR that records what was measured and decides go or no-go (R1); the DESIGN.md and ADR-012 status
  lines that follow from it (R2).
- **out (explicit):** any change to `bin/`, `hooks/`, `skills/`, `templates/` or tests. If the ADR says go, the build is a separate plan and PR (A4).
  Replying to or resolving comments (out of scope in BUSINESS_MODEL). Moving or deleting the old revision Docs. Any Doc outside a synthetic spike Doc.

## Acceptance criteria
- [x] AC1 Given the Google Docs connector is signed in, when the spike runs, then it records for `update_doc`: the input keys that hold the Doc id, the new text and
      the mode; and which modes exist (replace, insert, `SUGGEST`).
- [x] AC2 Given a synthetic Doc with one open comment thread, when its whole body is replaced, then the ADR states whether the thread survives, where its anchor
      goes and what `read_file_content(includeComments: true)` returns after.
- [x] AC3 Given the same Doc, when a change is made in `SUGGEST` mode, then the ADR states what `read_file_content` returns (is the suggestion visible, is the
      body the old or the new text) and whether a human accepting it changes the body.
- [x] AC4 Given a name typed after `Approved-by:` in the Doc, when the plugin then updates the body, then the ADR states whether the typed name survives and
      whether the record-approval check (body equals the artifact's copy, approval line ignored) can still tell a human edit from the plugin's own.
- [x] AC5 The ADR lists what ADR-012 (decisions 1, 3; "Rejected alternatives" row 1) and ADR-016 (approval record per Doc revision, `.docs-created.json`,
      the guard's refusal of every non-read tool on a logged Doc) would have to change for go, or says why they cannot.
- [x] AC6 The ADR ends in one word, GO or NO-GO, with the reason. DESIGN.md's FT-21 row is updated to match (`decided: go, build planned` or
      `rejected`), and ADR-012 gets a "Refined by" or "Superseded by" line only on GO.
- [x] AC7 No payload content (article text, comment text, names) appears in the repo; only key names and types (PLG-1).

## Edge cases
| Case | Expected behaviour | Decided by |
|------|--------------------|-----------|
| The Docs connector is not connected in the session | Stop: nothing in the ADR is guessed. Report and wait for an interactive session | D4, F2 |
| `update_doc` has no replace-all, only insert and delete by range | Record it; a rewrite by ranges is part of the go or no-go reasoning | R0 |
| Comments are dropped or orphaned by a rewrite | NO-GO unless `SUGGEST` keeps them; reviewer comments are the sync's input | ADR-012.6 |
| `update_doc` is unavailable but a Doc's content can be changed some other way | Record the tool and its input; do not adopt it without its own spike | D4 |
| The spike Doc is left in the human's Drive | The spike names it and trashes it only on the human's word (C4) | C4 |

## Open questions
| # | Question | My assumed answer | Needs a human? |
|---|----------|-------------------|----------------|
| 1 | Who runs R0? | The human, in an interactive session with `/mcp` signed in to Google Docs; I drive the calls once the tools load | yes: connect it |
| 2 | Where does the spike Doc live? | A throwaway Doc in My Drive root, titled `spike-ft-21`, synthetic text only | yes: confirm |
| 3 | Does NO-GO close FT-21? | Yes: status `rejected`, with the reason and what would reopen it | no |
