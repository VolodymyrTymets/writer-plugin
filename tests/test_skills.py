"""Contracts of the Phase 3 skills and agents that the structure guard does not cover.

test_structure.py checks form (fork, write-free, command map). These tests check what the gates and actors promise
each other: which agent can open sources, and (as skills land) the verdict-file format that Phase 4 hooks will parse.
Run: python -m pytest tests/test_skills.py
"""
import re
from pathlib import Path

from conftest import PLUGIN as ROOT


def tools_of(agent: str) -> set:
    text = (ROOT / 'agents' / f'{agent}.md').read_text(encoding='utf-8')
    front = text.split('\n---\n', 1)[0]
    line = next(l for l in front.split('\n') if l.startswith('tools:'))
    return {t.strip() for t in line[len('tools:'):].split(',')}


def test_fact_gate_can_open_sources_and_gate_cannot():
    assert {'WebFetch', 'WebSearch'} <= tools_of('fact-gate')
    assert not {'WebFetch', 'WebSearch'} & tools_of('gate')
