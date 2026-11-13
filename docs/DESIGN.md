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

`/article <slug>` runs the whole chain (the counterpart of rln-agent's feature orchestrator). Each stage also works on its own.

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
  final.md                      # + title, meta description, slug
  gates/G<n>-<stage>.r<k>.md    # every verdict, saved by the caller (gates cannot write)
  docs.json                     # Google Doc id + URL per artifact revision
  comments/<stage>.r<k>.md      # comments pulled back from the Google Doc by /sync
```

## Actors

Each actor reads its inputs from disk, writes exactly one artifact, publishes its Google Doc copy (from Phase 7), then invokes its
gate. An actor never edits an earlier stage's artifact; if it finds a problem upstream it stops and says so.

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
  `gate` (Read, Grep, Glob, the prose-lint script) and `fact-gate` (the same plus WebFetch / WebSearch, for G1 and the
  fact part of G4, which must open the sources).
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
| FACT | Facts | FACT-1 every statistic, date, named claim and quote cites a fact ID · FACT-2 every fact has a URL that resolves, publisher, published and accessed dates (a first-party vendor page with no date may say `n/a (live page)`) · FACT-3 quotes verbatim and attributed · FACT-4 statistics older than the style guide's limit are flagged; a live-page fact is aged by its accessed date and later stated as "checked <month year>" · FACT-5 no claim stronger than its source · FACT-6 every brief question is answered by a fact or listed under Open gaps |
| STR | Structure | STR-1 the promise is stated in the first 100 words · STR-2 every section traces to the brief's goal · STR-3 section budgets sum to the target ±10% · STR-4 one H1, no skipped heading levels · STR-5 the close delivers the CTA |
| VOI | Voice | VOI-1 voice per style guide · VOI-2 banned phrases · VOI-3 AI tells · VOI-4 reading-level target · VOI-5 no filler or stacked hedges |
| SEO | Search | SEO-1 keyword in title, first 100 words and at least one H2 · SEO-2 title ≤ 60 chars · SEO-3 meta description 120–155 chars · SEO-4 matches the search intent in the brief · SEO-5 internal links from the style guide, external links to sources |
| FLOW | Workflow | FLOW-1 a stage starts only after the previous gate's PASS is on disk · FLOW-2 no draft unless `Approved-by:` in the outline has a non-empty value · FLOW-3 two BLOCKs → human · FLOW-4 gates never edit · FLOW-5 fix the artifact, never the style guide · FLOW-6 no `final` Doc is labelled publish-ready without `Signed-off-by:`, and none while a `<Can't be verified. Reason: …>` marker remains |
| PLG | This plugin | PLG-1 no client-specific knowledge enters the plugin repo |

## Mechanical enforcement (hooks)

Prefer a script or a hook over a prompt rule.

| Hook / script | When | Enforces |
|---------------|------|----------|
| `guard-stage-order` | PreToolUse on `Edit|Write|MultiEdit|Bash|mcp__.*` | Writing `articles/<slug>/<stage>.md` needs the previous gate's latest verdict to be PASS (FLOW-1); `draft.md` also needs a non-empty `Approved-by:` value in `outline.md` (FLOW-2). Path-based, so it needs no branch or ticket. Open questions 5 and 6 add a staleness check |
| `prose-lint.py` | Called by `/edit` and the G4 gate; also usable alone | Word count vs brief, banned phrases and AI tells from `style.md`, numbers with no `[F#]`, heading levels, title and meta lengths, keyword placement. Stdlib only |
| `verify-final` | Stop | `final.md` changed but no prose-lint run recorded → block once, quoting the command |
| `session-context` | SessionStart | Lists articles in flight and the stage each is at |

## Google Docs copies

What the connected Google Drive tools can do today (checked 2026-11-12):

- `create_file` with `textContent` uploads text and **converts it to a Google Doc** by default.
- `update_file` changes **metadata only**, never content. So a revision is a **new Doc** (`<slug> · draft · r2`),
  recorded in `docs.json`; the previous revision stays as the record of what reviewers commented on.
- `read_file_content(includeComments: true)` returns the text with comments inlined → `/sync` writes them to
  `comments/<stage>.r<k>.md`, which the next actor reads as input.
- Replying to or resolving comments is not available in the connector right now; `/sync` only reads.

Publishing is an **adapter step**, not a dependency: `/publish` looks for a Drive create tool; if none is connected it
says so once and the workflow continues — the local files are canonical (D1). Fact IDs are stripped from the Doc copy.

## Agents

| Agent | Tools | Used by |
|-------|-------|---------|
| `gate` | Read, Grep, Glob, prose-lint | G0, G2, G3, G4 (non-fact part) |
| `fact-gate` | Read, Grep, Glob, WebFetch, WebSearch | G1, G4 fact check |

## Open questions

1. **Markdown fidelity in the Doc copy.** Does an upload with `text/markdown` become headings and lists, or flat text?
   If flat, convert locally to `.docx` and upload that with conversion. Spike in Phase 7.
2. **Drive tools inside Claude Code.** The claude.ai connectors may not be present in every Claude Code session; the
   adapter design above tolerates that, but it decides whether `/publish` is useful out of the box.
3. **G4 in parallel.** A forked gate probably cannot spawn subagents, so the parallel fact / voice / SEO checks may
   have to be fanned out by `/article`, with G4 merging their verdicts. Decide in Phase 5.
4. **Keyword data.** There is no SERP or volume tool; the brief supplies the keyword and `/research` reads the current
   top results via WebSearch.
5. **A human's edit before approval.** The plugin cannot record a gate rerun for a hand edit. Phase 4 decides how it is
   re-gated and recorded, and how the hook tells it from the approval edit (ADR-007).
6. **Stale downstream verdicts.** Rebuilding an artifact leaves later verdicts covering the old input. Phase 4's hook
   should require a downstream verdict to be newer than the upstream verdict it relied on (ADR-007).

## Build plan

| Phase | Scope | Status |
|-------|-------|--------|
| 0 | Decisions D1–D4; 2–3 real briefs to test with | decisions done · **briefs needed** |
| 1 | Repo skeleton: manifest, marketplace, `CLAUDE.md`, README, CONTRIBUTING, this design, structure test | done |
| 2 | `rules/core/CLAUDE.template.md` (rule IDs above), `templates/`: brief, research dossier, outline, style guide | done |
| 3 | **Vertical slice:** `/brief`, `/research`, `/outline`, `/check-brief`, `/check-research`, `/check-outline`, agents `gate` and `fact-gate`. Run on one real brief before going further | built · brief and research stages run on one real brief (see PR); outline stage not yet run on it |
| 4 | `guard-stage-order`, `prose-lint.py`, `verify-final`, `session-context` + hook tests. `prose-lint` flags any marker left in `final.md`, with the loose pattern `<Can.t be verified` (ADR-008) | |
| 5 | `/draft`, `/edit`, `/check-draft`, `/check-final` (resolve open question 3). They carry markers through and refuse sign-off while one remains (FLOW-6, ADR-008) | |
| 6 | `/article` orchestrator with the two human checkpoints | |
| 7 | `/publish`, `/sync` (resolve open questions 1–2), `/setup`, evals on the test briefs | |
