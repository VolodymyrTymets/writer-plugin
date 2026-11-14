#!/usr/bin/env python3
"""Where one article is and its next step, as one JSON object on stdout. Called by the article skill (ADR-011); also usable alone.

    python3 bin/article-status.py [--root <workspace>] <slug>

Keys: slug, stage, next, reason, markers, stale. `next` is a stage to run (brief, research, outline, draft, final), approve,
sign-off, stopped, stale, done or unknown. Read-only: it writes no file. It always exits 0 and prints JSON, because the skill
acts on `next`; any failure is `next: "unknown"` with the reason, so the orchestrator stops instead of guessing a stage.
"""
import argparse
import json
import os
import sys

from lib import writer as w


def main() -> None:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('--root', default=None)
    ap.add_argument('slug', nargs='?', default='')
    args, _ = ap.parse_known_args()
    root = args.root or os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    try:
        state = w.article_state(root, args.slug) if args.slug else w.unknown_state('', 'no article slug given')
    except Exception as exc:  # the skill must always get JSON; the reason names the failure so a human can act on it
        state = w.unknown_state(args.slug, f'article-status failed: {type(exc).__name__}: {exc}')
    print(json.dumps({k: state[k] for k in w.STATE_KEYS}))


if __name__ == '__main__':
    main()
    sys.exit(0)
