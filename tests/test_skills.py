"""Contracts of the Phase 3 skills and agents that the structure guard does not cover.

test_structure.py checks form (fork, write-free, command map). These tests check what the gates and actors promise
each other: which agent can open sources, and (as skills land) the verdict-file format that Phase 4 hooks will parse.
Run: python -m pytest tests/test_skills.py
"""
import re
from pathlib import Path

import pytest

from conftest import PLUGIN as ROOT


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
}
# actor skill dir -> (stage, gate it invokes)
ACTORS = {
    'intake-brief': ('G0-brief', 'check-brief'),
    'research': ('G1-research', 'check-research'),
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
    previous = {'research': 'G0-brief'}[d]
    assert f'gates/{previous}.r' in text, f'{d} must name the verdict file it needs ({previous})'


def test_research_actor_fetches_every_source_itself_and_gate_opens_them():
    assert 'WebFetch' in skill_text('research').split('---', 2)[1]
    assert '**Open every source URL' in (ROOT / 'skills' / 'check-research' / 'SKILL.md').read_text(encoding='utf-8')
