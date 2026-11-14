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
