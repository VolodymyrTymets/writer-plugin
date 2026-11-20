"""prose-lint.py: one parametrised case per rule, run as the script is run (a subprocess). Run: python -m pytest tests/test_prose_lint.py

Fixtures are neutral synthetic articles built under tmp_path (PLG-1). The checks and their rule IDs are the contract in
docs/decisions/ADR-009 and docs/DESIGN.md.
"""
import importlib.util
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


def final_text(title=TITLE, meta=META, body=None, extra='', words=None, slug='pick-a-standing-desk'):
    if body is None:
        intro = f'Choosing a {KEYWORD} is simple when you measure first. ' + filler(20)
        body = (f'# {title or "Title"}\n\n{intro}\n\n## Measure for a {KEYWORD}\n\n{filler(words if words is not None else 150)}\n\n'
                f'## Close\n\n{filler(20)}\n{extra}\n')
    head = '---\n' + (f'title: {title}\n' if title is not None else '') + (f'meta_description: {meta}\n' if meta is not None else '') \
        + f'slug: {slug}\n---\n'
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
    (dict(slug='Acme Review'), 'SEO-6'),
    (dict(slug='Pick-A-Desk'), 'SEO-6'),
    (dict(slug='pick--a-desk'), 'SEO-6'),
    (dict(slug='two words'), 'SEO-6'),
], ids=['too-long', 'too-short', 'title-over-60', 'meta-short', 'meta-long', 'keyword-not-in-title', 'banned-phrase', 'ai-tell',
        'marker', 'marker-curly', 'number-without-fact-id', 'slug-spaces', 'slug-capitals', 'slug-double-hyphen', 'slug-space-only'])
def test_each_rule_fires_on_its_own_case(ws, kwargs, rule):
    (ws / 'final.md').write_text(final_text(**kwargs))
    r = lint(ws / 'final.md')
    assert rule in rules(r), r.out
    assert r.code == 1


def test_a_number_with_a_fact_id_in_the_same_sentence_is_fine(ws):
    (ws / 'final.md').write_text(final_text(extra='The desk weighs 40 kilograms [F3].'))
    assert 'FACT-1' not in rules(lint(ws / 'final.md'))


# FT-4: 36 of 69 recorded lines on a real final were noise. Each is a form that makes no claim a fact ID could source.
NOISE = [
    "<Can't be verified. Reason: the page returned HTTP 403 to the fetch tool, so no price was read.>",
    "The review sites could not be read. <Can't be verified. Reason: G2 returned HTTP 403 after 2 tries.>",
    'The dashboard looks like this.\n\n![Screenshot 1: the dashboard](shots/one.png)',
    '![Screenshot of the settings page](shots/step-2.png)',
    'Screenshot 2 shows the settings page.',
    'Figure 3 and Table 4 sum it up.',
    'Step 2 is to measure the room.',
    "**G2 rating:** <Can't be verified. Reason: G2 returned HTTP 403.>",
    'B2B teams read the H2 headings on G2.',
    'Data checked in November 2026.',
    'Prices checked on 3 November 2026.',
    'The desk weighs less than the chair [F5, F14].',
    'The desk weighs less than the chair [F5,F14,F15].',
]


@pytest.mark.parametrize('extra', NOISE, ids=['marker-reason', 'marker-reason-inline', 'image-label', 'image-path-digits', 'screenshot-label', 'figure-and-table',
                                              'step-label', 'name-with-a-digit-beside-a-marker', 'names-with-digits', 'checked-in-month-year', 'checked-on-date', 'fact-list', 'fact-list-no-spaces'])
def test_forms_that_make_no_claim_are_not_flagged_by_the_number_check(ws, extra):
    (ws / 'final.md').write_text(final_text(extra='\n' + extra + '\n'))
    r = lint(ws / 'final.md')
    assert 'FACT-1' not in rules(r), r.out


@pytest.mark.parametrize('extra', [
    'The desk weighs 40 kilograms.',
    "The desk weighs 40 kilograms. <Can't be verified. Reason: the page returned HTTP 403.>",
    'Screenshot 2 shows that 45% of buyers return the desk.',
    'Data checked in November 2026 shows 45% growth.',
    'Step 2 costs 30 dollars.',
    'G2 lists 45 tools.',
    'Revenue in Q3 grew 45%.',
    'The desk weighs 40 kilograms [F5, X14].',
    'In 2025, 40% of desks were returned [F5]. Also 3 of 4 buyers said so.',
], ids=['plain-number', 'number-beside-a-marker', 'number-after-a-label', 'number-after-a-checked-date', 'number-after-a-step', 'number-beside-a-name', 'number-after-a-quarter',
        'broken-list', 'second-sentence-has-no-id'])
def test_a_real_unsourced_number_is_still_flagged(ws, extra):
    (ws / 'final.md').write_text(final_text(extra='\n' + extra + '\n'))
    assert 'FACT-1' in rules(lint(ws / 'final.md')), extra


def test_a_fact_list_is_not_counted_as_prose_words():
    """`[F5, F14]` is a tag, like `[F5]`: counting its pieces as words moved an article across its length bound."""
    spec = importlib.util.spec_from_file_location('prose_lint', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert len(mod.prose_words('A claim [F5, F14, F15].')) == len(mod.prose_words('A claim [F5].')) == 2


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


@pytest.mark.parametrize('line,keyword', [
    ('standing desk (150 US / 250 global searches a month, Ahrefs, October 2026). Use 14 to 20 exact uses.', 'standing desk'),
    ('standing desk; 150 searches a month', 'standing desk'),
    ('standing desk. Use it 14 to 20 times.', 'standing desk'),
    ('standing desk', 'standing desk'),
], ids=['parenthesis-and-notes', 'semicolon', 'full-stop-notes', 'bare'])
def test_the_keyword_is_the_bare_phrase_before_notes_in_the_brief_line(ws, line, keyword):
    (ws / 'brief.md').write_text(f'# Brief\n\n- **Primary keyword:** {line}\n- **Target length:** 200 words\n')
    (ws / 'final.md').write_text(final_text())
    r = lint(ws / 'final.md')
    assert 'SEO-1' not in rules(r), r.out


def test_a_keyword_missing_from_the_title_is_still_reported_when_the_brief_line_has_notes(ws):
    (ws / 'brief.md').write_text('# Brief\n\n- **Primary keyword:** standing desk (150 searches a month). Notes.\n')
    (ws / 'final.md').write_text(final_text(title='How to pick a desk'))
    r = lint(ws / 'final.md')
    assert 'SEO-1' in rules(r) and '"standing desk" is not in the title' in r.out


@pytest.mark.parametrize('body,why', [
    ('# One\n\ntext\n\n# Two\n\ntext\n', 'two H1'),
    ('text only\n', 'no H1'),
    ('# One\n\ntext\n\n### Skipped\n\ntext\n', 'skipped level'),
], ids=['two-h1', 'no-h1', 'skipped-level'])
def test_heading_rules_apply_to_any_article_file(ws, body, why):
    (ws / 'draft.md').write_text(body)
    r = lint(ws / 'draft.md')
    assert 'STR-4' in rules(r), why


@pytest.mark.parametrize('slug', ['"pick-a-desk"', "'pick-a-desk'", 'pick-a-desk'], ids=['double-quoted', 'single-quoted', 'plain'])
def test_a_well_formed_slug_is_no_finding_even_in_yaml_quotes(ws, slug):
    (ws / 'final.md').write_text(final_text(slug=slug))
    assert 'SEO-6' not in rules(lint(ws / 'final.md'))


def test_a_final_with_no_slug_line_is_no_seo_6_finding(ws):
    text = final_text()
    (ws / 'final.md').write_text(text.replace('slug: pick-a-standing-desk\n', ''))
    assert 'SEO-6' not in rules(lint(ws / 'final.md'))


def test_a_draft_is_not_held_to_the_final_only_rules(ws):
    (ws / 'draft.md').write_text(f'---\nslug: Bad Slug\n---\n# {TITLE}\n\nChoosing a {KEYWORD}. {filler(180)}\n\n## Part\n\n{filler(10)}\n')
    r = lint(ws / 'draft.md')
    assert not {'SEO-1', 'SEO-2', 'SEO-3', 'SEO-6', 'FLOW-6'} & set(rules(r)), r.out


def test_a_missing_front_matter_is_a_finding_for_a_final(ws):
    (ws / 'final.md').write_text(f'# {TITLE}\n\n{filler(180)}\n')
    r = lint(ws / 'final.md')
    assert 'SEO-2' in rules(r) and 'SEO-3' in rules(r)


@pytest.mark.parametrize('brief,expected_bounds', [
    ('- **Target length:** 200 words', (180, 220)),
    ('- **Target length:** 1,400', (1260, 1540)),
    ('- **Target length:** 3,500-4,000 words', (3150, 4400)),
    ('- **Target length:** 3,500 to 4,000 words', (3150, 4400)),
], ids=['single', 'thousands-separator', 'range', 'range-with-to'])
def test_the_target_length_is_read_from_the_brief(brief, expected_bounds):
    sys.path.insert(0, str(PLUGIN / 'bin'))
    import importlib.util
    spec = importlib.util.spec_from_file_location('prose_lint', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.length_bounds(brief) == expected_bounds


def test_a_few_words_under_a_range_is_not_a_finding(ws):
    # FT-7: 3,493 words against 3,500-4,000 was flagged and the actor padded prose to clear it; STR-6 is the range plus or minus 10%
    (ws / 'brief.md').write_text(BRIEF.replace('200 words', '3,500-4,000 words'))
    (ws / 'final.md').write_text(final_text(words=3300))
    assert 'STR-6' not in rules(lint(ws / 'final.md'))
    (ws / 'final.md').write_text(final_text(words=2800))
    assert 'STR-6' in rules(lint(ws / 'final.md'))


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


# The setup skill writes "none" for an empty list; read as a phrase it would ban the word itself and G4 would block on noise.
@pytest.mark.parametrize('value', ['none', 'None', 'NONE', ' none '], ids=['lower', 'title', 'upper', 'spaced'])
def test_a_none_style_value_is_an_empty_list_not_a_banned_word(ws, tmp_path, value):
    (tmp_path / '.claude' / 'rules' / 'style.md').write_text(
        f'## Banned phrases (VOI-2)\n- **Phrases:** {value}\n\n## AI tells to flag (VOI-3)\n- **Tells:** {value}\n')
    (ws / 'final.md').write_text(final_text(extra='There is none left to measure.'))
    r = lint(ws / 'final.md')
    assert (rules(r), [l for l in r.out.split('\n') if 'no filled style guide' in l]) == ([], [])


def test_none_inside_a_longer_list_is_still_a_phrase(ws, tmp_path):
    (tmp_path / '.claude' / 'rules' / 'style.md').write_text('## Banned phrases (VOI-2)\n- **Phrases:** none, game changer\n')
    (ws / 'final.md').write_text(final_text(extra='There is none left, a game changer.'))
    assert [l.split(' ', 2)[2] for l in findings(lint(ws / 'final.md')) if l.startswith('VOI-2')] == \
        ['banned phrase "none"', 'banned phrase "game changer"']


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


def test_record_keeps_the_printed_finding_lines_for_a_gate_that_cannot_run_the_script(ws):
    r = lint(ws / 'final.md', '--record')
    rec = json.loads((ws / '.prose-lint.json').read_text())
    assert rec['lines'] == findings(r) and rec['findings'] == len(rec['lines'])


# ---------------- the questions list (FT-22, ADR-023) ----------------
QUESTIONS = ('\n## Questions for the human\n'
             '1. [OPEN] Which page shows the 2026 price, and what is its date?\n'
             '2. [RESOLVED] The standard is named; a fact row now says so.\n')


def draft_with(questions):
    body = f'# {TITLE}\n\nChoosing a {KEYWORD} is simple when you measure first. {filler(20)}\n\n## Measure for a {KEYWORD}\n\n{filler(150)}\n\n## Close\n\n{filler(20)}\n'
    return body + questions + '\nApproved-by:\n'


def test_the_questions_section_is_outside_the_word_count_and_the_number_check_in_a_draft(ws):
    (ws / 'draft.md').write_text(draft_with(''))
    plain = lint(ws / 'draft.md')
    (ws / 'draft.md').write_text(draft_with(QUESTIONS + '3. [OPEN] ' + 'word ' * 120 + 'costs 40 dollars?\n'))
    with_list = lint(ws / 'draft.md')
    assert findings(plain) == findings(with_list) == [], 'a list of 120 extra words and a bare number must change nothing in a draft'


def test_a_questions_section_left_in_a_final_is_str_7(ws):
    (ws / 'final.md').write_text(final_text(extra=QUESTIONS))
    r = lint(ws / 'final.md')
    assert rules(r) == ['STR-7'] and r.code == 1, r.out
    assert 'working list' in r.out
    text = final_text(extra=QUESTIONS)
    heading_line = text.split('\n').index('## Questions for the human') + 1
    assert f'final.md:{heading_line} ' in r.out, 'STR-7 points at the section heading, front matter included'


def test_a_final_without_the_section_is_clean_of_str_7(ws):
    (ws / 'final.md').write_text(final_text())
    assert 'STR-7' not in rules(lint(ws / 'final.md'))


def test_the_doc_copy_of_a_draft_keeps_the_section():
    text = draft_with(QUESTIONS)
    assert '## Questions for the human' in writer.doc_text(text, 'draft')
