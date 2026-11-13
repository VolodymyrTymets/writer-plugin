# verdict-covers-artifact — implementation plan

Found by running the brief stage on a real brief: the actor fixed the gate's advisory findings in `brief.md` after the
PASS and did not rerun the gate, so the saved verdict described an earlier version. No tracker, so the slug stands in
for a ticket ID. Branch `fix/verdict-covers-artifact` off `main`.

<!-- A human writes this line to approve. Until it is here, guard-plan-approval blocks writes to code. -->
Approved-by: Volodymyr - 2026-11-13

Pattern followed: the three actor skills from PR #3 (`skills/intake-brief`, `skills/research`, `skills/outline`); all
three share the step layout and the flaw. New decision records follow ADR-006's precedent: refine by a new ADR that
refers to the earlier one, never amend in place.

## Problem
A verdict file is the record that a stage passed, and FLOW-1 trusts it. If the actor changes the artifact after the gate
ran, the verdict no longer describes what is on disk, and the next stage starts from content nobody judged.

## Rule (the whole change)
1. **After a PASS the actor never edits the artifact.** It reports the gate's advisory findings to the user and stops.
2. **If the artifact has to change, the stage runs again and the gate judges the new version.** For the brief stage the
   change arrives as a corrected input file, saved as `brief.source.md` (`skills/intake-brief/SKILL.md` Step 1, PR #3);
   research and outline rebuild from their upstream artifacts. The rebuilt artifact's verdict is saved as the next
   `r<k>`. A BLOCK from a rerun counts toward FLOW-3 like any other BLOCK.
3. **Earlier work survives a rebuild.** The brief stage's Step 1 reads the previous `brief.md` before rebuilding and carries its `<field>: answered by the user, round <n>` lines forward **verbatim**, keeping their original `round <n>`, unless the corrected input overrides the
   field (the gate cannot see the chat, so those lines are the record). The outline stage reads the existing `outline.md`
   and its `Approved-by:` value before writing, and **whatever the value is** it first copies the file to `outline.prev.<n>.md`, where `n` is 1 plus the highest `n` among existing `outline.prev.*.md` files (1 if there are none), independent of verdicts, so the name cannot collide in a run that saved no verdict or after an archive. A backup is **never replaced**, so a second rebuild cannot delete an earlier copy and a human's approved or hand-edited outline is never lost. If the value was non-empty, the report also says the approval was cleared.
4. **A rebuild stales what was built on it.** When a stage replaces an artifact and a later stage's artifact already
   exists, its report names those later artifacts as built on the replaced version, to be rerun. A rebuilt outline has an
   empty `Approved-by:` (the template ships it empty), so the outline stage says a replaced outline needs a new approval.
5. **Scope: the actor's behaviour only.** A human may still read the outline and change direction before approving
   (`docs/DESIGN.md` line 28 and the outline skill's Step 6 stay as they are). The verdict covers the artifact as gated,
   apart from the human approval line (`Approved-by:`, later `Signed-off-by:`). A human's hand edit is not re-gated by
   this plugin: that is an **open question for Phase 4** (how a human edit before approval is re-gated and recorded), listed
   in ADR-007 and the PR, not designed here (B4).
- **Known gap, not closed here:** an edit by the main agent outside the stage skill on a request such as "fix that
  advisory" is not enforced until Phase 4's hook. The cheap mitigation is one hygiene line in
  `rules/core/CLAUDE.template.md` (a request, not a mechanism): "an agent does not edit an artifact after its gate has passed, upstream ones included; the stage is rerun (the brief stage from a corrected input file the human supplies), and a needed upstream change means rerunning that upstream stage first. A human's edit is the human's call."

## Contract changes
- Behaviour of the three stage skills (text) and one line in the constitution template. No change to the verdict format, rule IDs or the checklists, and no new input file. One new backup file family, `outline.prev.<n>.md`, never overwritten (unlike `brief.source.prev.md`, which is replaced, because the brief's source is rebuilt from a supplied file the human still has).
- New `docs/decisions/ADR-007-verdict-covers-the-artifact.md`, refining ADR-004 (rules 1 to 5, the known gap, and the
  Phase 4 open questions (DESIGN items 5 and 6): re-gating a human edit before approval, and checking a downstream verdict against a changed
  upstream artifact). ADR-004 gets a one-line "Refined by ADR-007" pointer, not a rewrite.
- `docs/DESIGN.md` §Gates gets one bullet; §Open questions gets items 5 and 6 (re-gating a human edit before approval;
  checking a downstream verdict against a changed upstream artifact) and the `guard-stage-order` hooks-table row cites them;
  the workspace tree in DESIGN (§The content workspace) gains `brief.source.prev.md` and `outline.prev.<n>.md`; the glossary's Verdict file row gets the carve-out, and one new row covers backups (`brief.source.prev.md`, `outline.prev.<n>.md`: a copy kept before a rebuild, not an artifact and not gated, so "an actor writes exactly one artifact" stays true).

## Requirements

### R1 — Stage skills keep the verdict and the artifact in step (S)
- files: `skills/intake-brief/SKILL.md`, `skills/research/SKILL.md`, `skills/outline/SKILL.md`,
  `rules/core/CLAUDE.template.md`, `tests/test_skills.py`, `tests/test_templates.py`, ADR-007 (new), ADR-004 (pointer), `docs/DESIGN.md`,
  `docs/DOMAIN_GLOSSARY.md`, `CHANGELOG.md`
- test (red before, green after): one test per promise, each parametrised over the three actors with readable `ids=` (`test_actor_does_not_edit_after_a_pass`, `test_actor_reports_advisories_and_stops`, `test_actor_reruns_with_the_next_verdict_after_a_change`, `test_actor_names_later_artifacts_as_stale_after_a_rebuild`), plus single-actor tests next to `test_outline_actor_never_writes_the_approval` for the brief's carry-forward and the outline's backup. Together they assert the text says: the verdict covers the artifact as it was when the gate ran; the actor does not edit after a PASS and reports
  the advisory findings; a change means changing the written input and rerunning, with the next `r<k>`; a BLOCK from a
  rerun counts toward FLOW-3; a rebuild names later artifacts as built on the replaced version; the brief text carries earlier answers forward and the outline text saves any existing outline to a new `outline.prev.<n>.md` before replacing it, never replacing an earlier backup, whatever its `Approved-by:` value. A second test,
  `test_outline_stage_resets_the_approval_when_it_rebuilds`, next to `test_outline_actor_never_writes_the_approval`,
  asserts the outline text says a replaced outline needs a new approval and that Step 6 still lets the human change direction. `test_constitution_has_the_edit_after_pass_hygiene_line`, in `tests/test_templates.py` next to the FLOW-2 test, asserts the constitution hygiene line and the words "upstream ones included" (the line goes in the Workspace hygiene section; the test's module docstring is updated to name this second wording check, next to FLOW-2, and why).
- checks before the runs, with real output in the PR: `.venv/bin/python -m pytest` (full suite, green) and `claude plugin validate ./` (one expected warning).
- executed how (scratchpad workspaces only, each a new directory under the session scratchpad; each step a separate
  `claude -p "/writer-plugin:<stage> …" --plugin-dir <this checkout> --permission-mode acceptEdits` call):
  0. setup, as in the earlier plans: `cp -R` the workspace under the scratchpad, `ls gates/` and record the verdict counts,
     and move earlier `G0-brief.r*.md` files into the copy's `gates/archive/` so FLOW-3 cannot stop the run.
  1. brief stage on the real brief; the first PASS is `G0-brief.r<k>`. Expect the advisories reported and `brief.md` not
     newer than that verdict (modification times). If the PASS has no advisories, repeat on a synthetic neutral brief built
     to produce one; otherwise list "edit-after-advisory not exercised" under Not verified.
  2. in a copy that already has `research.md` and a `brief.md` containing at least one `answered by the user, round <n>`
     line (synthetic neutral workspace; build it by editing a copy), rerun the brief stage with a corrected input file that
     changes a field the source states explicitly; expect `G0-brief.r<k+1>` with no finding on the changed field or on the
     answered field (the earlier answer survived), and a reply that names `research.md` as built on the replaced brief.
     Record field types, not values (PLG-1).
  3. outline stage in a synthetic neutral workspace (stages run once to a G2 PASS), a name written after `Approved-by:`,
     then `/writer-plugin:outline <slug>` again (a plain rerun); expect `outline.prev.<n>.md` holding the approved outline, then run the stage a second time before approving the new outline and expect **both** backups on disk. Between runs, if FLOW-3 would stop the sequence, move the scratch copy's `G2-outline.r*.md` into its `gates/archive/` and record that you did. "A run that saved no verdict" cannot be produced on demand, so the unit of the backup numbering is checked by the text test only and listed under Not verified (the approved one and the unapproved one); repeat once on an outline with an empty `Approved-by:` that was hand-edited and has a G2 PASS: expect the edit in its backup, `G2-outline.r<k+1>` (k is the highest number before the rerun), an empty `Approved-by:` in the new
     `outline.md`, and a reply that says the approval was cleared and the old outline was kept. Report line 1 and ordering only.
  3b. in the same workspace, after the G2 PASS, run `/writer-plugin:research <slug>` again; expect `G1-research.r<k+1>` (k is
     the highest number before the rerun) and a reply that names `outline.md` as built on the replaced research. Report line
     1 and file ordering only (a synthetic, neutral topic; web research is real).

## Docs to update in this PR
- [ ] ADR-007 (new) and the ADR-004 pointer · DESIGN.md §Gates bullet, §Open questions 5 and 6, hooks-table row and the workspace tree · DOMAIN_GLOSSARY.md · CHANGELOG.md

## Risks
| Risk | Impact | Cheapest way to find out early |
|------|--------|-------------------------------|
| The actor still edits after PASS despite the text | verdict stale again | step 1 compares file times; Phase 4's hook is the real fix |
| A rebuilt outline discards an approved one | lost human work | the old outline is kept as `outline.prev.<n>.md`; step 3 checks it |
| Client data in evidence | PLG-1 | only line 1, counts and time ordering go in the PR; advisory text and full verdicts stay in the scratchpad, and before the PR opens the PR body and `git diff` are grepped for the real brief's client and vendor names (any hit stops the PR) |

## Assumptions
- ADR-007 states that an advisory on a research or outline PASS is the human's to accept or act on: a rerun rebuilds from upstream and does not target it. The actor reports it, and that is all it does.
- Headless runs cannot answer question rounds. Step 2's corrected input is built so the only gap is the field already answered, and the evidence must show no question was asked; if one is, that is reported. Question rounds in a headless run are otherwise listed under Not verified. One draft PR; `.serena/` is never committed. Not verified in the PR: edits outside the skill and a human's hand edit
  (Phase 4 open questions), mechanical enforcement (Phase 4).
