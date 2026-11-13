"""Shape guard for the inert library (rules/core and templates/).

Later phases parse these files (gates, prose-lint, guard-stage-order), so these tests pin the shape, not the wording.
Two deliberate wording checks: FLOW-2 (`non-empty`), because a guard built on it must not accept an empty line, and the
edit-after-PASS hygiene line (ADR-007), because it is the only mitigation until Phase 4's hook can enforce it.
Run: python -m pytest tests/test_templates.py
"""
import re
from pathlib import Path

import pytest

from conftest import PLUGIN as ROOT

CONSTITUTION = ROOT / 'rules' / 'core' / 'CLAUDE.template.md'
TEMPLATES = ROOT / 'templates'
RULE_ID = re.compile(r'\b(?:BRF|FACT|STR|VOI|SEO|FLOW|PLG)-\d+\b')
ONE_PLACEHOLDER = re.compile(r'\{\{[^{}]*\}\}')
PREFIXES = {'BRF', 'FACT', 'STR', 'VOI', 'SEO', 'FLOW', 'PLG'}
# A value line is a bullet "- **Label:** value" (the form every template uses for a fill-in field).
VALUE_LINE = re.compile(r'^- \*\*[^*]+:\*\*\s*(.*)$')


def read(path) -> str:
    return Path(path).read_text(encoding='utf-8')


def headings(text: str) -> list:
    return [m.group(1) for m in re.finditer(r'^#{1,6}\s+(.*)$', text, re.M)]


def table_header(text: str, after_heading: str) -> list:
    """Column names of the first table after the given heading."""
    start = text.index(after_heading)
    for line in text[start:].split('\n'):
        if line.startswith('|'):
            return [c.strip() for c in line.strip().strip('|').split('|')]
    raise AssertionError(f'no table after "{after_heading}"')


def design_rule_ids() -> set:
    """Rule IDs from the rule table in docs/DESIGN.md (rows start with a rule prefix)."""
    ids, seen = set(), set()
    for line in read(ROOT / 'docs' / 'DESIGN.md').split('\n'):
        row = re.match(r'^\|\s*(BRF|FACT|STR|VOI|SEO|FLOW|PLG)\s*\|', line)
        if row:
            seen.add(row.group(1))
            ids.update(RULE_ID.findall(line))
    # A reformatted row must fail loudly, not drop its rule IDs from the check.
    assert seen == PREFIXES, f'DESIGN rule table rows found for {sorted(seen)}, expected {sorted(PREFIXES)}'
    return ids


def test_constitution_defines_every_design_rule_id():
    wanted = design_rule_ids()
    assert wanted, 'found no rule IDs in the docs/DESIGN.md rule table - the table format changed'
    text = read(CONSTITUTION)
    missing = sorted(wanted - set(RULE_ID.findall(text)))
    assert not missing, f'constitution does not define: {", ".join(missing)}'
    assert len(text.split('\n')) < 200, 'constitution is over the 200-line budget'


def test_constitution_flow_2_requires_a_non_empty_approval():
    line = next(l for l in read(CONSTITUTION).split('\n') if '**FLOW-2**' in l)
    assert 'non-empty' in line, 'FLOW-2 must say that an empty Approved-by line is not approval'


@pytest.mark.parametrize('name', ['brief', 'research', 'outline', 'style'])
def test_every_template_exists_and_has_a_title(name):
    path = TEMPLATES / f'{name}.md'
    assert path.exists(), f'templates/{name}.md is missing'
    assert read(path).startswith('# '), f'templates/{name}.md must start with an H1'


@pytest.mark.parametrize('n', range(1, 7), ids=lambda n: f'BRF-{n}')
def test_brief_has_a_section_per_brf_rule(n):
    assert any(f'(BRF-{n})' in h for h in headings(read(TEMPLATES / 'brief.md')))


def test_research_fact_bank_columns_match_glossary():
    glossary = read(ROOT / 'docs' / 'DOMAIN_GLOSSARY.md')
    row = re.search(r'Rows `([^`]+)` in `research.md`', glossary)
    assert row, 'glossary has no fact-bank row definition'
    expected = [c.strip() for c in row.group(1).replace('\\|', '|').split('|')]
    assert table_header(read(TEMPLATES / 'research.md'), '## Fact bank') == expected


def test_outline_has_empty_approval_line_and_budget_column():
    text = read(TEMPLATES / 'outline.md')
    lines = [l for l in text.split('\n') if l.startswith('Approved-by:')]
    assert len(lines) == 1, 'outline template needs exactly one Approved-by: line'
    assert lines[0][len('Approved-by:'):].strip() == '', 'a shipped template must never be pre-approved (FLOW-2)'
    cols = table_header(text, '## Structure')
    assert {'Fact IDs', 'Words'} <= set(cols), f'outline structure table lacks Fact IDs or Words: {cols}'


def test_style_template_has_no_filled_client_values():
    lines = [l for l in read(TEMPLATES / 'style.md').split('\n') if l.strip()]
    values = [(l, VALUE_LINE.match(l)) for l in lines if VALUE_LINE.match(l)]
    assert values, 'style template has no value lines'
    filled = [l for l, m in values if not ONE_PLACEHOLDER.fullmatch(m.group(1))]
    assert not filled, 'style template carries a real value (PLG-1): ' + '; '.join(filled)
    # Anything that is not a heading or a value line is prose, where a client name could hide. One intro line is allowed.
    prose = [l for l in lines if not l.startswith('#') and not VALUE_LINE.match(l)]
    assert len(prose) <= 1, f'style template has stray prose: {prose}'
    # SEO-2/3 are fixed rules, so no field may configure a title or meta limit.
    assert not [l for l, _ in values if re.search(r'(?i)\*\*[^*]*(title|meta)', l)], 'title/meta limits are not configurable'


def test_constitution_has_the_edit_after_pass_hygiene_line():
    text = ' '.join(read(CONSTITUTION).split())
    assert 'does not edit an artifact after its gate has passed' in text
    assert 'upstream ones included' in text, 'editing an upstream artifact stales the earlier gate that passed it'
