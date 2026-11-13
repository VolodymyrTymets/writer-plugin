#!/usr/bin/env python3
"""Mechanical prose checks for a draft or a final (stdlib only). Not a hook: run it as a command.

    python3 prose-lint.py [--record] [--brief PATH] [--style PATH] articles/<slug>/final.md

Prints one finding per line, `RULE path:line message`, and `NOTE ...` for a check it skipped because an input is missing.
Exits 0 with no findings and 1 with any. Without `--record` it writes nothing, so a gate that calls it stays write-free (FLOW-4);
with `--record` (the edit stage) it writes `.prose-lint.json` beside the file (the printed findings too, so a write-free gate can read them): `verify-final` and the
guard look at it. Only this script writes that file (ADR-010).

Checks (rule IDs are the constitution's): STR-4 headings (any file); STR-6 length against the brief's target (draft, final);
FACT-1 a number with no [F#] in its sentence (draft, final; a heuristic); and for a final only: SEO-1/2/3 from the front matter
and the brief's keyword, VOI-2/3 from the style guide, FLOW-6 a marker left in the text (loose pattern).
"""
import datetime
import os
import re
import sys
from typing import List, Optional, Tuple

from lib import writer as w

FENCE = re.compile(r'^\s*(```|~~~)')
HEADING = re.compile(r'^(#{1,6})\s+(\S.*)$')
FACT_REF = re.compile(r'\[F\d+\]')
URL = re.compile(r'https?://\S+')
LIST_PREFIX = re.compile(r'^\s*(?:[-*+]|\d+[.)])\s+')
MARKER_LOOSE = re.compile(r'<Can.t be verified')
WORD = re.compile(r"\w[\w'’-]*")


def length_bounds(brief_text: str) -> Optional[Tuple[int, int]]:
    """The brief's target length as (min, max) words: a range uses its bounds, a single number is plus or minus 10%."""
    m = re.search(r'\*\*Target length:\*\*\s*(.+)', brief_text)
    value = m.group(1) if m else ''
    nums = [int(n.replace(',', '')) for n in re.findall(r'\d[\d,]*', value) if n.replace(',', '')]
    if not nums:
        return None
    if len(nums) >= 2 and nums[1] > nums[0]:
        return nums[0], nums[1]
    return round(nums[0] * 0.9), round(nums[0] * 1.1)


def split_front_matter(text: str) -> Tuple[dict, str, int]:
    """(front matter keys, body, number of lines the front matter took)."""
    lines = text.split('\n')
    if not lines or lines[0].strip() != '---':
        return {}, text, 0
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            keys = {}
            for line in lines[1:i]:
                k, sep, v = line.partition(':')
                if sep:
                    keys[k.strip()] = v.strip()
            return keys, '\n'.join(lines[i + 1:]), i + 1
    return {}, text, 0


def body_lines(body: str) -> List[Tuple[int, str, bool]]:
    """(1-based line in the body, text, inside a code fence) for every line."""
    out, fenced = [], False
    for n, line in enumerate(body.split('\n'), 1):
        if FENCE.match(line):
            fenced = not fenced
            out.append((n, line, True))
        else:
            out.append((n, line, fenced))
    return out


def prose_words(body: str) -> List[str]:
    words = []
    for _, line, fenced in body_lines(body):
        if fenced or FENCE.match(line):
            continue
        words.extend(WORD.findall(FACT_REF.sub('', URL.sub('', line))))
    return words


def find_style(path: str) -> Optional[str]:
    d = os.path.dirname(os.path.abspath(path))
    while True:
        cand = os.path.join(d, '.claude', 'rules', 'style.md')
        if os.path.exists(cand):
            return cand
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def style_list(style_text: str, label: str) -> Optional[List[str]]:
    m = re.search(r'\*\*' + label + r':\*\*\s*(.+)', style_text)
    if not m or '{{' in m.group(1):
        return None
    return [p.strip() for p in m.group(1).split(',') if p.strip()]


def read(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    try:
        with open(path, encoding='utf-8') as fh:
            return fh.read()
    except OSError:
        return None


def lint(path: str, brief_path: Optional[str], style_path: Optional[str]) -> Tuple[List[str], List[str]]:
    text = read(path)
    if text is None:
        return [], [f'cannot read {path}']
    name = os.path.basename(path)
    kind = name[:-3] if name in ('draft.md', 'final.md') else 'other'
    keys, body, fm_lines = split_front_matter(text)
    found: List[str] = []
    notes: List[str] = []

    def add(rule: str, line: int, message: str) -> None:
        found.append(f'{rule} {path}:{line + fm_lines} {message}')

    # STR-4: one H1 and no skipped level, in any article file
    h1, last = 0, 0
    for n, line, fenced in body_lines(body):
        m = None if fenced else HEADING.match(line)
        if not m:
            continue
        level = len(m.group(1))
        h1 += level == 1
        if last and level > last + 1:
            add('STR-4', n, f'heading level jumps from H{last} to H{level}: "{m.group(2)[:50]}"')
        last = level
    if h1 != 1:
        add('STR-4', 1, f'expected one H1, found {h1}')

    if kind in ('draft', 'final'):
        brief_text = read(brief_path or os.path.join(os.path.dirname(os.path.abspath(path)), 'brief.md'))
        bounds = length_bounds(brief_text) if brief_text else None
        if bounds:
            n_words = len(prose_words(body))
            if not bounds[0] <= n_words <= bounds[1]:
                add('STR-6', 1, f'{n_words} words, but the brief\'s target is {bounds[0]} to {bounds[1]}')
        else:
            notes.append('STR-6 skipped: no brief.md with a Target length')
        # FACT-1 (heuristic): a number in a sentence that has no [F#]
        para: List[Tuple[int, str]] = []

        def flush() -> None:
            if not para:
                return
            joined = ' '.join(t for _, t in para)
            for sentence in re.split(r'(?<=[.!?])\s+', joined):
                if FACT_REF.search(sentence):
                    continue
                if re.search(r'\d', URL.sub('', sentence)):
                    add('FACT-1', para[0][0], f'a number with no [F#] in its sentence: "{sentence.strip()[:70]}"')
            para.clear()

        for n, line, fenced in body_lines(body):
            if fenced or HEADING.match(line) or line.lstrip().startswith('|') or not line.strip():
                flush()
                continue
            para.append((n, LIST_PREFIX.sub('', line).strip()))
        flush()

    if kind == 'final':
        title, meta = keys.get('title'), keys.get('meta_description')
        if not title:
            add('SEO-2', 0, 'no title in the front matter')
        elif len(title) > 60:
            add('SEO-2', 0, f'title is {len(title)} characters, the limit is 60')
        if not meta:
            add('SEO-3', 0, 'no meta_description in the front matter')
        elif not 120 <= len(meta) <= 155:
            add('SEO-3', 0, f'meta description is {len(meta)} characters, it must be 120 to 155')
        brief_text = read(brief_path or os.path.join(os.path.dirname(os.path.abspath(path)), 'brief.md'))
        km = re.search(r'\*\*Primary keyword:\*\*\s*(.+)', brief_text or '')
        keyword = km.group(1).strip().lower() if km else None
        if keyword and '{{' not in keyword:
            if title and keyword not in title.lower():
                add('SEO-1', 0, f'the primary keyword "{keyword}" is not in the title')
            first100 = ' '.join(w_.lower() for w_ in [
                x for _, line, fenced in body_lines(body) if not fenced and not HEADING.match(line)
                for x in WORD.findall(line)][:100])
            if keyword not in first100:
                add('SEO-1', 1, f'the primary keyword "{keyword}" is not in the first 100 words')
            if not any(keyword in m.group(2).lower() for _, l_, f_ in body_lines(body)
                       for m in [HEADING.match(l_)] if m and len(m.group(1)) == 2 and not f_):
                add('SEO-1', 1, f'the primary keyword "{keyword}" is in no H2')
        else:
            notes.append('SEO-1 skipped: no Primary keyword in brief.md')
        style_text = read(style_path or find_style(path))
        for rule, label, what in (('VOI-2', 'Phrases', 'banned phrase'), ('VOI-3', 'Tells', 'AI tell')):
            items = style_list(style_text, label) if style_text else None
            if items is None:
                notes.append(f'{rule} skipped: no filled style guide (.claude/rules/style.md)')
                continue
            for n, line, fenced in body_lines(body):
                if fenced:
                    continue
                for phrase in items:
                    if re.search(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', line, re.I):
                        add(rule, n, f'{what} "{phrase}"')
        for i, line in enumerate(text.split('\n'), 1):
            if MARKER_LOOSE.search(line):
                found.append(f'FLOW-6 {path}:{i} an unverified-claim marker is still in the final')
    return found, notes


def record(path: str, found: List[str]) -> None:
    text = read(path) or ''
    rec = {'file': os.path.basename(path), 'sha256': w.text_hash(text), 'findings': len(found), 'lines': found,
           'at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}
    import json
    with open(os.path.join(os.path.dirname(os.path.abspath(path)), '.prose-lint.json'), 'w', encoding='utf-8') as fh:
        json.dump(rec, fh)


def main(argv: List[str]) -> int:
    args, brief, style, do_record, files = list(argv), None, None, False, []
    while args:
        a = args.pop(0)
        if a == '--record':
            do_record = True
        elif a == '--brief' and args:
            brief = args.pop(0)
        elif a == '--style' and args:
            style = args.pop(0)
        else:
            files.append(a)
    if len(files) != 1:
        sys.stderr.write('usage: prose-lint.py [--record] [--brief PATH] [--style PATH] FILE\n')
        return 2
    found, notes = lint(files[0], brief, style)
    for n in notes:
        print(f'NOTE {n}')
    for f in found:
        print(f)
    if do_record:
        record(files[0], found)
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
