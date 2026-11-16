#!/usr/bin/env python3
"""Is each fact-bank quote on its source page, word for word? (ADR-015)

    python3 bin/quote-check.py [--record] [--root <workspace>] [--timeout SECONDS] [--budget SECONDS] <slug>

Fetches every source URL in `articles/<slug>/research.md` once, takes the page's visible text and looks for the quote in it. One line
per row: `F<n> found | not-found | unreachable | unreadable [detail]`.
  found        the quote is on the page (markup, whitespace, curly quotes and entities do not count as differences)
  found-elided the quote has an ellipsis and its pieces are on the page, close together and in order: what the ellipsis hid is not checked
  not-found    the page was read, it has real text, and the quote is not in it
  unreachable  no usable page: HTTP error, timeout, not HTML, over 3 MB, a non-public address, or the time budget ran out
  unreadable   the page has too little text to judge (a page that builds itself in the browser): no verdict on the quote
Exit 0 when no row is not-found, 1 when one is, 2 on a bad request. It sends a plain client name and never pretends to be a browser:
a blocked page stays unreachable. It refuses any address that is not public (loopback, private, link-local), also after a redirect,
because the URLs come from a file a model wrote from web content. Without `--record` it writes nothing (so it may be run any time); with `--record` (the research stage, last)
it writes `.quote-check.json` beside the dossier: the hash of research.md, every row's status and the printed lines, so a write-free gate
can read them and the guard can tell they are current. Stdlib only.
"""
import datetime
import ipaddress
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple

from lib import writer as w

MIN_WORDS = 200          # below this a page is "unreadable", not a miss (spec open question 2)
MAX_BYTES = 3_000_000
WORST = ['not-found', 'unreachable', 'unreadable', 'found-elided', 'found']
USER_AGENT = 'writer-plugin-quote-check/1'
SKIP = {'script', 'style', 'noscript', 'template', 'head', 'svg'}
# only these break text; an inline tag (a, em, code, sup, ...) sits inside a word or sentence, so it adds nothing
BLOCK = {'p', 'div', 'br', 'hr', 'li', 'ul', 'ol', 'dl', 'dt', 'dd', 'tr', 'td', 'th', 'table', 'thead', 'tbody', 'tfoot', 'caption',
         'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'section', 'article', 'aside', 'header', 'footer', 'nav', 'main', 'blockquote', 'pre',
         'figure', 'figcaption', 'form', 'fieldset', 'details', 'summary', 'option', 'address', 'body'}


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == 'body':
            self.skip = 0  # `</head>` is optional in HTML; the body starts here either way
        if tag in SKIP:
            self.skip += 1
        elif tag in BLOCK:
            self.parts.append(' ')

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIP and self.skip:
            self.skip -= 1
        elif tag in BLOCK:
            self.parts.append(' ')

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.parts.append(data)


def visible_text(html: str) -> str:
    parser = _Text()
    parser.feed(html)
    parser.close()
    return w.normalize_text(''.join(parser.parts))


def markdown_text(md: str) -> str:
    """The words of a markdown page: link and image syntax keeps its text, emphasis marks, code ticks and line-start markers go."""
    md = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', md)
    md = re.sub(r'(?m)^[ \t]*(?:#{1,6}|>|[-*+]|\d+[.)])[ \t]+', '', md)
    return w.normalize_text(re.sub(r'\*\*|__|`', '', md))


def refuse(url: str) -> Optional[str]:
    """Why this URL may not be fetched, or None. Only http(s) to a public address; `QUOTE_CHECK_ALLOW_LOOPBACK=1` is the test seam."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme.lower() not in ('http', 'https') or not parts.hostname:
        return 'not an http(s) URL'
    port = parts.port or (443 if parts.scheme.lower() == 'https' else 80)
    for info in socket.getaddrinfo(parts.hostname, port, proto=socket.IPPROTO_TCP):
        ip = ipaddress.ip_address(info[4][0].split('%')[0])
        if ip.is_loopback and os.environ.get('QUOTE_CHECK_ALLOW_LOOPBACK') == '1':
            continue
        if not ip.is_global:
            return f'not a public address ({ip})'
    return None


class _PublicRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        why = refuse(urllib.parse.urljoin(req.full_url, newurl))
        if why:
            raise urllib.error.URLError(why)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _charset(header_charset: Optional[str], head: bytes) -> str:
    if header_charset:
        return header_charset
    m = re.search(rb'<meta[^>]+charset\s*=\s*["\']?([\w.:-]+)', head[:2048], re.I)
    return m.group(1).decode('ascii', 'replace') if m else 'utf-8'


def fetch(url: str, timeout: float, deadline: float) -> Tuple[Optional[str], str]:
    """(page text, '') or (None, why it could not be read). The body is read in pieces so the deadline holds even when it trickles in."""
    try:
        why = refuse(url)
        if why:
            return None, why
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'text/html,application/xhtml+xml,text/plain'})
        with urllib.request.build_opener(_PublicRedirects).open(req, timeout=timeout) as resp:
            kind = (resp.headers.get_content_type() or '').lower()
            if kind not in ('text/html', 'application/xhtml+xml', 'text/plain', 'text/markdown'):
                return None, f'not a web page ({kind})'
            chunks: List[bytes] = []
            size = 0
            while True:
                if time.monotonic() > deadline:
                    return None, 'time budget used up'
                piece = resp.read1(65536)
                if not piece:
                    break
                size += len(piece)
                if size > MAX_BYTES:
                    return None, 'page over 3 MB'
                chunks.append(piece)
            header_charset = resp.headers.get_content_charset()
    except urllib.error.HTTPError as exc:
        return None, f'HTTP {exc.code}'
    except Exception as exc:  # timeout, DNS failure, TLS error, a refused redirect: all mean "no page", never a crash
        return None, f'{type(exc).__name__}: {getattr(exc, "reason", exc)}'[:90]
    raw = b''.join(chunks)
    try:
        text = raw.decode(_charset(header_charset, raw), errors='replace')
    except LookupError:
        text = raw.decode('utf-8', errors='replace')
    if kind in ('text/html', 'application/xhtml+xml'):
        return visible_text(text), ''
    return (markdown_text(text) if kind == 'text/markdown' else w.normalize_text(text)), ''


def check(rows: List[Dict[str, str]], timeout: float, budget: float) -> List[Tuple[str, str, str]]:
    deadline = time.monotonic() + budget
    pages: Dict[str, Tuple[Optional[str], str]] = {}
    out = []
    for row in rows:
        url = row['url']
        if url not in pages:
            left = deadline - time.monotonic()
            pages[url] = (None, 'time budget used up') if left <= 0 else fetch(url, min(timeout, left), deadline)
        text, why = pages[url]
        if text is None:
            out.append((row['id'], 'unreachable', why))
        elif len(text.split()) < MIN_WORDS:
            out.append((row['id'], 'unreadable', f'{len(text.split())} words of text'))
        else:
            out.append((row['id'], w.quote_status(text, row['quote']), ''))
    return out


def record(path: str, text: str, results: List[Tuple[str, str, str]], lines: List[str]) -> None:
    rows: Dict[str, str] = {}
    for fid, status, _ in results:  # a repeated ID keeps its worst status, so a miss cannot hide behind a later hit
        if fid not in rows or WORST.index(status) < WORST.index(rows[fid]):
            rows[fid] = status
    rec = {'file': os.path.basename(path), 'sha256': w.text_hash(text), 'rows': rows, 'lines': lines,
           'at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}
    with open(os.path.join(os.path.dirname(os.path.abspath(path)), '.quote-check.json'), 'w', encoding='utf-8') as fh:
        json.dump(rec, fh)


def main(argv: List[str]) -> int:
    args, root, timeout, budget, slugs, do_record = list(argv), None, 10.0, 90.0, [], False
    try:
        while args:
            a = args.pop(0)
            if a == '--record':
                do_record = True
            elif a == '--root' and args:
                root = args.pop(0)
            elif a == '--timeout' and args:
                timeout = float(args.pop(0))
            elif a == '--budget' and args:
                budget = float(args.pop(0))
            else:
                slugs.append(a)
    except ValueError:
        slugs = []
    if len(slugs) != 1:
        sys.stderr.write('usage: quote-check.py [--record] [--root <workspace>] [--timeout SECONDS] [--budget SECONDS] <slug>\n')
        return 2
    slug = slugs[0]
    if not w.SLUG.match(slug):
        sys.stderr.write(f'"{slug}" is not an article slug (one folder name under articles/)\n')
        return 2
    root = root or os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    path = os.path.join(w.article_dir(root, slug), 'research.md')
    text = w.read_text(path) if os.path.isfile(path) else None
    if text is None:
        sys.stderr.write(f'articles/{slug}/research.md does not exist under {root}\n')
        return 2
    rows = w.fact_rows(text)
    results = check(rows, timeout, budget) if rows else []
    lines = [f'{fid} {status}' + (f' {why}' if why else '') for fid, status, why in results]
    print('\n'.join(lines) if lines else 'quote-check: no fact rows in the Fact bank')
    if do_record:
        record(path, text, results, lines)
    if not rows:
        return 0
    counts = {s: sum(1 for _, st, _ in results if st == s) for s in ('found', 'found-elided', 'not-found', 'unreachable', 'unreadable')}
    print('quote-check: ' + ', '.join(f'{n} {s}' for s, n in counts.items()))
    return 1 if counts['not-found'] else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
