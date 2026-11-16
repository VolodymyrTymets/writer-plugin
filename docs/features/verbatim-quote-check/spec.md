# verbatim-quote-check — spec

No tracker, so the slug stands in for a ticket ID. Follow-up to field-test finding FT-3 (`docs/DESIGN.md`).

## Problem
G1 (FACT-3) judges "the quote is verbatim on the page" through WebFetch, which returns a processed summary, not the page's
raw text. A paraphrase and a real quote can look the same to it. The research stage has the same blind spot when it writes
the quote. FACT-3 therefore rests on a model's reading of a summary.

## Goal / business value
BUSINESS_MODEL goal 1, correct gates: a gate that passes an altered quote defeats the plugin. A deterministic string check
against the raw page text replaces the model's judgement wherever the page is readable.

## Scope
- in: `bin/quote-check.py` (stdlib; fetches each fact-bank source and looks for the quote in the page's text); `--record`
  writes `articles/<slug>/.quote-check.json`; G1 reads the record and does not re-judge a quote the script found; a guard
  rule ties a G1 verdict to a record that matches `research.md`; the research stage runs the script last.
- **out (explicit):**
  - A shell in any gate. ADR-010 decision 3 rejected it (FLOW-4); the gate reads a record, as G4 reads `.prose-lint.json`.
  - G4 quote checking (the bank is judged at G1; G4 re-opens sources for FACT-5 as today).
  - Fetching through a browser, a header that pretends to be one, or any way round a block: a blocked page stays blocked.
  - Checking that the claim matches the quote (FACT-5 stays a gate judgement).

## Acceptance criteria
- [x] AC1 Given a fact row whose quote is on the page, when the script runs, then its status is `found`.
- [x] AC2 Given a quote with a word changed, then `not-found`; given the same text with different whitespace, curly quotes,
  entities or HTML tags between words, then `found`.
- [x] AC3 Given a 403, a timeout or a non-HTML body, then `unreachable`; given a page with under 200 words of visible text
  (a script-rendered shell), then `unreadable`. Neither is a verdict on the quote.
- [x] AC4 Given `--record`, then `.quote-check.json` holds the `research.md` hash and one line per row; the script alone writes it.
- [x] AC5 Given a G1 verdict saved with no record, or one whose hash is not `research.md`'s, then the guard blocks it (FLOW-4). One exception: the BLOCK verdict for `Artifact: none` (no `research.md` exists), which needs no record.
- [x] AC6 Given a `not-found` row, then G1 blocks it as FACT-3 without a model judgement; given `unreachable` or `unreadable`,
  then G1 judges that row as it does today, through the page.
- [x] AC7 No gate gains Bash; `fact-gate` tools are unchanged.

## Edge cases
| Case | Expected behaviour | Decided by |
|------|--------------------|------------|
| Quote with `...` or `…` inside | each segment must be found, in order | assumption A3 |
| `n/a (live page)` row | checked like any row | none needed |
| Same URL on several rows | fetched once per run | none needed |
| Site blocks non-browser clients | `unreachable`; gate falls back to today's behaviour | non-goal: no evasion |

## Open questions
| # | Question | My assumed answer | Needs a human? |
|---|----------|-------------------|----------------|
| 1 | Gate reads a record, or gets Bash? | Record (ADR-010 is settled) | no |
| 2 | Does `not-found` block alone? | Yes when the page has 200+ visible words; below that it is `unreadable` | yes: the human decides after R1 reports its counts |
