# ADR-014 — G1 blocks a dossier that answers fewer than half of the brief's questions

- **Date:** 2026-11-16
- **Status:** accepted
- **Deciders:** Volodymyr Tymets
- **Ticket:** none (field-test finding FT-2)

## Context
FACT-6 let a brief question sit under Open gaps with no limit. A real run passed G1 with `Coverage: 1 answered, 9 open (of 10)`;
the outline then carried 29 unverified markers, the draft 30 and the final 31, and sign-off was out of reach (FLOW-6).

## Decision
G1 adds one blocking FACT-6 finding when `answered x 2 < m` (`Coverage:` numbers, counted as the checklist says). At or over
the floor, open questions still pass under Open gaps (ADR-008). The research stage is told the floor and tries another source before
it opens a gap. The floor is fixed in the checklist, not configurable.
- A BLOCK goes back to research; two BLOCKs stop the run and hand it to a human (FLOW-3, ADR-004). That is the stop for a human;
  no new state, line or hook is added.
- `Coverage:` stays for people; no parser reads it.

## Rejected alternatives
| Alternative | Why not |
|-------------|---------|
| PASS, then stop in `article-status.py` for a human decision | A new `next` state, a human line and a guard rule, for the same outcome FLOW-3 already gives |
| A floor set in `style.md` | A new style key before one real client needs a different value; add it when one does |
