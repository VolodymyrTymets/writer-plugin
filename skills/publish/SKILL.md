---
name: publish
description: Copies one article artifact (brief, research, outline, draft or final) to a new Google Doc revision for review and comments, and records it in docs.json. Use after a stage passes its gate, after its second BLOCK (an ungated copy for reviewers to comment on), or after sign-off for the publish-ready copy. The local Markdown stays the source of truth.
argument-hint: "[article slug] [stage: brief | research | outline | draft | final]"
allowed-tools: Read, Write, Glob, AskUserQuestion, Bash(python3 ${CLAUDE_PLUGIN_ROOT}/bin/doc-copy.py *), mcp__claude_ai_Google_Drive__create_file, mcp__claude_ai_Google_Drive__search_files
---

# Doc copy

This skill's command is `writer-plugin:publish`; when you tell the user how to rerun it, use that name.

A Google Doc is a **review copy**; the local Markdown is the source of truth (D1, ADR-012). Each copy is a **new Doc**: the
connector cannot change a Doc's content, so a revision is never an edit of an earlier Doc. You write one file, `articles/<slug>/docs.json`,
and only by appending one entry.

## Step 1 — Resolve the article and the stage

`$ARGUMENTS` is `<slug> <stage>`, `<slug>`, or empty. The stage is one of `brief`, `research`, `outline`, `draft`, `final`.
- No stage: the latest artifact that exists, in the order final, draft, outline, research, brief.
- No slug means `$ARGUMENTS` is empty or only a stage name (`brief`, `research`, `outline`, `draft` or `final`, which then stays the stage). List `articles/*/brief.md` with Glob: exactly one article, take it and name it in the report; two to four, ask with one `AskUserQuestion`, one option per article folder (the tool takes two to four options); more than four, print the folders and stop, so the user reruns with the slug; none, say there are no articles in this workspace and stop. If the question cannot be asked or returns no choice, print the folders and stop. A slug the user types counts only if it is one of the listed folders; otherwise say so and stop. Never guess it from the newest folder.

## Step 2 — Check for a Drive connection

The Doc is created with the tool `mcp__claude_ai_Google_Drive__create_file`. If that tool is not available in this session (the
connector is absent, or only its sign-in tool is offered), say once: "Doc copy: no Google Drive connection; run `/mcp` and sign in to
claude.ai Google Drive to make review copies. The local files are unaffected." Then stop and write nothing. Do not start a sign-in
yourself, and do not treat this as an error: the workflow goes on without the copy.

## Step 3 — Get the copy from the script

Run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/doc-copy.py <slug> <stage>` from the workspace root. It prints one JSON object:
`text`, `sha256`, `text_sha256`, `rev`, `publish_ready`, `title`, `skip`, `existing_url`, `folder_path`, `folder_id`, or `error`.
- On `error`: stop and quote it.
- If `skip` is true, this exact copy already exists: report `existing_url` and stop. No new Doc, no new entry.

You never strip fact tags, hash a file, pick a revision number or decide a label yourself: the script does all four, and the
guard checks the record against the same rules. Use its fields and copy them unchanged.

## Step 4 — Find the article's Drive folder

Every copy of an article goes into the folder `folder_path` names in My Drive, top first: `articles`, then the workspace folder's
name, then the slug. If `folder_id` is set, use it and go to Step 5. Otherwise resolve the folders of `folder_path` in order, each by
name under its parent (`'root'` for the first, then the id of the folder before it), with `mcp__claude_ai_Google_Drive__search_files`:

`title = '<name>' and mimeType = 'application/vnd.google-apps.folder' and parentId = '<parent>' and trashed = false`

Write the name exactly, with any `'` in it escaped as `\'`. One match: use it. None: create it with
`mcp__claude_ai_Google_Drive__create_file` (`title`: the name, `contentMimeType`: `application/vnd.google-apps.folder`, `parentId`:
the parent; no content). Several: use the oldest by `createdTime` and say so in the report. The slug folder's id is the one you record.

## Step 5 — Create the Doc

Call `mcp__claude_ai_Google_Drive__create_file` with:
- `title`: the script's `title`, unchanged
- `textContent`: the script's `text`, unchanged (it is Markdown; Drive keeps the headings, lists, bold and links)
- `contentMimeType`: `text/markdown`
- `parentId`: the slug folder's id from Step 4

Leave the other arguments unset. If the call fails, stop and report the error; write nothing.

## Step 6 — Record it

Read `articles/<slug>/docs.json` if it exists. Append one entry to its `revisions` list, set its `folder` to
`{"id": "<the slug folder's id>", "path": "<folder_path joined with />"}`, and write the whole file back with Write
(a missing file starts as `{"revisions": []}`):

```json
{"stage": "<stage>", "rev": <rev>, "id": "<the new Doc's id>", "url": "<its viewUrl>", "sha256": "<sha256>",
 "text_sha256": "<text_sha256>", "title": "<title>", "at": "<its createdTime>", "publish_ready": <publish_ready>}
```

`rev`, `sha256`, `text_sha256`, `title` and `publish_ready` come from the script; `id`, `url` and `at` come from the create call's result. Keep
every existing entry byte for byte: never change or remove an existing entry, never reorder them. If a hook blocks the write, stop
and report its message together with the new Doc's URL, and say the Doc exists but is not recorded.

## Step 7 — Report

One or two lines: the Doc URL, its title, the Drive folder it is in, and whether it is the publish-ready copy. For a final that is not publish-ready, say
why in one phrase (not signed off, or a marker remains; FLOW-6). Comments made on the Doc come back with `writer-plugin:sync`.

## Definition of done
- [ ] Without a Drive connection, nothing was written and the user was told once
- [ ] The Doc's title and text are the script's, unchanged
- [ ] `docs.json` gained exactly one entry, and no earlier entry changed
