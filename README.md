# writer-plugin

A Claude Code plugin that takes an **article brief** to a **publish-ready English blog post** through a chain of
actors and gates. Each actor writes one artifact (brief, research with a fact bank, outline, draft, final); each gate
judges one artifact in a fresh, read-only context and returns PASS or BLOCK with rule IDs. You approve the outline
before any drafting starts and sign off the final. Every artifact also gets a Google Doc copy for review and comments.

> **Status: Phase 7 of 7 in progress — all five stages, their gates, the orchestrator, workspace setup, Doc copies and comment
> sync are built** (brief, research, outline, draft, edit, `/article`, `/setup`, `/publish`, `/sync`). Evals are planned. The first three stages ran on a real brief; draft, edit and the
> orchestrator have run only on scratch articles. Design and
> build plan: [docs/DESIGN.md](docs/DESIGN.md).

## The flow

```
brief ──G0──▶ research ──G1──▶ outline ──G2──▶ you approve ──▶ draft ──G3──▶ final ──G4──▶ you sign off
```

## Commands

Built: every command below.

| Command | What it does or will do |
|---------|-------------------------|
| `/article <slug>` | The whole chain, stopping for your outline approval and final sign-off |
| `/setup` | Once per content workspace: writes `CLAUDE.md` and `.claude/rules/style.md` (voice, audience, banned phrases, links). Never overwrites either; Claude Code asks you to approve the write under `.claude/` |
| `/brief` | Normalise the brief into `brief.md`, asking only the gaps that change the article |
| `/research` | Sources, competitor coverage and the fact bank (`F1…Fn`, each with URL and dates) |
| `/outline` | Thesis, headings, per-section facts and word budgets, keyword map, CTA |
| `/draft` | The article, section by section, every claim tagged with its fact ID |
| `/edit` | Revise into `final.md` from the gate verdict and reviewer comments; title, meta, slug |
| `/check-brief`, `/check-research`, `/check-outline`, `/check-draft`, `/check-final` | Gates G0–G4 |
| `/publish` | Copy an artifact to a new Google Doc revision in the Drive folder `<your workspace folder>/<slug>/` (each stage does this after its gate passes). After you sign off, run `/publish <slug> final` for the copy labelled publish-ready |
| `/sync` | Pull a Doc's comments back, quoted verbatim, as `comments/<stage>.r<k>.md`; the edit stage reads them |

## Install (once the repository is on GitHub)

```bash
claude plugin marketplace add VolodymyrTymets/writer-plugin
claude plugin install writer-plugin@writer
```

## Requirements

- Claude Code 2.1.x
- `python3` 3.9+ on `PATH` for the hooks (standard library only). The hooks block a stage that starts out of order, any edit of a
  saved verdict, a final that changed without a prose-lint run, and a sign-off while a marker remains or the final gate has not passed on the exact text; see [docs/decisions/ADR-009](docs/decisions/ADR-009-mechanical-stage-order.md)
- Optional: the claude.ai Google Drive connector for the Doc copies and comment sync. Sign in with `/mcp` in an interactive session; a
  headless `claude -p` run never has it. Without it the workflow still runs on the local files.
