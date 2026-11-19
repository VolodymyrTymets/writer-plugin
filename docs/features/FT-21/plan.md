# FT-21 — implementation plan

No tracker. Branch `chore/ft-21-doc-update-spike`, cut from an up-to-date `main`. One draft PR (A4). Spec: `spec.md`. This plan writes **no code**: its output is
an ADR and status lines. A build, if the ADR says GO, gets its own plan.

<!-- A human writes this line to approve. Until it is here, guard-plan-approval blocks writes to code. -->
Approved-by: Volodymyr · 2026-11-19

Pattern followed: `docs/features/comment-rerun-and-clean-copies/plan.md` R0 ("capture the connector's shapes") and its record in `docs/decisions/ADR-016-approval-in-the-doc.md`
(key names and types only, a stop rule if the measurement is impossible). The decision is an ADR in the style of ADR-012 and ADR-016, next number ADR-022. No new pattern.

## Contract changes
- none in code, hooks, data formats or boundaries.
- docs only: a new ADR; one status line in `docs/DESIGN.md`; on GO, one "Refined by" line in ADR-012.

## Requirements (ordered, each independently verifiable)

### R0 — Measure `update_doc` on a synthetic Doc (S, needs one interactive step from the human)
- files: none in the repo. A scratch note of key names and types in the session scratchpad.
- layer: connector spike, as ADR-016's R0.
- precondition: the Google Docs connector's tools are loaded (`mcp__claude_ai_Google_Docs__*`). If they are not, **stop and report** (B4); do not substitute the Drive tools or claude.ai's own docs tools.
- steps, on one synthetic Doc created with the Drive `create_file` (`text/markdown`, the eval fixture's outline text, an empty `Approved-by:` line):
  1. list the Docs connector's tools and, for `update_doc`, its input keys, modes and which key holds the Doc id (AC1).
  2. a human adds one comment on a sentence, and types a name after `Approved-by:`.
  3. call `update_doc` with a body replace, then `read_file_content(includeComments: true)` and compare: thread, anchor, typed name, text (AC2, AC4). If step 1 shows no replace mode, do the rewrite as a ranged delete plus insert and say so in the record.
  4. repeat on a fresh copy in `SUGGEST` mode; read back before and after the human accepts (AC3).
  5. if step 1 lists a revision tool (`list_file_revisions` is on the Drive connector in this session; ADR-012 and ADR-016 never recorded it), use it: is the old body recoverable (input to AC5). If it is absent, record that and the ADR says the old body cannot be recovered through the connector; no other tool is substituted.
  6. **run the hook, not the eye (AC4).** Save the raw `create_file` and each `read_file_content` `tool_response` (before the update, after the plugin's update, after the human's typed name) to the session scratchpad. Replay them through `bin/record-approval.py` in a scratch workspace outside the repo whose `articles/<slug>/` holds the fixture outline and a matching `docs.json` and title (`<slug> · outline · r1`), since the spike title is not an article title and the hook would skip it. Record per replay: whether `approvals/outline.r1.json` holds the name, null with its reason, or nothing, and the hook's stderr line. The ADR's AC4 answer cites this result; without it the answer is "not sure" (F3) and the decision is NO-GO.
- executed how: the calls above, live. Evidence in the PR: the key-name table and a yes/no per question, no content (AC7).
- risk: the Docs connector cannot be connected. Cheapest check: `/mcp` shows it signed in before any call.

### R1 — ADR-022: go or no-go (S)
- files: `docs/decisions/ADR-022-one-doc-per-artifact.md` (new)
- layer: documentation.
- content: context (ADR-012 rejection row and what changed), what was measured (R0 table), the effect on ADR-016's record per revision and on the guard, then Decision: GO or NO-GO with the reason (AC5, AC6). On GO it names the follow-up requirements (record per Doc, not per revision; guard allows `update_doc` only for the plugin's own text; what the old revision Docs become) without building them.
- test: none exists for ADR prose. `.venv/bin/python -m pytest` still passes (it reads `docs/` only in structure checks); run it to prove nothing else moved.
- executed how: pytest green; `grep -rn` of the ADR for any article or comment text from the spike returns nothing.
- risk: the measurement is partial (for example `SUGGEST` read-back unclear). Then the ADR says "not sure" (F3) and the decision is NO-GO until measured.

### R2 — Status lines (S)
- files: `docs/DESIGN.md` (FT-21 row Status), `docs/decisions/ADR-012-doc-copies.md` and `docs/decisions/ADR-016-approval-in-the-doc.md` (one "Refined by: ADR-022" line each, only on GO; ADR-016 decisions 3, 4 and 6 and its "Revisit when" are what ADR-022 changes)
- test: `.venv/bin/python -m pytest`; `claude plugin validate ./`.
- executed how: both commands, real output in the PR body.
- risk: none.

## Docs to update in this PR
- [ ] docs/features/FT-21/spec.md (acceptance criteria checked off)
- [ ] docs/DESIGN.md — FT-21 row
- [ ] docs/decisions/ADR-022 (new), ADR-012 and ADR-016 on GO
- [ ] docs/DOMAIN_GLOSSARY.md — only on GO, if the ADR names a new term
- [ ] CHANGELOG.md — Deleted section first; nothing deleted, one Added line for the ADR

## Risks
| Risk | Impact | Cheapest way to find out early |
|------|--------|-------------------------------|
| Docs connector not available | spike blocked | `/mcp` check before R0 step 1 |
| A rewrite drops comment anchors | GO would break `/sync` | R0 step 3 on a Doc with one thread |
| An in-place body breaks the approval hash check (ADR-016: one record per Doc revision) | a false approval, FLOW-2 breached | R0 step 6 replays the real payloads through `record-approval.py` |
| Spike Doc or payload text leaks into the repo | PLG-1 | record names and types only; grep before commit |

## Assumptions
- The spike Doc is synthetic and sits in My Drive root; the human decides when it is trashed (C4).
- `update_doc` exists as ADR-016 recorded it; if the connector's tool list differs, R0 records the real one.
- Size: R0 S, R1 S, R2 S. A GO build is estimated L and is not in this plan.
