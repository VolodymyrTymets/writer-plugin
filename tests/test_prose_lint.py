"""prose-lint.py: one parametrised case per rule, run as the script is run (a subprocess). Run: python -m pytest tests/test_prose_lint.py

Fixtures are neutral synthetic articles built under tmp_path (PLG-1). The checks and their rule IDs are the contract in
docs/decisions/ADR-009 and docs/DESIGN.md.
"""
import json
import re
import subprocess
import sys
from collections import namedtuple

import pytest

from conftest import PLUGIN
from lib import writer

Result = namedtuple('Result', 'code out err')
SCRIPT = PLUGIN / 'bin' / 'prose-lint.py'
KEYWORD = 'standing desk'
TITLE = 'How to pick a standing desk'
META = ('A short guide to choosing a standing desk for a small room, with the checks that matter before you buy it and '
        'what to measure at home first.')
BRIEF = f"""# Brief

- **Primary keyword:** {KEYWORD}
- **Target length:** 200 words
"""
STYLE = """# Style

## Banned phrases (VOI-2)
- **Phrases:** game changer, in today's world

## AI tells to flag (VOI-3)
- **Tells:** delve into, it is worth noting
"""


def filler(n):
    return ' '.join(['plain'] * n) + '.'


def final_text(title=TITLE, meta=META, body=None, extra='', words=None):
    if body is None:
        intro = f'Choosing a {KEYWORD} is simple when you measure first. ' + filler(20)
        body = (f'# {title or "Title"}\n\n{intro}\n\n## Measure for a {KEYWORD}\n\n{filler(words if words is not None else 150)}\n\n'
                f'## Close\n\n{filler(20)}\n{extra}\n')
    head = '---\n' + (f'title: {title}\n' if title is not None else '') + (f'meta_description: {meta}\n' if meta is not None else '') \
        + 'slug: pick-a-standing-desk\n---\n'
    return head + body


@pytest.fixture
def ws(tmp_path):
    (tmp_path / '.claude' / 'rules').mkdir(parents=True)
    (tmp_path / '.claude' / 'rules' / 'style.md').write_text(STYLE)
    art = tmp_path / 'articles' / 'demo'
    art.mkdir(parents=True)
    (art / 'brief.md').write_text(BRIEF)
    return art


def lint(path, *args):
    r = subprocess.run([sys.executable, str(SCRIPT), *args, str(path)], capture_output=True, text=True, cwd=str(path.parent))
    return Result(r.returncode, r.stdout, r.stderr)


def findings(r):
    return [l for l in r.out.split('\n') if re.match(r'^[A-Z]+-\d+ ', l)]


def rules(r):
    return sorted({l.split()[0] for l in findings(r)})


def test_a_clean_final_has_no_findings_and_exits_0(ws):
    assert len(META) in range(120, 156) and len(TITLE) <= 60
    (ws / 'final.md').write_text(final_text())
    r = lint(ws / 'final.md')
    assert r.code == 0 and findings(r) == [], r.out


@pytest.mark.parametrize('kwargs,rule', [
    (dict(words=400), 'STR-6'),
    (dict(words=20), 'STR-6'),
    (dict(title='A very long title that is certainly more than sixty characters in length for a standing desk'), 'SEO-2'),
    (dict(meta='Too short.'), 'SEO-3'),
    (dict(meta='x ' * 100), 'SEO-3'),
    (dict(title='How to pick a chair'), 'SEO-1'),
    (dict(extra='This is a game changer for any home office.'), 'VOI-2'),
    (dict(extra='Let us delve into the details.'), 'VOI-3'),
    (dict(extra="<Can't be verified. Reason: the page blocked the fetch.>"), 'FLOW-6'),
    (dict(extra='<Can’t be verified. Reason: a curly apostrophe is still a marker.>'), 'FLOW-6'),
    (dict(extra='The desk weighs 40 kilograms.'), 'FACT-1'),
], ids=['too-long', 'too-short', 'title-over-60', 'meta-short', 'meta-long', 'keyword-not-in-title', 'banned-phrase', 'ai-tell',
        'marker', 'marker-curly', 'number-without-fact-id'])
def test_each_rule_fires_on_its_own_case(ws, kwargs, rule):
    (ws / 'final.md').write_text(final_text(**kwargs))
    r = lint(ws / 'final.md')
    assert rule in rules(r), r.out
    assert r.code == 1


def test_a_number_with_a_fact_id_in_the_same_sentence_is_fine(ws):
    (ws / 'final.md').write_text(final_text(extra='The desk weighs 40 kilograms [F3].'))
    assert 'FACT-1' not in rules(lint(ws / 'final.md'))


@pytest.mark.parametrize('extra', ['See https://example.com/page2 for more.', '1. A list item.', '## Step 2 of the plan [F1]'],
                         ids=['url', 'list-ordinal', 'heading-with-fact-id'])
def test_forms_that_are_not_claims_are_ignored_by_the_number_check(ws, extra):
    (ws / 'final.md').write_text(final_text(extra='\n' + extra + '\n'))
    assert 'FACT-1' not in rules(lint(ws / 'final.md'))


def test_the_keyword_must_be_in_the_first_100_words_and_in_an_h2(ws):
    body = f'# {TITLE}\n\n{filler(120)} {KEYWORD} appears late.\n\n## Measure first\n\n{filler(20)}\n'
    (ws / 'final.md').write_text(final_text(body=body))
    r = lint(ws / 'final.md')
    assert 'SEO-1' in rules(r) and 'first 100 words' in r.out and 'H2' in r.out


@pytest.mark.parametrize('body,why', [
    ('# One\n\ntext\n\n# Two\n\ntext\n', 'two H1'),
    ('text only\n', 'no H1'),
    ('# One\n\ntext\n\n### Skipped\n\ntext\n', 'skipped level'),
], ids=['two-h1', 'no-h1', 'skipped-level'])
def test_heading_rules_apply_to_any_article_file(ws, body, why):
    (ws / 'draft.md').write_text(body)
    r = lint(ws / 'draft.md')
    assert 'STR-4' in rules(r), why


def test_a_draft_is_not_held_to_the_final_only_rules(ws):
    (ws / 'draft.md').write_text(f'# {TITLE}\n\nChoosing a {KEYWORD}. {filler(180)}\n\n## Part\n\n{filler(10)}\n')
    r = lint(ws / 'draft.md')
    assert not {'SEO-1', 'SEO-2', 'SEO-3', 'FLOW-6'} & set(rules(r)), r.out


def test_a_missing_front_matter_is_a_finding_for_a_final(ws):
    (ws / 'final.md').write_text(f'# {TITLE}\n\n{filler(180)}\n')
    r = lint(ws / 'final.md')
    assert 'SEO-2' in rules(r) and 'SEO-3' in rules(r)


@pytest.mark.parametrize('brief,expected_bounds', [
    ('- **Target length:** 200 words', (180, 220)),
    ('- **Target length:** 1,400', (1260, 1540)),
    ('- **Target length:** 3,500-4,000 words', (3500, 4000)),
], ids=['single', 'thousands-separator', 'range'])
def test_the_target_length_is_read_from_the_brief(brief, expected_bounds):
    sys.path.insert(0, str(PLUGIN / 'bin'))
    import importlib.util
    spec = importlib.util.spec_from_file_location('prose_lint', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.length_bounds(brief) == expected_bounds


def test_missing_inputs_skip_their_checks_with_a_note_and_do_not_fail(ws, tmp_path):
    (ws / 'brief.md').unlink()
    (tmp_path / '.claude' / 'rules' / 'style.md').unlink()
    (ws / 'final.md').write_text(final_text(extra='This is a game changer.'))
    r = lint(ws / 'final.md')
    assert 'NOTE' in r.out and 'VOI-2' not in rules(r) and 'STR-6' not in rules(r)


def test_a_placeholder_style_value_is_skipped_not_matched(ws, tmp_path):
    (tmp_path / '.claude' / 'rules' / 'style.md').write_text('## Banned phrases (VOI-2)\n- **Phrases:** {{comma separated list}}\n')
    (ws / 'final.md').write_text(final_text(extra='Plain text about comma separated list.'))
    assert 'VOI-2' not in rules(lint(ws / 'final.md'))


# ---------------- the run record ----------------
def test_without_record_nothing_is_written(ws):
    (ws / 'final.md').write_text(final_text())
    lint(ws / 'final.md')
    assert not (ws / '.prose-lint.json').exists()


def test_record_writes_the_hash_the_count_and_a_time(ws):
    (ws / 'final.md').write_text(final_text(extra='This is a game changer.'))
    r = lint(ws / 'final.md', '--record')
    rec = json.loads((ws / '.prose-lint.json').read_text())
    assert rec['file'] == 'final.md' and rec['findings'] == len(findings(r)) and rec['at']
    assert rec['sha256'] == writer.text_hash((ws / 'final.md').read_text())


def test_a_sign_off_line_does_not_change_the_recorded_hash(ws):
    text = final_text()
    (ws / 'final.md').write_text(text)
    lint(ws / 'final.md', '--record')
    before = json.loads((ws / '.prose-lint.json').read_text())['sha256']
    (ws / 'final.md').write_text(text.replace('slug: pick-a-standing-desk', 'slug: pick-a-standing-desk\nSigned-off-by: Test Human'))
    assert writer.text_hash((ws / 'final.md').read_text()) == before
