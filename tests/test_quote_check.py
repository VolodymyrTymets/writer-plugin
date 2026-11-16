"""quote-check.py: is each fact-bank quote on its source page, word for word (ADR-015). Run: python -m pytest tests/test_quote_check.py

The script is driven as it is run (a subprocess) against a local HTTP server, so no test touches the network. Fixtures are
neutral synthetic pages under tmp_path (PLG-1).
"""
import json
import os
import subprocess
import sys
import threading
import time
from collections import namedtuple
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from conftest import PLUGIN
from lib import writer

Result = namedtuple('Result', 'code out err')
SCRIPT = PLUGIN / 'bin' / 'quote-check.py'
QUOTE = 'The max-age directive says a response is stale once its age passes the given number of seconds.'


def filler(n):
    return ' '.join(['plain'] * n) + '.'


PAGES = {
    '/ok': ('text/html', f'<html><body><h1>Caching</h1><p>{QUOTE}</p><p>{filler(250)}</p></body></html>', 200),
    '/split': ('text/html', f'<body><p>The max-age   directive says a <b>response</b> is stale\n once its age passes the&nbsp;given number of seconds.</p><p>{filler(250)}</p></body>', 200),
    '/curly': ('text/html', f'<body><p>It’s “stale” when the age passes the limit – not before.</p><p>{filler(250)}</p></body>', 200),
    '/entities': ('text/html', f'<body><p>Tom &amp; Jerry say a cache MUST NOT store &lt;secrets&gt;.</p><p>{filler(250)}</p></body>', 200),
    '/scripted': ('text/html', f'<body><script>var x = "{QUOTE}";</script><style>.a{{}}</style><p>{filler(250)}</p></body>', 200),
    '/inline': ('text/html', f'<body><p>A response stays <a href="/x">fresh</a>, or <code>stale</code>.</p><p>It is <em>very</em>cached<sup>1</sup>.</p><p>{filler(250)}</p></body>', 200),
    '/blocks': ('text/html', f'<body><table><tr><td>first cell</td><td>second cell</td></tr></table><ul><li>one item</li><li>next item</li></ul>{filler(250)}</body>', 200),
    '/changed': ('text/html', f'<body><p>The max-age directive says a response is fresh once its age passes the given number of seconds.</p><p>{filler(250)}</p></body>', 200),
    '/segments': ('text/html', f'<body><p>A cache stores a response. Many words sit between. Later the cache reuses it.</p><p>{filler(250)}</p></body>', 200),
    '/shell': ('text/html', f'<body><div id="app"></div><p>{filler(50)}</p></body>', 200),
    '/md': ('text/markdown', f'# Title\n\nThe cache MUST NOT store the response. {filler(250)}', 200),
    '/md2': ('text/markdown', f'## Limits\n\n- While **Gmail/Microsoft Outlook** accounts work, see [the help page](https://x.test/a) and `code`.\n> A __quoted__ line.\n\n{filler(250)}', 200),
    '/clause': ('text/html', f'<body><p>While the account is linked, our team works on more accounts as well.</p><p>{filler(250)}</p></body>', 200),
    '/num': ('text/html', f'<body><p>The plan costs $5.99 per month. 23 million users signed up. Latency fell by 40 percent.</p><p>{filler(250)}</p></body>', 200),
    '/gap': ('text/html', f'<body><p>A cache MUST NOT store the response.</p><p>{filler(400)}</p><p>Then it MUST revalidate.</p></body>', 200),
    '/huge': ('text/html', '<body><p>' + 'plain ' * 600000 + '</p></body>', 200),
    '/cp1252': ('text/html', b'<html><head><meta charset="windows-1252"></head><body><p>It\x92s \x93stale\x94 now.</p><p>' + filler(250).encode() + b'</p></body>', 200),
    '/nohead': ('text/html', f'<html><head><title>T</title><body><p>{QUOTE}</p><p>{filler(250)}</p></body>', 200),
    '/pdf': ('application/pdf', '%PDF-1.4 ' + QUOTE, 200),
    '/gone': ('text/html', 'not here', 404),
    '/blocked': ('text/html', 'denied', 403),
}
HITS = []
REDIRECTS = {'/to-ftp': 'ftp://example.com/x', '/to-private': 'http://10.0.0.1/x', '/to-metadata': 'http://169.254.169.254/latest/meta-data/',
             '/to-ok': '/ok'}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        HITS.append(self.path)
        if self.path == '/slow':
            time.sleep(3)
        try:
            if self.path in REDIRECTS:
                self.send_response(302)
                self.send_header('Location', REDIRECTS[self.path])
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            if self.path == '/drip':  # a body that arrives a little at a time: no single socket read is ever slow
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.send_header('Content-Length', '100000')
                self.end_headers()
                for _ in range(100):
                    self.wfile.write(b'x' * 1000)
                    self.wfile.flush()
                    time.sleep(0.2)
                return
            kind, body, status = PAGES.get(self.path, ('text/html', 'x', 404))
            data = body if isinstance(body, bytes) else body.encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *args):
        pass


@pytest.fixture(scope='module')
def server():
    srv = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{srv.server_address[1]}'
    srv.shutdown()


def bank(rows):
    head = ('# Research\n\n## Fact bank\n\n| F# | claim | source URL | publisher | published | accessed | verbatim quote |\n'
            '|----|-------|------------|-----------|-----------|----------|----------------|\n')
    return head + ''.join(f'| F{i} | a claim | {url} | Pub | 2026-01-01 | 2026-11-16 | {quote} |\n' for i, (url, quote) in enumerate(rows, 1)) \
        + '\n## Open gaps\n- none\n'


def run(tmp_path, rows, *extra, loopback=True):
    art = tmp_path / 'articles' / 'demo'
    art.mkdir(parents=True, exist_ok=True)
    (art / 'research.md').write_text(bank(rows), encoding='utf-8')
    env = dict(os.environ)
    env.pop('QUOTE_CHECK_ALLOW_LOOPBACK', None)
    if loopback:
        env['QUOTE_CHECK_ALLOW_LOOPBACK'] = '1'  # the test seam: the local server is the only loopback host a test may reach
    p = subprocess.run([sys.executable, str(SCRIPT), '--root', str(tmp_path), *extra, 'demo'], capture_output=True, text=True, env=env)
    return Result(p.returncode, p.stdout, p.stderr)


def statuses(r):
    return {line.split()[0]: line.split()[1] for line in r.out.strip().split('\n') if line.startswith('F')}


def test_a_quote_on_the_page_is_found(server, tmp_path):
    r = run(tmp_path, [(server + '/ok', QUOTE)])
    assert r.code == 0 and statuses(r) == {'F1': 'found'}, r.out + r.err


@pytest.mark.parametrize('path,quote', [
    ('/split', QUOTE),
    ('/curly', 'It\'s "stale" when the age passes the limit - not before.'),
    ('/curly', 'It’s “stale” when the age passes the limit – not before.'),
    ('/entities', 'Tom & Jerry say a cache MUST NOT store <secrets>.'),
    ('/ok', f'"{QUOTE}"'),
    ('/ok', f'“{QUOTE}”'),
], ids=['whitespace-tags-nbsp', 'page-curly-quote-straight', 'both-curly', 'entities', 'wrapped-in-quotes', 'wrapped-in-curly'])
def test_markup_whitespace_and_typography_do_not_hide_a_real_quote(server, tmp_path, path, quote):
    assert statuses(run(tmp_path, [(server + path, quote)])) == {'F1': 'found'}


@pytest.mark.parametrize('path,quote', [
    ('/inline', 'A response stays fresh, or stale.'),
    ('/inline', 'It is verycached1.'),
    ('/blocks', 'first cell second cell'),
    ('/blocks', 'one item next item'),
], ids=['link-then-comma', 'inline-tags-add-no-space', 'table-cells-are-separate-words', 'list-items-are-separate-words'])
def test_inline_tags_join_text_and_block_tags_separate_it(server, tmp_path, path, quote):
    assert statuses(run(tmp_path, [(server + path, quote)])) == {'F1': 'found'}


@pytest.mark.parametrize('path,quote', [('/blocks', 'first cellsecond cell'), ('/blocks', 'one itemnext item')],
                         ids=['cells-not-glued', 'items-not-glued'])
def test_block_boundaries_are_never_glued_into_one_word(server, tmp_path, path, quote):
    assert statuses(run(tmp_path, [(server + path, quote)])) == {'F1': 'not-found'}


@pytest.mark.parametrize('path,quote,why', [
    ('/changed', QUOTE, 'one word changed'),
    ('/ok', QUOTE.lower(), 'case changed'),
    ('/ok', QUOTE.replace('stale', 'old'), 'word swapped'),
    ('/scripted', QUOTE, 'text only inside a script block'),
], ids=['word-changed', 'case-changed', 'word-swapped', 'script-text'])
def test_an_altered_quote_is_not_found(server, tmp_path, path, quote, why):
    r = run(tmp_path, [(server + path, quote)])
    assert statuses(r) == {'F1': 'not-found'} and r.code == 1, why


@pytest.mark.parametrize('quote,expected', [
    ('A cache stores a response ... the cache reuses it.', 'found-elided'),
    ('A cache stores a response … Later the cache reuses it.', 'found-elided'),
    ('the cache reuses it. ... A cache stores a response', 'not-found'),
    ('A cache stores a response ... never said.', 'not-found'),
], ids=['three-dots', 'ellipsis-char', 'out-of-order', 'missing-segment'])
def test_a_quote_with_an_ellipsis_is_found_in_pieces_and_says_so(server, tmp_path, quote, expected):
    assert statuses(run(tmp_path, [(server + '/segments', quote)])) == {'F1': expected}


def test_a_plain_text_or_markdown_page_is_read_as_text(server, tmp_path):
    assert statuses(run(tmp_path, [(server + '/md', 'The cache MUST NOT store the response.')])) == {'F1': 'found'}


@pytest.mark.parametrize('quote', ['While Gmail/Microsoft Outlook accounts work, see the help page and code.', 'A quoted line.'],
                         ids=['bold-link-code', 'blockquote-underscores'])
def test_markdown_syntax_is_not_part_of_the_words(server, tmp_path, quote):
    assert statuses(run(tmp_path, [(server + '/md2', quote)])) == {'F1': 'found'}


@pytest.mark.parametrize('quote,expected', [
    ('While the account is linked.', 'found'),
    ('While the account is linked,', 'found'),
    ('While the account is linked;:.', 'found'),
    ('While the account is unlinked.', 'not-found'),
    ('While the account. is linked', 'not-found'),
    ('.', 'not-found'),
], ids=['full-stop', 'comma', 'mixed', 'word-changed', 'inner-punctuation-kept', 'only-punctuation'])
def test_closing_punctuation_on_a_cut_quote_is_not_a_difference(server, tmp_path, quote, expected):
    assert statuses(run(tmp_path, [(server + '/clause', quote)])) == {'F1': expected}


def test_a_page_with_almost_no_text_is_unreadable_not_a_miss(server, tmp_path):
    r = run(tmp_path, [(server + '/shell', QUOTE)])
    assert statuses(r) == {'F1': 'unreadable'} and r.code == 0


@pytest.mark.parametrize('path', ['/blocked', '/gone', '/pdf', '/nowhere'], ids=['403', '404', 'not-html', 'unknown'])
def test_a_page_that_cannot_be_read_is_unreachable(server, tmp_path, path):
    r = run(tmp_path, [(server + path, QUOTE)])
    assert statuses(r) == {'F1': 'unreachable'} and r.code == 0, r.out


@pytest.mark.parametrize('url', ['file:///etc/hosts', 'ftp://example.com/x', 'not a url'], ids=['file', 'ftp', 'junk'])
def test_only_http_and_https_are_fetched(tmp_path, url):
    assert statuses(run(tmp_path, [(url, QUOTE)])) == {'F1': 'unreachable'}


def test_a_url_shared_by_several_rows_is_fetched_once(server, tmp_path):
    HITS.clear()
    r = run(tmp_path, [(server + '/ok', QUOTE), (server + '/ok', 'plain plain plain'), (server + '/ok', 'never on the page')])
    assert statuses(r) == {'F1': 'found', 'F2': 'found', 'F3': 'not-found'}
    assert HITS.count('/ok') == 1


def test_slow_pages_end_as_unreachable_within_the_budget(server, tmp_path):
    started = time.time()
    r = run(tmp_path, [(server + '/slow', QUOTE), (server + '/slow', 'x'), (server + '/ok', QUOTE)], '--timeout', '0.3', '--budget', '1')
    assert statuses(r) == {'F1': 'unreachable', 'F2': 'unreachable', 'F3': 'found'}, r.out
    assert time.time() - started < 5


def test_an_exhausted_budget_marks_the_rest_unreachable_and_still_reports_every_row(server, tmp_path):
    r = run(tmp_path, [(server + '/slow', QUOTE), (server + '/ok', QUOTE), (server + '/split', QUOTE)], '--timeout', '1', '--budget', '0.5')
    assert set(statuses(r)) == {'F1', 'F2', 'F3'} and 'unreachable' in r.out


def test_the_script_writes_nothing_by_default(server, tmp_path):
    run(tmp_path, [(server + '/ok', QUOTE)])
    assert sorted(p.name for p in (tmp_path / 'articles' / 'demo').iterdir()) == ['research.md']


@pytest.mark.parametrize('args,expect', [
    (['nope'], 'does not exist'),
    (['../x'], 'not an article slug'),
    ([], 'usage'),
], ids=['no-research', 'bad-slug', 'no-slug'])
def test_a_bad_request_exits_2_with_a_message(tmp_path, args, expect):
    p = subprocess.run([sys.executable, str(SCRIPT), '--root', str(tmp_path), *args], capture_output=True, text=True)
    assert p.returncode == 2 and expect in p.stderr


def test_a_dossier_with_no_fact_rows_reports_none(tmp_path):
    art = tmp_path / 'articles' / 'demo'
    art.mkdir(parents=True)
    (art / 'research.md').write_text('# Research\n\n## Fact bank\n\nnone yet\n', encoding='utf-8')
    p = subprocess.run([sys.executable, str(SCRIPT), '--root', str(tmp_path), 'demo'], capture_output=True, text=True)
    assert p.returncode == 0 and 'no fact rows' in p.stdout


def test_fact_rows_reads_the_fixture_dossier():
    path = PLUGIN / 'evals' / 'fixtures' / 'http-caching' / 'articles' / 'http-caching' / 'research.md'
    rows = writer.fact_rows(path.read_text(encoding='utf-8'))
    assert rows and rows[0]['id'] == 'F1' and rows[0]['url'].startswith('https://') and 'max-age' in rows[0]['quote']
    assert [r['id'] for r in rows] == [f'F{i}' for i in range(1, len(rows) + 1)]


# ---------------- --record (ADR-015): the file the guard and G1 read ----------------
def test_record_writes_the_hash_the_statuses_and_the_printed_lines(server, tmp_path):
    r = run(tmp_path, [(server + '/ok', QUOTE), (server + '/blocked', QUOTE)], '--record')
    rec = json.loads((tmp_path / 'articles' / 'demo' / '.quote-check.json').read_text())
    assert rec['file'] == 'research.md' and rec['sha256'] == writer.text_hash((tmp_path / 'articles' / 'demo' / 'research.md').read_text())
    assert rec['rows'] == {'F1': 'found', 'F2': 'unreachable'} and rec['lines'][0] == 'F1 found' and rec['lines'][1].startswith('F2 unreachable')
    assert r.code == 0 and rec['at']


def test_record_is_written_even_when_a_quote_is_not_found(server, tmp_path):
    r = run(tmp_path, [(server + '/changed', QUOTE)], '--record')
    rec = json.loads((tmp_path / 'articles' / 'demo' / '.quote-check.json').read_text())
    assert r.code == 1 and rec['rows'] == {'F1': 'not-found'}


def test_record_of_a_dossier_with_no_fact_rows_is_an_empty_one(tmp_path):
    art = tmp_path / 'articles' / 'demo'
    art.mkdir(parents=True)
    (art / 'research.md').write_text('# Research\n\nnone yet\n', encoding='utf-8')
    subprocess.run([sys.executable, str(SCRIPT), '--root', str(tmp_path), '--record', 'demo'], capture_output=True, text=True)
    assert json.loads((art / '.quote-check.json').read_text())['rows'] == {}


def test_record_ignores_the_approval_lines_in_its_hash(server, tmp_path):
    run(tmp_path, [(server + '/ok', QUOTE)], '--record')
    path = tmp_path / 'articles' / 'demo' / 'research.md'
    path.write_text(path.read_text() + '\nApproved-by: Test Human\n')
    assert json.loads((path.parent / '.quote-check.json').read_text())['sha256'] == writer.text_hash(path.read_text())


def test_a_bad_request_writes_no_record(tmp_path):
    subprocess.run([sys.executable, str(SCRIPT), '--root', str(tmp_path), '--record', 'nope'], capture_output=True, text=True)
    assert not (tmp_path / 'articles').exists()


# ---------------- findings of the self-review ----------------
@pytest.mark.parametrize('quote,expected', [
    ('The plan costs $5.99 per month.', 'found'),
    ('23 million users signed up.', 'found'),
    ('3 million users signed up.', 'not-found'),
    ('The plan costs $5.', 'not-found'),
    ('Latency fell by 4', 'not-found'),
    ('Latency fell by 40', 'found'),
], ids=['full-price', 'full-number', 'longer-number-left', 'cut-price', 'cut-number-right', 'whole-number'])
def test_a_quote_never_matches_the_middle_of_a_longer_word_or_number(server, tmp_path, quote, expected):
    assert statuses(run(tmp_path, [(server + '/num', quote)])) == {'F1': expected}


@pytest.mark.parametrize('quote,expected', [
    ('A cache MUST ... store the response.', 'found-elided'),
    ('A cache MUST NOT store the response. ... Then it MUST revalidate.', 'not-found'),
], ids=['short-elision-is-flagged', 'pieces-far-apart'])
def test_pieces_of_an_elided_quote_must_sit_close_together(server, tmp_path, quote, expected):
    assert statuses(run(tmp_path, [(server + '/gap', quote)])) == {'F1': expected}


def test_a_page_over_the_size_cap_is_unreachable_not_a_miss(server, tmp_path):
    r = run(tmp_path, [(server + '/huge', 'plain plain plain')])
    assert statuses(r) == {'F1': 'unreachable'} and 'over 3 MB' in r.out


def test_a_body_that_trickles_in_still_ends_inside_the_budget_and_the_record_is_written(server, tmp_path):
    started = time.time()
    r = run(tmp_path, [(server + '/drip', QUOTE), (server + '/ok', QUOTE)], '--timeout', '1', '--budget', '1', '--record')
    assert statuses(r)['F1'] == 'unreachable' and time.time() - started < 6
    assert (tmp_path / 'articles' / 'demo' / '.quote-check.json').exists()


def test_a_loopback_address_is_refused_unless_a_test_allows_it(server, tmp_path):
    r = run(tmp_path, [(server + '/ok', QUOTE)], loopback=False)
    assert statuses(r) == {'F1': 'unreachable'} and 'not a public address' in r.out


@pytest.mark.parametrize('path,why', [('/to-ftp', 'not an http(s) URL'), ('/to-private', 'not a public address'),
                                      ('/to-metadata', 'not a public address')], ids=['ftp', 'private-range', 'metadata-address'])
def test_a_redirect_to_a_non_web_or_non_public_target_is_refused(server, tmp_path, path, why):
    r = run(tmp_path, [(server + path, QUOTE)])
    assert statuses(r) == {'F1': 'unreachable'} and why in r.out


def test_a_redirect_to_a_normal_page_is_followed(server, tmp_path):
    assert statuses(run(tmp_path, [(server + '/to-ok', QUOTE)])) == {'F1': 'found'}


def test_a_charset_declared_only_in_the_page_is_used(server, tmp_path):
    assert statuses(run(tmp_path, [(server + '/cp1252', 'It\u2019s \u201cstale\u201d now.')])) == {'F1': 'found'}


def test_a_head_that_is_never_closed_does_not_hide_the_body(server, tmp_path):
    assert statuses(run(tmp_path, [(server + '/nohead', QUOTE)])) == {'F1': 'found'}


def test_a_repeated_fact_id_keeps_its_worst_status_in_the_record(server, tmp_path):
    art = tmp_path / 'articles' / 'demo'
    art.mkdir(parents=True)
    row = '| F1 | c | {u} | P | 2026-01-01 | 2026-11-16 | {q} |\n'
    (art / 'research.md').write_text('## Fact bank\n\n| F# | claim | source URL | publisher | published | accessed | verbatim quote |\n|--|--|--|--|--|--|--|\n'
                                     + row.format(u=server + '/changed', q=QUOTE) + row.format(u=server + '/ok', q=QUOTE), encoding='utf-8')
    env = dict(os.environ, QUOTE_CHECK_ALLOW_LOOPBACK='1')
    subprocess.run([sys.executable, str(SCRIPT), '--root', str(tmp_path), '--record', 'demo'], capture_output=True, text=True, env=env)
    assert json.loads((art / '.quote-check.json').read_text())['rows'] == {'F1': 'not-found'}
