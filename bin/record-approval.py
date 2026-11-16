#!/usr/bin/env python3
"""Records the Docs the copy skill creates and the approval a Doc carries (ADR-016). PostToolUse: Drive create_file and read_file_content.

On `create_file` it logs the new Doc in `articles/<slug>/.docs-created.json` only when its title is an article title and its text is exactly
`doc_text` of the artifact on disk: a Doc made any other way (a filled line, a copy, other text) never enters the log, so it can never yield an
approval. On `read_file_content` of a logged Doc that is the latest revision of its stage it compares the Doc body with the artifact, and writes
`articles/<slug>/approvals/<stage>.r<rev>.json` with the name typed after the approval label, or with the reason there is none. The model never
parses a Doc: this hook reads what the connector returned. Only this script writes either file; the guard refuses a tool write (ADR-016).
"""
import datetime
import json
import os
from typing import Optional, Tuple

from lib import writer as w

DRIVE_CREATE = 'mcp__claude_ai_Google_Drive__create_file'
DRIVE_READ = 'mcp__claude_ai_Google_Drive__read_file_content'


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')


def write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(data, fh)
    os.replace(tmp, path)


def log_created(root: str, tool_input: dict, response: object) -> None:
    parts = w.parse_doc_title(str(tool_input.get('title') or ''))
    result = w.tool_result(response)
    doc_id = result.get('id') if result else None
    if not parts or not isinstance(doc_id, str) or not doc_id:
        return
    slug, stage = str(parts['slug']), str(parts['stage'])
    if not os.path.isfile(os.path.join(w.article_dir(root, slug), f'{stage}.md')) or tool_input.get('base64Content') is not None:
        return
    ready = parts['label'] == 'publish-ready'
    artifact = w.read_text(os.path.join(w.article_dir(root, slug), f'{stage}.md'))
    uploaded = tool_input.get('textContent')
    if uploaded != w.doc_text(artifact, stage, keep_signoff=ready):
        return
    docs = w.created_log(root, slug)
    docs = [d for d in docs if d.get('id') != doc_id] + [{
        'id': doc_id, 'title': tool_input.get('title'), 'slug': slug, 'stage': stage, 'rev': parts['rev'], 'label': parts['label'],
        'text_sha256': w.text_hash(uploaded), 'approvable': not ready, 'at': now()}]
    write_json(os.path.join(w.article_dir(root, slug), w.CREATED_LOG), {'docs': docs})


def find_logged(root: str, doc_id: str) -> Optional[Tuple[str, dict]]:
    for slug in w.article_slugs(root):
        try:
            for d in w.created_log(root, slug):
                if d.get('id') == doc_id:
                    return slug, d
        except ValueError:
            continue
    return None


def record_read(root: str, tool_input: dict, response: object) -> None:
    doc_id = tool_input.get('fileId')
    result = w.tool_result(response)
    body = result.get('fileContent') if result else None
    found = find_logged(root, doc_id) if isinstance(doc_id, str) else None
    if not found or not isinstance(body, str) or not found[1].get('approvable'):
        return
    slug, doc = found
    stage = str(doc['stage'])
    rows = [e for e in w.docs_index(root, slug) if e.get('stage') == stage]
    entry = next((e for e in rows if e.get('id') == doc_id), None)
    if entry is None or int(entry.get('rev') or 0) != max(int(e.get('rev') or 0) for e in rows):
        return  # not recorded by the copy skill, or an older revision: nothing to say about it
    rev = int(entry['rev'])
    artifact = w.read_text(os.path.join(w.article_dir(root, slug), f'{stage}.md'))
    value, reason = None, None
    if w.text_hash(w.doc_text(artifact, stage)) != doc.get('text_sha256'):
        reason = 'the artifact changed since this Doc was made'
    elif not w.doc_equals_artifact(root, slug, stage, body):
        reason = 'the Doc text differs from the artifact (it was edited in the Doc)'
    else:
        value = w.doc_approval(body, stage)
        if value is None:
            reason = 'no name after the approval label in the Doc'
    write_json(w.approval_path(root, slug, stage, rev), {
        'doc_id': doc_id, 'rev': rev, 'artifact_sha256': w.text_hash(artifact), 'value': value, 'reason': reason, 'at': now()})


def main() -> None:
    p = w.read_payload()
    root = w.project_dir(p)
    ti = p.get('tool_input')
    if not isinstance(ti, dict):
        return
    if p.get('tool_name') == DRIVE_CREATE:
        log_created(root, ti, p.get('tool_response'))
    elif p.get('tool_name') == DRIVE_READ:
        record_read(root, ti, p.get('tool_response'))


w.fail_open(main, 'record-approval')
