#!/usr/bin/env python3
"""Where each article is (at most 30 lines; stdout becomes session context). SessionStart: startup|resume|clear|compact.

Silent outside a writer workspace (no `articles/` folder), because the plugin is installed everywhere. Also records when the
session started, once, so the Stop check can tell which final.md files were written in this session.
"""
import os
import time

from lib import writer as w

MAX_LINES = 30


def main():
    p = w.read_payload()
    root = w.project_dir(p)
    slugs = w.article_slugs(root)
    if not slugs:
        return
    sid = p.get('session_id')
    state = w.load_state(sid)
    if 'started' not in state:                 # `resume`, `clear` and `compact` reuse the session id: do not move it
        state['started'] = time.time()
        state.setdefault('blocked', [])
        w.save_state(sid, state)
    lines = ['## Writer workspace (writer-plugin)']
    room = MAX_LINES - len(lines)
    shown = slugs if len(slugs) <= room else slugs[:room - 1]
    lines += [f'- **{s}**: {w.describe_article(root, s)}' for s in shown]
    if len(shown) < len(slugs):
        lines.append(f'- ... and {len(slugs) - len(shown)} more articles')
    print('\n'.join(lines))


w.fail_open(main, 'session-context')
