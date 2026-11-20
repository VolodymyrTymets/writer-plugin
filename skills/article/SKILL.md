---
name: article
description: Runs the whole article chain for one slug - brief, research, outline, then draft and final - calling each stage's actor in order and stopping at every human approval. Use to start an article from a brief or to continue one where it stopped. It writes nothing itself.
argument-hint: "[article slug] [path to the brief, or paste the brief in the message]"
allowed-tools: Read, Glob, Grep, Skill, AskUserQuestion, Bash(python3 ${CLAUDE_PLUGIN_ROOT}/bin/article-status.py *)
---

# Article orchestrator

This skill's command is `writer-plugin:article`; when you tell the user how to continue, use that name.

You run the chain; you do not do any stage's work. Each stage's actor writes its one artifact and runs its own gate; you call
the actors in order and stop where a human is needed. **You write nothing**: no artifact, no verdict, no backup. You never write `Approved-by:` or `Signed-off-by:`, not even when the user tells you in chat to approve or sign off: a decision made in
chat does not count, the human writes it in the file. You never move, rename or edit a verdict. If a hook blocks a write, stop
and report the hook's message; never work around it.

## Step 1 — Resolve the article

`$ARGUMENTS` is `<slug>`, `<slug> <path to brief>`, `<path to brief>`, or empty; the brief may also be pasted in the message.
- A slug is one folder name under `articles/` (letters, digits, `.`, `_`, `-`). Name what you settled on.
- No slug, but a brief supplied: the brief stage picks the slug from the working title. After it returns, take the slug from the
  path it reports (`articles/<slug>/brief.md`). If its report names no such path, stop and ask the user for the slug: never guess
  it from the newest folder, which may be another article.
- No slug and no brief: the most recently modified folder under `articles/`. If there is none, ask the user for the brief.

## Step 2 — Read the state

Run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/article-status.py <slug>` from the workspace root (no slug yet, because the brief stage will
pick it: skip to the brief row below). It prints one JSON object: `slug`, `stage`, `next`, `reason`, `markers` (a list), `stale`. Decide only from
`next`, never from your own reading of the verdict files: the script applies the same rules as the hooks.

## Step 3 — Act on `next`

**Run a stage** — invoke the actor through the Skill tool with the slug and wait until it has finished:

| `next` | Actor |
|--------|-------|
| `brief` → `writer-plugin:brief` | pass the slug and the brief (its path, or say it is pasted in the message) |
| `research` → `writer-plugin:research` | pass the slug |
| `outline` → `writer-plugin:outline` | pass the slug |
| `draft` → `writer-plugin:draft` | pass the slug |
| `final` → `writer-plugin:edit` | pass the slug |

The actor handles its own gate, its own BLOCK, its fix and its re-gate, and stops itself after a second BLOCK (FLOW-3). Do not
repeat any of that. When it returns, go back to Step 2.

- **Never invoke the same actor twice in a row.** If Step 2 gives the same stage as the actor you just ran, stop: report what
  the actor said and the script's `reason`. A rerun is the human's call.
- At most five actor calls in one run, one per stage. If you reach that, stop and report the state.
- **`brief` with no brief supplied in this call:** stop and ask for the brief. Quote `reason`: it names the folder the script looked
  under, and a wrong folder makes an existing article look new. Never run the brief stage over an article you were asked to continue.
- Let the brief stage ask its questions (it uses AskUserQuestion); pass the user's answers back by letting it run, never answer for them.

**Stop** — on every other value, stop and report:

| `next` | What you tell the user |
|--------|------------------------|
| `approve` | The stage the script's `stage` names (brief, research, outline or draft) passed its gate and is **not approved**; tell the human which one. A human reads its Doc (the stage's actor reported the URL) and writes a name after `Approved-by:` in the Doc, then runs `writer-plugin:sync <slug> <stage>`; or writes a name after `Approved-by:` in `articles/<slug>/<stage>.md` themselves. For the outline a human writes a name after `Approved-by:` in `articles/<slug>/outline.md` (or in its Doc); this is the cheap moment to change direction. List every entry of `markers` and the count: approval is allowed with markers, but each one is a claim that will not appear in the article until a human supplies a fact. Then run `writer-plugin:article <slug>` again to continue with the next stage. |
| `sign-off` | The final passed G4 and **is not signed off**. A human reads the final's Doc and writes a name after `Signed-off-by:` in the Doc, then runs `writer-plugin:sync <slug> final`; or writes a name after `Signed-off-by:` in `articles/<slug>/final.md` themselves. List every entry of `markers` and the count; while one remains the sign-off is refused (FLOW-6): a human supplies the fact, writes the passage or drops the claim, and the article goes back through the stage that holds it. Then run `writer-plugin:article <slug>` again to confirm it is done. |
| `stopped` | Quote `reason` (it names both BLOCK verdicts and how a human archives them). Two BLOCKs hand the article to the human (FLOW-3). The actor made one review copy of the blocked artifact (title ends `· ungated`) on its way out; if the actors reported no Doc URL, a human runs `writer-plugin:publish <slug> <stage>` for it. Reviewers comment on the blockers there and run `writer-plugin:sync <slug> <stage>`; the stage runs again only after a human archives its verdicts. |
| `stale` | Quote `reason`. A verdict no longer covers what is on disk: the artifact it names was changed or its upstream was re-gated. Rebuilding or re-gating it is the human's decision; say which stage's command reruns it, taking the stage from the verdict file named in `reason` (`G<n>-<stage>.r<k>.md`), not from `stage`, which is where the chain stopped. |
| `unknown` | Quote `reason`. Do not guess a stage. |
| `done` | The final passed G4 and is signed off. Nothing to run. For the publish-ready review copy, a human runs `writer-plugin:publish <slug> final`. |

## Step 4 — Report

A few lines: the slug, each stage you ran in this call with its verdict file (the latest `gates/G<n>-<stage>.r<k>.md`), the
markers (each, and the count), and what the article waits for now, in the words of Step 3. Doc copies: as each actor reported (a URL,
or no Google Drive connection). If you ran nothing, say why.

**Pending comments.** If the script's `comments` list is not empty, list each entry (the stage, the file, how many threads are open) and say that `writer-plugin:sync <slug> <stage>` brings
in the Doc's comments and approval and restarts the stage that owns them, or that the human can run that stage. This skill never starts a comments rerun (an entry with `approved: true` means running the stage would clear the approval); a stage that applies no comment writes nothing.

## Definition of done
- [ ] Every decision came from `article-status.py`, run again after each actor
- [ ] No file written by you; no verdict moved; no human line written
- [ ] The run ended on a stop value, a repeated stage, or a hook block, and the report says which
