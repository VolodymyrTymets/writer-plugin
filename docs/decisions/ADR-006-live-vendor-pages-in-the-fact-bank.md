# ADR-006 — A first-party vendor page with no date may enter the fact bank as `n/a (live page)`

- **Date:** 2026-11-12
- **Status:** accepted
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (`docs/features/g1-live-vendor-pages/plan.md`)

## Context
FACT-2 required a published date on every fact. A real brief told the writer to take prices and features from each
vendor's own live pages and not from competitor articles. Those pages usually show no date, so the research stage
dropped them and fell back on competitor articles, the very sources the brief ruled out, and the dossier had almost
nothing about the brief's main subject.

## Decision
A fact row may say `n/a (live page)` in the published column (also in the Sources table) only when all hold:
the publisher names the vendor and the claim is about that vendor; the URL is on the vendor's own domain; the page shows
no published or updated date; and the claim says "as listed on the page". Otherwise `n/a` is a blocking FACT-2 finding.
Articles, statistics from other publishers and regulator pages never qualify. FACT-4 ages such a row by its accessed
date, and any later statement of it says "checked <month year>". The gate still opens the page, checks the quote, and
confirms the page really shows no date.
- Precedence: the gate follows its own checklist. A workspace whose `CLAUDE.md` still carries the strict FACT-2 does not
  change what G1 accepts. A `research.md` with real published dates stays valid; there is nothing to migrate.
- Line 3 of a G1 verdict is `Coverage: <a> answered, <o> open (of <m>)` (see the plan). It is for people; no parser reads it
  and ADR-004's pattern for lines 1 and 2 is unchanged.

## Rejected alternatives
| Alternative | Why not |
|-------------|---------|
| Keep FACT-2 strict (every fact dated) | A pricing page has no publish date, so the writer is pushed onto competitor articles, which the brief forbids |
| Let any undated page in | A blog post or a stat with no date is exactly what FACT-4 exists to catch |
| Use the accessed date as the published date | It would hide that the page's own age is unknown |

## Consequences
- Positive: first-party prices and features can be facts, with the brief's own "checked <month and year>" requirement met.
- Accepted cost: the gate cannot verify a publish date for these rows, and a price can change after the access date.
  Freshness rests on the accessed date and on the draft saying when it was checked.
- Follow-ups: the draft stage (Phase 5) must carry "checked <month year>" for such facts.

## Revisit when
A vendor-page row is found to be wrong or stale in a published article, or the gate cannot tell a first-party domain reliably.
