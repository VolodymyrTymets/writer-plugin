# writer-plugin — design

A Claude Code plugin that takes an **article brief** to a publish-ready English blog post through a fixed chain of
**actors** (each writes one artifact) and **gates** (each judges one artifact, read-only, in a fresh context).
Modelled on `rln-agent`: the same actor → gate → human-approval shape, the same "a hook is a mechanism, a prompt is a
request" stance, the same flat skills and structure test.

## Decisions

| # | Decision | Date |
|---|----------|------|
| D1 | **Source of truth is local Markdown** in the content workspace. Every artifact is *also* published as a Google Doc copy for review and comments. Hooks and gates read only the local files | 2026-11-12 |
| D2 | Content type: **blog posts**. SEO is a first-class gate concern, not an optional checklist | 2026-11-12 |
| D3 | Language: **English** only. No translation or localisation stage | 2026-11-12 |
| D4 | Plugin name `writer-plugin`, its own repo next to `rln-agent`, its own marketplace (`writer`) | 2026-11-12 |

## The flow

```
brief ──G0──▶ [approve] ──▶ research ──G1──▶ [approve] ──▶ outline ──G2──▶ [approve] ──▶ draft ──G3──▶ [approve] ──▶ final ──G4──▶ [sign off]
```

| Stage | Actor (writes) | Artifact | Gate (judges, read-only) | The gate asks |
|-------|----------------|----------|--------------------------|---------------|
| 0 | `/brief` | `brief.md` | G0 `/check-brief` | Is the brief complete and unambiguous enough to research? |
| 1 | `/research` | `research.md` with the fact bank | G1 `/check-research` | Are the sources real, authoritative and recent, and do they cover every question the brief raises? |
| 2 | `/outline` | `outline.md` | G2 `/check-outline` | Does the outline serve the brief's goal, reader and keyword, with every claim traceable to a fact? |
| — | **human** | `Approved-by:` line, after every stage but the last: typed in the stage's Google Doc and carried into the local file by `/sync` (or typed in the file) | — | The stage is closed when the local artifact has it; the outline's is the cheap moment to change direction |
| 3 | `/draft` | `draft.md` | G3 `/check-draft` | Developmental edit: does it follow the outline, does the argument hold, does it fit the brief? |
| 4 | `/edit` | `final.md` | G4 `/check-final` | Line edit: facts against sources, voice, SEO, prose lint, length |
| — | **human** | `Signed-off-by:` line in `final.md` | — | Publish-ready |

`/article <slug>` runs the whole chain (the counterpart of rln-agent's feature orchestrator): it asks `article-status.py` for the
next step, calls that stage's actor, asks again, and stops at every human approval, on two BLOCKs, on a stale verdict, or when
done. It writes nothing itself, never a human line, and never calls the same actor twice in a row (ADR-011). Each stage also works on its own.

**Why five gates, not two.** A brief with no named reader produces a generic article, and research with a wrong
number poisons every later stage; both are cheapest to catch where they are made. G3 and G4 are deliberately
different editors: judging structure and commas in one pass buries the structural finding under twenty line notes.

## The content workspace (what `/setup` creates in the user's repo)

```
CLAUDE.md                       # editorial constitution: rule IDs, publish config, which style guide applies
.claude/rules/style.md          # this client's voice, audience, banned phrases, link lists, SEO targets
articles/<slug>/
  brief.md                      # normalised brief (the input brief is kept as brief.source.md; a replaced one as brief.source.prev.md)
  research.md                   # questions, sources, FACT BANK (F1…Fn), competitor coverage, gaps
  outline.md                    # thesis, H2/H3 plan, per-section purpose + facts + word budget, keyword map, CTA
  outline.prev.<n>.md           # backup of an outline a rebuild replaced; never overwritten (ADR-007)
  draft.md
  draft.prev.<n>.md             # backup of a draft a rebuild replaced; never overwritten
  final.md                      # starts with front matter: title, meta_description, slug (read by prose-lint)
  final.prev.<n>.md             # backup of a final a rebuild replaced (its sign-off is cleared); never overwritten
  .quote-check.json             # the last recorded quote-check run on research.md (hash, one status per fact row, time); only the script writes it (ADR-015)
  .prose-lint.json              # the last recorded prose-lint run on final.md (hash, findings, finding lines, time); only the script writes it (ADR-010)
  gates/G<n>-<stage>.r<k>.md    # every verdict, saved by the caller with the Write tool (gates cannot write)
  gates/G<n>-<stage>.r<k>.json  # sidecar the record-verdict hook writes: what the verdict judged (ADR-009)
  docs.json                     # Google Doc id + URL per artifact revision
  .docs-created.json            # the Docs the copy skill created (id, title, text hash), written only by the record-approval hook (ADR-016)
  approvals/<stage>.r<rev>.json # the name a human typed in that Doc revision, or why there is none; written only by the hook (ADR-016)
  comments/<stage>.r<k>.md      # comments pulled back from the Google Doc by /sync
```

## Actors

Each actor reads its inputs from disk, writes exactly one artifact, invokes its gate, and after a PASS makes its Google Doc copy
through the `publish` skill (ADR-012). Each stage reruns on its reviewers' pending comments (ADR-016): the owning actor reads `comments/`, backs the artifact up, rebuilds it with them as input and is gated again, and `/sync` can start that rerun. An actor never edits an earlier stage's artifact; if it finds a problem upstream it stops and says so.

- **`/brief`** — turns whatever the user supplied (paste, file, Google Doc) into `brief.md` using the brief template.
  Asks at most two batched rounds of questions, only for gaps that change the article (`rln-agent` rule F1).
- **`/research`** — web research. Output is a dossier, not prose: the questions the brief raises, the sources, and the
  **fact bank** — one row per usable fact: `F7 | claim | source URL | publisher | published | accessed | verbatim quote`.
  Also: what the top-ranking articles for the keyword already say, and the gap this article fills.
- **`/outline`** — thesis, title options, H2/H3 structure; per section: purpose, key points, fact IDs, word budget;
  keyword placement; intro hook; CTA.
- **`/draft`** — writes the article section by section from the approved outline. Every factual claim carries its fact
  ID inline (`[F7]`) so later checks are mechanical; the IDs are stripped only when the Google Doc copy is made.
- **`/edit`** — revises the draft into `final.md` against G3's verdict and synced reviewer comments, then adds title,
  meta description and slug.

## Gates

- Every gate is a skill with `context: fork`, `background: false` and a write-free agent, exactly like `rln-agent`'s
  analyze gate. It sees only what is on disk — a decision made in chat but not written down does not count.
- Two agents serve all five gates; the checklist lives in each gate skill:
  `gate` (Read, Grep, Glob; G0, G2, G3) and `fact-gate` (the same plus WebFetch / WebSearch; G1 and G4, which must open the
  sources). No gate runs a script: G4 reads the finding lines the edit stage recorded in `.prose-lint.json` (ADR-010), and G1 reads the quote statuses the research stage recorded in `.quote-check.json` (ADR-015).
- G4 is one forked gate working sequentially (facts against sources, the recorded lint, voice, SEO); it is not fanned out.
- Verdict: `PASS | BLOCK`, every finding with a rule ID, the offending line and a concrete fix. Three real findings beat
  twelve stylistic ones. The caller saves the verdict to `gates/`.
- A BLOCK sends the work back to the same actor. **Two BLOCKs on the same artifact stop the run** (counted from the verdict files on disk, so a rerun cannot skip it; a human resumes by archiving that gate's verdicts; ADR-004) and hand it to the
  human (FLOW-3).
- Where research cannot find or prove something, a marker `<Can't be verified. Reason: …>` stands in for the claim and the flow goes on; a marker is not a BLOCK (ADR-008).
- A verdict covers the artifact as the gate saw it. After a PASS the actor never edits it: a change means changing the stage's
  written input and rerunning, with a new verdict (ADR-007). The human approval line is the only post-PASS write.

## Editorial constitution — rule IDs

Generic rules live in the plugin's `rules/core/`; anything client-specific (voice, banned words, internal link list,
reading level) lives in the workspace's `.claude/rules/style.md`, written by `/setup`. Gates cite these IDs.

| Prefix | Area | Examples |
|--------|------|----------|
| BRF | Brief | BRF-1 a specific reader is named · BRF-2 one goal and one CTA · BRF-3 primary keyword and search intent · BRF-4 target length and format · BRF-5 must-include / must-avoid stated · BRF-6 the questions the research must answer are listed |
| FACT | Facts | FACT-1 every statistic, date, named claim and quote cites a fact ID · FACT-2 every fact has a URL that resolves, publisher, published and accessed dates (a first-party vendor page with no date may say `n/a (live page)`) · FACT-3 quotes verbatim and attributed · FACT-4 statistics older than the style guide's limit are flagged; a live-page fact is aged by its accessed date and later stated as "checked <month year>" · FACT-5 no claim stronger than its source · FACT-6 every brief question is answered by a fact or listed under Open gaps, and at least half are answered (ADR-014) |
| STR | Structure | STR-1 the promise is stated in the first 100 words · STR-2 every section traces to the brief's goal · STR-3 section budgets sum to the target ±10% · STR-4 one H1, no skipped heading levels · STR-5 the close delivers the CTA · STR-6 the article's length is within the brief's target ±10% (a range widens at both ends) |
| VOI | Voice | VOI-1 voice per style guide · VOI-2 banned phrases · VOI-3 AI tells · VOI-4 reading-level target · VOI-5 no filler or stacked hedges |
| SEO | Search | SEO-1 keyword in title, first 100 words and at least one H2 · SEO-2 title ≤ 60 chars · SEO-3 meta description 120–155 chars · SEO-4 matches the search intent in the brief · SEO-5 internal links from the style guide, external links to sources · SEO-6 the final's `slug:` is lowercase kebab-case, chosen from the title or keyword |
| FLOW | Workflow | FLOW-1 a stage starts only after the previous gate's PASS is on disk · FLOW-2 no stage starts before the previous artifact is approved: `Approved-by:` on the brief, research, outline and draft, `Signed-off-by:` on the final (ADR-016) · FLOW-3 two BLOCKs → human · FLOW-4 gates never edit · FLOW-5 fix the artifact, never the style guide · FLOW-6 no `final` Doc is labelled publish-ready without `Signed-off-by:`, and none while a `<Can't be verified. Reason: …>` marker remains |
| PLG | This plugin | PLG-1 no client-specific knowledge enters the plugin repo |

## Mechanical enforcement (hooks)

Prefer a script or a hook over a prompt rule.

| Hook / script | When | Enforces |
|---------------|------|----------|
| `guard-stage-order` | PreToolUse on `Edit|Write|Bash` and every Drive and Docs connector tool | FLOW-1: writing `articles/<slug>/<stage>.md` needs the previous gate's latest verdict to be a PASS on what is on disk, walking up the chain (a rebuilt upstream or a hand edit makes a verdict stale, through the sidecar). FLOW-2: every stage after the brief also needs the previous artifact approved (ADR-016). FLOW-3: a stage whose gate has two BLOCK verdicts is stopped. FLOW-4: verdicts are immutable, created only by Write with a valid line 1 and the next number; Bash cannot touch `gates/`; a G4 verdict is saved only against a lint record that matches `final.md`; only `prose-lint.py` writes `.prose-lint.json`; a G1 verdict is saved only against a quote-check record that matches `research.md` (the BLOCK for a missing research needs none); only `quote-check.py` writes `.quote-check.json` (ADR-015). FLOW-6: a non-empty `Signed-off-by:` is written only against a current G4 PASS on the resulting content and never beside a marker (tool writes only). FLOW-6 on Doc copies: `docs.json` is append-only valid JSON that Bash cannot write, an entry is `publish_ready` only for a publish-ready final on its exact hash, no Doc is created with a `publish-ready` title unless the final qualifies and the upload is exactly its text, and no Doc is renamed onto that label (ADR-012). Path-based; needs no branch or ticket (ADR-009, ADR-010). ADR-016, failing closed (a false allow would skip a human checkpoint): FLOW-2 for every stage; a tool fills an approval line only against an approval record that matches the content (clearing is allowed, changing an approved artifact while keeping the name is not); no tool writes `approvals/` or `.docs-created.json`; a Doc upload never carries a filled approval line and an article Doc is exactly the artifact's copy; a new `docs.json` entry matches a logged Doc; a connector call on a logged Doc is refused unless it is a read |
| `record-verdict` | PostToolUse on `Write` | Writes the sidecar beside a saved verdict: the hash of the artifact it judged (approval lines ignored) and the upstream verdict it relied on |
| `record-approval` | PostToolUse on Drive `create_file` and `read_file_content` | Logs the Docs the copy skill creates (`.docs-created.json`) and, on a read of the latest Doc of a stage, records the name after the approval label (`approvals/<stage>.r<rev>.json`, or the reason there is none) when the Doc text equals the artifact's copy. A hook reads what the connector returned; the model never parses a Doc. Fails open: a failure records nothing (ADR-016) |
| `prose-lint.py` | A script, not a hook: called by `/draft` (without `--record`) and `/edit` (without, then with `--record` last); a gate never runs it; also usable alone | STR-4 headings, STR-6 length vs the brief, FACT-1 numbers with no `[F#]` (heuristic; it skips marker text, image paths, numbered labels such as "Screenshot 2" or "Step 3", "checked in <month year>", names with a digit such as G2, and reads `[F5, F14]` as one tag), and for a final SEO-1/2/3, VOI-2/3 from `style.md`, and any marker left in the text (FLOW-6, loose pattern). `--record` writes `.prose-lint.json` with the finding lines. Stdlib only |
| `quote-check.py` | A script, not a hook: called by the research stage (without `--record`, then with it as the last action on `research.md`); a gate never runs it; also usable alone | Fetches each fact-bank URL once and reports `found`, `found-elided`, `not-found`, `unreachable` or `unreadable` per row, a quote being checked word for word against the page's text (markup, whitespace, typography and closing punctuation on a cut quote do not count). 10 s per fetch, 90 s in all; plain client name, no browser disguise; it refuses non-public addresses, redirects included. `--record` writes `.quote-check.json`. Stdlib only (ADR-015) |
| `verify-final` | Stop | `final.md` written this session but no matching prose-lint run recorded → block once per article, quoting the command with the script's absolute path |
| `session-context` | SessionStart | At most 30 lines: where each article is and what it waits for (from `article_state()`, ADR-011); records the session start once. Silent outside a workspace |
| `article-status.py` | A script, not a hook: called by `/article` before and after every actor; also usable alone | One JSON object per article: `next` (a stage, `approve`, `sign-off`, `stopped`, `stale`, `done`, `unknown`), `reason`, `markers`. Same rules as the guard (FLOW-1 to FLOW-3, stale, FLOW-6), read-only. Stdlib only (ADR-011) |
| `doc-copy.py` | A script, not a hook: called by `/publish` before every upload; also usable alone | One JSON object: the Markdown to upload (fact IDs stripped), the artifact's hash, the next revision, the title with its label, `publish_ready` (done and no marker), and whether an identical copy already exists. Read-only. Stdlib only (ADR-012) |

## Google Docs copies

What the claude.ai Google Drive connector can do (spike, 2026-11-14; ADR-012):

- The tools exist as `mcp__claude_ai_Google_Drive__*` in an **interactive** session after a `/mcp` sign-in. A headless `claude -p` session had none in the
  2026-11-14 spike, but one run on 2026-11-16 had them and created a real Doc: a test run that must not touch Drive disallows `mcp__claude_ai_Google_Drive__*` and `mcp__claude_ai_Google_Docs__*`.
- `create_file` with `textContent` and `contentMimeType: text/markdown` **converts it to a Google Doc** that keeps headings, lists,
  bold and links (inline code loses its monospace).
- `update_file` changes **metadata only**, never content. So a revision is a **new Doc** (`<slug> · draft · r2`) in the Drive
  folder `articles/<workspace folder name>/<slug>/`, recorded in `docs.json`; the previous revision stays as the record of what reviewers commented on.
- `read_file_content(includeComments: true)` returns comment threads and inline anchors → `/sync` writes them, quoted verbatim, to
  `comments/<stage>.r<k>.md`, which the edit stage reads as reviewer input.
- Replying to or resolving comments is not available in the connector; `/sync` only reads.

Publishing is an **adapter step**, not a dependency: `/publish` looks for the Drive create tool; if none is connected it
says so once and the workflow continues — the local files are canonical (D1). `bin/doc-copy.py` computes the copy (text with fact IDs
stripped, hash, revision, title, publish-ready label), so the skill never does; the guard refuses a `docs.json` entry or a Doc title
that claims publish-ready for a final that is not (FLOW-6).

**Approval in the Doc (ADR-016).** Every copy is unapproved and says where to approve: one instruction names the `Approved-by:` (or `Signed-off-by:`) label and
`writer-plugin:sync`. A human types a name there; the `record-approval` hook records it when the Doc is read and its text still equals the artifact's copy; `/sync`
writes it into the local artifact; the guard accepts a tool write of an approval only against that record. The local file stays the source of truth (D1): a Doc is
the place a name is typed, not a source of the article's content. Whoever can edit a Doc can approve it, so the model may not share or edit one.

## Agents

| Agent | Tools | Used by |
|-------|-------|---------|
| `gate` | Read, Grep, Glob | G0, G2, G3 |
| `fact-gate` | Read, Grep, Glob, WebFetch, WebSearch | G1, G4 |

## Open questions

1. ~~Markdown fidelity in the Doc copy.~~ Resolved in Phase 7b (ADR-012): a `text/markdown` upload keeps headings, lists, bold and
   links; no conversion step.
2. ~~Drive tools inside Claude Code.~~ Resolved in Phase 7b (ADR-012): present in an interactive session after a `/mcp` sign-in, absent
   in headless `claude -p`; `/publish` and `/sync` say so once and the workflow goes on.
3. ~~G4 in parallel.~~ Resolved in Phase 5 (ADR-010): G4 is one forked gate on `fact-gate`, sequential; ten sources fit its turn budget.
4. **Keyword data.** There is no SERP or volume tool; the brief supplies the keyword and `/research` reads the current
   top results via WebSearch.
5. ~~A human's edit before approval.~~ Resolved in Phase 4 (ADR-009): the verdict's sidecar hash ignores the approval lines, so a hand edit makes it stale; a gate rerun saved with Write as the next verdict re-records it.
6. ~~Stale downstream verdicts.~~ Resolved in Phase 4 (ADR-009): each sidecar records the upstream verdict it relied on, and the guard blocks when that is no longer the latest. No file times are used.

## Field-test findings

One real brief run through the whole chain in a client workspace on 2026-11-15, plugin 0.0.1, interactive session with the
Drive connector: setup, brief, research, outline (stopped by FLOW-3, resumed by a human), approval, draft, Doc copies
and comment syncs for every stage, edit, G4. It stopped at a G4 BLOCK before sign-off. Findings are written generically
(PLG-1). Each fix is its own PR; it ticks its item here. Ranked by BUSINESS_MODEL goal 1: gate correctness first.

| # | Where | What happened | Expected | Rule | Status |
|---|-------|---------------|----------|------|--------|
| FT-1 | `prose-lint.py` SEO-1 | Reads the whole `**Primary keyword:**` value as the keyword (`bin/prose-lint.py:181`). The brief line held the keyword plus search volumes and usage notes, so SEO-1 fired three times (title, first 100 words, H2) though the keyword was in all three. G4 must block on recorded lint lines, so a lint bug cost one of two FLOW-3 strikes; the only ways out are a lint fix or a brief rebuild that stales every verdict. G0 passed the brief | The keyword is the bare phrase: parse up to the first `(`, `.` or `;`, or have BRF-3 and the template require a bare keyword | SEO-1, BRF-3 | fixed: the lint ends the keyword at the first `(`, `;` or `. `, and the brief template says bare phrase only |
| FT-2 | G1 coverage | G1 passed with `Coverage: 1 answered, 9 open (of 10)`: an open question listed under Open gaps is allowed, with no minimum. The outline then carried 29 markers, the draft 30 and the final 31, so sign-off was out of reach without a large manual fill | A research dossier that answers few of the brief's questions does not pass silently: a coverage floor, or a stop for a human to decide | FACT-6, FLOW-3 | fixed: G1 blocks when fewer than half the questions are answered (ADR-014); two BLOCKs then hand it to a human |
| FT-3 | Research sources | Review sites and one vendor pricing page returned HTTP 403 to WebFetch. Research took about two minutes, tried no fallback (search results, another copy of the page, asking the human for an export) and moved the questions to Open gaps. Its "verbatim" quotes come through WebFetch's summary of the page | A blocked source gets a fallback or a request to the human before it becomes a gap; quotes are checked as verbatim | FACT-2, FACT-3 | fixed: the research stage retries, then looks for another page, then opens a gap that names the tries, and reports blocked sources; the verbatim check is a script whose recorded result G1 reads (ADR-015) |
| FT-4 | `prose-lint.py` FACT-1 | 36 of 69 recorded lint lines were noise: numbers inside marker reasons ("HTTP 403"), numbered screenshot labels, the method date ("Data checked in <month year>"), and fact lists written `[F5, F14]` (the pattern accepts only `[F5][F14]`). Actors called the rest "false positives" and filtered the lint with `grep -v`; G4 discarded them by hand | Skip marker text and labels, accept a comma list of IDs, so a FACT-1 line is worth reading | FACT-1 | fixed: the lint skips those forms and reads a comma list as one tag; on a real final 36 FACT-1 lines became 1, a dated method statement the finding did not list |
| FT-5 | Reviewer comments → stages | Only the edit stage reads `comments/`. A reviewer's comments on a research, outline or draft Doc, synced with `/sync <stage>`, changed nothing: the draft stage refused ("already passed its gate") and the comments landed one stage later in `final.md`; research and outline comments had no reader at all until the human asked by hand | Sync a stage's comments, then that same stage reruns with them as input: backup, rebuilt artifact, gate `r<k+1>`, Doc `r2`; downstream verdicts go stale (ADR-009). A new flow: needs an ADR | FLOW-1, ADR-007, ADR-012 | fixed: a pending comments file (its hash is the artifact's, with an open thread) is the written input of research, outline, draft or the edit stage; `/sync` restarts that stage once when no approval came in; the stage backs up, rebuilds, clears the approval and is gated again, and downstream verdicts go stale (ADR-016) |
| FT-6 | Doc copy of the outline | The copy contains the `Approved-by:` line and its comment. The human approved in the Doc; the local line stayed empty. Sync noticed the mismatch and said so | The Doc copy leaves out the approval and sign-off lines, or replaces them with one line saying where to approve | FLOW-2, ADR-012 | fixed in PR 1: a copy is always unapproved and says where to approve; approval typed in the Doc is recorded by a hook and carried in by `/sync` (ADR-016); the comment half of the stage flow is FT-5 |
| FT-7 | Draft length | The lint flagged 3,493 words against a 3,500 to 4,000 range, and the actor padded prose to chase the count. STR-6 says "within the brief's target ±10%", but `length_bounds` applies the 10% only to a single number, not to a range; the actor then told the user it was within tolerance | The lint and STR-6 agree on one rule for a range, and an actor does not pad to clear a flag | STR-6 | fixed: `length_bounds` applies the 10% to both ends of a range (3,500 to 4,000 allows 3,150 to 4,400); the draft and edit skills say not to pad to clear a flag |
| FT-8 | Brief from a PDF | The brief stage says to save the input unchanged as `brief.source.md`; a PDF has no unchanged text form. The actor ran `pdftotext` through Bash, outside its allowed tools, and it worked only because the tool was installed | Say how a PDF brief is read and saved | — | fixed: a PDF is read with Read in chunks of at most 20 pages and saved as the text Read returned under an "extracted from" line; a scanned PDF stops the stage and asks for text (no shell, no OCR). Ran headless on a text PDF, a replacement PDF (backup made) and an image-only PDF (stopped, nothing written); Read returned only page images for one text PDF on one run, so a text PDF is not guaranteed |
| FT-9 | Slug | The user gave a capitalised publisher name as the slug. It was accepted, and became the `slug:` in the final's front matter, so the article's URL slug was the folder name | Validate the folder slug as kebab-case; keep the SEO slug a separate value from the folder name | — | fixed: the brief stage normalises the folder slug to kebab-case and names the change, never renames a folder; the final's `slug:` is the SEO slug and `prose-lint.py` reports one that is not kebab-case as SEO-6. The guard and status script still accept any folder name |
| FT-10 | Outline markers | Research held 6 markers; the outline turned its open gaps into 29 | Decide whether one gap may fan out into many markers, or one marker per gap | ADR-008 | fixed: one open gap gets at most one marker and a claim with no fact and no gap is dropped; G2 blocks more markers than open gaps as FACT-1 (ADR-017). A gap that needs two facts may now block G2 (one FLOW-3 strike, accepted) |
| FT-11 | Command names | The user ran `/writer-plugin:setup-workspace` and `/writer-plugin:sync-comments`, the folder names, while the skills tell users to rerun `writer-plugin:setup` and `writer-plugin:sync` (frontmatter `name:`). The Skill tool did resolve `writer-plugin:brief` to `intake-brief`. The Claude Code docs build the command as `/<plugin>:<directory>` and let `name:` replace the last segment | One name per command that the menu, the skill text and `COMMANDS` agree on | — | fixed: the four folders are renamed to their command and the structure test fails when a folder and its `name:` differ (ADR-018) |
| FT-12 | Sync without a slug | `/sync research` with no slug: the actor asked with a one-option question, the tool rejected it, and the actor guessed the slug, against its own "never guess" line | With one article in the workspace, take it; otherwise offer the folders as options | — | fixed: `sync` and `publish` list `articles/*/brief.md`; one article is taken, two to four are offered with `AskUserQuestion`, more are listed, a lone stage name counts as no slug |
| FT-13 | Verdict save | Actors did not save the verdict unchanged: blank lines added, so `Coverage:` and `Markers:` moved off line 3. Only line 1 is parsed today | Save the gate's text byte for byte, or have `record-verdict` check lines 1 to 3 | ADR-004 | open |
| FT-14 | Markers in the Doc copy | A `<Can't be verified. Reason: …>` marker reads as plain text in the Doc, so a reviewer scanning the copy cannot see the gaps they are meant to fill | Each marker stands out in the Doc. Bold is known to survive the Markdown upload (ADR-012); whether the connector can set a highlight colour is not checked | FLOW-6, ADR-012 | open |

Worked as designed: the guard refused a shell write into `gates/` and the actor saved with Write (FLOW-4); FLOW-3 stopped
the outline after two BLOCKs and a human's archive resumed it; G4 opened all 21 sources and caught a dropped condition
that G3 had passed (FACT-5); `docs.json` stayed append-only; the session recovered from disk after an auto-compaction.

Not plugin bugs: another plugin's hooks were active in the workspace and asked for confirmations and "done" evidence on
`docs.json`; the workspace was not a git repository.

## Build plan

| Phase | Scope | Status                                                                                                                                                                                            |
|-------|-------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 0 | Decisions D1–D4; 2–3 real briefs to test with | decisions done · test briefs: three synthetic public-topic briefs in `evals/briefs/` (ADR-013); real client briefs run only in client workspaces (PLG-1) |
| 1 | Repo skeleton: manifest, marketplace, `CLAUDE.md`, README, CONTRIBUTING, this design, structure test | done                                                                                                                                                                                              |
| 2 | `rules/core/CLAUDE.template.md` (rule IDs above), `templates/`: brief, research dossier, outline, style guide | done                                                                                                                                                                                              |
| 3 | **Vertical slice:** `/brief`, `/research`, `/outline`, `/check-brief`, `/check-research`, `/check-outline`, agents `gate` and `fact-gate`. Run on one real brief before going further | done · all three stages ran end to end on one real brief; the outline passed its gate with markers (ADR-008) and a human approved it |
| 4 | `guard-stage-order`, `record-verdict`, `prose-lint.py`, `verify-final`, `session-context` + hook tests (ADR-009) | built · run in real sessions; draft, edit and final-gate stages are Phase 5 |
| 5 | `/draft`, `/edit`, `/check-draft`, `/check-final` (open question 3 resolved, ADR-010). They carry markers through and the guard refuses sign-off while one remains (FLOW-6, ADR-008) | built · each stage and gate run in a scratch workspace; one real brief run through draft, edit and G4, stopped at a G4 BLOCK before sign-off (FT-1, FT-2; see Field-test findings) |
| 6 | `/article` orchestrator with the human approvals (ADR-011; five of them since ADR-016) | built · ran end to end on a scratch article from brief to sign-off, with both checkpoints; one real brief run from brief to G4 with the outline checkpoint, 14 findings (see Field-test findings) |
| 7 | `/publish`, `/sync` (resolve open questions 1–2), `/setup`, evals on the test briefs | 7a built · `/setup` ran headless in a scratch workspace (constitution written, rerun left it unchanged, refused in the plugin repo); the `.claude/` write needs an interactive approval. 7b built · open questions 1–2 resolved by a Drive spike (ADR-012); the guard's FLOW-6 rules ran on real payloads; the Drive tools exist only in interactive sessions, and `/publish` and `/sync` ran live in one (an outline copy, a publish-ready final, a skip, a comment sync); headless, both took the no-connection path. 7c built · 16 eval cases (ADR-013): a PASS and a seeded BLOCK per gate, G0 per brief and the brief stage per brief; one case run ($0.05, score 1.00), the full suite not yet run |
| 8 | Approval in the Doc (FT-6, ADR-016): unapproved copies with an instruction, the `record-approval` hook, the guard's fail-closed rules, `approve` for every stage, `/sync` carrying the approval | built · ran live on a synthetic Doc: the create hook logged the real `create_file` response, the recorder read the name typed in the Doc, `/sync` wrote only the approval line and the status moved to `draft`; the comment rerun ran live too: a comment with no approval restarted the outline stage once (`outline.prev.1.md`, `G2` r2, a new Doc), and a comment with an approval restarted nothing and left the comment listed; the Docs connector's `update_doc` was never exercised |
