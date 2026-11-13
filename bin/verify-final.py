#!/usr/bin/env python3
"""A final that changed this session must have a recorded prose-lint run. Stop hook.

Blocks once per article and session when `articles/<slug>/final.md` was written after the session started and has no
`.prose-lint.json` whose hash matches it (approval lines ignored, ADR-007). A run is what is required, not zero findings.
`stop_hook_active` and a second attempt always allow, so it can never loop. Silent outside a writer workspace.
"""
import json
import os
import sys
import time

from lib import writer as w


def main():
    p = w.read_payload()
    if p.get('stop_hook_active'):
        return
    root = w.project_dir(p)
    slugs = w.article_slugs(root)
    if not slugs:
        return
    sid = p.get('session_id')
    state = w.load_state(sid)
    started = state.get('started', time.time() - 6 * 3600)
    blocked = list(state.get('blocked') or [])
    pending = []
    for slug in slugs:
        path = os.path.join(w.article_dir(root, slug), 'final.md')
        try:
            if os.path.getmtime(path) < started:
                continue
        except OSError:
            continue
        try:
            with open(os.path.join(w.article_dir(root, slug), '.prose-lint.json'), encoding='utf-8') as fh:
                recorded = json.load(fh).get('sha256')
        except (OSError, ValueError):
            recorded = None
        if recorded != w.text_hash(w.read_text(path)) and slug not in blocked:
            pending.append(slug)
    if not pending:
        return
    state['blocked'] = blocked + pending
    state.setdefault('started', started)
    w.save_state(sid, state)
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prose-lint.py')
    cmds = '\n'.join(f'  python3 "{script}" --record articles/{s}/final.md' for s in pending)
    sys.stderr.write(
        '[writer-plugin] verify-final: final.md changed in this session but has no recorded prose-lint run. Run:\n' + cmds +
        '\nThen fix what it reports, or say plainly why a finding stands. A recorded run is what lets you stop; zero findings is not required.\n')
    sys.exit(2)


w.fail_open(main, 'verify-final')
