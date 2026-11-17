# FT-11, FT-12 — one name per command; sync without a slug

No tracker; both are rows of the Field-test findings table in `docs/DESIGN.md`.

## Problem
- **FT-11.** Four skills have a folder name that differs from their command (`intake-brief`→`brief`, `edit-final`→`edit`,
  `setup-workspace`→`setup`, `sync-comments`→`sync`). A user ran `/writer-plugin:setup-workspace`, the folder name, while the skill text
  says `writer-plugin:setup`. The Claude Code docs (`/<plugin>:<directory>`; frontmatter `name` replaces the last segment) say the menu
  shows the `name:` form; whether the folder form also resolves is not documented, and one run showed it does. Two names for one
  command is the defect, whichever resolves.
- **FT-12.** `/sync research` with no slug: the skill says "ask the user", the actor asked with a one-option `AskUserQuestion`
  (the tool needs 2 to 4 options and rejected it), then guessed the slug, against the skill's own "never guess" line.

## Goal / business value
BUSINESS_MODEL goal 3 (polish), with a goal-1 edge: a guessed slug makes `/sync` read and write the wrong article's comments and approval.

## Scope
- in: rename the four skill folders to their command; make `tests/test_structure.py`, `tests/test_skills.py`, the glossary and DESIGN agree;
  an ADR for the rule "folder name = command". `sync` and `publish` resolve a missing slug: one article is taken, 2 to 4 are offered,
  more than 4 are listed in plain text.
- **out (explicit):** the `article` skill's slug rule (its own, tested at `tests/test_skills.py:689`); any change to `bin/` scripts or hooks;
  FT-13 and FT-14; editing old `docs/features/*/` plans and ADR-010 (history); migrating users' installed copies.

## Acceptance criteria
- [x] AC1 `skills/` holds `brief`, `edit`, `setup`, `sync` and none of the four old folders; every skill's `name:` equals its folder name.
- [x] AC2 `tests/test_structure.py` fails if a skill folder differs from its frontmatter `name:`.
- [x] AC3 No file outside history (`docs/features/*/`, ADR-010, CHANGELOG), `ADR-018` and the FT-11 row of `docs/DESIGN.md` names an old folder.
- [x] AC4 `sync` and `publish`, given no slug (or only a stage name, as in `/sync research`): exactly one folder under `articles/` is taken and named in the report; 2 to 4 are offered through `AskUserQuestion`; more than 4 are listed and the user types one; none stops with a one-line message. Never "newest folder".
- [x] AC5 `claude plugin validate ./` passes with only the known warning; the full pytest suite passes.
- [x] AC6 (one folder: taken; two folders: listed headless, the interactive question not seen) Run: `/writer-plugin:sync` with no slug behaves as AC4 in a scratch workspace with one folder, and with two.

## Edge cases
| Case | Expected behaviour | Decided by |
|------|--------------------|-----------|
| `articles/` has a non-article folder (no `brief.md`) | not counted as an article | assumption |
| Slug given but folder missing | existing behaviour kept (the skills already stop) | unchanged |
| Old command typed by a user with the plugin not yet updated | not handled; the CHANGELOG says the folders were renamed | out of scope |

## Open questions
| # | Question | My assumed answer | Needs a human? |
|---|----------|-------------------|----------------|
| 1 | Rename folders, or only make the text consistent? | Rename: the docs give `/<plugin>:<directory>` as the form, so equal names are right under either reading | yes, it is the one structural choice |
| 2 | Fix `publish` too, which has the same line? | Yes, same defect, same two-line change | no |
| 3 | Does the old folder form still resolve after the rename? | No and not needed; not verified, listed under "Not verified" | no |
