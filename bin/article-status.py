#!/usr/bin/env python3
"""Where one article is and its next step, as one JSON object on stdout. Called by the article skill (ADR-011); also usable alone.

    python3 bin/article-status.py [--root <workspace>] <slug>

Keys: slug, stage, next, reason, markers, stale. `next` is a stage to run (brief, research, outline, draft, final), approve,
sign-off, stopped, stale, done or unknown. Read-only: it writes no file. It always exits 0 and prints JSON, bad arguments included, because the skill
acts on `next`; any failure is `next: "unknown"` with the reason, so the orchestrator stops instead of guessing a stage.
"""
import argparse
import json
import os
import sys
from typing import Dict

from lib import writer as w


class _ArgError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    # argparse prints usage and exits 2 on a bad argument; the skill needs JSON instead (Python 3.9 has no exit_on_error)
    def error(self, message: str) -> None:
        raise _ArgError(message)


def state_for(argv) -> Dict[str, object]:
    ap = _Parser(add_help=False)
    ap.add_argument('--root', default=None)
    ap.add_argument('slug', nargs='?', default='')
    try:
        args = ap.parse_args(argv)
    except _ArgError as exc:
        return w.unknown_state('', f'bad arguments ({exc}); usage: article-status.py [--root <workspace>] <slug>')
    if not args.slug:
        return w.unknown_state('', 'no article slug given')
    root = args.root or os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    try:
        return w.article_state(root, args.slug)
    except Exception as exc:  # the skill must always get JSON; the reason names the failure so a human can act on it
        return w.unknown_state(args.slug, f'article-status failed: {type(exc).__name__}: {exc}')


def main() -> None:
    state = state_for(sys.argv[1:])
    print(json.dumps({k: state[k] for k in w.STATE_KEYS}))


if __name__ == '__main__':
    main()
    sys.exit(0)
