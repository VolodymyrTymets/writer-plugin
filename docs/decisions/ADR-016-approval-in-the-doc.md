# ADR-016 — A human approves in the Google Doc; a hook records it, sync carries it, and a stage is closed when the local artifact has it

- **Date:** 2026-11-17
- **Status:** accepted
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (`docs/features/comment-rerun-and-clean-copies/plan.md`, field-test finding FT-6; FT-5 follows in a second PR)
- **Refines:** ADR-001 (a Doc is still never a source of an artifact's content; it is now also where an approval is typed), ADR-005 (the draft
  has no template: its stage writes the empty line), ADR-009 (more hook rules), ADR-011 (a model still never writes an approval on someone's
  say-so: `/sync` writes it from a record a hook made), ADR-012.3, .5 and .6 (Doc text, the guard on uploads and `docs.json`, and what sync does).

## Context
A field test (FT-6) showed a human approving the outline in its Google Doc while the local `Approved-by:` line, the only one the guard reads
(FLOW-2), stayed empty. Approval and the place it counts were apart. The maintainer's flow: the human approves in the Doc, `/sync` brings the
approval into the local file, and the stage is closed when the local file has it, for every stage.

## What was verified first (D4, 2026-11-16 and 17)
A throwaway logging plugin and one synthetic Doc (the eval fixture's outline), key names and types only:
- A `PostToolUse` hook is called for the claude.ai Drive tools. Its input has `tool_input` (`fileId`, `includeComments` for a read), `tool_response`,
  `mcp_server {name, source}` and the usual session keys. For `read_file_content`, `tool_response` is a **JSON string** with `fileContent`, `title`, `viewUrl`
  and, only when there are comments, `commentThreads[{commentId, headPost{authorName, content, modifiedTime, postId}, status}]`. For `create_file` it
  is a JSON string holding the new Doc's `id` (confirmed live, 2026-11-17). The shape differs per tool (`Bash` returns a dict).
- The read-back is a lossy rendering: the HTML comment is dropped, headings come back as `## *Thesis*`, backticks are gone, single newlines merge into one
  paragraph, a table gets an empty header row, URLs sit in `<…>`, and a comment anchor is `<comment_start id=X>…<comment_end id=X>` inside the text. The
  lower-case `\w+` word sequence of the upload (minus the HTML comment and the approval line) equals the read-back's (463 tokens each).
- A name typed after the label reads back on the same line, `Approved-by: <name>`. A line directly after another line merges with it, so the instruction and the
  label are separate paragraphs.
- Tools: the Docs server has `read_doc` and `update_doc` (id in `documentId`; it can edit body text and has a `SUGGEST` mode); the Drive server's tools all take
  `fileId`, and `create_file` also takes `base64Content` and a deprecated `content`. The Docs connector was not connected in the session used, so `update_doc` was
  never called; a pending suggestion left no trace in `fileContent` (not confirmed that one was made).
- `/hooks` does not list plugin-provided hooks in this build; the check that works is a call the guard must refuse.

## Decision
1. **Five human checkpoints.** FLOW-2 becomes "no stage starts before the previous artifact is approved": `Approved-by:` on the brief, research, outline and
   draft; the final keeps `Signed-off-by:` (FLOW-6 unchanged). A stage is finished when its local artifact carries the line.
2. **A Doc copy is always unapproved.** `doc_text` empties every approval line and adds one instruction naming the label and `writer-plugin:sync`, in its own
   paragraph; the instruction is never in a local artifact. The one exception is the publish-ready final, which keeps its signed line. A guidance HTML comment
   above the line is dropped (Google drops it anyway).
3. **A hook, not the model, reads the Doc.** `record-approval.py` (PostToolUse on Drive `create_file` and `read_file_content`):
   - on create, it logs the Doc in `articles/<slug>/.docs-created.json` only if the title is an article title and the text is exactly `doc_text` of the artifact on
     disk (an unapproved copy, or the exact publish-ready final, which is logged as not approvable);
   - on read of a logged Doc that is the latest revision of its stage, it writes `approvals/<stage>.r<rev>.json` `{doc_id, rev, artifact_sha256, value, reason, at}`:
     `value` is the name after the label (first label line outside a fence, trimmed, at most 120 characters, comment anchors stripped), or null with a `reason` (no
     name; an older Doc; the artifact changed since the Doc was made; the Doc text was edited in the Doc). The body must equal the artifact's copy by word
     sequence (numbers keep their sign, decimal mark, currency and percent; `<`, `>`, `=` and `±` count; markdown escapes and underscores do not), ignoring
     the approval line and the instruction. A later read without a name clears the earlier approval. The recorder fails open.
4. **The guard fails closed for these rules** (ADR-012.5: a false allow would skip a human checkpoint), in a wrapper outside `fail_open`, with a test seam
   `WRITER_GUARD_TEST_FAULT` (like `QUOTE_CHECK_ALLOW_LOOPBACK`):
   - writing a stage's file needs the previous artifact approved;
   - a Write or Edit makes an approval line non-empty only against a record whose value and hash match the resulting content; clearing it, or leaving the file
     untouched, is allowed; changing an approved artifact while keeping the name is not (an approval covers the exact text);
   - no tool writes `approvals/` or `.docs-created.json`;
   - a `create_file` never carries a filled approval line (the exact publish-ready final excepted), and a Doc titled as an article's copy is exactly that copy;
   - a new `docs.json` entry matches a logged Doc (id, title, text hash) and the artifact's hash;
   - a connector call on a logged Doc is refused unless it is on a read list: the Doc id is looked for in every string of the tool input, at any depth and inside
     a URL, so a tool added later is caught whatever key it uses; a write tool that names no Doc is refused.
   - a shell command that names an approval label and writes an artifact is refused (the parser sees the target, not the content);
     an `articles/` path is read case-insensitively and through symlinks (the default macOS filesystem ignores case).
     A missing log means "nothing protected yet"; only a log that exists but cannot be read refuses. The Drive and Docs server prefixes are matched.
5. **`/sync` carries the approval in.** It reads the record, never the Doc text or a comment, and writes only the approval line, with Edit; it never overwrites a
   different local value, and it reports the guard's refusal as it is.
6. **Trust.** Whoever can edit a Doc can approve it, and the name is recorded as typed. Sharing is the control, so the model may not share, copy, rename, trash or
   edit a logged Doc (the human does it in Google Drive). A human typing in the local file in an editor is allowed: no hook sees an editor.

## Known gaps
- A write the shell parser cannot read (`python3 -c`, command substitution) can still put an approval line into an artifact, as the final's sign-off could (ADR-010).
- The guard matches Edit, Write, Bash and the two connector servers. A file-writing tool of any other MCP server is outside every rule here.
- A connector outside the two matched servers that can edit a Doc body is not covered. Within them, an unknown tool is refused only on a logged Doc id.
- Whether a pending (unaccepted) suggestion could show as text was not observed.
- The recorder trusts `tool_response` as the connector returned it.

## Rejected alternatives
| Alternative | Why not |
|-------------|---------|
| The `sync` skill reads the name out of the Doc | The model would parse reviewer-controlled text and write an approval from it; the hook reads the response instead |
| Approval stays local only | It is the failure FT-6 found: reviewers approve where they review |
| Trust the `docs.json` hash to know a Doc is the copy | The model appends those entries; the created log and the body comparison do not rely on it |
| Guard only `update_doc` | `copy_file`, `share_file` and a tool added later can reach the same Doc; the read list is the allow-list |
| Keep the filled line in the copy | A forged or stale name in an upload would be read back as an approval |

## Consequences
- In-progress articles with no approval line on a passed stage show `approve` for it until a human adds the line (a missing line is not approved).
- Workspaces that already hold the old constitution re-run `writer-plugin:setup` or edit FLOW-2 in their `CLAUDE.md`.
- Downgrade: `approvals/` and `.docs-created.json` are inert under the old version and safe to delete; the old FLOW-2 checks only the outline.
- A new Doc revision is made once per article because the Doc text changed (ADR-012.3).
- Follow-up (PR 2): comments synced from a Doc become the written input of the stage that owns the artifact (FT-5).

## Revisit when
The Docs connector's `update_doc` can be exercised and a suggestion's read-back is known, or a tool that edits a Doc body appears outside the matched servers.
