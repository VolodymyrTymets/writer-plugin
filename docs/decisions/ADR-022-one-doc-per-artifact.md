# ADR-022 — One Google Doc per artifact, updated in place: NO-GO

- **Date:** 2026-11-19
- **Status:** accepted
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (`docs/features/FT-21/plan.md`, field-test finding FT-21)
- **Revisits:** ADR-012 ("Rejected alternatives", row 1), whose reason was that the Drive connector cannot change content. That reason no longer holds
  as stated; this ADR records what was measured and why the decision still stands.
- **Leaves unchanged:** ADR-012 and ADR-016. No "Refined by" line is added to either (a NO-GO changes nothing in them).

## Context
Every run of a stage makes a new Doc (`r1`, `r2`, ...), so the Drive fills with copies (FT-21). ADR-012 rejected updating one Doc in place because
`update_file` changes metadata only. ADR-016 recorded that the Google Docs connector has `update_doc` and a `SUGGEST` mode, but it was never connected,
so nothing was known (D4). Two mechanisms depend on "one Doc revision = one immutable text": the approval record (ADR-016: one record per Doc revision,
valid only while the Doc body equals the artifact's copy) and the comment sync (ADR-012.6: comments belong to one revision of one artifact).

## What was measured first (D4, 2026-11-19)
Two synthetic Docs made with the Drive `create_file` from the eval fixture's outline, `update_doc` called live, every read-back through
`read_file_content(includeComments: true)`. A human added one comment, typed a name after the approval label, and accepted a suggestion. Key names and
yes/no only; no payload text is recorded here (PLG-1).

| Question | Result |
|----------|--------|
| `update_doc` input | `documentId` (the Drive file id), `requests[]` (`documents.batchUpdate` operations), `writeControl{writeMode, requiredRevisionId, targetRevisionId}`; `writeMode` is `EDIT` or `SUGGEST` |
| Modes | No replace-whole-body operation. A rewrite is `replaceAllText`, or `deleteContentRange` plus `insertText`; a range may not include the body's last newline |
| Targeted `replaceAllText` in `EDIT` | The comment thread, its anchor, the typed name and all other text survive; the read-back changes only the replaced words |
| Whole-body delete plus insert in `EDIT` | The comment thread is gone from the read-back (`commentThreads` absent). Inserted text takes the formatting of the paragraph at the insertion point (headings and paragraphs came back as list items); Markdown is not interpreted |
| `SUGGEST`, before a human accepts | The read-back holds the old and the new text joined in one paragraph, with no marker that a suggestion is pending |
| `SUGGEST`, after a human accepts | The read-back holds only the new text |
| Old body recoverable | No. `list_file_revisions` returns the revision id, time and user name, never a text; no connector tool seen returns a revision's body. Whether `download_file_content` can fetch an old revision was not tried |
| Does the typed name survive | Yes, when the update does not touch its line (targeted edit, and a rewrite that spares it) |

**The hook, not the eye (AC4).** The same read-back strings were replayed through `bin/record-approval.py` in a scratch workspace holding the fixture
outline, a matching `docs.json` and a logged Doc (strings rebuilt from this session's connector results, not saved raw):

| Read-back | `approvals/outline.r1.json` |
|-----------|-----------------------------|
| Unnamed, unchanged | `value` null, reason "no name after the approval label" |
| Named, unchanged | the name is recorded |
| Text edited in the Doc, local artifact not updated | null, "the Doc text differs from the artifact (it was edited in the Doc)" |
| Text edited in the Doc, local artifact updated afterwards | null, "the artifact changed since this Doc was made" |
| Whole-body rewrite | null, "the Doc text differs from the artifact" |
| `SUGGEST` pending | null, "the Doc text differs from the artifact" |

The recorder never recorded a false approval, and it cannot tell the plugin's own update from a human edit: both read as "edited in the Doc". After an
in-place update, therefore, no approval can be recorded at all until the record's anchor changes (below).

## What GO would have to change (AC5)
- **ADR-012.1 and .3 (a new Doc per revision, `docs.json` append-only per revision).** `docs.json` would need one Doc per artifact plus a revision
  counter inside it; the guard's FLOW-6 rule that an entry is `publish_ready` only on its exact hash assumes one hash per entry.
- **ADR-012 "Rejected alternatives", row 1.** Its first half is false now (`update_doc` changes content). Its second half stands: an overwrite loses
  what reviewers commented on, unless the update is a computed diff of targeted edits, never a body rewrite.
- **ADR-016.3 (the approval record is per Doc revision, anchored to the Doc text as created).** It would become per Doc and per text version,
  anchored to the plugin's last write. A name typed on the old text stays in the Doc after an in-place update, so the update would have to clear the
  approval line, or a human could appear to approve text they never saw (FLOW-2).
- **ADR-016.4 (the guard refuses every non-read tool on a logged Doc).** `update_doc` would be allowed only for the plugin's own text, which the guard
  can check only against the computed diff of the artifact; a `requiredRevisionId` would have to be sent so a reviewer's concurrent edit is not overwritten.
- **ADR-012.6 (comment sync).** A comment's anchor text may have been rewritten by the time it is synced; the sync would need to say which text version
  a comment was made on, and no tool returns an old version.
- **The old revision Docs.** What they become (kept, trashed by a human, linked) is a separate decision.

## Decision
**NO-GO.** Keep a new Doc per revision.

Reason: the measurements remove the connector's blocker but not the two that matter for goal 1. (1) A whole-body rewrite loses the comment thread, so
the only safe update is a diff of targeted edits, a new component the plugin would have to get right for tables, lists and Google's reformatting
(the read-back is a lossy rendering, ADR-016). (2) An in-place update makes approval and comment history depend on a text version the connector can
neither return nor show as pending (`SUGGEST` is invisible in the read-back), so an approval could cover text the human never read. The cost of the
current design is clutter in Drive, which a human can trash; the cost of GO is a possible false approval at a human checkpoint. Not sure, and not
measured: `update_doc` on a Doc with several tabs, on a table cell, with two people editing at once, and on a long body; and whether a revision's text
can be fetched with `download_file_content`.

**What would reopen it:** a connector tool that returns a revision's text or shows a pending suggestion in the read-back, or a measured diff-based
update that keeps comment threads on a table-heavy outline.

## Consequences
- FT-21 is closed as `rejected` in `docs/DESIGN.md`; nothing in `bin/`, `hooks/`, `skills/` or tests changes.
- Clutter stays. A human can trash old revision Docs in Google Drive; the plugin never trashes or edits a logged Doc (ADR-016.6).
- Two synthetic spike Docs are left in the human's Drive root for the human to trash (C4).
