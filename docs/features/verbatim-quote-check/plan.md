# verbatim-quote-check — implementation plan

No tracker, so the slug stands in for a ticket ID. Follows FT-3 (`docs/DESIGN.md`).
Branch: `feat/verbatim-quote-check`, cut from `main` **after** the FT-3 fix (`fix/research-blocked-sources`, with `ADR-014`) has merged, because R3 and R4 edit the text it adds. One draft PR (A4).

<!-- A human writes this line to approve. Until it is here, guard-plan-approval blocks writes to code. -->
Approved-by: Volodymyr - 2026-11-16

Pattern followed: `bin/prose-lint.py --record` and `.prose-lint.json` (ADR-010): a stdlib script run by the actor writes a
hash-bound record; the guard ties the gate's verdict to it; the gate only reads. Settled decision kept: no shell in a gate (ADR-010.3).

## Contract changes
- **boundary (additive):** `bin/quote-check.py [--record] [--root R] <slug>` prints one line per fact-bank row, `F<n> found|not-found|unreachable|unreadable <detail>`; exits 1 when any row is `not-found`.
- **data (new file):** `articles/<slug>/.quote-check.json` `{file, sha256, rows: {F<n>: status}, lines, at}`. Absent on existing
  articles; only a new G1 verdict needs it, so nothing to migrate.
- **guard:** two rules, mirrors of ADR-010.4(1)(2): a G1 verdict is saved only against a record whose hash equals `research.md`
  (approval lines ignored); no tool writes `.quote-check.json`.
- **skills:** `research` gains `Bash(python3 ${CLAUDE_PLUGIN_ROOT}/bin/quote-check.py *)`; G1 reads the record. `fact-gate` tools unchanged.
- generated output: none.

## Requirements (ordered, each independently verifiable)

### R1 — The script (M)
- files: `bin/quote-check.py` (new), `bin/lib/writer.py` (change: `fact_rows(text)` parses the Fact bank table; `quote_present(page_text, quote)`), `tests/test_quote_check.py` (new)
- layer: script over the shared lib, as `doc-copy.py`.
- test: local `http.server` fixtures, no outbound traffic: found; word changed; whitespace, curly quotes, entities, tags; ellipsis segments in order; 403 and timeout; a 50-word shell; non-HTML; one fetch per URL; no write without `--record`.
- executed how: run it on the field-test dossier (FT-1 to FT-3, outside this repo) and on the eval fixture; report counts per status. Only counts go in the PR body, never URLs, quotes or row text from that dossier (PLG-1).
- **stop:** report the counts and the rows near the 200-word line to the human, who decides open question 2; create `ADR-015` with that decision before R2 starts (R4 completes it). A run cannot approve its own threshold.
- time budget: 10 s per fetch and a 90 s total cap, under the Bash default; rows not reached in time are recorded `unreachable`, so a record is always written. Test: several slow local URLs still end with a record. The field-test run reports its wall time with the counts.
- risk: many real pages will be `unreachable`, which is today's behaviour and so no regression.

### R2 — Record and guard (M)
- files: `bin/quote-check.py` (`--record`), `bin/lib/writer.py` (`quote_record`), `bin/guard-stage-order.py` (two rules), `tests/test_hooks.py` (cases)
- layer: hook, beside the `.prose-lint.json` rules.
- test: G1 verdict with no record, a stale record and a matching record (block, block, allow); Write and Bash to `.quote-check.json` blocked; the G4 rules unchanged.
- executed how: feed the guard real hook payloads in a scratch workspace, as ADR-010 did.
- risk: the one exception: the BLOCK for `Artifact: none` (no `research.md`) needs no record; a test pins it.

### R3 — Skills read and run it (M)
- files: `skills/research/SKILL.md` (run it last, fix `not-found` rows, rerun after every edit), `skills/check-research/SKILL.md` and `references/checklist.md` (read the record; `not-found` is blocking FACT-3, `found` needs no quote comparison, other statuses as today; no record is a blocking finding), `tests/test_skills.py`
- test: the research front matter has the exact Bash rule; the gate text names the record and has no Bash; `fact-gate` tools unchanged.
- executed how, two runs on scratch copies of the field-test workspace:
  (a) gate path: alter one quote by hand, run `python3 bin/quote-check.py --record --root <scratch> <slug>`, then `/writer-plugin:check-research <slug>` alone: expect `BLOCK` with `[FACT-3]` on that row, taken from the record;
  (b) actor path: the scratch workspace lives outside this repo (`articles/**` is protected here, PLG-1); first move its G1 verdicts to `gates/archive/` and keep a backup of `research.md`. Then run the research stage on the unaltered copy: expect it to run the script last, write `.quote-check.json` and save a G1 verdict the guard allows.
- risk: the actor edits `research.md` after recording; the guard's hash check makes that a block, not a pass.

### R3b — Eval fixtures carry a record (S)
- files: `evals/fixtures/http-caching/articles/http-caching/.quote-check.json` (new, written by `quote-check.py --record`, not by hand), the same in `evals/g1-block-overstated-claim/seed/` for its replaced `research.md`, `tests/test_evals.py`
- test: each record's `sha256` equals `writer.text_hash` of the `research.md` beside it; the seed-change filter in `test_every_block_case_seeds_a_real_change_to_what_it_overrides` ignores `.quote-check.json`, as it ignores `.prose-lint.json`.
- executed how: `.venv/bin/python -m pytest tests/test_evals.py`, then locally `claude plugin eval` on `g1-pass` and `g1-block-overstated-claim` (ADR-013: never in CI). Without this R3 would make `g1-pass` BLOCK for a missing record.
- risk: a fixture URL is `unreachable` at record time; the record then says so and the case judges that row as today.

### R4 — Docs and decision (S)
- files: `docs/decisions/ADR-015-verbatim-quote-check.md` (created at R1's stop with the threshold; completed here with the record, the guard rules and the rejected alternatives), `docs/DESIGN.md` (mechanical table, FT-3 row, file tree), `docs/ARCHITECTURE.md` (script row, record row, `tests/test_quote_check.py` in the tests row), `docs/DOMAIN_GLOSSARY.md` (quote record), `CHANGELOG.md`, `CONTRIBUTING.md` (it lists the scripts)
- test: `tests/test_structure.py` and the glossary and design checks stay green.
- executed how: full `.venv/bin/python -m pytest` and `claude plugin validate ./` (one expected warning), after R3's front-matter change.

## Docs to update in this PR
- [x] spec.md acceptance criteria checked off
- [x] ARCHITECTURE.md, DOMAIN_GLOSSARY.md, DESIGN.md, CHANGELOG.md
- [x] ADR-015 (a new record and guard rules extend ADR-010's pattern)

## Risks
| Risk | Impact | Cheapest way to find out early |
|------|--------|--------------------------------|
| Most sources are `unreachable` or `unreadable` | The check adds little | R1's run on the field-test dossier, before R2 |
| A false `not-found` (odd markup, hyphenation) blocks a good row | Noise in a gate (goal 1) | R1's run; widen normalisation, never weaken a test (B3) |
| The record is written by an actor that then changes the file | Stale record | The guard's hash check (R2) |

## Assumptions
- A1 No gate gets Bash; the record pattern is used (ADR-010.3 is settled).
- A2 A generic client name in the User-Agent; no browser impersonation.
- A3 Quotes with an ellipsis match as ordered segments.
- A4 ADR numbering continues at 015. `ADR-014` (the coverage floor) is committed on the FT-3 branch before that PR merges, since main already cites it; it stays out of this PR. The 90 s cap sits under the 120 s Bash default.
