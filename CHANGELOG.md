# Changelog

Format: **Deleted** first — a smaller plugin each release is the goal.

## Unreleased

### Deleted
- Nothing yet.

### Added
- Phase 2 library: editorial constitution template (`rules/core/CLAUDE.template.md`, all rule IDs) and the brief,
  research, outline and style templates under `templates/`. `tests/test_templates.py` pins their shape.
- FLOW-2 now says an outline is approved only when `Approved-by:` has a non-empty value.

## 0.0.1 — 2026-11-12 · skeleton

### Deleted
- Nothing yet.

### Added
- Design (`docs/DESIGN.md`): actor → gate flow from brief to final, five gates, two human checkpoints, rule IDs
  (BRF, FACT, STR, VOI, SEO, FLOW, PLG), hooks plan, Google Doc copies, build plan.
- Plugin manifest and marketplace (`writer`), an empty `hooks/hooks.json`, and the structure test with the command
  map. Planned commands (`/article`, `/brief`, `/research`, `/outline`, `/draft`, `/edit`, the five `/check-*` gates,
  `/publish`, `/sync`, `/setup`) are listed but not built.
