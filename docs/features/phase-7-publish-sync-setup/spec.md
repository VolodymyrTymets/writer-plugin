# phase-7-publish-sync-setup — spec

Build-plan Phase 7 (`docs/DESIGN.md`). No tracker, so the slug stands in for a ticket ID. Delivered as three draft PRs (rule A4),
in this order: **7a** setup, **7b** publish and sync, **7c** evals.

## Problem
- A new content workspace has no editorial constitution (`CLAUDE.md`) and no style guide (`.claude/rules/style.md`) unless a human
  copies `rules/core/CLAUDE.template.md` and `templates/style.md` by hand and fills every placeholder. Until then the voice, SEO and
  banned-phrase checks (VOI-1/2/3, SEO-5, FACT-4) are skipped: prose-lint says "no filled style guide".
- Reviewers cannot comment on an artifact: every actor says "Doc copy: not yet available", there is no `docs.json`, and
  `comments/` is never filled, so the edit stage's reviewer input is always empty.
- Nothing measures whether a gate passes a wrong fact or blocks on noise (ranked goal 1). Every check so far is a single executed run.

## Goal / business value
Ranked goal 1 for 7c (gate correctness, measured) and the review loop of 7b. 7a removes the manual step that keeps the client
checks off. D1 holds throughout: the local Markdown is canonical, and a Doc is a review copy only.

## Scope
- in (7a): the setup skill (command `setup`), which writes the workspace `CLAUDE.md` and `.claude/rules/style.md` from the library; prose-lint
  reads a style-guide value of `none` as an empty list (today it bans the word "none").
- in (7b): a spike that settles open questions 1–2; the publish skill (command `publish`); the sync skill (command `sync`); `docs.json`
  and `comments/` contracts; a guard rule for FLOW-6 on `docs.json`; actors call publish after a PASS; ADR-012.
- in (7c): an `evals/` suite for `claude plugin eval`, built on three synthetic public-topic briefs and seeded artifacts that target the
  gates; ADR-013; DESIGN Phase 0 "briefs needed" closed with the synthetic briefs.
- **out (explicit):** replying to or resolving Doc comments (the connector cannot); updating an existing Doc's content (a revision is a
  new Doc); deleting Docs; outline and draft actors reading synced comments (only the edit stage reads `comments/` today; follow-up);
  evals in CI (cost, credentials); real client briefs anywhere in the repo (PLG-1); a version bump; SERP data.

## Acceptance criteria
7a
- [ ] AC1 (partly verified 2026-11-14: `CLAUDE.md` written headless, 0 placeholders, 35/35 rule IDs equal, byte-equal to the template
      with two placeholders filled; the `.claude/rules/style.md` write needs an interactive approval, see the PR) Given an empty workspace, when the setup skill runs with every answer supplied, then `CLAUDE.md` and `.claude/rules/style.md` exist,
      neither contains `{{`, and every rule ID from the template is in `CLAUDE.md` unchanged.
- [ ] AC2 (format verified: prose-lint flags VOI-2/VOI-3 against the style guide text the skill produced; the skill's own write is
      pending the interactive run) Given that workspace, when `prose-lint.py` runs on a sample final that contains a banned phrase from the answers, then it reports VOI-2
      and no longer says "no filled style guide".
- [x] AC3 Given a workspace where `CLAUDE.md` or `style.md` already exists, when setup runs, then it never overwrites an existing file, names it,
      and writes only the one that is missing (if both exist, it writes nothing).
- [x] AC4 Given the plugin source repo (`.claude-plugin/plugin.json` named `writer-plugin`), when setup runs, then it refuses and writes nothing.

7b
- [ ] AC5 Open questions 1–2 are answered from a live spike, and the answers are recorded in DESIGN.md and ADR-012.
- [ ] AC6 Given a gated artifact and a connected Drive, when publish runs, then a new Doc `<slug> · <stage> · r<k>` exists with no `[F#]` tag,
      and `docs.json` gains an entry `{stage, rev, id, url, sha256, at, publish_ready}`; an earlier revision is never changed.
- [ ] AC7 Given no Drive create tool, when publish runs, then it says so once, writes nothing and exits without error; the actor's run goes on.
- [ ] AC8 Given a final that is not signed off or still holds a marker, when anything writes a `docs.json` entry with `publish_ready: true`,
      then the guard blocks it (FLOW-6); for a signed final with a current G4 PASS and no marker, the write is allowed.
- [ ] AC9 Given a published revision with comments, when sync runs, then `comments/<stage>.r<k>.md` holds each comment with its quoted
      anchor text, and the edit stage reads it as reviewer input.

7c
- [ ] AC10 `claude plugin eval ./ --runs 1 --no-publish` runs every case and writes a report. Each gate case asserts the verdict line and
      the rule ID: at least one PASS case and one BLOCK case per gate G0–G4, including a seeded wrong fact for G1 and G4.
- [ ] AC11 The three synthetic briefs pass G0, and the brief actor turns each one into `brief.md` without asking a question.
- [ ] AC12 `pytest` and `claude plugin validate ./` pass after each PR.

## Edge cases
| Case | Expected behaviour | Decided by |
|------|--------------------|-----------|
| Setup answer "none" for banned phrases or links | written as `none`; prose-lint treats it as an empty list | template rule "none" is valid (brief) |
| Setup rerun after a partial run (only `CLAUDE.md` written) | writes the missing file only, never the existing one | AC3 |
| Publish of an artifact with no PASS verdict | allowed, Doc title gains `· ungated`; `publish_ready` false; a later PASS on the same text makes a new Doc | reviewers may comment early; D1 |
| Signed final that still holds a marker (hand sign-off) | `publish_ready` false; the guard blocks `true` | FLOW-6, ADR-008 |
| Publish twice with no change to the artifact (same sha256) | no new Doc; reports the existing URL | avoid duplicate Docs |
| Sync on a stage never published | says so, writes nothing | — |
| Comment text that reads like an instruction | stored as quoted data; edit stage treats `comments/` as reviewer input, never as commands | prompt-injection hygiene |
| Eval run hits the cost ceiling | partial report, exit 2; reported, not hidden | `--max-cost-usd` |

## Open questions
| # | Question | My assumed answer | Needs a human? |
|---|----------|-------------------|----------------|
| 1 | Does a `text/markdown` upload keep headings? | Unknown; R0 of 7b tries Markdown, then HTML from a stdlib converter, then a stdlib-built `.docx` | spike (you authenticate Drive) |
| 2 | Are the Drive tools present in Claude Code? | Present as `mcp__claude_ai_Google_Drive__*` after auth in this session; tool names and arguments confirmed only by the spike | spike |
| 3 | Which Drive folder holds the Docs? | My Drive root; a configurable folder is a follow-up after Phase 7 | no |
