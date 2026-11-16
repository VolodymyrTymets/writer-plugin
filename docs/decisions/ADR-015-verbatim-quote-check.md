# ADR-015 — A script checks that each fact-bank quote is on its source page; G1 reads the record

- **Date:** 2026-11-16
- **Status:** accepted
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
4. **The gate reads a record, it does not run the script** (ADR-010.3 stands). The research stage runs the script without `--record`,
   fixes what it flags, then with `--record` as the last action on `research.md`. `.quote-check.json` holds `file`, the `sha256` of
   `research.md` (approval lines ignored), `rows` (fact ID to status), the printed `lines` and `at`.
5. **Two guard rules, mirrors of ADR-010.4:** a G1 verdict, PASS or BLOCK, is saved only against a record whose hash equals
   `research.md`; the one exception is G1's BLOCK for `Artifact: none` while `research.md` does not exist. No tool writes
   `.quote-check.json`; only the script does (a hook sees tool calls, not the script's own write: the same known gap as `prose-lint.py`).
6. **What G1 does with a status:** `found` settles FACT-3's verbatim question (FACT-5 and attribution are still judged); `not-found`
   is a blocking FACT-3 finding that the gate may not overrule from a fetch summary; `unreachable` and `unreadable` settle nothing and
   the row is judged through the page as before; a missing record is a blocking finding.

## Rejected alternatives
| Alternative | Why not |
|-------------|---------|
| A scoped Bash tool on `fact-gate` | A shell in a gate; settled against in ADR-010 (FLOW-4) |
| Literal match, closing marks included | Every added full stop would block FACT-3: noise in a gate (goal 1) |
| A browser user agent, or a headless browser | Gets round blocks the site chose to put up; the plugin does not |

## Consequences
- A `found` row needs no quote comparison by the gate; `unreachable` and `unreadable` rows are judged as before.
- On the field-test dossier 21 of 25 rows were `found` and 4 `unreachable` (3 TLS rejections by the local system Python, 1 HTTP 404).
- Known gaps: a shell write by the script is invisible to the guard; an `unreachable` row is no better checked than before; a page that
  differs for a script and for a browser can give a false `not-found` (the research stage then re-reads the page or drops the row).
- `evals/` fixtures carry a record written by the script, with a test that pins its hash to the research beside it.
