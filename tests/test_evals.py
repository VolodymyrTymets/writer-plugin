"""The eval suite's own contract (ADR-013): what `claude plugin eval` runs must be well formed before anyone pays for a run.

The cases live in evals/<case>/ (case.yaml, case.env, scaffold.sh, optional seed/), built on the synthetic briefs in
evals/briefs/ and the one-article fixture in evals/fixtures/. Run: python -m pytest tests/test_evals.py
"""
import json
import re
from pathlib import Path

import pytest

from conftest import PLUGIN
from lib import writer

EVALS = PLUGIN / 'evals'
CASES = sorted(p.parent for p in EVALS.glob('*/case.yaml'))
FIXTURE = EVALS / 'fixtures' / 'http-caching'
ARTICLE = FIXTURE / 'articles' / 'http-caching'
# PLG-1: only public standards, public docs and the reserved example domain may appear in eval material.
ALLOWED_DOMAINS = {'www.rfc-editor.org', 'developer.mozilla.org', 'example.com'}
URL = re.compile(r'https?://([^/\s)|>`"]+)')


def eval_files():
    return [p for p in EVALS.rglob('*') if p.is_file() and 'results' not in p.relative_to(EVALS).parts]


def test_there_is_a_pass_and_a_block_case_for_every_gate():
    names = {c.name for c in CASES}
    for g in ('g0', 'g1', 'g2', 'g3', 'g4'):
        assert any(n.startswith(f'{g}-pass') for n in names) and any(n.startswith(f'{g}-block') for n in names), g


def test_each_synthetic_brief_has_a_g0_case_and_a_brief_actor_case():
    briefs = sorted(p.stem for p in (EVALS / 'briefs').glob('*.md'))
    names = {c.name for c in CASES}
    assert len(briefs) == 3
    assert all(f'g0-pass-{b}' in names and f'brief-actor-{b}' in names for b in briefs)


def test_every_case_uses_the_one_scaffold_and_names_what_it_seeds():
    first = (CASES[0] / 'scaffold.sh').read_text()
    for c in CASES:
        assert (c / 'scaffold.sh').read_text() == first, f'{c.name}: scaffold.sh differs from the shared one'
        env = dict(line.split('=', 1) for line in (c / 'case.env').read_text().split())
        assert set(env) <= {'FIXTURE', 'BRIEF', 'SLUG', 'INPUT'} and env, c.name
        assert 'scaffold_script: scaffold.sh' in (c / 'case.yaml').read_text()


def test_the_fixture_final_matches_its_recorded_lint_run():
    """G4 refuses a lint record for another version of the final; a stale one would make g4-pass block for the wrong reason."""
    rec = json.loads((ARTICLE / '.prose-lint.json').read_text())
    assert (rec['sha256'], rec['lines']) == (writer.text_hash((ARTICLE / 'final.md').read_text()), [])


@pytest.mark.parametrize('case', [c for c in CASES if (c / 'seed').exists() and '-block-' in c.name], ids=lambda c: c.name)
def test_every_block_case_seeds_a_real_change_to_the_fixture_or_brief(case):
    for p in (case / 'seed').rglob('*'):
        if p.is_file() and p.name != '.prose-lint.json':
            rel = p.relative_to(case / 'seed')
            base = FIXTURE / rel if (FIXTURE / rel).exists() else EVALS / 'briefs' / f'{rel.parent.name}.md'
            assert p.read_text() != base.read_text(), f'{case.name}: {rel} is identical to what it overrides'


def test_a_seeded_final_comes_with_its_own_lint_record():
    for c in CASES:
        final = c / 'seed' / 'articles' / 'http-caching' / 'final.md'
        if final.exists():
            rec = json.loads((final.parent / '.prose-lint.json').read_text())
            assert rec['sha256'] == writer.text_hash(final.read_text()), c.name


def test_fact_bank_quotes_appear_verbatim_in_the_final_when_quoted():
    """The g4-pass final quotes F1; the quote must be the bank's, byte for byte, or the PASS case is wrong."""
    bank = (ARTICLE / 'research.md').read_text()
    f1 = next(l for l in bank.split('\n') if l.startswith('| F1 |')).rstrip(' |').rsplit('| ', 1)[1]
    # Markdown joins a wrapped line into one sentence, so compare the text a reader sees
    final = ' '.join((ARTICLE / 'final.md').read_text().split())
    assert f'"{f1}" [F1]' in final


def test_eval_material_has_no_placeholder_and_only_allowed_domains():
    for p in eval_files():
        text = p.read_text(errors='replace')
        assert '{{' not in text, f'{p.relative_to(PLUGIN)} holds a placeholder'
        hosts = set(URL.findall(text))
        assert hosts <= ALLOWED_DOMAINS, f'{p.relative_to(PLUGIN)} names {sorted(hosts - ALLOWED_DOMAINS)} (PLG-1 allowlist)'


def test_eval_results_are_never_committed():
    assert 'evals/results/' in (PLUGIN / '.gitignore').read_text().split()
