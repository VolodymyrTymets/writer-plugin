# ADR-015 — A script checks that each fact-bank quote is on its source page; G1 reads the record

- **Date:** 2026-11-16
- **Status:** accepted (decisions 1 to 3; the record and guard rules are added with R2 to R4)
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (`docs/features/verbatim-quote-check/plan.md`, field-test finding FT-3)

## Context
G1 judges FACT-3 ("the quote is verbatim on the page") through WebFetch, which returns a processed summary, so a paraphrase and a
real quote can look alike. ADR-010 decision 3 settled that no gate gets a shell, so a gate cannot run a checking script itself.

## Decision
1. **`bin/quote-check.py` fetches each fact-bank URL once and looks for the quote in the page's visible text.** Statuses: `found`,
   `not-found` (the page was read and has 200 or more words of text), `unreachable` (HTTP error, timeout, not a web page, not
   http(s), time budget used up) and `unreadable` (under 200 words, a page that builds itself in the browser). 10 s per fetch, 90 s
   in all. It sends a plain client name and never pretends to be a browser; a blocked page stays `unreachable`.
2. **What counts as the same text:** typesetting only. Markup, whitespace, entities, curly quotes, dashes and soft hyphens do not
   count as differences; case and wording do. HTML inline tags join text and block tags separate it; markdown emphasis, code ticks,
   link syntax and line-start markers are not words. A quote with `...`, `[...]` or `…` matches as segments in order.
3. **Closing punctuation (decided by the human, 2026-11-16, option A).** A quote cut mid-sentence may end in `.`, `,`, `;` or `:` that the
   page does not have there; those marks are ignored at the end of the last segment only. Marks inside the quote still count. On the
   field-test dossier this turned 4 of 4 `not-found` rows into `found` and left every real difference blocking; the cost is that a
   quote cut mid-claim passes this check, which FACT-5 still judges.
4. **The gate reads a record, it does not run the script** (ADR-010.3 stands): the research stage runs the script with `--record`, the
   guard ties a G1 verdict to a record that matches `research.md`, and G1 reads it. Added with R2 and R3.

## Rejected alternatives
| Alternative | Why not |
|-------------|---------|
| A scoped Bash tool on `fact-gate` | A shell in a gate; settled against in ADR-010 (FLOW-4) |
| Literal match, closing marks included | Every added full stop would block FACT-3: noise in a gate (goal 1) |
| A browser user agent, or a headless browser | Gets round blocks the site chose to put up; the plugin does not |

## Consequences
- A `found` row needs no quote comparison by the gate; `unreachable` and `unreadable` rows are judged as before.
- On the field-test dossier 21 of 25 rows were `found` and 4 `unreachable` (3 TLS rejections by the local system Python, 1 HTTP 404).
