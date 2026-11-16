"""Shared helpers for the writer-plugin hooks. Python 3.9, standard library only (rule C2).

The contracts here are written down in docs/decisions/ADR-004 (verdict file), ADR-007 (a verdict covers its artifact) and
ADR-009 (the sidecar and the guard rules). A hook never raises into the session: an unexpected error allows the action and
says so on stderr, because a false block costs a writer's turn (see `fail_open`).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import sys
import tempfile
import unicodedata
from typing import Callable, Dict, List, Optional, Tuple

for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass

# ADR-004: line 1 of a verdict. A PASS carries no blockers and a BLOCK at least one, so a contradictory count can never read as a PASS.
VERDICT_LINE = re.compile(
    r'^## (G0 brief|G1 research|G2 outline|G3 draft|G4 final) gate: '
    r'(PASS \(0 blocking|BLOCK \([1-9]\d* blocking), \d+ advisory\)$')
STAGES = ['brief', 'research', 'outline', 'draft', 'final']
GATE_ID = {'brief': 'G0', 'research': 'G1', 'outline': 'G2', 'draft': 'G3', 'final': 'G4'}
VERDICT_NAME = re.compile(r'^(G[0-4])-(brief|research|outline|draft|final)\.r(\d+)\.md$')
# the human writes these after a PASS by design (ADR-007), so they are not part of what a verdict covers
APPROVAL_LINE = re.compile(r'^[ \t]*(?:Approved-by|Signed-off-by):.*(?:\n|$)', re.M)
# `[^\S\n]*` on purpose: `\s*` would swallow the newline and read the next line as the signature
APPROVED = re.compile(r'^[^\S\n]*Approved-by:[^\S\n]*\S+', re.M)
SIGNED = re.compile(r'^[^\S\n]*Signed-off-by:[^\S\n]*\S+', re.M)
_SIGN_LINE = re.compile(r'^[^\S\n]*Signed-off-by:(.*)$')
_FENCE = re.compile(r'^\s*(```|~~~)')


# ---------------- payload and blocking ----------------
def read_payload() -> dict:
    try:
        raw = sys.stdin.read().strip()
        data = json.loads(raw) if raw else {}
        return data if isinstance(data, dict) else {}
    except (ValueError, OSError):
        return {}


def project_dir(payload: Optional[dict] = None) -> str:
    return os.environ.get('CLAUDE_PROJECT_DIR') or (payload or {}).get('cwd') or os.getcwd()


def block(rule: str, message: str, alternative: Optional[str] = None) -> None:
    """Block the action: exit 2 and the stderr text is what the agent sees (verified with a probe, ADR-009)."""
    lines = [f'[writer-plugin] BLOCKED by rule {rule}: {message}']
    if alternative:
        lines.append(f'Do this instead: {alternative}')
    sys.stderr.write('\n'.join(lines) + '\n')
    sys.stderr.flush()
    sys.exit(2)


def fail_open(main: Callable[[], None], name: str) -> None:
    """Run a hook body; an unexpected error allows the action instead of blocking a writer for a bug of ours."""
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:   # deliberate (see the docstring): the error is reported on stderr, not swallowed
        sys.stderr.write(f'[writer-plugin] {name} hit an unexpected error and allowed the action: {type(exc).__name__}: {exc}\n')
        sys.exit(0)


def rel_path(root: str, path: str, cwd: Optional[str] = None) -> Optional[str]:
    """`path` relative to the workspace root, with forward slashes, or None when it lies outside it."""
    if not path:
        return None
    full = path if os.path.isabs(path) else os.path.join(cwd or root, path)
    full = os.path.normpath(full)
    base = os.path.normpath(root)
    if full != base and not full.startswith(base + os.sep):
        return None
    return os.path.relpath(full, base).replace(os.sep, '/')


# ---------------- articles, gates, verdicts ----------------
def gate_name(stage: str) -> str:
    return f'{GATE_ID[stage]}-{stage}'


def previous_stage(stage: str) -> Optional[str]:
    i = STAGES.index(stage)
    return STAGES[i - 1] if i else None


def article_dir(root: str, slug: str) -> str:
    return os.path.join(root, 'articles', slug)


def first_line(path: str) -> str:
    try:
        with open(path, encoding='utf-8') as fh:
            return fh.readline().rstrip('\n').rstrip('\r')
    except OSError:
        return ''


def is_pass(path: str) -> bool:
    m = VERDICT_LINE.match(first_line(path))
    return bool(m) and m.group(2).startswith('PASS')


def is_block(path: str) -> bool:
    m = VERDICT_LINE.match(first_line(path))
    return bool(m) and m.group(2).startswith('BLOCK')


def verdicts(root: str, slug: str, stage: str, archived: bool = False) -> List[Tuple[int, str]]:
    """(k, file name) of the verdicts of one gate, ordered by k. Archived ones live in gates/archive/."""
    d = os.path.join(article_dir(root, slug), 'gates', 'archive' if archived else '')
    out = []
    try:
        names = os.listdir(d)
    except OSError:
        return out
    for n in names:
        m = VERDICT_NAME.match(n)
        if m and m.group(2) == stage and m.group(1) == GATE_ID[stage]:
            out.append((int(m.group(3)), n))
    return sorted(out)


def latest(root: str, slug: str, stage: str) -> Optional[str]:
    v = verdicts(root, slug, stage)
    return v[-1][1] if v else None


def next_k(root: str, slug: str, stage: str) -> int:
    ks = [k for k, _ in verdicts(root, slug, stage)] + [k for k, _ in verdicts(root, slug, stage, archived=True)]
    return max(ks) + 1 if ks else 1


def block_count(root: str, slug: str, stage: str) -> int:
    d = os.path.join(article_dir(root, slug), 'gates')
    return sum(1 for _, n in verdicts(root, slug, stage) if is_block(os.path.join(d, n)))


# ---------------- what a verdict covers (ADR-007, ADR-009) ----------------
def strip_approval(text: str) -> str:
    text = APPROVAL_LINE.sub('', text.replace('\r\n', '\n'))
    return '\n'.join(line.rstrip() for line in text.split('\n')).strip()


def text_hash(text: str) -> str:
    return hashlib.sha256(strip_approval(text).encode('utf-8')).hexdigest()


def artifact_hash(root: str, slug: str, stage: str) -> Optional[str]:
    try:
        with open(os.path.join(article_dir(root, slug), f'{stage}.md'), encoding='utf-8') as fh:
            return text_hash(fh.read())
    except OSError:
        return None


def sidecar_path(root: str, slug: str, verdict_name: str) -> str:
    return os.path.join(article_dir(root, slug), 'gates', verdict_name[:-3] + '.json')


def read_sidecar(root: str, slug: str, verdict_name: str) -> Optional[Dict[str, object]]:
    try:
        with open(sidecar_path(root, slug, verdict_name), encoding='utf-8') as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def write_sidecar(root: str, slug: str, verdict_name: str) -> None:
    """Record what the verdict judged: the artifact's hash now, and the latest verdict of the gate before it."""
    m = VERDICT_NAME.match(verdict_name)
    if not m:
        return
    stage = m.group(2)
    up = previous_stage(stage)
    data = {'artifact_sha256': artifact_hash(root, slug, stage), 'upstream': latest(root, slug, up) if up else None}
    with open(sidecar_path(root, slug, verdict_name), 'w', encoding='utf-8') as fh:
        json.dump(data, fh)


def check_gate(root: str, slug: str, stage: str, text: Optional[str] = None) -> Optional[str]:
    """None when the gate of `stage` stands (its latest verdict is a PASS on what is on disk, all the way up), else why not.

    `text` replaces the on-disk artifact for this stage only: the sign-off guard asks about the file a write is about to produce."""
    gate = gate_name(stage)
    name = latest(root, slug, stage)
    if not name:
        return f'there is no {gate} verdict in articles/{slug}/gates/'
    path = os.path.join(article_dir(root, slug), 'gates', name)
    if not is_pass(path):
        return f'the latest {gate} verdict, {name}, is not a valid PASS (line 1: "{first_line(path)[:80]}")'
    up = previous_stage(stage)
    recorded = [read_sidecar(root, slug, n) for _, n in verdicts(root, slug, stage)]
    legacy = not any(recorded)           # a gate none of whose verdicts has a sidecar predates the hooks: its links are skipped
    if not legacy:
        sc = read_sidecar(root, slug, name)
        if sc is None:
            return (f'{name} has no sidecar although an earlier {gate} verdict does, so what it judged is unknown: '
                    f're-gate the {stage} and save the verdict again')
        now = text_hash(text) if text is not None else artifact_hash(root, slug, stage)
        if now is None:
            return f'{stage}.md is missing'
        if sc.get('artifact_sha256') != now:
            return f'{stage}.md changed since {name} judged it (the approval line does not count)'
        if up and sc.get('upstream') != latest(root, slug, up):
            return (f'{name} is stale: it relied on {sc.get("upstream")} but the latest {gate_name(up)} verdict is '
                    f'{latest(root, slug, up)}')
    return check_gate(root, slug, up) if up else None


def is_signed(text: str) -> bool:
    """True when the sign-off line, the last `Signed-off-by:` outside a code fence, has a value. A body line that quotes a
    commit trailer inside a fence (an article about git) is not the sign-off."""
    fenced, last = False, None
    for line in text.replace('\r\n', '\n').split('\n'):
        if _FENCE.match(line):
            fenced = not fenced
        elif not fenced:
            m = _SIGN_LINE.match(line)
            if m:
                last = m.group(1).strip()
    return bool(last)


def lint_record(root: str, slug: str) -> Optional[Dict[str, object]]:
    """The run recorded by `prose-lint.py --record` beside the final, or None when absent or unreadable."""
    try:
        with open(os.path.join(article_dir(root, slug), '.prose-lint.json'), encoding='utf-8') as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def quote_record(root: str, slug: str) -> Optional[Dict[str, object]]:
    """The run recorded by `quote-check.py --record` beside the research dossier, or None when absent or unreadable (ADR-015)."""
    try:
        with open(os.path.join(article_dir(root, slug), '.quote-check.json'), encoding='utf-8') as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def resulting_text(root: str, rel: str, tool: str, tool_input: dict) -> Optional[str]:
    """The content `rel` will have after a Write or Edit, or None when it cannot be worked out (a Bash write, a missing file,
    an old_string that is not there). The caller then allows the action: a false block costs a writer's turn."""
    if tool == 'Write':
        content = tool_input.get('content')
        return content if isinstance(content, str) else None
    if tool != 'Edit':
        return None
    old, new = tool_input.get('old_string'), tool_input.get('new_string')
    try:
        with open(os.path.join(root, rel), encoding='utf-8') as fh:
            current = fh.read()
    except OSError:
        return None
    if not isinstance(old, str) or not isinstance(new, str) or not old or old not in current:
        return None
    return current.replace(old, new) if tool_input.get('replace_all') else current.replace(old, new, 1)


# ---------------- which paths the guard cares about ----------------
ARTICLE_PATH = re.compile(r'^articles/([^/]+)/(.+)$')


def split_article(rel: str) -> Optional[Tuple[str, str]]:
    m = ARTICLE_PATH.match(rel or '')
    return (m.group(1), m.group(2)) if m else None


_HEREDOC = re.compile(r'<<-?\s*[\'"]?([A-Za-z_]\w*)[\'"]?')
_SEPARATORS = re.compile(r'&&|\|\||;|(?<!\|)\|(?!\|)')
_REDIRECT = re.compile(r'(?:^|[\s(])\d*>>?\s*([^\s<>&|;()]+)')
_WRITERS = {'tee', 'cp', 'mv', 'rm', 'install', 'ln', 'touch', 'truncate'}


def _without_heredoc_bodies(command: str) -> List[str]:
    lines, out, end = command.split('\n'), [], None
    for line in lines:
        if end is not None:
            if line.strip() == end:
                end = None
            continue
        out.append(line)
        m = _HEREDOC.search(line)
        if m:
            end = m.group(1)
    return out


def bash_targets(command: str) -> List[Tuple[str, str]]:
    """Paths a shell command line writes, moves, copies or removes, as (kind, path); a best-effort parse (ADR-009).

    Reads (`cat`, `ls`, `grep`, `git status`) produce nothing. A heredoc body is skipped so text with `>` in it is not read as
    a redirect. What it cannot read (`python -c`, command substitution, variables) it does not report: that is a stated gap.
    """
    targets: List[Tuple[str, str]] = []
    for line in _without_heredoc_bodies(command):
        for seg in _SEPARATORS.split(line):
            seg = seg.strip()
            if not seg:
                continue
            unquoted = re.sub(r'"[^"]*"|\'[^\']*\'', '""', seg)   # a `>` inside quotes is text, not a redirect
            for m in _REDIRECT.finditer(unquoted):
                p = m.group(1)
                if p not in ('/dev/null',) and not p.startswith('&'):
                    targets.append(('write', p))
            try:
                tokens = shlex.split(seg)
            except ValueError:
                tokens = seg.split()
            tokens = [t for t in tokens if not re.match(r'^\d*>>?', t)]
            if not tokens:
                continue
            prog = os.path.basename(tokens[0])
            args = [t for t in tokens[1:] if not t.startswith('-')]
            if prog in _WRITERS:
                targets.extend(('write', a) for a in args)
            elif prog in ('sed', 'perl') and any(t.startswith('-i') for t in tokens[1:]):
                targets.extend(('write', a) for a in args[1:])
    return targets


# ---------------- session state (a temp file keyed by session id, never inside the workspace) ----------------
MARKER_LOOSE = re.compile(r'<Can.t be verified')


def state_path(session_id: str) -> str:
    base = os.environ.get('WRITER_PLUGIN_STATE_DIR') or os.path.join(tempfile.gettempdir(), 'writer-plugin')
    return os.path.join(base, re.sub(r'[^\w.-]', '_', str(session_id or 'unknown')) + '.json')


def load_state(session_id: str) -> dict:
    try:
        with open(state_path(session_id), encoding='utf-8') as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(session_id: str, data: dict) -> None:
    path = state_path(session_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh)


def article_slugs(root: str) -> List[str]:
    d = os.path.join(root, 'articles')
    try:
        return sorted(n for n in os.listdir(d) if os.path.isdir(os.path.join(d, n)) and not n.startswith('.'))
    except OSError:
        return []


def read_text(path: str) -> str:
    try:
        with open(path, encoding='utf-8') as fh:
            return fh.read()
    except OSError:
        return ''


# The whole marker as the guard sees it: built from the guard's own loose pattern, never a second one (ADR-011).
MARKER_TEXT = re.compile(MARKER_LOOSE.pattern + r'[^>\n]*>?')
# A slug is one visible folder name under articles/: no separator, no leading dot (so no `..`), no line break. Anything else could
# point the status script outside articles/. Spaces are allowed: the guard treats any such folder as an article too.
SLUG = re.compile(r'(?!\.)[^/\\\x00\r\n]+\Z')
STATE_KEYS = ('slug', 'stage', 'next', 'reason', 'markers', 'stale')


def unknown_state(slug: str, reason: str) -> Dict[str, object]:
    return {'slug': slug, 'stage': None, 'next': 'unknown', 'reason': reason, 'markers': [], 'stale': False,
            'summary': f'unknown: {reason}', 'stale_reason': None}


def article_state(root: str, slug: str) -> Dict[str, object]:
    """Where an article is and the one next step, read from the files and the verdicts (ADR-011).

    `next` is a stage to run (`brief` .. `final`), `approve`, `sign-off`, `stopped`, `stale`, `done` or `unknown`. First match
    wins: unknown, then stopped (a gate with two BLOCKs, the guard's FLOW-3 rule whatever its latest verdict), then stale (a
    verdict no longer covers what is on disk), then the walk down the chain. `summary` and `stale_reason` feed the briefing
    line; the orchestrator reads the rest."""
    if not SLUG.match(slug or ''):  # the pattern ends in \Z, so match() is a full match
        return unknown_state(slug, f'"{slug}" is not an article slug (one folder name under articles/)')
    articles = os.path.join(root, 'articles')
    if os.path.exists(articles) and not os.path.isdir(articles):
        return unknown_state(slug, f'{articles} is not a folder, so the workspace cannot be read')
    art = article_dir(root, slug)
    stage, nxt, summary, last_pass, reason_override = None, None, None, None, None
    for s in STAGES:
        gate = gate_name(s)
        stage = s
        if not os.path.exists(os.path.join(art, f'{s}.md')):
            nxt = s
            summary = 'no brief.md yet: start with the brief stage' if s == 'brief' else f'{last_pass} passed; next: the {s} stage'
            if s == 'brief':        # a wrong root reads as a new article: name where we looked, so the orchestrator can tell
                reason_override = f'no articles/{slug}/brief.md under {root}: start with the brief stage'
            break
        name = latest(root, slug, s)
        if not name:
            nxt, summary = s, f'{s}.md written, {gate} not run'
            break
        if not is_pass(os.path.join(art, 'gates', name)):
            nxt, summary = s, f'{gate} BLOCK ({name}): the {s} stage fixes it and reruns'
            break
        last_pass = s
        if s == 'outline' and not APPROVED.search(read_text(os.path.join(art, 'outline.md'))):
            nxt, summary = 'approve', "outline passed G2, waiting for a human's Approved-by"
            break
        if s == 'final':
            if is_signed(read_text(os.path.join(art, 'final.md'))):
                nxt, summary = 'done', 'final passed G4 and is signed off'
            else:
                nxt, summary = 'sign-off', "final passed G4, waiting for a human's Signed-off-by"
    stale_reason = check_gate(root, slug, last_pass) if last_pass else None
    # Markers of the artifact the article is at, so a final left over from an earlier run cannot speak for a rebuilt outline.
    upto = STAGES.index(stage) if stage in ('draft', 'final') else STAGES.index('outline')
    marked = next((f'{s}.md' for s in reversed(STAGES[STAGES.index('outline'):upto + 1])
                   if os.path.exists(os.path.join(art, f'{s}.md'))), 'outline.md')
    markers = MARKER_TEXT.findall(read_text(os.path.join(art, marked)))
    reason = reason_override or summary
    stopped = next((s for s in STAGES if block_count(root, slug, s) >= 2), None)
    if stopped:
        gate = gate_name(stopped)
        blocks = [n for _, n in verdicts(root, slug, stopped) if is_block(os.path.join(art, 'gates', n))]
        stage, nxt = stopped, 'stopped'
        summary = f'{gate} STOPPED (FLOW-3): two BLOCK verdicts, a human archives them to resume'
        reason = (f'{gate} STOPPED (FLOW-3): {", ".join(blocks)} are BLOCK verdicts. A human resumes the article by moving every '
                  f'{gate}.r*.md verdict, PASS ones too, into articles/{slug}/gates/archive/')
    elif stale_reason:
        nxt, reason = 'stale', stale_reason
    return {'slug': slug, 'stage': stage, 'next': nxt, 'reason': reason, 'markers': markers, 'stale': nxt == 'stale',
            'summary': summary, 'stale_reason': stale_reason}


def describe_article(root: str, slug: str) -> str:
    """One line: where an article is and what it waits for. Built on article_state, so the session briefing and the
    orchestrator can never disagree."""
    s = article_state(root, slug)
    parts = [s['summary']]
    if s['stale_reason']:
        parts.append(f'STALE: {s["stale_reason"]}'[:130])
    n = len(s['markers'])
    if n:
        parts.append(f'{n} marker{"s" if n != 1 else ""} to resolve')
    return ' · '.join(parts)


# ---------------- Doc copies (Phase 7b, ADR-012) ----------------
# A fact tag as the draft stage writes it: `[F7]` or `[F7, F9]`, with the one space before it, so "claim [F7]." becomes "claim.".
# one definition of a fact tag, `[F7]` or a list `[F7, F9]`, for the Doc copy and for the lint
FACT_REF = re.compile(r'\[F\d+(?:[ \t]*,[ \t]*F\d+)*\]')
FACT_TAG = re.compile(r'[ \t]?' + FACT_REF.pattern)
_REV_IN_TITLE = re.compile(r' · r\d+')


def strip_fact_ids(text: str) -> str:
    """The text a reviewer sees: fact tags removed outside code fences, everything else unchanged."""
    out, fenced = [], False
    for line in text.split('\n'):
        if _FENCE.match(line):
            fenced = not fenced
            out.append(line)
        else:
            out.append(line if fenced else FACT_TAG.sub('', line))
    return '\n'.join(out)


_FRONT_MATTER = re.compile(r'\A---\n(.*?)\n---\n', re.S)


_APPROVAL_LINE_ANY = re.compile(r'^[ \t]*(Approved-by|Signed-off-by):.*$')


def approval_key(stage: Optional[str]) -> str:
    """The human line a stage closes with: the final's is a sign-off (FLOW-6), every other artifact's an approval (FLOW-2)."""
    return 'Signed-off-by' if stage == 'final' else 'Approved-by'


def doc_note(key: str) -> str:
    # Plain words, no backticks or colon after the label: Google drops backticks and the read-back keeps this line apart from the label (R0).
    return f'To approve, write your name after the {key} label below, then run writer-plugin:sync.'


def _open_approval(text: str, stage: Optional[str], keep_signoff: bool) -> str:
    """A Doc copy is always unapproved (FT-6, ADR-016): each approval line is emptied and given the instruction, in its own paragraph,
    and a guidance HTML comment directly above it is dropped (Google drops it anyway). An artifact with no such line gets the block at
    its end. The one exception is the publish-ready final, which keeps its signed line and gets no instruction."""
    out: List[str] = []
    fenced = found = False
    lines = text.split('\n')
    for n, line in enumerate(lines):
        if _FENCE.match(line):
            fenced = not fenced
        m = None if fenced else _APPROVAL_LINE_ANY.match(line)
        if not m:
            out.append(line)
            continue
        found = True
        if keep_signoff and m.group(1) == 'Signed-off-by':
            out.append(line)
            continue
        if out and out[-1].strip().endswith('-->'):  # the note a template puts straight above the line
            k = len(out) - 1
            while k >= 0 and '<!--' not in out[k]:
                k -= 1
            if k >= 0 and all(o.strip() for o in out[k:]):
                del out[k:]
        if out and out[-1].strip():
            out.append('')
        out += [doc_note(m.group(1)), '', f'{m.group(1)}:']
        if n + 1 < len(lines) and lines[n + 1].strip():
            out.append('')
    body = '\n'.join(out)
    if not found and stage and not (keep_signoff and stage == 'final'):
        key = approval_key(stage)
        body = body.rstrip('\n') + f'\n\n{doc_note(key)}\n\n{key}:\n'
    return body


def doc_text(text: str, stage: Optional[str] = None, keep_signoff: bool = False) -> str:
    """The Markdown a reviewer's Doc gets: fact tags stripped, a leading front-matter block turned into a list (Google reads raw front
    matter as a rule plus a heading, live run 2026-11-14), and, when `stage` is given, every approval line emptied with the instruction
    (`keep_signoff` is for the publish-ready final alone). Without a stage the approval lines are left as they are."""
    m = _FRONT_MATTER.match(text)
    if not m:
        shown = strip_fact_ids(text)
        return _open_approval(shown, stage, keep_signoff) if stage else shown
    items = []
    for line in m.group(1).split('\n'):
        key, sep, value = line.partition(':')
        if sep and key.strip():
            items.append(f'- **{key.strip().replace("_", " ").capitalize()}:** {value.strip()}')
    body = strip_fact_ids(text[m.end():])
    return '\n'.join(items) + '\n\n' + (_open_approval(body, stage, keep_signoff) if stage else body)


def docs_path(root: str, slug: str) -> str:
    return os.path.join(article_dir(root, slug), 'docs.json')


def _no_duplicate_keys(pairs: List[Tuple[str, object]]) -> Dict[str, object]:
    keys = [k for k, _ in pairs]
    dup = next((k for k in keys if keys.count(k) > 1), None)
    if dup is not None:
        # json keeps the last value, but a reader sees the first: `"publish_ready": true, "publish_ready": false` would mislead
        raise ValueError(f'duplicate key "{dup}"')
    return dict(pairs)


def parse_docs(text: str) -> List[Dict[str, object]]:
    """The revisions list of a docs.json text; ValueError when it is not valid {"revisions": [{...}, ...]} with unique keys."""
    data = json.loads(text, object_pairs_hook=_no_duplicate_keys)
    revs = data.get('revisions') if isinstance(data, dict) else None
    if not isinstance(revs, list) or not all(isinstance(e, dict) for e in revs):
        raise ValueError('it is not {"revisions": [...]}, a list of entries')
    return revs


def docs_index(root: str, slug: str) -> List[Dict[str, object]]:
    """The recorded Doc revisions, oldest first. A missing file is no history; an unreadable one raises ValueError, because
    reading it as empty would restart the numbering and hide which revision reviewers commented on."""
    path = docs_path(root, slug)
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding='utf-8') as fh:
            return parse_docs(fh.read())
    except (OSError, ValueError) as exc:
        raise ValueError(f'articles/{slug}/docs.json cannot be read ({exc})') from exc


DRIVE_TOP_FOLDER = 'articles'  # one place in My Drive for every workspace's copies


def drive_folder_path(root: str, slug: str) -> List[str]:
    """Where an article's Doc copies live in My Drive: `articles/<workspace folder name>/<slug>/` (approver's choice on PR #13)."""
    return [DRIVE_TOP_FOLDER, os.path.basename(os.path.realpath(root)) or 'workspace', slug]


def recorded_folder_id(root: str, slug: str) -> Optional[str]:
    """The Drive folder id recorded in docs.json for this article, if it was recorded for the same folder path. A renamed
    workspace changes the path, and then the skill looks the folders up again."""
    path = docs_path(root, slug)
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as fh:
        data = json.loads(fh.read(), object_pairs_hook=_no_duplicate_keys)
    folder = data.get('folder') if isinstance(data, dict) else None
    if isinstance(folder, dict) and folder.get('path') == '/'.join(drive_folder_path(root, slug)) and \
            isinstance(folder.get('id'), str) and folder['id']:
        return folder['id']
    return None


def next_rev(root: str, slug: str, stage: str) -> int:
    revs = [e.get('rev') for e in docs_index(root, slug) if e.get('stage') == stage]
    return 1 + max((r for r in revs if isinstance(r, int)), default=0)


def publish_ready(root: str, slug: str) -> bool:
    """FLOW-6, defined once for the copy script and the guard: the final is signed off on a current G4 PASS (`done`) and holds
    no marker. `done` alone is not enough: G4 may pass a marker (ADR-008) and a sign-off typed by hand skips the guard."""
    if article_state(root, slug)['next'] != 'done':
        return False
    return not MARKER_LOOSE.search(read_text(os.path.join(article_dir(root, slug), 'final.md')))


def publish_ready_or_false(root: str, slug: str) -> bool:
    """publish_ready() for the guard. Any failure reading the final means not publish-ready: here a false allow is a FLOW-6
    breach, while a false block costs only the label, so this check fails closed, unlike the rest of the guard."""
    try:
        return publish_ready(root, slug)
    except (OSError, ValueError):  # ValueError covers UnicodeDecodeError: a final that is not UTF-8
        return False


def claims_publish_ready(title: str) -> bool:
    """True for any spelling a reader takes as the label: case, spaces, underscores, other hyphens or none at all."""
    return 'publishready' in re.sub(r'[\W_]+', '', title.lower())


def doc_title(slug: str, stage: str, rev: int, ready: bool, gated: bool) -> str:
    label = ' · publish-ready' if ready else ('' if gated else ' · ungated')
    return f'{slug} · {stage} · r{rev}{label}'


def doc_copy(root: str, slug: str, stage: str) -> Dict[str, object]:
    """Everything the copy skill uploads and records, so the model never computes a hash, a revision or a label.

    `sha256` is the artifact on disk (what the guard checks); `text_sha256` is what reviewers see. `skip` is true when the
    stage's last recorded copy has the same `text_sha256` and the same label. Both hashes ignore approval lines, so a
    sign-off or a later PASS on unchanged text still gives a new Doc through its label, and a change in how the text is
    rendered gives a new Doc through `text_sha256` (an entry recorded without one never causes a skip)."""
    text = read_text(os.path.join(article_dir(root, slug), f'{stage}.md'))
    rev = next_rev(root, slug, stage)
    ready = stage == 'final' and publish_ready(root, slug)
    title = doc_title(slug, stage, rev, ready, check_gate(root, slug, stage) is None)
    shown = doc_text(text, stage, keep_signoff=ready)
    shown_sha = text_hash(shown)
    last = next((e for e in reversed(docs_index(root, slug)) if e.get('stage') == stage), None)
    skip = bool(last) and last.get('text_sha256') == shown_sha and \
        _REV_IN_TITLE.sub('', str(last.get('title', ''))) == _REV_IN_TITLE.sub('', title)
    return {'text': shown, 'sha256': text_hash(text), 'text_sha256': shown_sha, 'rev': rev, 'publish_ready': ready,
            'title': title, 'skip': skip, 'existing_url': last.get('url') if skip else None,
            'folder_path': drive_folder_path(root, slug), 'folder_id': recorded_folder_id(root, slug)}


# ---------------- Docs the copy skill created, and the approval a Doc carries (ADR-016) ----------------
CREATED_LOG = '.docs-created.json'
_DOC_TITLE = re.compile(r'^(?P<slug>.+?) · (?P<stage>brief|research|outline|draft|final) · r(?P<rev>\d+)(?: · (?P<label>ungated|publish-ready))?$')
_COMMENT_TAG = re.compile(r'<comment_(?:start|end) id=[^>]*>')
_HTML_COMMENT = re.compile(r'<!--.*?-->', re.S)
MAX_APPROVAL = 120


def parse_doc_title(title: str) -> Optional[Dict[str, object]]:
    """`<slug> · <stage> · r<k>[ · ungated | · publish-ready]` (ADR-012.1) as {slug, stage, rev, label}, or None for any other title."""
    m = _DOC_TITLE.match(title or '')
    if not m or not SLUG.match(m.group('slug')):
        return None
    return {'slug': m.group('slug'), 'stage': m.group('stage'), 'rev': int(m.group('rev')), 'label': m.group('label') or ''}


def tool_result(response: object) -> Optional[dict]:
    """A connector tool's result as a dict. A hook gets it as a JSON string (R0, 2026-11-16), but a dict or a list of text blocks is read too."""
    if isinstance(response, list):
        response = ''.join(str(b.get('text', '')) for b in response if isinstance(b, dict))
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except ValueError:
            return None
    return response if isinstance(response, dict) else None


def created_log(root: str, slug: str) -> List[Dict[str, object]]:
    """The Docs the copy skill created for an article. A missing file is an empty log; one that exists but cannot be read raises ValueError."""
    path = os.path.join(article_dir(root, slug), CREATED_LOG)
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding='utf-8') as fh:
            data = json.load(fh)
        docs = data.get('docs') if isinstance(data, dict) else None
        if not isinstance(docs, list) or not all(isinstance(d, dict) for d in docs):
            raise ValueError('it is not {"docs": [...]}')
        return docs
    except (OSError, ValueError) as exc:
        raise ValueError(f'articles/{slug}/{CREATED_LOG} cannot be read ({exc})') from exc


def doc_approval(file_content: str, stage: str) -> Optional[str]:
    """The name typed after the stage's approval label in a Doc body: the first such line outside a code fence, comment anchors stripped,
    trimmed, one line, at most 120 characters (a longer value is refused, never cut). None when the line is empty or absent."""
    key = approval_key(stage)
    fenced = False
    for line in _COMMENT_TAG.sub('', file_content).split('\n'):
        if _FENCE.match(line):
            fenced = not fenced
            continue
        m = None if fenced else re.match(r'^' + key + r':[ \t]*(.*)$', line)
        if m:
            value = m.group(1).strip()
            return value if value and len(value) <= MAX_APPROVAL else None
    return None


def _doc_words(text: str, stage: str) -> List[str]:
    """Words of a Doc body for comparison (R0): comment tags and HTML comments gone, the approval lines and the instruction left out,
    lower case `\\w+` runs. Google reflows lines, drops backticks and wraps headings, but keeps the words in order."""
    key = approval_key(stage)
    text = _HTML_COMMENT.sub('', _COMMENT_TAG.sub('', text))
    text = re.sub(r'^[ \t]*(?:Approved-by|Signed-off-by):.*$', '', text, flags=re.M)
    text = text.replace(doc_note(key), '')
    return re.findall(r'\w+', text.lower())


def doc_equals_artifact(root: str, slug: str, stage: str, file_content: str) -> bool:
    """True when a Doc body is the copy of the artifact on disk, apart from the approval line, the instruction and Google's reformatting."""
    expected = doc_text(read_text(os.path.join(article_dir(root, slug), f'{stage}.md')), stage)
    return _doc_words(expected, stage) == _doc_words(file_content, stage)


def approval_path(root: str, slug: str, stage: str, rev: int) -> str:
    return os.path.join(article_dir(root, slug), 'approvals', f'{stage}.r{rev}.json')


def read_approval(root: str, slug: str, stage: str, rev: int) -> Optional[Dict[str, object]]:
    try:
        with open(approval_path(root, slug, stage, rev), encoding='utf-8') as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def approval_value(text: str, key: str) -> str:
    """The value of the last `<key>:` line outside a code fence ('' when empty or absent), as `is_signed` reads a sign-off."""
    fenced, last = False, ''
    for line in text.replace('\r\n', '\n').split('\n'):
        if _FENCE.match(line):
            fenced = not fenced
        elif not fenced:
            m = re.match(r'^[ \t]*' + key + r':(.*)$', line)
            if m:
                last = m.group(1).strip()
    return last


def approval_filled(text: str) -> bool:
    """True when either human line has a value (outside a code fence)."""
    return bool(approval_value(text, 'Approved-by') or approval_value(text, 'Signed-off-by'))


def approved(root: str, slug: str, stage: str) -> bool:
    """FLOW-2: the stage's artifact carries its approval (`Signed-off-by:` for the final)."""
    return bool(approval_value(read_text(os.path.join(article_dir(root, slug), f'{stage}.md')), approval_key(stage)))


def latest_approval(root: str, slug: str, stage: str) -> Optional[Dict[str, object]]:
    """The approval record of the highest revision for a stage, or None. A record that exists but cannot be read raises ValueError."""
    d = os.path.join(article_dir(root, slug), 'approvals')
    try:
        names = os.listdir(d)
    except OSError:
        return None
    revs = sorted((int(m.group(1)), n) for n in names for m in [re.match(r'^' + stage + r'\.r(\d+)\.json$', n)] if m)
    if not revs:
        return None
    try:
        with open(os.path.join(d, revs[-1][1]), encoding='utf-8') as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        raise ValueError(f'articles/{slug}/approvals/{revs[-1][1]} cannot be read ({exc})') from exc
    return data if isinstance(data, dict) else None


def logged_doc_ids(root: str) -> set:
    """Every Doc id the copy skill created in any article of this workspace (ADR-016). An unreadable log raises ValueError."""
    ids = set()
    for slug in article_slugs(root):
        ids.update(str(d.get('id')) for d in created_log(root, slug) if d.get('id'))
    return ids


# ---------------- the fact bank and verbatim quotes (ADR-015) ----------------
_FACT_ROW = re.compile(r'^\s*\|\s*(F\d+)\s*\|')
_URL = re.compile(r'https?://[^\s<>)\]|]+')
_ELLIPSIS = re.compile(r'\s*(?:\[\.\.\.\]|\.\.\.|\u2026)\s*')


def fact_rows(text: str) -> List[Dict[str, str]]:
    """The Fact bank rows of research.md as {id, url, quote}. A row is a table line whose first cell is F<number>; the quote is the
    seventh cell (a stray `|` inside it is kept) with one pair of surrounding double quotation marks removed."""
    rows = []
    for line in text.replace('\r\n', '\n').split('\n'):
        m = _FACT_ROW.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 7:
            continue
        found = _URL.search(cells[2])
        quote = '|'.join(cells[6:]).strip()
        if len(quote) >= 2 and (quote[0], quote[-1]) in (('"', '"'), ('\u201c', '\u201d')):
            quote = quote[1:-1].strip()
        rows.append({'id': m.group(1), 'url': found.group(0) if found else cells[2], 'quote': quote})
    return rows


_QUOTE_MARKS = str.maketrans({'\u2018': "'", '\u2019': "'", '\u201a': "'", '\u201b': "'", '\u201c': '"', '\u201d': '"',
                              '\u201e': '"', '\u201f': '"', '\u2013': '-', '\u2014': '-', '\u2012': '-', '\u2015': '-'})
_INVISIBLE = dict.fromkeys(map(ord, '\u00ad\u200b\u200c\u200d\ufeff'))


def normalize_text(text: str) -> str:
    """Only what typesetting changes: compatibility forms, curly quotes, dashes, soft hyphens and runs of whitespace. Case and wording stay."""
    text = unicodedata.normalize('NFKC', text).translate(_INVISIBLE).translate(_QUOTE_MARKS)
    return re.sub(r'\s+', ' ', text).strip()


MAX_ELISION = 300  # characters of page text an ellipsis may stand for; further apart than this the pieces are not one quote


def _bounded_hits(page: str, seg: str, start: int):
    """Every place `seg` occurs in `page` from `start` that is not the middle of a longer word or number."""
    i = page.find(seg, start)
    while i >= 0:
        j = i + len(seg)
        left = page[i - 1] if i else ''
        right = page[j] if j < len(page) else ''
        inside_word = (seg[0].isalnum() and left.isalnum()) or (seg[-1].isalnum() and right.isalnum())
        inside_number = seg[-1].isdigit() and right in ('.', ',') and j + 1 < len(page) and page[j + 1].isdigit()
        if not (inside_word or inside_number):
            yield i, j
        i = page.find(seg, i + 1)


def _match(page: str, segments: List[str], pos: int, prev_end: Optional[int]) -> bool:
    if not segments:
        return True
    for i, j in _bounded_hits(page, segments[0], pos):
        if prev_end is not None and i - prev_end > MAX_ELISION:
            return False  # hits only get further away
        if _match(page, segments[1:], j, j):
            return True
    return False


def quote_status(page_text: str, quote: str) -> str:
    """`found` (one piece, on the page), `found-elided` (several pieces, close together and in order: what the ellipsis hid still needs
    reading) or `not-found`. `page_text` is already normalised. Closing marks on the last piece are ignored (ADR-015)."""
    segments = [normalize_text(seg) for seg in _ELLIPSIS.split(quote)]
    segments = [seg for seg in segments if seg]
    if segments:  # a quote cut mid-sentence may close with a mark the page does not have there; inner marks still count
        segments[-1] = segments[-1].rstrip(' .,;:')
    segments = [seg for seg in segments if seg]
    if not segments or not _match(page_text, segments, 0, None):
        return 'not-found'
    return 'found' if len(segments) == 1 else 'found-elided'
