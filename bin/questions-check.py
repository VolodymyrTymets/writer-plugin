#!/usr/bin/env python3
"""Checks the form of an artifact's `## Questions for the human` list (FT-22, ADR-023). Stdlib only. Not a hook: run it as a command.

    python3 bin/questions-check.py [--root <workspace>] <slug> <stage>

`stage` is research, outline or draft. Prints one JSON object, `{"findings": [{rule, line, message}], "notes": [...]}`, and exits 0 even with findings (they are
advisory, FACT-6); a bad request prints `{"error": ...}` and exits 1. Read-only: it writes no file, so the actors that call it need no write access
for it. It checks form only; the gates keep the judgement (does a question say what would answer it).
"""
import argparse
import json
import os
import sys
from typing import Dict, Optional, Sequence

from lib import writer as w

USAGE = 'usage: questions-check.py [--root <workspace>] <slug> <stage>'
UPSTREAM = {'research': None, 'outline': 'research', 'draft': 'outline'}


class _ArgError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    # argparse prints usage and exits 2; the caller needs JSON instead (Python 3.9 has no exit_on_error)
    def error(self, message: str) -> None:
        raise _ArgError(message)


def check(argv: Sequence[str]) -> Dict[str, object]:
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
    if args.stage not in UPSTREAM:
        return {'error': f'"{args.stage}" has no questions list; one of {", ".join(UPSTREAM)}'}
    root = args.root or os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    art = w.article_dir(root, args.slug)
    path = os.path.join(art, f'{args.stage}.md')
    if not os.path.isfile(path):
        return {'error': f'articles/{args.slug}/{args.stage}.md does not exist under {root}'}
    up_stage: Optional[str] = UPSTREAM[args.stage]
    upstream = None
    notes = []
    try:
        with open(path, encoding='utf-8') as fh:  # w.read_text returns '' on an unreadable file, which would read as a clean list
            text = fh.read()
    except OSError as exc:
        return {'error': f'articles/{args.slug}/{args.stage}.md cannot be read ({exc})'}
    if up_stage:
        up_path = os.path.join(art, f'{up_stage}.md')
        try:
            with open(up_path, encoding='utf-8') as fh:
                upstream = fh.read()
        except FileNotFoundError:
            notes.append(f'{up_stage}.md is missing, so a repeated resolved question cannot be checked')
        except OSError as exc:
            notes.append(f'{up_stage}.md could not be read ({exc}), so a repeated resolved question cannot be checked')
    findings = w.questions_findings(text, upstream)
    return {'findings': findings, 'notes': notes}


def main() -> int:
    out = check(sys.argv[1:])
    print(json.dumps(out, ensure_ascii=False))
    return 1 if 'error' in out else 0


if __name__ == '__main__':
    sys.exit(main())
