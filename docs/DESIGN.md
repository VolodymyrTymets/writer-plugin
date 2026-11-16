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
brief ──G0──▶ research ──G1──▶ outline ──G2──▶ [human approves] ──▶ draft ──G3──▶ final ──G4──▶ [human signs off]
```

| Stage | Actor (writes) | Artifact | Gate (judges, read-only) | The gate asks |
|-------|----------------|----------|--------------------------|---------------|
| 0 | `/brief` | `brief.md` | G0 `/check-brief` | Is the brief complete and unambiguous enough to research? |
| 1 | `/research` | `research.md` with the fact bank | G1 `/check-research` | Are the sources real, authoritative and recent, and do they cover every question the brief raises? |
| 2 | `/outline` | `outline.md` | G2 `/check-outline` | Does the outline serve the brief's goal, reader and keyword, with every claim traceable to a fact? |
| — | **human** | `Approved-by:` line in `outline.md` | — | The cheap moment to change direction |
| 3 | `/draft` | `draft.md` | G3 `/check-draft` | Developmental edit: does it follow the outline, does the argument hold, does it fit the brief? |
| 4 | `/edit` | `final.md` | G4 `/check-final` | Line edit: facts against sources, voice, SEO, prose lint, length |
| — | **human** | `Signed-off-by:` line in `final.md` | — | Publish-ready |

`/article <slug>` runs the whole chain (the counterpart of rln-agent's feature orchestrator): it asks `article-status.py` for the
next step, calls that stage's actor, asks again, and stops at the two human checkpoints, on two BLOCKs, on a stale verdict, or when
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
  .prose-lint.json              # the last recorded prose-lint run on final.md (hash, findings, finding lines, time); only the script writes it (ADR-010)
  gates/G<n>-<stage>.r<k>.md    # every verdict, saved by the caller with the Write tool (gates cannot write)
  gates/G<n>-<stage>.r<k>.json  # sidecar the record-verdict hook writes: what the verdict judged (ADR-009)
  docs.json                     # Google Doc id + URL per artifact revision
  comments/<stage>.r<k>.md      # comments pulled back from the Google Doc by /sync
```

## Actors

Each actor reads its inputs from disk, writes exactly one artifact, invokes its gate, and after a PASS makes its Google Doc copy
through the `publish` skill (ADR-012). An actor never edits an earlier stage's artifact; if it finds a problem upstream it stops and says so.

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
  sources). No gate runs a script: G4 reads the finding lines the edit stage recorded in `.prose-lint.json` (ADR-010).
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
| STR | Structure | STR-1 the promise is stated in the first 100 words · STR-2 every section traces to the brief's goal · STR-3 section budgets sum to the target ±10% · STR-4 one H1, no skipped heading levels · STR-5 the close delivers the CTA · STR-6 the article's length is within the brief's target ±10% |
| VOI | Voice | VOI-1 voice per style guide · VOI-2 banned phrases · VOI-3 AI tells · VOI-4 reading-level target · VOI-5 no filler or stacked hedges |
| SEO | Search | SEO-1 keyword in title, first 100 words and at least one H2 · SEO-2 title ≤ 60 chars · SEO-3 meta description 120–155 chars · SEO-4 matches the search intent in the brief · SEO-5 internal links from the style guide, external links to sources |
| FLOW | Workflow | FLOW-1 a stage starts only after the previous gate's PASS is on disk · FLOW-2 no draft unless `Approved-by:` in the outline has a non-empty value · FLOW-3 two BLOCKs → human · FLOW-4 gates never edit · FLOW-5 fix the artifact, never the style guide · FLOW-6 no `final` Doc is labelled publish-ready without `Signed-off-by:`, and none while a `<Can't be verified. Reason: …>` marker remains |
| PLG | This plugin | PLG-1 no client-specific knowledge enters the plugin repo |

## Mechanical enforcement (hooks)

Prefer a script or a hook over a prompt rule.

| Hook / script | When | Enforces |
|---------------|------|----------|
| `guard-stage-order` | PreToolUse on `Edit|Write|Bash` and the Drive `create_file` and `update_file` tools | FLOW-1: writing `articles/<slug>/<stage>.md` needs the previous gate's latest verdict to be a PASS on what is on disk, walking up the chain (a rebuilt upstream or a hand edit makes a verdict stale, through the sidecar). FLOW-2: `draft.md` also needs a non-empty `Approved-by:`. FLOW-3: a stage whose gate has two BLOCK verdicts is stopped. FLOW-4: verdicts are immutable, created only by Write with a valid line 1 and the next number; Bash cannot touch `gates/`; a G4 verdict is saved only against a lint record that matches `final.md`; only `prose-lint.py` writes `.prose-lint.json`. FLOW-6: a non-empty `Signed-off-by:` is written only against a current G4 PASS on the resulting content and never beside a marker (tool writes only). FLOW-6 on Doc copies: `docs.json` is append-only valid JSON that Bash cannot write, an entry is `publish_ready` only for a publish-ready final on its exact hash, no Doc is created with a `publish-ready` title unless the final qualifies and the upload is exactly its text, and no Doc is renamed onto that label (ADR-012). Path-based; needs no branch or ticket (ADR-009, ADR-010) |
| `record-verdict` | PostToolUse on `Write` | Writes the sidecar beside a saved verdict: the hash of the artifact it judged (approval lines ignored) and the upstream verdict it relied on |
| `prose-lint.py` | A script, not a hook: called by `/draft` (without `--record`) and `/edit` (without, then with `--record` last); a gate never runs it; also usable alone | STR-4 headings, STR-6 length vs the brief, FACT-1 numbers with no `[F#]` (heuristic), and for a final SEO-1/2/3, VOI-2/3 from `style.md`, and any marker left in the text (FLOW-6, loose pattern). `--record` writes `.prose-lint.json` with the finding lines. Stdlib only |
| `verify-final` | Stop | `final.md` written this session but no matching prose-lint run recorded → block once per article, quoting the command with the script's absolute path |
| `session-context` | SessionStart | At most 30 lines: where each article is and what it waits for (from `article_state()`, ADR-011); records the session start once. Silent outside a workspace |
| `article-status.py` | A script, not a hook: called by `/article` before and after every actor; also usable alone | One JSON object per article: `next` (a stage, `approve`, `sign-off`, `stopped`, `stale`, `done`, `unknown`), `reason`, `markers`. Same rules as the guard (FLOW-1 to FLOW-3, stale, FLOW-6), read-only. Stdlib only (ADR-011) |
| `doc-copy.py` | A script, not a hook: called by `/publish` before every upload; also usable alone | One JSON object: the Markdown to upload (fact IDs stripped), the artifact's hash, the next revision, the title with its label, `publish_ready` (done and no marker), and whether an identical copy already exists. Read-only. Stdlib only (ADR-012) |

## Google Docs copies

What the claude.ai Google Drive connector can do (spike, 2026-11-14; ADR-012):

- The tools exist as `mcp__claude_ai_Google_Drive__*` only in an **interactive** session after a `/mcp` sign-in; a headless
  `claude -p` session has none.
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
| FT-3 | Research sources | Review sites and one vendor pricing page returned HTTP 403 to WebFetch. Research took about two minutes, tried no fallback (search results, another copy of the page, asking the human for an export) and moved the questions to Open gaps. Its "verbatim" quotes come through WebFetch's summary of the page | A blocked source gets a fallback or a request to the human before it becomes a gap; quotes are checked as verbatim | FACT-2, FACT-3 | open |
| FT-4 | `prose-lint.py` FACT-1 | 36 of 69 recorded lint lines were noise: numbers inside marker reasons ("HTTP 403"), numbered screenshot labels, the method date ("Data checked in <month year>"), and fact lists written `[F5, F14]` (the pattern accepts only `[F5][F14]`). Actors called the rest "false positives" and filtered the lint with `grep -v`; G4 discarded them by hand | Skip marker text and labels, accept a comma list of IDs, so a FACT-1 line is worth reading | FACT-1 | open |
| FT-5 | Reviewer comments → stages | Only the edit stage reads `comments/`. A reviewer's comments on a research, outline or draft Doc, synced with `/sync <stage>`, changed nothing: the draft stage refused ("already passed its gate") and the comments landed one stage later in `final.md`; research and outline comments had no reader at all until the human asked by hand | Sync a stage's comments, then that same stage reruns with them as input: backup, rebuilt artifact, gate `r<k+1>`, Doc `r2`; downstream verdicts go stale (ADR-009). A new flow: needs an ADR | FLOW-1, ADR-007, ADR-012 | open |
| FT-6 | Doc copy of the outline | The copy contains the `Approved-by:` line and its comment. The human approved in the Doc; the local line stayed empty. Sync noticed the mismatch and said so | The Doc copy leaves out the approval and sign-off lines, or replaces them with one line saying where to approve | FLOW-2, ADR-012 | open |
| FT-7 | Draft length | The lint flagged 3,493 words against a 3,500 to 4,000 range, and the actor padded prose to chase the count. STR-6 says "within the brief's target ±10%", but `length_bounds` applies the 10% only to a single number, not to a range; the actor then told the user it was within tolerance | The lint and STR-6 agree on one rule for a range, and an actor does not pad to clear a flag | STR-6 | open |
| FT-8 | Brief from a PDF | The brief stage says to save the input unchanged as `brief.source.md`; a PDF has no unchanged text form. The actor ran `pdftotext` through Bash, outside its allowed tools, and it worked only because the tool was installed | Say how a PDF brief is read and saved | — | open |
| FT-9 | Slug | The user gave a capitalised publisher name as the slug. It was accepted, and became the `slug:` in the final's front matter, so the article's URL slug was the folder name | Validate the folder slug as kebab-case; keep the SEO slug a separate value from the folder name | — | open |
| FT-10 | Outline markers | Research held 6 markers; the outline turned its open gaps into 29 | Decide whether one gap may fan out into many markers, or one marker per gap | ADR-008 | open |
| FT-11 | Command names | The user ran `/writer-plugin:setup-workspace` and `/writer-plugin:sync-comments`, the folder names, while the skills tell users to rerun `writer-plugin:setup` and `writer-plugin:sync` (frontmatter `name:`). The Skill tool did resolve `writer-plugin:brief` to `intake-brief`. Not yet checked against the docs which name the slash menu shows | One name per command that the menu, the skill text and `COMMANDS` agree on | — | open |
| FT-12 | Sync without a slug | `/sync research` with no slug: the actor asked with a one-option question, the tool rejected it, and the actor guessed the slug, against its own "never guess" line | With one article in the workspace, take it; otherwise offer the folders as options | — | open |
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
| 6 | `/article` orchestrator with the two human checkpoints (ADR-011) | built · ran end to end on a scratch article from brief to sign-off, with both checkpoints; one real brief run from brief to G4 with the outline checkpoint, 14 findings (see Field-test findings) |
| 7 | `/publish`, `/sync` (resolve open questions 1–2), `/setup`, evals on the test briefs | 7a built · `/setup` ran headless in a scratch workspace (constitution written, rerun left it unchanged, refused in the plugin repo); the `.claude/` write needs an interactive approval. 7b built · open questions 1–2 resolved by a Drive spike (ADR-012); the guard's FLOW-6 rules ran on real payloads; the Drive tools exist only in interactive sessions, and `/publish` and `/sync` ran live in one (an outline copy, a publish-ready final, a skip, a comment sync); headless, both took the no-connection path. 7c built · 16 eval cases (ADR-013): a PASS and a seeded BLOCK per gate, G0 per brief and the brief stage per brief; one case run ($0.05, score 1.00), the full suite not yet run |
