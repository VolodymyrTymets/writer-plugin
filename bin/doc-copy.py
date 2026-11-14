#!/usr/bin/env python3
"""What the publish skill uploads for one artifact, and what it records in docs.json, as one JSON object (ADR-012).

    python3 bin/doc-copy.py [--root <workspace>] <slug> <stage>

Keys: text (the artifact as Markdown, fact tags stripped), sha256 (of the file on disk, approval lines ignored), rev,
publish_ready, title, skip, existing_url. Read-only: it writes no file. On a bad request it prints {"error": ...} and exits 1,
so the skill stops instead of uploading a guess.
"""
import argparse
import json
import os
import sys
from typing import Dict, Sequence

from lib import writer as w

USAGE = 'usage: doc-copy.py [--root <workspace>] <slug> <stage>'


class _ArgError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    # argparse prints usage and exits 2 on a bad argument; the skill needs JSON instead (Python 3.9 has no exit_on_error)
    def error(self, message: str) -> None:
        raise _ArgError(message)


def copy_for(argv: Sequence[str]) -> Dict[str, object]:
    ap = _Parser(add_help=False)
    ap.add_argument('--root', default=None)
    ap.add_argument('slug')
    ap.add_argument('stage')
    try:
        args = ap.parse_args(argv)
    except _ArgError as exc:
        return {'error': f'bad arguments ({exc}); {USAGE}'}
    if not w.SLUG.match(args.slug):
        return {'error': f'"{args.slug}" is not an article slug (one folder name under articles/)'}
    if args.stage not in w.STAGES:
        return {'error': f'"{args.stage}" is not a stage; one of {", ".join(w.STAGES)}'}
    root = args.root or os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    if not os.path.isfile(os.path.join(w.article_dir(root, args.slug), f'{args.stage}.md')):
        return {'error': f'articles/{args.slug}/{args.stage}.md does not exist under {root}'}
    try:
        return w.doc_copy(root, args.slug, args.stage)
    except ValueError as exc:  # an unreadable docs.json: stopping beats restarting the revision numbers
        return {'error': str(exc)}


def main() -> int:
    out = copy_for(sys.argv[1:])
    print(json.dumps(out, ensure_ascii=False))
    return 1 if 'error' in out else 0


if __name__ == '__main__':
    sys.exit(main())
