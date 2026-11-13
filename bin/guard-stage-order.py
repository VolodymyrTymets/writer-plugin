#!/usr/bin/env python3
"""Stage order, mechanical (FLOW-1, FLOW-2, FLOW-3, FLOW-4). PreToolUse: Edit|Write|Bash.

Path-based, so it needs no branch or ticket: it acts only on `articles/<slug>/...` inside the workspace.
- Writing research.md, outline.md, draft.md or final.md needs the previous gate's latest verdict to be a PASS on what is on disk
  (FLOW-1, with stale verdicts caught through the sidecar, ADR-009); draft.md also needs a non-empty `Approved-by:` (FLOW-2).
- A stage whose own gate has two BLOCK verdicts is stopped until a human archives them (FLOW-3).
- Verdict files are immutable and are created only by the Write tool with a valid line 1 and the next number (FLOW-4, ADR-004);
  no tool writes a sidecar and Bash cannot touch gates/ at all.
An unexpected error allows the action (see lib/writer.fail_open).
"""
import os

from lib import writer as w


def deny_stage(rule, message, alternative):
    w.block(rule, message, alternative)


def check_gates(root, slug, sub, tool, tool_input):
    if tool == 'Bash':
        w.block('FLOW-4', f'a shell command may not write, move, copy or delete anything in articles/{slug}/gates/.',
                'Read verdicts with cat or grep. Save a new verdict with the Write tool. Archiving verdicts to resume a stopped '
                'article is the human\'s step (ADR-004): do it by hand.')
    if sub.startswith('archive/') or sub == 'archive':
        w.block('FLOW-4', 'the archive is where a human moves verdicts to resume a stopped article; no tool writes there.',
                'ask the human to archive by hand (ADR-004).')
    if sub.endswith('.json'):
        w.block('FLOW-4', 'sidecars are written by the record-verdict hook only; a tool may not write one.',
                'save the verdict with the Write tool and the hook records its sidecar.')
    m = w.VERDICT_NAME.match(sub)
    if not m or m.group(1) != w.GATE_ID.get(m.group(2)):
        w.block('FLOW-4', f'"{sub}" is not a verdict file name; only G<n>-<stage>.r<k>.md files live in gates/.',
                'verdicts are named G0-brief.r1.md, G1-research.r1.md, G2-outline.r1.md, G3-draft.r1.md, G4-final.r1.md.')
    stage = m.group(2)
    if os.path.exists(os.path.join(w.article_dir(root, slug), 'gates', sub)):
        w.block('FLOW-4', f'{sub} is a saved verdict and is never edited or overwritten (ADR-004).',
                'save a new verdict under the next number.')
    if tool != 'Write':
        w.block('FLOW-4', 'a new verdict is created with the Write tool, so the hook that records it always runs.', None)
    k, want = int(m.group(3)), w.next_k(root, slug, stage)
    if k != want:
        w.block('FLOW-4', f'the next {w.gate_name(stage)} verdict is r{want} (one past the highest in gates/ and gates/archive/), not r{k}.',
                f'save it as {w.gate_name(stage)}.r{want}.md.')
    line = str((tool_input or {}).get('content') or '').split('\n', 1)[0].rstrip('\r')
    lm = w.VERDICT_LINE.match(line)
    if not lm or lm.group(1) != f'{w.GATE_ID[stage]} {stage}':
        w.block('FLOW-4', f'line 1 of a {w.gate_name(stage)} verdict must match the ADR-004 pattern for its own gate (got "{line[:80]}").',
                'save the verdict exactly as the gate returned it, line 1 first.')


def check_stage(root, slug, stage):
    gate = w.gate_name(stage)
    if w.block_count(root, slug, stage) >= 2:
        w.block('FLOW-3', f'{gate} has two BLOCK verdicts for articles/{slug}, so the {stage} stage is stopped.',
                'hand the article to the human; they resume it by archiving that gate\'s verdicts by hand (ADR-004).')
    if stage == 'brief':
        return
    prev = w.previous_stage(stage)
    why = w.check_gate(root, slug, prev)
    if why:
        w.block('FLOW-1', f'the {stage} stage may not start: {why}.',
                f'run the {prev} stage so its gate saves a PASS verdict on what is on disk. After a hand edit, a gate rerun saved '
                f'by Write as the next verdict re-records it (ADR-009).')
    if stage == 'draft':
        try:
            with open(os.path.join(w.article_dir(root, slug), 'outline.md'), encoding='utf-8') as fh:
                approved = bool(w.APPROVED.search(fh.read()))
        except OSError:
            approved = False
        if not approved:
            w.block('FLOW-2', 'the draft may not be written: `Approved-by:` in outline.md has no value. An empty line is not approval.',
                    'a human reads the outline and writes their name after `Approved-by:`.')


def check_target(root, rel, tool, tool_input):
    parts = w.split_article(rel)
    if not parts:
        return
    slug, rest = parts
    if rest.startswith('gates/') or rest == 'gates':
        check_gates(root, slug, rest[len('gates/'):], tool, tool_input)
    elif rest in ('brief.md', 'research.md', 'outline.md', 'draft.md', 'final.md'):
        check_stage(root, slug, rest[:-3])


def main():
    p = w.read_payload()
    root = w.project_dir(p)
    cwd = p.get('cwd') or root
    tool, ti = p.get('tool_name'), p.get('tool_input')
    if not isinstance(ti, dict):
        return
    if tool in ('Write', 'Edit'):
        paths = [ti.get('file_path')]
    elif tool == 'Bash':
        paths = [path for _, path in w.bash_targets(str(ti.get('command') or ''))]
    else:
        return
    for path in paths:
        rel = w.rel_path(root, str(path or ''), cwd)
        if rel:
            check_target(root, rel, tool, ti)


w.fail_open(main, 'guard-stage-order')
