#!/usr/bin/env python3
"""Stage order, mechanical (FLOW-1, FLOW-2, FLOW-3, FLOW-4). PreToolUse: Edit|Write|Bash and the Drive and Docs connector tools.

ADR-016 adds, and these rules FAIL CLOSED (any error blocks; a false allow would skip a human checkpoint, as ADR-012.5): no stage starts before the
previous artifact is approved (FLOW-2, brief to draft; the final closes with a sign-off); a Write or Edit fills an approval line only against an approval
record that matches the content (a name is typed in the Google Doc and carried over by sync); no tool writes `approvals/` or `.docs-created.json`;
a Doc upload never carries a filled approval line and an article Doc is exactly the artifact's copy; a `docs.json` entry matches a Doc the create hook
logged; no connector tool outside the read list touches a logged Doc.

ADR-015 adds: a G1 verdict is saved only against a quote-check record that matches research.md; `.quote-check.json` is written only
by quote-check.py.

Phase 5 adds (ADR-010): a G4 verdict is saved only against a lint record that matches final.md; `.prose-lint.json` is written
only by prose-lint.py; a non-empty `Signed-off-by:` is written only against a current G4 PASS on the content the write produces,
and never beside an unverified-claim marker (FLOW-6).

Path-based, so it needs no branch or ticket: it acts only on `articles/<slug>/...` inside the workspace.
- Writing research.md, outline.md, draft.md or final.md needs the previous gate's latest verdict to be a PASS on what is on disk
  (FLOW-1, with stale verdicts caught through the sidecar, ADR-009); every stage after the brief also needs the previous artifact approved (FLOW-2, ADR-016).
- A stage whose own gate has two BLOCK verdicts is stopped until a human archives them (FLOW-3).
- Verdict files are immutable and are created only by the Write tool with a valid line 1 and the next number (FLOW-4, ADR-004);
  no tool writes a sidecar and Bash cannot touch gates/ at all.
Phase 7b adds (ADR-012), FLOW-6 on the Doc copies: `docs.json` is append-only, valid JSON, never written by Bash, and an entry
says publish_ready only for a publish-ready final on its exact hash; the Drive create call (`DRIVE_CREATE`) may title a Doc
publish-ready only for such a final carrying exactly its text, and the update call (`DRIVE_UPDATE`) never renames onto the label.
An unexpected error allows the action (see lib/writer.fail_open) for the older rules; the ADR-016 rules above are wrapped by `fail_closed` and refuse instead.
A shell command is judged by the paths it writes and, for an artifact, by whether it names an approval label (it cannot be judged by what it writes); a
write the parser cannot read (`python -c`) and the file-writing tools of other MCP servers are outside this guard (ADR-016, known gaps).
"""
import json
import os
import re
import sys

from lib import writer as w

DRIVE_CREATE = 'mcp__claude_ai_Google_Drive__create_file'  # the real names, recorded by the Phase 7b spike (2026-11-14)
DRIVE_UPDATE = 'mcp__claude_ai_Google_Drive__update_file'  # metadata only; its `title` can rename a Doc
DOC_PREFIXES = {'mcp__claude_ai_Google_Drive__': 'fileId', 'mcp__claude_ai_Google_Docs__': 'documentId'}  # the key that holds a Doc id (R0, 2026-11-16)
DOC_READ_TOOLS = {'read_file_content', 'download_file_content', 'get_file_metadata', 'get_file_permissions', 'list_file_revisions',
                  'list_recent_files', 'search_files', 'list_shared_drives', 'get_shared_drive_metadata', 'read_doc'}
DOC_WRITE_TOOLS = {'update_file', 'copy_file', 'trash_file', 'share_file', 'update_doc'}  # each carries a Doc id: without one the call is refused


def fault(name):
    """Test seam, like QUOTE_CHECK_ALLOW_LOOPBACK: WRITER_GUARD_TEST_FAULT=<rule> makes that rule raise, to prove it blocks instead of allowing."""
    if os.environ.get('WRITER_GUARD_TEST_FAULT') == name:
        raise RuntimeError('test fault')


def fail_closed(rule, what):
    """Run a rule so that an unexpected error blocks (ADR-012.5): outside the guard's fail_open, which would allow."""
    def wrap(fn):
        def run(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except SystemExit:
                raise
            except Exception as exc:  # deliberate: a rule that cannot decide refuses, because allowing would skip a human checkpoint
                w.block(rule, f'{what} could not be checked ({type(exc).__name__}: {exc}), so it is refused.',
                        'fix the cause named above, then try again; do not work around the guard.')
        return run
    return wrap


def deny_stage(rule, message, alternative):
    w.block(rule, message, alternative)


@fail_closed('FLOW-2', 'an approval write')
def check_approval_write(root, slug, stage, rel, tool, tool_input):
    """FLOW-2/FLOW-6: a tool makes an approval line non-empty only against the record the recorder wrote from the Google Doc, for exactly
    this content. Clearing it, or leaving an untouched file as it is, is allowed; changing an approved artifact while keeping the name is not."""
    fault('approval-write')
    new = w.resulting_text(root, rel, tool, tool_input)
    if new is None:  # an Edit that cannot apply writes nothing
        return
    key = w.approval_key(stage)
    value = w.approval_value(new, key)
    if not value:
        return
    old = w.read_text(os.path.join(w.article_dir(root, slug), f'{stage}.md'))
    if value == w.approval_value(old, key) and w.text_hash(new) == w.text_hash(old):
        return
    record = w.latest_approval(root, slug, stage)
    if record and record.get('value') == value and record.get('artifact_sha256') == w.text_hash(new):
        return
    w.block('FLOW-2' if stage != 'final' else 'FLOW-6', f'articles/{slug}/{stage}.md may not get `{key}: {value[:40]}` from a tool: no approval recorded from the '
            'Google Doc matches this content (an approval covers the exact text, so changing an approved file clears it).',
            f'the human writes their name after `{key}:` in the {stage} Doc and runs writer-plugin:sync, or types it in the file themselves.')


def check_gates(root, slug, sub, tool, tool_input):
    if tool == 'Bash':
        w.block('FLOW-4', f'a shell command may not write, move, copy or delete anything in articles/{slug}/gates/.',
                'Read verdicts with cat or grep. Save a new verdict with the Write tool. Archiving verdicts to resume a stopped '
                'article is the human\'s step (ADR-004): do it by hand.')
    if sub.lower().startswith('archive/') or sub.lower() == 'archive':
        w.block('FLOW-4', 'the archive is where a human moves verdicts to resume a stopped article; no tool writes there.',
                'ask the human to archive by hand (ADR-004).')
    if sub.lower().endswith('.json'):
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
    now_research = w.artifact_hash(root, slug, 'research') if stage == 'research' else None
    # the one verdict that needs no record is G1's BLOCK for a research.md that does not exist; the text alone cannot claim it
    if stage == 'research' and not (now_research is None and _says_no_artifact(str((tool_input or {}).get('content') or ''))):
        record, now = w.quote_record(root, slug), now_research
        if record is None or now is None or record.get('sha256') != now:
            script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'quote-check.py')
            w.block('FLOW-4', f'a G1 verdict is saved only against a quote-check run on the research as it is now, and articles/{slug}/.quote-check.json '
                    'is missing or was recorded for another version of research.md (the gate reads the statuses from it).',
                    f'run: python3 {script} --record {slug}, change nothing in research.md afterwards, then rerun G1 and save its verdict.')
    if stage == 'final':
        record, now = w.lint_record(root, slug), w.artifact_hash(root, slug, 'final')
        if record is None or now is None or record.get('sha256') != now:
            script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prose-lint.py')
            w.block('FLOW-4', f'a G4 verdict is saved only against a prose-lint run on the final as it is now, and articles/{slug}/.prose-lint.json '
                    'is missing or was recorded for another version of final.md (the gate reads the findings from it).',
                    f'run: python3 {script} --record articles/{slug}/final.md, change nothing in final.md afterwards, then rerun G4 and save its verdict.')


def _says_no_artifact(content: str) -> bool:
    """G1's BLOCK for a missing research.md (`Artifact: none`): there is nothing to check quotes in. A PASS never qualifies."""
    lines = content.split('\n')
    return len(lines) > 1 and lines[0].startswith('## G1 research gate: BLOCK') and lines[1].strip() == 'Artifact: none'


def check_signoff(root, slug, text):
    """FLOW-6: a sign-off needs a G4 PASS on exactly the content being written, and no marker left in it."""
    if not w.is_signed(text):
        return
    if w.MARKER_LOOSE.search(text):
        w.block('FLOW-6', f'articles/{slug}/final.md may not be signed off while an unverified-claim marker (<Can\'t be verified ...>) is in it.',
                'resolve every marker in the text (a human supplies the fact or removes the claim), rerun the edit stage and its gate, then sign off.')
    name = w.latest(root, slug, 'final')
    why = None
    if not name or w.read_sidecar(root, slug, name) is None:
        why = (f'{name} has no sidecar, so what it judged is unknown' if name else 'there is no G4 verdict for the final')
    else:
        why = w.check_gate(root, slug, 'final', text)
    if why:
        w.block('FLOW-6', f'articles/{slug}/final.md may not be signed off: {why}.',
                'sign off only a final whose latest G4 verdict is a PASS on exactly this text; after any change, rerun G4 and save the verdict with Write.')


def check_docs(root, slug, rel, tool, tool_input):
    """FLOW-6 on the Doc copy record (ADR-012): docs.json is an append-only list, and an entry may say publish_ready only for a
    final that is publish-ready now, on exactly the text on disk."""
    if tool == 'Bash':
        w.block('FLOW-6', f'articles/{slug}/docs.json is the record of the Doc copies; a shell command may not write it.',
                'the copy skill appends an entry with the Write tool.')
    text = w.resulting_text(root, rel, tool, tool_input)
    if text is None:
        sys.stderr.write(f'[writer-plugin] guard-stage-order could not work out the content of {rel}, so the docs.json check was skipped.\n')
        return
    try:
        new = w.parse_docs(text)
    except ValueError as exc:
        w.block('FLOW-6', f'articles/{slug}/docs.json must stay {{"revisions": [...]}}, a list of entries with unique keys; this write '
                f'would break it ({exc}).', 'read the file, append one entry to its revisions list and write the whole file back.')
    try:
        old = w.docs_index(root, slug)
    except ValueError:
        old = []  # an unreadable record has no history left to protect; a valid rewrite repairs it
    if new[:len(old)] != old:
        w.block('FLOW-6', f'articles/{slug}/docs.json is append-only: this write changes, removes or reorders an entry already recorded.',
                'keep every existing entry as it is and append the new one at the end.')
    check_docs_created(root, slug, new[len(old):])
    for e in new[len(old):]:
        ready = e.get('publish_ready')
        if not isinstance(ready, bool):
            w.block('FLOW-6', f'publish_ready must be true or false, not {json.dumps(ready)}.',
                    'copy publish_ready from the doc-copy script unchanged.')
        if not ready:
            if w.claims_publish_ready(str(e.get('title', ''))):
                w.block('FLOW-6', 'this entry says publish_ready false but its title carries the publish-ready label.',
                        'copy the title from the doc-copy script unchanged.')
            continue
        if e.get('stage') != 'final':
            w.block('FLOW-6', f'only a final can be publish-ready; this entry is for "{e.get("stage")}".',
                    'record it with "publish_ready": false, exactly as the doc-copy script printed it.')
        if not w.publish_ready_or_false(root, slug):
            w.block('FLOW-6', f'articles/{slug}/final.md is not publish-ready: it needs a non-empty Signed-off-by on a current G4 PASS '
                    'and no unverified-claim marker.', 'record the copy with "publish_ready": false, or sign off a final that qualifies.')
        if e.get('sha256') != w.artifact_hash(root, slug, 'final'):
            w.block('FLOW-6', 'this publish-ready entry records a hash that is not the final on disk.',
                    'run doc-copy.py again and record its sha256 unchanged.')


@fail_closed('FLOW-6', 'a docs.json entry')
def check_docs_created(root, slug, entries):
    """ADR-016: a new entry records a Doc the create hook logged (same id, title and uploaded text), made from the artifact as it is now."""
    fault('docs-entry')
    log = w.created_log(root, slug)
    for e in entries:
        hit = next((d for d in log if d.get('id') == e.get('id') and d.get('title') == e.get('title')
                    and d.get('text_sha256') == e.get('text_sha256') and d.get('stage') == e.get('stage')), None)
        if hit is None:
            w.block('FLOW-6', f'docs.json entry "{str(e.get("title"))[:60]}" matches no Doc the copy skill created (id, title and text_sha256 must match '
                    'what the create hook logged), so it cannot record a revision.',
                    'record only a Doc made by the copy skill with the fields doc-copy.py printed; a Doc made any other way is not a revision.')
        if e.get('sha256') != w.artifact_hash(root, slug, str(e.get('stage'))):
            w.block('FLOW-6', 'this entry records a hash that is not the artifact on disk now.',
                    'run doc-copy.py again, make the copy again, and record its sha256 unchanged.')


@fail_closed('FLOW-6', 'a Doc upload')
def check_create_rules(root, tool_input):
    """ADR-016: an upload never carries a filled approval line (the exact publish-ready final excepted, which check_drive_create already judged),
    and a Doc titled as an article's copy is exactly that copy, as text."""
    fault('create')
    title = str(tool_input.get('title') or '')
    if w.claims_publish_ready(title):
        return
    text = tool_input.get('textContent')
    if isinstance(text, str) and w.approval_filled(text):
        w.block('FLOW-2', 'a Doc may not be uploaded with a name already after `Approved-by:` or `Signed-off-by:`: approval is typed in the Doc by a human.',
                'upload the text the doc-copy script prints, unchanged; it carries the labels empty.')
    parts = w.parse_doc_title(title)
    if not parts or not os.path.isdir(w.article_dir(root, str(parts['slug']))):
        return
    slug, stage = str(parts['slug']), str(parts['stage'])
    path = os.path.join(w.article_dir(root, slug), f'{stage}.md')
    if (not os.path.isfile(path) or tool_input.get('base64Content') is not None or tool_input.get('content') is not None
            or text != w.doc_text(w.read_text(path), stage)):
        w.block('FLOW-6', f'a Doc titled "{title[:60]}" must carry exactly the copy of articles/{slug}/{stage}.md, as textContent.',
                'upload the text the doc-copy script prints, unchanged, under the title it prints.')


@fail_closed('FLOW-6', 'a Drive or Docs call')
def check_doc_tool(root, tool, tool_input):
    """ADR-016: outside the read list, no connector call touches a Doc the copy skill created; a call that must name a Doc and does not is refused."""
    fault('doc-tool')
    prefix = next(p for p in DOC_PREFIXES if tool.startswith(p))
    name = tool[len(prefix):]
    if name in DOC_READ_TOOLS or name == 'create_file' or not os.path.isdir(os.path.join(root, 'articles')):
        return
    logged_ids = w.logged_doc_ids(root)
    if any(i in s for s in _strings(tool_input) for i in logged_ids):  # any key, any depth, a URL: a tool added later may name a Doc differently
        w.block('FLOW-6', f'{name} names a review Doc the copy skill created: only a human edits, shares or removes it, and approval is typed there.',
                'ask the human to do it in Google Docs; a new revision is a new copy made by the copy skill.')
    doc_id = tool_input.get(DOC_PREFIXES[prefix])
    if not isinstance(doc_id, str) or not doc_id:
        if name in DOC_WRITE_TOOLS:
            w.block('FLOW-6', f'{name} must name the Doc it changes (`{DOC_PREFIXES[prefix]}`); this call does not, so it cannot be checked.',
                    'pass the Doc id.')
        return
    if doc_id in logged_ids:
        w.block('FLOW-6', f'{name} would change or share a review Doc the copy skill created ({doc_id[:12]}…): only a human edits, shares or '
                'removes it, and approval is typed there.', 'ask the human to do it in Google Docs; a new revision is a new copy made by the copy skill.')


PUBLISH_READY_TITLE = re.compile(r'^(?P<slug>.+?) · final · r\d+ · publish-ready$')


def check_drive_create(root, tool_input):
    """FLOW-6 on the Doc itself: checked before the Doc exists, so no mislabelled copy is ever created (ADR-012). The label
    is caught in any spelling, and a labelled Doc must carry exactly the final that qualifies, as doc-copy.py prints it."""
    title = str(tool_input.get('title') or '')
    if not w.claims_publish_ready(title):
        return
    m = PUBLISH_READY_TITLE.match(title)
    slug = m.group('slug') if m else None
    if not slug or not w.SLUG.match(slug):
        w.block('FLOW-6', f'a Doc titled "{title[:80]}" claims to be publish-ready but is not titled as one article\'s final.',
                'use the title the doc-copy script prints: <slug> · final · r<k> · publish-ready.')
    if not w.publish_ready_or_false(root, slug):
        w.block('FLOW-6', f'articles/{slug}/final.md is not publish-ready (it needs a non-empty Signed-off-by on a current G4 PASS and no '
                'unverified-claim marker), so no Doc may be labelled publish-ready.',
                'make the copy under the title the doc-copy script prints now, which carries no publish-ready label.')
    expected = w.doc_text(w.read_text(os.path.join(w.article_dir(root, slug), 'final.md')), 'final', keep_signoff=True)
    if tool_input.get('base64Content') is not None or tool_input.get('textContent') != expected:
        w.block('FLOW-6', f'a publish-ready Doc must carry exactly articles/{slug}/final.md as signed off (fact IDs stripped); this '
                'upload carries other content.', 'upload the text the doc-copy script prints, as textContent, unchanged.')


def check_drive_update(tool_input):
    """FLOW-6 on a rename: a title change cannot be checked against the Doc's content, so no Doc is renamed onto the label.
    A final that qualifies gets its labelled Doc from a new upload, which check_drive_create judges (ADR-012)."""
    title = tool_input.get('title')
    if isinstance(title, str) and w.claims_publish_ready(title):
        w.block('FLOW-6', f'no Doc may be renamed to "{title[:80]}": a publish-ready Doc is only ever created from the signed final.',
                'run the copy skill on the final; it uploads a new revision under the publish-ready title when the final qualifies.')


def _strings(value):
    """Every string inside a tool input, at any depth."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _strings(v)


@fail_closed('FLOW-2', 'a stage start')
def check_stage(root, slug, stage):
    fault('stage')
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
    if not w.approved(root, slug, prev):
        w.block('FLOW-2', f'the {stage} may not be written: `{w.approval_key(prev)}:` in {prev}.md has no value. An empty line is not approval.',
                f'a human approves the {prev} in its Google Doc and runs writer-plugin:sync, or writes their name after `{w.approval_key(prev)}:` in the file.')


def check_target(root, rel, tool, tool_input):
    parts = w.split_article(rel)
    if not parts:
        return
    slug, rest = parts
    # compared in lower case: the default macOS filesystem is case-insensitive, so `Final.md` is final.md
    low = rest.lower()
    if low.startswith('gates/') or low == 'gates':
        check_gates(root, slug, rest[len('gates/'):], tool, tool_input)
    elif low == '.prose-lint.json':
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prose-lint.py')
        w.block('FLOW-4', f'articles/{slug}/.prose-lint.json is the record of a real prose-lint run; a tool may not write it (the G4 gate trusts it).',
                f'run: python3 {script} --record articles/{slug}/final.md')
    elif low == '.quote-check.json':
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'quote-check.py')
        w.block('FLOW-4', f'articles/{slug}/.quote-check.json is the record of a real quote-check run; a tool may not write it (the G1 gate trusts it).',
                f'run: python3 {script} --record {slug}')
    elif low == 'docs.json':
        check_docs(root, slug, rel, tool, tool_input)
    elif low == w.CREATED_LOG or low == 'approvals' or low.startswith('approvals/'):
        w.block('FLOW-4', f'articles/{slug}/{rest} is written by the record-approval hook from what the Google Doc says; a tool may not write it.',
                'a human writes their name in the Doc and runs writer-plugin:sync; the hook records it.')
    elif low in ('brief.md', 'research.md', 'outline.md', 'draft.md', 'final.md'):
        if tool == 'Bash' and re.search(r'approved-by|signed-off-by', str(tool_input.get('command') or ''), re.I):
            w.block('FLOW-6' if low == 'final.md' else 'FLOW-2', f'a shell command that names an approval label may not write articles/{slug}/{low}: the guard cannot see what it writes.',
                    'the human writes their name in the Doc and runs writer-plugin:sync, or types it in the file; stage actors write with the Write tool.')
        check_stage(root, slug, low[:-3])
        if low == 'final.md' and tool in ('Write', 'Edit'):
            text = w.resulting_text(root, rel, tool, tool_input)
            if text is None:
                sys.stderr.write(f'[writer-plugin] guard-stage-order could not work out the content of {rel}, so the sign-off check was skipped.\n')
            else:
                check_signoff(root, slug, text)
        if tool in ('Write', 'Edit'):
            check_approval_write(root, slug, low[:-3], rel, tool, tool_input)


def main():
    p = w.read_payload()
    root = w.project_dir(p)
    cwd = p.get('cwd') or root
    tool, ti = p.get('tool_name'), p.get('tool_input')
    doc_tool = isinstance(tool, str) and any(tool.startswith(p) for p in DOC_PREFIXES)
    if doc_tool and not isinstance(ti, dict):
        w.block('FLOW-6', f'{tool} was called with input the guard cannot read, so it is refused.', 'call the tool with its normal arguments.')
    if not isinstance(ti, dict):
        return
    if tool == DRIVE_CREATE:
        check_drive_create(root, ti)
        check_create_rules(root, ti)
        return
    if doc_tool:
        if tool == DRIVE_UPDATE:
            check_drive_update(ti)
        check_doc_tool(root, tool, ti)
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
