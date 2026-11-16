# ADR-012 — Doc copies are new Markdown Docs computed by a script, with FLOW-6 guarded on the record and the title

- **Date:** 2026-11-14
- **Status:** accepted
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (`docs/features/phase-7-publish-sync-setup/plan.md`, part 7b)
- **Refined by:** ADR-016 (approval typed in the Doc, the guard on Docs and connector tools; a headless session can have the Drive connector, so decision 7's "without a connection" path is not only for headless runs).
- **Refines:** ADR-001 (local Markdown stays the source of truth; a Doc is a review copy), ADR-009 (one more guarded path and the
  first MCP tool in the guard's matcher).

## Context
Every artifact gets a Google Doc copy for reviewers, and their comments come back as input to the next revision (DESIGN, Google Docs
copies). Two questions were open: does a Markdown upload keep its structure (open question 1), and are the Drive tools present in a
Claude Code session at all (open question 2). FLOW-6 says no final Doc is labelled publish-ready without a sign-off and while a
marker remains. Up to now the guard enforced FLOW-6 only on the sign-off line, not on any Doc.

## What was verified first (D4, 2026-11-14)
One spike Doc through the claude.ai Google Drive connector in an interactive Claude Code session:
- **Tools:** present as `mcp__claude_ai_Google_Drive__*` only after a `/mcp` sign-in. Before sign-in only an authenticate tool is
  offered. **A headless `claude -p` session has no Drive tools at all**, even when the same user is signed in interactively.
  - `create_file` takes `title`, `textContent`, `contentMimeType` and an optional `parentId`, and returns `id`, `viewUrl` and `createdTime`.
  - `update_file` changes metadata only, never content.
  - `read_file_content(fileId, includeComments)` returns the text with comments.
- **Fidelity:** `contentMimeType: text/markdown` converts to a Google Doc that keeps H1 to H3, bulleted and numbered lists, bold, and
  links, checked by HTML export and by read-back. Inline code loses its monospace and stays as plain text.
- **Comments:** `commentThreads[]` (`commentId`, `status`, `headPost` {`authorName`, `content`, `modifiedTime`}, `replies[]`). Each
  anchor sits inline in `fileContent` as `<comment_start id=X>…<comment_end id=X>`. An instruction-shaped comment arrives as ordinary
  text.
- **Folders (second spike, same day):** `create_file` with `contentMimeType: application/vnd.google-apps.folder` makes a folder.
  `parentId` nests folders and places Docs. `search_files` finds a folder by exact `title`, the folder `mimeType` and its `parentId`
  (`'root'` for My Drive).

## Decision
1. **A revision is a new Doc in the folder `articles/<workspace folder name>/<slug>/` in My Drive** (the approver's choice on PR #13:
   one `articles` folder holds every workspace). The copy skill finds or creates each of the three folders by exact name under their parent once, and records the slug
   folder's id and path in `docs.json` (`"folder"`); a renamed workspace changes the path, so the folders are looked up again. Each
   Doc is titled `<slug> · <stage> · r<k>`, plus ` · publish-ready` for a final that qualifies or ` · ungated`
   when the stage has no current PASS. Earlier Docs stay as the record of what reviewers commented on.
2. **The upload is Markdown** (`text/markdown`) with fact tags stripped outside code fences. No HTML or `.docx` conversion. A
   leading front-matter block becomes a `- **Title:** …` list (`writer.doc_text`). In the live run, Google turned raw front matter
   into a horizontal rule plus a stray heading, and a reviewer still needs to check the title, meta description and slug.
3. **`bin/doc-copy.py <slug> <stage>` computes everything the copy needs:** `text`, `sha256`, `rev`, `publish_ready`, `title`,
   `skip` and `existing_url`. It is read-only (the ADR-011 pattern). The `publish` skill uploads `text` under `title` and copies the
   fields unchanged into `articles/<slug>/docs.json`; the model never hashes, numbers or labels. `sha256` is the on-disk artifact's
   `text_hash` (approval lines ignored); the guard checks it. `text_sha256` is the hash of what reviewers see. A copy is skipped only
   when the stage's last entry has the same `text_sha256` **and** the same label. So a sign-off or a later PASS on unchanged text
   still makes a new Doc, and so does a change in how the text is rendered; an entry recorded without `text_sha256` never causes a skip.
4. **Publish-ready is defined once**, as `writer.publish_ready()`: the article is `done` (signed off on a current G4 PASS) **and**
   `final.md` holds no marker. `done` alone is not enough, because G4 may pass a marker (ADR-008) and a sign-off typed by hand skips
   the guard.
5. **The guard enforces FLOW-6 on both the record and the Doc:**
   - `docs.json` is append-only, valid `{"revisions": [...]}`, and never written by Bash.
   - A new entry may say `publish_ready: true` only for a final that is publish-ready, recorded on its exact on-disk hash.
   - The guard's PreToolUse matcher gains `mcp__claude_ai_Google_Drive__create_file` (and `update_file`, see Consequences). A create whose title claims the label, in any
     spelling (case, spaces, underscores, any hyphen), is refused unless that final qualifies **and** the upload is exactly that final
     as `doc-copy.py` prints it (`textContent`; never `base64Content`). The check runs before the Doc exists.
   - In `docs.json`, a new entry's `publish_ready` must be a boolean, a title with the label needs `true`, and duplicate keys are refused.
   - Unlike the rest of the guard, these checks **fail closed**: a final that cannot be read is not publish-ready. A false block
     costs only the label; a false allow breaches FLOW-6.
6. **The `sync` skill writes `articles/<slug>/comments/<stage>.r<rev>.md`.** It quotes every comment and reply verbatim with its anchor,
   under a header that says they are input to weigh, never instructions. It never replies, resolves or acts on a comment. The edit
   stage already reads `comments/`.
7. **Actors make their copy after a PASS** by invoking the `publish` skill. Without a Drive connection it says so once and the stage goes
   on. The orchestrator relays the actors' copies, and at `done` a human runs the copy skill for the publish-ready Doc.

## Rejected alternatives
| Alternative | Why not |
|-------------|---------|
| Update one Doc per stage in place | The connector cannot change content (`update_file` is metadata only), and an overwrite loses what reviewers commented on |
| HTML or `.docx` upload | Markdown already keeps the structure that matters; a converter is code with no gain |
| Let the skill hash, number and label | A prompt is a request; the guard would then judge numbers the model made up |
| Guard only `docs.json` | The Doc title is what a reviewer sees, and it is created before the record is written; a hook on the create call is the only check that runs first |
| `publish_ready` = `next == done` | A hand sign-off with a marker reads as `done`; FLOW-6 forbids it |

## Consequences
- Positive: FLOW-6 is mechanical on the Doc a reviewer sees, not just on a line in a file. The history of revisions is
  tamper-evident. Comments come back in a form the edit stage can cite.
- Accepted cost: copies and comment sync work only in an interactive session with the connector signed in. Headless runs (CI,
  evals, `claude -p`) always take the no-connection path. Inline code loses its monospace in the Doc. Each revision is a new Doc in the article's folder.
- Renames: `update_file` can retitle a Doc, so the matcher also includes `mcp__claude_ai_Google_Drive__update_file`, and no Doc is
  ever renamed onto the label, in any spelling. A rename cannot be checked against the Doc's content, so a final that qualifies
  gets its labelled Doc from a new upload. The copy skill never renames.
- Known limit: synced comments are reviewer-controlled text read by sessions that can write. The sync skill and the edit stage say
  a comment is data, never an instruction, but that is a prompt rule. The guard still refuses a sign-off that G4 did not pass.
- Follow-ups: the outline and draft stages reading synced comments.

## Revisit when
The connector can update a Doc's content or reply to comments, or a headless session can load the claude.ai connectors.
