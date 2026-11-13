"""Contracts of the Phase 3 skills and agents that the structure guard does not cover.

test_structure.py checks form (fork, write-free, command map). These tests check what the gates and actors promise
each other: which agent can open sources, and (as skills land) the verdict-file format that Phase 4 hooks will parse.
Run: python -m pytest tests/test_skills.py
"""
import re
from pathlib import Path

import pytest

from conftest import PLUGIN as ROOT, UNVERIFIED_MARKER


def tools_of(agent: str) -> set:
    text = (ROOT / 'agents' / f'{agent}.md').read_text(encoding='utf-8')
    front = text.split('\n---\n', 1)[0]
    line = next(l for l in front.split('\n') if l.startswith('tools:'))
    return {t.strip() for t in line[len('tools:'):].split(',')}


def test_fact_gate_can_open_sources_and_gate_cannot():
    assert {'WebFetch', 'WebSearch'} <= tools_of('fact-gate')
    assert not {'WebFetch', 'WebSearch'} & tools_of('gate')


# ---------------- verdict-file contract (ADR-004) ----------------
# Phase 4's guard-stage-order reads line 1 of the latest verdict file with this pattern. A PASS carries no blockers and
# a BLOCK carries at least one, so a contradictory count can never read as a PASS.
VERDICT_LINE = re.compile(
    r'^## (G0 brief|G1 research|G2 outline|G3 draft|G4 final) gate: '
    r'(PASS \(0 blocking|BLOCK \([1-9]\d* blocking), \d+ advisory\)$')
# Each dict lists only the skills that exist at this commit; the commit that adds a skill adds its entry.
# gate skill dir -> its own gate/stage pair, the agent it forks into, and the rule IDs its checklist may cite
GATES = {
    'check-brief': ('G0 brief', 'gate', {f'BRF-{n}' for n in range(1, 7)}),
    'check-research': ('G1 research', 'fact-gate', {f'FACT-{n}' for n in range(1, 7)}),
    'check-outline': ('G2 outline', 'gate', {'STR-2', 'STR-3', 'STR-5', 'SEO-1', 'FACT-1'}),
    'check-draft': ('G3 draft', 'gate', {'STR-1', 'STR-2', 'STR-5', 'STR-6', 'SEO-4', 'FACT-1', 'FACT-5', 'BRF-5'}),
}
# actor skill dir -> (stage, gate it invokes)
ACTORS = {
    'intake-brief': ('G0-brief', 'check-brief'),
    'research': ('G1-research', 'check-research'),
    'outline': ('G2-outline', 'check-outline'),
}
# Rules a gate's checklist must still carry. Deleting one of these rows must turn a test red.
MUST_CITE = {
    'check-brief': {f'BRF-{n}' for n in range(1, 7)},
    'check-research': {'FACT-2', 'FACT-3', 'FACT-5', 'FACT-6'},
    'check-outline': {'STR-2', 'STR-3', 'STR-5', 'SEO-1', 'FACT-1'},
    'check-draft': {'STR-1', 'STR-2', 'STR-5', 'SEO-4', 'FACT-1', 'FACT-5', 'BRF-5'},
}
RULE_ID = re.compile(r'\b(?:BRF|FACT|STR|VOI|SEO|FLOW|PLG)-\d+\b')


def skill_text(d: str) -> str:
    return (ROOT / 'skills' / d / 'SKILL.md').read_text(encoding='utf-8')


@pytest.mark.parametrize('d', GATES)
def test_verdict_regex_accepts_each_gates_own_examples_and_only_those(d):
    pair = GATES[d][0]
    heads = [l for l in skill_text(d).split('\n') if l.startswith('## G')]
    assert any('PASS' in l for l in heads) and any('BLOCK' in l for l in heads), f'{d} needs a literal PASS and BLOCK example'
    for line in heads:
        assert VERDICT_LINE.match(line), f'{d}: example does not match the verdict contract: {line}'
        assert line.startswith(f'## {pair} gate'), f'{d}: example uses another gate\'s pair: {line}'


@pytest.mark.parametrize('line', [
    '## G0 brief gate: PASS (1 blocking, 0 advisory)',
    '## G0 brief gate: BLOCK (0 blocking, 0 advisory)',
    '## G0 final gate: PASS (0 blocking, 0 advisory)',
    'PASS',
])
def test_verdict_regex_rejects_contradictory_or_mismatched_lines(line):
    assert not VERDICT_LINE.match(line)


@pytest.mark.parametrize('d', GATES)
def test_gate_uses_its_own_agent_and_checklist_cites_only_its_rules(d):
    _, agent, allowed = GATES[d]
    assert f'agent: writer-plugin:{agent}' in skill_text(d)
    cited = set(RULE_ID.findall((ROOT / 'skills' / d / 'references' / 'checklist.md').read_text(encoding='utf-8')))
    assert cited, f'{d} checklist cites no rule'
    assert not cited - allowed, f'{d} checklist cites rules outside its gate: {sorted(cited - allowed)}'


@pytest.mark.parametrize('d', ACTORS)
def test_actor_saves_verdicts_counts_blocks_on_disk_and_stops_after_two(d):
    stage, gate = ACTORS[d]
    text = skill_text(d)
    assert f'gates/{stage}.r' in text, f'{d} must save to gates/{stage}.r<k>.md'
    assert 'FLOW-3' in text and 'two or more' in text, f'{d} must stop after two BLOCKs across runs'
    assert f'writer-plugin:{gate}' in text, f'{d} must invoke {gate} through the Skill tool'
    assert '^## G' in text, f'{d} must check line 1 of the verdict before saving'


@pytest.mark.parametrize('d', [a for a in ACTORS if a != 'intake-brief'])
def test_actor_after_the_brief_refuses_without_the_previous_pass(d):
    text = skill_text(d)
    assert 'FLOW-1' in text and 'PASS' in text, f'{d} must refuse to start without the previous gate PASS on disk'
    previous = {'research': 'G0-brief', 'outline': 'G1-research'}[d]
    assert f'gates/{previous}.r' in text, f'{d} must name the verdict file it needs ({previous})'


def test_research_actor_fetches_every_source_itself_and_gate_opens_them():
    assert 'WebFetch' in skill_text('research').split('---', 2)[1]
    assert '**Open every source URL' in (ROOT / 'skills' / 'check-research' / 'SKILL.md').read_text(encoding='utf-8')


def test_outline_actor_never_writes_the_approval():
    text = skill_text('outline')
    assert 'FLOW-2' in text and 'never fill the `Approved-by:`' in text.replace('\n', ' ').replace('**', ''), \
        'the outline stage must say it never fills Approved-by (FLOW-2)'
    assert 'the outline is not approved' in text.lower()


def test_outline_gate_does_not_judge_the_approval_line():
    assert 'Approved-by' in skill_text('check-outline') and 'no rule here covers it' in skill_text('check-outline')


@pytest.mark.parametrize('d', GATES)
def test_gate_checklist_keeps_its_must_cite_rules(d):
    cited = set(RULE_ID.findall((ROOT / 'skills' / d / 'references' / 'checklist.md').read_text(encoding='utf-8')))
    assert not MUST_CITE[d] - cited, f'{d} checklist lost: {sorted(MUST_CITE[d] - cited)}'


@pytest.mark.parametrize('d', GATES)
def test_gate_resolves_its_input_from_disk_and_names_the_artifact(d):
    text = skill_text(d)
    assert '$ARGUMENTS' in text and 'most recently modified' in text, f'{d} must resolve its input itself'
    assert 'Artifact: none' in text, f'{d} must give a contract-conforming verdict when the artifact is missing'


def test_research_gate_reads_the_style_guide_at_the_path_design_uses():
    assert '.claude/rules/style.md' in skill_text('check-research')


def checklist_text(d: str) -> str:
    return ' '.join((ROOT / 'skills' / d / 'references' / 'checklist.md').read_text(encoding='utf-8').split())


def test_g1_checklist_blocks_ids_that_do_not_support_their_question():
    text = checklist_text('check-research')
    assert re.search(r'FACT-6.*blocking, and so is a listed ID that exists but does not support its question', text), 'a listed ID that does not support its question must be blocking'
    assert 'answers at least part of it' in text, 'say what "supports" means, so partial answers are judged the same way each run'


LIVE_PAGE = 'n/a (live page)'


def test_n_a_published_is_limited_to_first_party_vendor_pages():
    constitution = (ROOT / 'rules' / 'core' / 'CLAUDE.template.md').read_text(encoding='utf-8')
    # A rule is a bullet that may wrap over several lines, so read up to the next bullet or heading.
    def bullet(rule: str) -> str:
        return ' '.join(re.search(rf'- \*\*{rule}\*\*(.*?)(?=\n- \*\*|\n#|\Z)', constitution, re.S).group(1).split())
    fact_2, fact_4 = bullet('FACT-2'), bullet('FACT-4')
    assert 'live page' in fact_2, 'constitution FACT-2 must allow a live first-party page'
    assert 'checked' in fact_4, 'constitution FACT-4 must carry the "checked <month year>" duty'
    for path in (ROOT / 'skills' / 'research' / 'SKILL.md', ROOT / 'agents' / 'fact-gate.md'):
        assert LIVE_PAGE in path.read_text(encoding='utf-8'), f'{path.name} must carry {LIVE_PAGE}'
    text = checklist_text('check-research')
    assert LIVE_PAGE in text
    for needle in ('names the vendor', 'registrable domain', 'shows no published or updated date',
                   'third-party domain', 'another vendor', 'accessed date', 'as of'):
        assert needle in text, f'G1 checklist lost: {needle}'
    assert 'is blocking' in text.split(LIVE_PAGE, 1)[1], 'the checklist must say n/a is blocking outside the exception'


def test_research_template_notes_the_live_page_option_on_both_published_columns():
    text = (ROOT / 'templates' / 'research.md').read_text(encoding='utf-8')
    assert text.count(LIVE_PAGE) >= 2, 'both the Sources and the Fact bank tables must mention it'


def test_g1_prints_and_the_research_stage_reports_coverage():
    gate = skill_text('check-research')
    lines = gate.split('\n')
    heads = [i for i, l in enumerate(lines) if l.startswith('## G1 research gate')]
    assert heads, 'no G1 example found'
    for i in heads:
        assert lines[i + 1].startswith('Artifact:'), 'line 2 of an example must be Artifact:'
        assert re.fullmatch(r'Coverage: \d+ answered, \d+ open \(of \d+\)', lines[i + 2]), f'line 3 of an example must be Coverage: {lines[i + 2]!r}'
    assert 'Coverage: n/a' in gate, 'a missing artifact has no table to count'
    assert 'There is no "partial"' in checklist_text('check-research')
    assert 'Coverage' in skill_text('research'), 'the research stage must report coverage'


# ---------------- a verdict covers the artifact it judged (ADR-007) ----------------
def flat(d: str) -> str:
    return ' '.join(skill_text(d).split())


@pytest.mark.parametrize('d', ACTORS)
def test_actor_does_not_edit_after_a_pass(d):
    text = flat(d)
    assert 'covers the artifact as it was when the gate ran' in text
    assert 'After a PASS you never edit the artifact' in text


@pytest.mark.parametrize('d', ACTORS)
def test_actor_reports_advisories_and_stops(d):
    assert "report the gate's advisory findings" in flat(d)


@pytest.mark.parametrize('d', ACTORS)
def test_actor_reruns_with_the_next_verdict_after_a_change(d):
    text = flat(d)
    assert "change the stage's written input and run the stage again" in text
    assert 'saved as the next `r<k>`' in text
    assert 'A BLOCK from a rerun counts toward FLOW-3' in text


@pytest.mark.parametrize('d', ACTORS)
def test_actor_names_later_artifacts_as_stale_after_a_rebuild(d):
    assert 'built on the replaced version' in flat(d)


def test_brief_stage_carries_earlier_answers_forward_verbatim():
    text = flat('intake-brief')
    assert 'answered by the user, round <n>' in text
    assert 'verbatim' in text and 'unless the corrected input overrides' in text


def test_outline_stage_backs_up_the_outline_it_replaces_and_clears_the_approval():
    text = flat('outline')
    assert 'outline.prev.<n>.md' in text and 'never replace an earlier backup' in text
    assert 'whatever its `Approved-by:` value' in text
    assert 'needs a new approval' in text
    assert 'changes direction if needed' in text, 'Step 6 must still let the human change direction before approving'


# ---------------- the "can't be verified" marker (ADR-008) ----------------
MARKER_EXAMPLE = "<Can't be verified. Reason: the vendor's pricing page blocked the fetch.>"


def test_unverified_marker_regex_accepts_the_template():
    assert UNVERIFIED_MARKER.fullmatch(MARKER_EXAMPLE)


@pytest.mark.parametrize('variant', [
    "<Can\u2019t be verified. Reason: a curly apostrophe.>",
    "<Can't be verified. Reason: >",
    "<Can't be verified. Reason:    >",
    "<Can't be verified. Reason: first line\nsecond line>",
    "<Can't be verified. Reason: a <b> tag inside>",
    "<Can't be verified. Reason: a pipe | inside>",
    "<Cannot be verified. Reason: other wording.>",
    "<Can't be verified: no reason label>",
    "<Need human check/decision>",
], ids=['curly-apostrophe', 'empty-reason', 'spaces-only', 'multi-line', 'angle-in-reason', 'pipe-in-reason',
        'other-wording', 'no-reason-label', 'old-form'])
def test_unverified_marker_regex_rejects_variants(variant):
    assert not UNVERIFIED_MARKER.fullmatch(variant)


@pytest.mark.parametrize('d', ['research', 'outline'])
def test_stage_carries_the_exact_marker_form(d):
    assert "<Can't be verified. Reason:" in skill_text(d)


def test_research_stage_marks_what_it_cannot_prove_and_never_invents():
    text = flat('research')
    assert 'is not a fact row' in text and 'Open gaps' in text
    assert 'never invent' in text.lower()


def test_outline_stage_replaces_the_claim_with_the_marker_and_collects_them():
    text = flat('outline')
    assert 'replaces the claim' in text
    assert 'Open questions for the human' in text
    assert 'every marker in a cell appears in that section and nothing else does' in text


def test_outline_stage_writes_only_the_marker_and_a_neutral_label_in_a_marked_cell():
    text = flat('outline')
    assert 'write only the marker and a neutral label' in text
    assert 'do not list what the claim would have said' in text


def test_outline_stage_does_not_treat_open_gaps_or_its_own_knowledge_as_a_source():
    text = flat('outline')
    assert 'Open gaps, the brief and your own knowledge are not sources' in text
    assert 'a statement about a vendor, a price, a plan or a page that has no fact ID is a marker' in text


def test_g2_treats_a_marker_as_not_a_claim():
    text = checklist_text('check-outline')
    assert 'FACT-1 does not apply to a marker' in text
    assert 'beside a marker or inside its reason' in text
    assert 'not in the exact form' in text and 'is not counted' in text
    assert 'on a point the bank supports' in text and 'cite the fact ID instead' in text


def test_g2_prints_a_markers_line():
    gate = skill_text('check-outline')
    lines = gate.split('\n')
    heads = [i for i, l in enumerate(lines) if l.startswith('## G2 outline gate')]
    assert heads
    for i in heads:
        assert re.fullmatch(r'Markers: \d+', lines[i + 2]), f'line 3 of an example must be Markers: {lines[i + 2]!r}'
    assert 'Markers: n/a' in gate
    assert 'outside the "Open questions for the human" section' in checklist_text('check-outline')


# ---------------- verdicts are saved with the Write tool; a hand edit is re-gated (ADR-009) ----------------
@pytest.mark.parametrize('d', ACTORS)
def test_stage_skills_save_the_verdict_with_the_write_tool(d):
    assert 'with the Write tool' in flat(d), 'a Bash save of a verdict is blocked by the guard, so the skill must name the Write tool'


def test_outline_step_6_says_how_to_re_gate_a_hand_edit():
    text = flat('outline')
    assert 'the verdict no longer covers it' in text
    assert 'saved with the Write tool as the next verdict' in text
    assert 'a BLOCK counts toward FLOW-3' in text


# ---------------- G3, the draft gate (Phase 5) ----------------
def test_g3_reads_the_outline_brief_and_bank_and_cannot_open_sources():
    text = flat('check-draft')
    for needle in ('`outline.md`', '`brief.md`', '`research.md`', 'You cannot open web pages'):
        assert needle in text, f'G3 lost: {needle}'
    assert 'WebFetch' not in skill_text('check-draft').split('---', 2)[1]


def test_g3_prints_an_outline_line_and_never_blocks_on_length():
    gate = skill_text('check-draft')
    lines = gate.split('\n')
    heads = [i for i, l in enumerate(lines) if l.startswith('## G3 draft gate')]
    assert heads
    for i in heads:
        assert re.fullmatch(r'Outline: \d+ of \d+ sections present', lines[i + 2]), f'line 3 must be Outline: {lines[i + 2]!r}'
    assert 'Outline: n/a' in gate
    text = checklist_text('check-draft')
    assert 'never blocking at this gate' in text and 'G4 enforces the length' in text


def test_g3_treats_a_marker_as_not_a_claim():
    text = checklist_text('check-draft')
    assert 'FACT-1 does not apply to a marker' in text
    assert 'beside a marker or inside its reason' in text
    assert 'not in the exact form' in text
    assert 'a marker the outline does not contain' in text.lower()
