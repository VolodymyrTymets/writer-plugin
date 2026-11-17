# FT-8-10 — brief from a PDF, slug validation, one marker per gap — spec

No tracker, so `FT-8-10` stands in for a ticket ID. Source: Field-test findings FT-8, FT-9, FT-10 in `docs/DESIGN.md`.

## Problem
- **FT-8.** The brief stage says to save the input unchanged as `brief.source.md`. A PDF has no unchanged text form. The actor ran
  `pdftotext` through Bash, outside its allowed tools (`Read, Write, Edit, Glob, Grep, Skill, AskUserQuestion`); it worked only because the tool was installed.
- **FT-9.** A capitalised publisher name was accepted as the folder slug and became the final's front-matter `slug:`, so the
  article's URL slug was the folder name. Nothing checks the folder slug, and nothing separates it from the SEO slug.
- **FT-10.** Research held 6 markers, the outline turned its open gaps into 29. The outline skill puts a marker in every cell whose
  claim lacks a fact, so one gap fans out into many markers and sign-off needs many manual fills of one missing fact.

## Scope
1. **FT-8:** the brief stage reads a PDF with the Read tool (`pages` for long files) and saves the text it returned as
   `brief.source.md` under a fixed first line naming the origin file; no shell.
2. **FT-9:** (a) the brief stage settles a kebab-case folder slug (normalises a given one and says so); (b) the final's `slug:` is a
   separate SEO slug (kebab-case, from the title or keyword), never copied from the folder; (c) `prose-lint.py` checks it (new rule SEO-6).
3. **FT-10:** one open gap yields at most one marker in the outline: in the single row that would carry the claim. Other rows that
   depend on it drop that point. G2 blocks an outline with more markers than research has open-gap markers.

## Acceptance criteria
- [ ] `intake-brief` allows no Bash; says how a `.pdf` is read (Read, `pages` in chunks of at most 20), what is saved, and what to do when the PDF has no text layer (stop and ask for text; never OCR through a shell).
- [ ] The brief skill's slug step: lowercase kebab-case, `[a-z0-9]+(-[a-z0-9]+)*`; a user-given slug that is not is normalised and the change named in the report; an existing folder is never renamed.
- [ ] `edit-final` writes `slug:` as the SEO slug, a value independent of the folder name.
- [ ] `prose-lint.py` reports a front-matter `slug:` that is not kebab-case as `SEO-6`, and records it like any finding; a final with a good slug adds no line.
- [ ] `SEO-6` exists in `rules/core/CLAUDE.template.md`, `docs/DESIGN.md` rule table and the `check-final` checklist.
- [ ] `outline` skill: marker per gap, in one row; `check-outline` checklist blocks (FACT-1) when exact-form markers outside "Open questions for the human" exceed the Open-gaps markers in `research.md`.
- [ ] Tests for each; `.venv/bin/python -m pytest` and `claude plugin validate ./` pass; each change executed on a sample (B1).
- [ ] FT-8, FT-9, FT-10 ticked in `DESIGN.md`; CHANGELOG, ADR written.

## Edge cases
- PDF over 20 pages; scanned PDF; PDF input replacing an earlier `brief.source.md` (the `.prev` rule still applies to the extracted text).
- Slug with spaces or capitals already in use by an existing article: status script and guard keep working (they accept any folder name).
- A gap that really needs two distinct facts: research is unchanged here, so G2 may block it; accepted, it costs one FLOW-3 strike.
- Final written before this change has `slug:` equal to a capitalised folder: lint reports SEO-6 on the next run; no migration.

## Out of scope
- Rejecting non-kebab folders in the guard or status script (existing workspaces use spaces on purpose, `bin/lib/writer.py:384`).
- Converting a PDF by any external tool, OCR, DOCX or Google Doc import changes.
- Changing the research stage's marker policy, ADR-008's marker form, or the FLOW-6 sign-off rule.
- Redirects or a URL-slug uniqueness check against a CMS.

## Open questions (assumed answers)
1. New rule ID SEO-6 for the slug? **Assumed yes**: a mechanical check needs a citable ID.
2. Is the G2 count check blocking? **Assumed blocking under FACT-1**, because it is a count, not a style call; two BLOCKs hand it to a human.
3. Does Read handle PDFs inside a plugin skill with `allowed-tools: Read`? **Assumed yes**; R1 verifies by running it on a sample PDF, else stop (D4).
