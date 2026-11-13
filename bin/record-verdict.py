#!/usr/bin/env python3
"""Records what a saved verdict judged (ADR-009). PostToolUse: Write.

After the Write tool saves `articles/<slug>/gates/G<n>-<stage>.r<k>.md`, this writes the sidecar beside it:
the hash of the artifact as it is now (approval lines ignored) and the file name of the latest verdict of the gate before it.
The guard reads the sidecar to tell a verdict that still covers the artifact from a stale one. Only this script writes sidecars.
"""
import os

from lib import writer as w


def main():
    p = w.read_payload()
    root = w.project_dir(p)
    ti = p.get('tool_input')
    if p.get('tool_name') != 'Write' or not isinstance(ti, dict):
        return
    rel = w.rel_path(root, str(ti.get('file_path') or ''), p.get('cwd') or root)
    parts = w.split_article(rel or '')
    if not parts or not parts[1].startswith('gates/'):
        return
    name = parts[1][len('gates/'):]
    if '/' in name or not w.VERDICT_NAME.match(name):
        return
    if os.path.exists(os.path.join(w.article_dir(root, parts[0]), 'gates', name)):
        w.write_sidecar(root, parts[0], name)


w.fail_open(main, 'record-verdict')
