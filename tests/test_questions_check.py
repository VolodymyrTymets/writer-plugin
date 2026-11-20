"""The questions-list checker (FT-22, ADR-023): `bin/questions-check.py` and `writer.questions_findings`. Form rules only."""
import json
import subprocess
import sys

import pytest

from conftest import PLUGIN
from lib import writer as w

SCRIPT = PLUGIN / 'bin' / 'questions-check.py'
MARK = "<Can't be verified. Reason: the vendor page is behind a login>"


def doc(body: str, markers: int = 0, tail: str = '') -> str:
    gaps = ''.join(f'- {MARK} what is needed {i}\n' for i in range(markers))
    return f'# Title\n\n## Open gaps\n{gaps}\n## Questions for the human\n{body}\n{tail}'


def rules(text, upstream=None):
    return [f['message'] for f in w.questions_findings(text, upstream)]


def test_clean_list_has_no_finding():
    assert rules(doc('1. [OPEN] Which page shows the price, and what is its date?\n2. [RESOLVED] The standard is named; a fact row now says so.', 1)) == []


def test_no_section_and_no_marker_is_fine_and_a_lone_none_too():
    assert rules('# Title\n\nbody\n') == []
    assert rules(doc('none')) == []
    assert rules(doc('- none')) == []


def test_no_section_but_markers_is_one_finding():
    out = rules(f'# T\n\n- {MARK}\n- {MARK}\n')
    assert len(out) == 1 and '2 marker(s)' in out[0]


HUMAN = '<Needs to be written by a human. Reason: the owner will write this part herself>'


def test_a_skipped_line_covers_the_human_written_marker_and_a_marker_with_no_line_is_one_finding():
    text = f'# T\n\nA part: {HUMAN}\n\n## Questions for the human\n1. [SKIPPED] The pricing story is left for the owner to write.\n'
    assert rules(text) == []
    assert any('no "## Questions for the human" section' in m for m in rules(f'# T\n\nA part: {HUMAN}\n'))
    assert any('no [OPEN] or [SKIPPED] question' in m for m in rules(f'# T\n\nA part: {HUMAN}\n\n## Questions for the human\n1. [RESOLVED] something else settled\n'))


def test_marker_count_is_not_matched_to_lines():
    # three markers and no [OPEN] line is one finding; one [OPEN] line covers them (one question may cover several markers about one page)
    assert len(rules(doc('1. [RESOLVED] something settled earlier', 3))) == 1
    assert rules(doc('1. [OPEN] one question for the three gaps on the same page', 3)) == []


@pytest.mark.parametrize('line,fragment', [
    ('1. What is the price?', 'does not start with [OPEN], [RESOLVED] or [SKIPPED]'),
    ('1. [OPEN] Q4: what is the price?', 'Q or F id'),
    ('1. [OPEN] Is the price (Q4) right?', 'Q or F id'),
    ('1. [OPEN] Is [F7] still right?', 'Q or F id'),
    ('1. [OPEN] Is [F7, F9] still right?', 'Q or F id'),
    ('1. [OPEN] See comment 3 about the price', 'Q or F id'),
])
def test_line_rules(line, fragment):
    assert any(fragment in m for m in rules(doc(line)))


def test_a_business_quarter_is_not_an_id():
    assert rules(doc('1. [OPEN] Which page gives Q3 2026 revenue, with its date?\n2. [OPEN] Is F1 car data public?')) == []


def test_list_prefixes_and_html_comment_are_ignored():
    body = '<!-- Start each line with [OPEN]; write none when nothing is owed. -->\n- [OPEN] a bullet question\n1) [OPEN] a numbered one'
    assert rules(doc(body)) == []


def test_section_must_be_last_but_an_approval_line_may_follow():
    assert rules(doc('1. [OPEN] ok', tail='Approved-by:\n')) == []
    assert rules(doc('1. [OPEN] ok', tail='Signed-off-by: A Name\n')) == []
    # prose after the list has no heading to end the section, so it reads as a question line with no mark
    assert rules(doc('1. [OPEN] ok', tail='Some prose after.\n'))
    assert any('not the last section' in m for m in rules(doc('1. [OPEN] ok', tail='## Another heading\ntext\n')))


def test_old_heading_gets_the_placement_rule_only():
    old = f'# T\n\n- {MARK}\n\n## Open questions for the human\n- Browser support for immutable: a support table.\n'
    assert rules(old) == []
    assert any('not the last section' in m for m in rules(old + '\n## Call to action\nx\n'))


def test_a_question_the_previous_stage_resolved_is_not_repeated_in_any_form():
    up = doc('1. [RESOLVED] The standard is named; a fact row now says so.')
    assert any('already resolved' in m for m in rules(doc('1. [RESOLVED] The standard is named, a fact row now says so'), up))
    assert any('already resolved' in m for m in rules(doc('1. [OPEN] The standard is named; a fact row now says so.'), up)), 'an [OPEN] copy is a repeat too'
    assert any('already resolved' in m for m in rules(doc('1. [OPEN] The standard is named?'), up)), 'the first sentence is what identifies the question'
    assert rules(doc('1. [RESOLVED] The standard was confirmed by the vendor'), up) == [], 'a different question is new'


def test_none_in_its_older_spellings_is_accepted():
    for body in ('none', 'None.', '- None.'):
        assert rules(doc(body)) == [], body


def test_findings_point_at_the_right_line_with_lf_and_crlf():
    text = '# T\n\n## Questions for the human\n1. [OPEN] ok\n2. no mark here\n'
    assert [f['line'] for f in w.questions_findings(text, None)] == [5]
    assert [f['line'] for f in w.questions_findings(text.replace('\n', '\r\n'), None)] == [5]
    after = '# T\n\n## Questions for the human\n1. [OPEN] ok\n\n## Next\nx\n'
    assert [f['line'] for f in w.questions_findings(after, None)] == [6]


def test_a_fenced_heading_is_not_the_section_and_a_hash_line_in_a_fence_does_not_end_it():
    fenced = '# T\n\n```\n## Questions for the human\nnot a list\n```\n'
    assert rules(fenced) == []
    inside = '# T\n\n## Questions for the human\n1. [OPEN] ok\n```\n# a comment line in a fence\n```\n'
    assert not any('not the last section' in m for m in rules(inside))


def run(root, *args):
    r = subprocess.run([sys.executable, str(SCRIPT), '--root', str(root), *args], capture_output=True, text=True)
    return r.returncode, json.loads(r.stdout)


def make(tmp_path, **files):
    art = tmp_path / 'articles' / 'a'
    art.mkdir(parents=True)
    for name, text in files.items():
        (art / f'{name}.md').write_text(text, encoding='utf-8')
    return tmp_path


def test_cli_checks_the_stage_against_its_upstream_and_writes_nothing(tmp_path):
    root = make(tmp_path, research=doc('1. [RESOLVED] Settled upstream.'), outline=doc('1. [RESOLVED] Settled upstream.'))
    before = sorted(p.name for p in (root / 'articles' / 'a').iterdir())
    code, out = run(root, 'a', 'outline')
    assert code == 0 and len(out['findings']) == 1 and out['findings'][0]['rule'] == 'FACT-6' and out['notes'] == []
    assert run(root, 'a', 'research') == (0, {'findings': [], 'notes': []})
    assert sorted(p.name for p in (root / 'articles' / 'a').iterdir()) == before


def test_cli_reports_a_missing_upstream_as_a_note_not_a_finding_or_a_crash(tmp_path):
    root = make(tmp_path, draft=doc('1. [OPEN] a question'))
    code, out = run(root, 'a', 'draft')
    assert code == 0 and out['findings'] == [] and any('outline.md is missing' in n for n in out['notes'])


def test_cli_never_reads_an_unreadable_target_as_a_clean_list(tmp_path):
    root = make(tmp_path, draft=doc('1. [OPEN] a question'))
    path = root / 'articles' / 'a' / 'draft.md'
    path.chmod(0)
    try:
        code, out = run(root, 'a', 'draft')
    finally:
        path.chmod(0o644)
    assert code == 1 and 'error' in out, out


@pytest.mark.parametrize('args', [('a', 'brief'), ('a', 'final'), ('..', 'draft'), ('a',), ('a', 'outline')])
def test_cli_bad_requests_are_json_errors(tmp_path, args):
    code, out = run(tmp_path, *args)
    assert code == 1 and 'error' in out
