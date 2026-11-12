# ADR-005 — Stage skills read their artifact template from the plugin at run time

- **Date:** 2026-11-12
- **Status:** accepted
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (build-plan Phase 3)

## Context
`templates/` was planned as an inert library that a later setup skill copies into a workspace. The Phase 3 stage skills
need the artifact shapes now, in a workspace that has had no setup. The Claude Code docs say `${CLAUDE_PLUGIN_ROOT}` is
substituted in plugin skill content and can reference files anywhere in the plugin (checked 2026-11-12 against
skills.md and plugins/components.md).

## Decision
The brief, research and outline skills read `${CLAUDE_PLUGIN_ROOT}/templates/<stage>.md` when they run. Gates carry
their own checklists in `references/` and read a workspace `CLAUDE.md` and `.claude/rules/style.md` only if present.
`rules/core/` stays an inert library for the setup skill. No copy of a template lives in a skill, so there is no drift.

## Rejected alternatives
| Alternative | Why not |
|-------------|---------|
| Copy each template under the skill's `references/` with a drift test | Two copies of one shape; only needed if the variable did not expand |
| Wait for the setup skill to copy templates into the workspace | Blocks the vertical slice on Phase 7 |

## Consequences
- Positive: one source for each shape; the slice runs in an empty workspace (verified in `claude -p --plugin-dir`).
- Accepted cost: `templates/` is now loaded at run time, so a template change is a behaviour change for the stage skills.
- Follow-ups: when setup lands, decide whether a workspace may override a template.

## Revisit when
The variable stops expanding in skill content, or a client needs its own brief shape.
