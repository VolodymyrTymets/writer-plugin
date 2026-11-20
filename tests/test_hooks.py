"""Hook behaviour against throwaway workspaces. Run: python -m pytest tests/test_hooks.py

Each test builds a small content workspace under tmp_path (neutral synthetic articles, PLG-1) and runs the real script as a
subprocess with the JSON payload Claude Code sends, the way the hooks run in a session. Payload shapes were observed with a
probe plugin (docs/decisions/ADR-009): Write has file_path and content, Edit has file_path/old_string/new_string/replace_all,
Bash has command; a block is exit 2 with the reason on stderr.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import namedtuple
from pathlib import Path

import pytest

from conftest import PLUGIN
from lib import writer

Result = namedtuple('Result', 'code out err')
BIN = PLUGIN / 'bin'
PASS = {
    'brief': '## G0 brief gate: PASS (0 blocking, 0 advisory)',
    'research': '## G1 research gate: PASS (0 blocking, 0 advisory)',
    'outline': '## G2 outline gate: PASS (0 blocking, 1 advisory)',
    'draft': '## G3 draft gate: PASS (0 blocking, 0 advisory)',
    'final': '## G4 final gate: PASS (0 blocking, 0 advisory)',
}
BLOCK = {
    'brief': '## G0 brief gate: BLOCK (1 blocking, 0 advisory)',
    'research': '## G1 research gate: BLOCK (1 blocking, 0 advisory)',
    'outline': '## G2 outline gate: BLOCK (2 blocking, 0 advisory)',
    'final': '## G4 final gate: BLOCK (1 blocking, 0 advisory)',
}
# line 3 of a saved verdict as the gate prints it (FT-13); G0 has none
COUNT = {'research': 'Coverage: 1 answered, 0 open (of 1)', 'outline': 'Markers: 0', 'draft': 'Outline: 1 of 1 sections present', 'final': 'Markers: 0'}


def head(stage, line, artifact='x', count=None):
    """A verdict's first three lines as the gate prints them (G0 has two)."""
    lines = [line, f'Artifact: {artifact}']
    if stage != 'brief':
        lines.append(count if count is not None else COUNT[stage])
    return '\n'.join(lines) + '\n'


GATE = {'brief': 'G0', 'research': 'G1', 'outline': 'G2', 'draft': 'G3', 'final': 'G4'}
STAGES = ['brief', 'research', 'outline', 'draft', 'final']
OUTLINE = '# Outline\n\nApproved-by:{approval}\n\n## Thesis\nA thesis.\n'


def run(script, payload, root, raw=None, env=None):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root), **(env or {}))
    data = raw if raw is not None else json.dumps(dict(payload, cwd=str(root)))
    r = subprocess.run([sys.executable, str(BIN / script)], input=data, capture_output=True, text=True, env=env, cwd=str(root))
    return Result(r.returncode, r.stdout, r.stderr)


def write_payload(rel, content='x'):
    return {'hook_event_name': 'PreToolUse', 'tool_name': 'Write', 'tool_input': {'file_path': rel, 'content': content}}


def edit_payload(rel):
    return {'hook_event_name': 'PreToolUse', 'tool_name': 'Edit',
            'tool_input': {'file_path': rel, 'old_string': 'a', 'new_string': 'b', 'replace_all': False}}


def bash_payload(command):
    return {'hook_event_name': 'PreToolUse', 'tool_name': 'Bash', 'tool_input': {'command': command}}


def guard(root, payload, env=None, **kw):
    return run('guard-stage-order.py', payload, root, env=env, **kw)


class Workspace:
    def __init__(self, root: Path, slug='demo'):
        self.root, self.slug = root, slug
        self.art = root / 'articles' / slug
        (self.art / 'gates').mkdir(parents=True)
        for stage in STAGES:
            # WHY: FLOW-2 now covers every stage (ADR-016), so an artifact the chain has passed is approved by default; the outline and the
            # final keep the empty line the tests drive explicitly.
            body = f'# {stage}\n\ntext\n' + ('' if stage in ('final',) else '\nApproved-by: Test Human\n')
            (self.art / f'{stage}.md').write_text(OUTLINE.format(approval='') if stage == 'outline' else body)

    def rel(self, name):
        return f'articles/{self.slug}/{name}'

    def verdict(self, stage, k, line, sidecar=False, archived=False):
        d = self.art / 'gates' / ('archive' if archived else '')
        d.mkdir(parents=True, exist_ok=True)
        name = f'{GATE[stage]}-{stage}.r{k}.md'
        (d / name).write_text(line + f'\nArtifact: {self.rel(stage + ".md")}\n')
        if sidecar and not archived:
            writer.write_sidecar(str(self.root), self.slug, name)
        return name

    def chain(self, upto, sidecars=True):
        """A PASS verdict for every gate before `upto`, each recorded in order, as a real flow would leave them."""
        for stage in STAGES[:STAGES.index(upto)]:
            self.verdict(stage, 1, PASS[stage], sidecar=sidecars)

    def approve(self, value=' Test Human 2026-11-13'):
        (self.art / 'outline.md').write_text(OUTLINE.format(approval=value))


@pytest.fixture
def ws(tmp_path):
    return Workspace(tmp_path)


# ---------------- FLOW-1: a stage starts only after the previous gate's PASS ----------------
@pytest.mark.parametrize('stage', ['research', 'outline', 'draft', 'final'])
def test_a_stage_write_is_allowed_after_the_previous_pass(ws, stage):
    ws.chain(stage)
    ws.approve()
    assert guard(ws.root, write_payload(ws.rel(f'{stage}.md'))).code == 0


@pytest.mark.parametrize('stage', ['research', 'outline', 'draft', 'final'])
def test_a_stage_write_is_blocked_with_no_previous_verdict(ws, stage):
    ws.approve()
    r = guard(ws.root, write_payload(ws.rel(f'{stage}.md')))
    assert r.code == 2 and 'FLOW-1' in r.err


@pytest.mark.parametrize('line', [
    BLOCK['brief'], '## G0 brief gate: PASS', '## G0 brief gate: PASS (1 blocking, 0 advisory)', 'PASS', ''],
    ids=['a-block', 'no-counts', 'contradictory-counts', 'bare-pass', 'empty'])
def test_a_verdict_that_is_not_a_valid_pass_does_not_unlock_the_next_stage(ws, line):
    ws.verdict('brief', 1, line)
    r = guard(ws.root, write_payload(ws.rel('research.md')))
    assert r.code == 2 and 'FLOW-1' in r.err


def test_the_latest_verdict_decides_not_an_earlier_pass(ws):
    ws.verdict('brief', 1, PASS['brief'])
    ws.verdict('brief', 2, BLOCK['brief'])
    assert guard(ws.root, write_payload(ws.rel('research.md'))).code == 2


# ---------------- FLOW-2: no draft without a non-empty Approved-by ----------------
@pytest.mark.parametrize('approval,expected', [('', 2), ('   ', 2), (' Test Human 2026-11-13', 0)], ids=['empty', 'spaces', 'named'])
def test_a_draft_needs_a_non_empty_approval(ws, approval, expected):
    ws.chain('draft')
    ws.approve(approval)
    r = guard(ws.root, write_payload(ws.rel('draft.md')))
    assert r.code == expected
    if expected:
        assert 'FLOW-2' in r.err


# ---------------- FLOW-3: two BLOCKs stop a stage ----------------
def test_two_block_files_stop_the_stage_that_owns_the_gate(ws):
    ws.chain('outline')
    ws.verdict('outline', 1, BLOCK['outline'])
    assert guard(ws.root, write_payload(ws.rel('outline.md'))).code == 0
    ws.verdict('outline', 2, BLOCK['outline'])
    r = guard(ws.root, write_payload(ws.rel('outline.md')))
    assert r.code == 2 and 'FLOW-3' in r.err


def test_the_brief_is_guarded_for_flow_3_only(ws):
    assert guard(ws.root, write_payload(ws.rel('brief.md'))).code == 0
    assert guard(ws.root, write_payload(ws.rel('brief.source.md'))).code == 0
    ws.verdict('brief', 1, BLOCK['brief'])
    ws.verdict('brief', 2, BLOCK['brief'])
    assert guard(ws.root, write_payload(ws.rel('brief.md'))).code == 2
    assert guard(ws.root, write_payload(ws.rel('brief.source.md'))).code == 0


# ---------------- stale verdicts (open questions 5 and 6) ----------------
def test_a_rebuilt_upstream_makes_the_downstream_verdict_stale(ws):
    ws.chain('outline')
    assert guard(ws.root, write_payload(ws.rel('outline.md'))).code == 0
    ws.verdict('brief', 2, PASS['brief'], sidecar=True)          # the brief was rebuilt and re-gated
    r = guard(ws.root, write_payload(ws.rel('outline.md')))
    assert r.code == 2 and 'stale' in r.err.lower()


def test_a_hand_edit_after_the_verdict_makes_it_stale(ws):
    ws.chain('outline')
    (ws.art / 'research.md').write_text('# research\n\nedited by hand\n')
    r = guard(ws.root, write_payload(ws.rel('outline.md')))
    assert r.code == 2 and 'changed since' in r.err


def test_writing_the_approval_line_does_not_make_the_verdict_stale(ws):
    ws.chain('draft')
    ws.verdict('outline', 1, PASS['outline'], sidecar=True)      # recorded while Approved-by was still empty
    ws.approve()
    assert guard(ws.root, write_payload(ws.rel('draft.md'))).code == 0


def test_a_hand_edit_of_the_outline_blocks_the_draft_until_a_new_verdict_is_saved(ws):
    ws.chain('draft')
    ws.verdict('outline', 1, PASS['outline'], sidecar=True)
    ws.approve()
    (ws.art / 'outline.md').write_text(OUTLINE.format(approval=' Test Human 2026-11-13') + 'One edited line.\n')
    assert guard(ws.root, write_payload(ws.rel('draft.md'))).code == 2
    ws.verdict('outline', 2, PASS['outline'], sidecar=True)      # the re-gate, saved as the next verdict
    assert guard(ws.root, write_payload(ws.rel('draft.md'))).code == 0


# ---------------- legacy articles (no sidecars) and the per-gate rule ----------------
def test_a_legacy_chain_with_no_sidecars_skips_the_hash_checks(ws):
    ws.chain('draft', sidecars=False)
    ws.verdict('outline', 1, PASS['outline'])
    ws.approve()
    (ws.art / 'research.md').write_text('# research\n\nedited\n')
    assert guard(ws.root, write_payload(ws.rel('draft.md'))).code == 0


def test_a_legacy_chain_plus_one_new_verdict_still_allows_the_next_stage(ws):
    ws.chain('outline', sidecars=False)
    ws.verdict('outline', 1, PASS['outline'], sidecar=True)      # first recorded verdict; its upstream is a legacy file name
    ws.approve()
    assert guard(ws.root, write_payload(ws.rel('draft.md'))).code == 0


def test_a_gate_whose_latest_verdict_lost_its_sidecar_is_blocked(ws):
    ws.chain('outline')
    ws.verdict('outline', 1, PASS['outline'], sidecar=True)
    ws.verdict('outline', 2, PASS['outline'], sidecar=False)
    ws.approve()
    r = guard(ws.root, write_payload(ws.rel('draft.md')))
    assert r.code == 2 and 'sidecar' in r.err


# ---------------- verdicts are immutable and carefully created (FLOW-4, ADR-004) ----------------
def test_an_existing_verdict_cannot_be_overwritten_or_edited(ws):
    name = ws.verdict('brief', 1, PASS['brief'])
    assert guard(ws.root, write_payload(ws.rel(f'gates/{name}'), PASS['brief'])).code == 2
    assert guard(ws.root, edit_payload(ws.rel(f'gates/{name}'))).code == 2


def test_a_new_verdict_with_the_right_number_and_line_1_is_allowed(ws):
    ws.verdict('brief', 1, PASS['brief'])
    r = guard(ws.root, write_payload(ws.rel('gates/G0-brief.r2.md'), head('brief', BLOCK['brief'])))
    assert r.code == 0


@pytest.mark.parametrize('name,content,why', [
    ('G0-brief.r2.md', 'PASS\nArtifact: x\n', 'a malformed line 1'),
    ('G0-brief.r2.md', '## G1 research gate: PASS (0 blocking, 0 advisory)\n', "another gate's line 1"),
    ('G0-brief.r3.md', PASS['brief'] + '\n', 'a skipped number'),
    ('G0-brief.r1.md', PASS['brief'] + '\n', 'a number that already exists'),
    ('G0-research.r2.md', PASS['brief'] + '\n', 'a gate and stage that do not pair'),
    ('G0-brief.r2.json', '{}', 'a sidecar written by a tool'),
    ('notes.md', 'hello', 'a file that is not a verdict'),
], ids=['bad-line-1', 'wrong-gate-line', 'skipped-number', 'existing-number', 'bad-pair', 'sidecar', 'not-a-verdict'])
def test_a_bad_new_verdict_is_blocked(ws, name, content, why):
    ws.verdict('brief', 1, PASS['brief'])
    assert guard(ws.root, write_payload(ws.rel(f'gates/{name}'), content)).code == 2, why


@pytest.mark.parametrize('stage,content,want', [
    ('brief', PASS['brief'] + '\n\nArtifact: x\n', 'line 2'),
    ('brief', PASS['brief'] + '\n Artifact: x\n', 'line 2'),
    ('brief', PASS['brief'] + '\n\ufeffArtifact: x\n', 'line 2'),
    ('brief', PASS['brief'] + '\nArtifact: \n', 'line 2'),
    ('brief', PASS['brief'] + '\n', 'line 2'),
    ('research', PASS['research'] + '\nArtifact: x\n\n' + COUNT['research'] + '\n', 'Coverage:'),
    ('research', PASS['research'] + '\nArtifact: x\n', 'Coverage:'),
    ('research', PASS['research'] + '\nArtifact: x\nMarkers: 0\n', 'Coverage:'),
    ('outline', PASS['outline'] + '\nArtifact: x\n\nMarkers: 0\n', 'Markers:'),
    ('draft', PASS['draft'] + '\nArtifact: x\nMarkers: 0\n', 'Outline:'),
    ('final', PASS['final'] + '\nArtifact: x\n\nMarkers: 0\n', 'Markers:'),
], ids=['blank-line-2', 'leading-space-line-2', 'bom-line-2', 'empty-artifact-value', 'one-line-verdict', 'blank-line-3-g1', 'two-line-g1',
        'wrong-label-g1', 'blank-line-3-g2', 'wrong-label-g3', 'blank-line-3-g4'])
def test_a_verdict_whose_header_lines_are_not_as_printed_is_blocked_and_the_message_says_which(ws, stage, content, want):
    ws.chain(stage)
    r = guard(ws.root, write_payload(ws.rel(f'gates/{GATE[stage]}-{stage}.r1.md'), content))
    assert r.code == 2 and 'FLOW-4' in r.err and want in r.err


@pytest.mark.parametrize('stage,eol', [('brief', '\n'), ('draft', '\r\n'), ('brief', '\r\n')], ids=['g0-free-line-3', 'crlf-g3', 'crlf-g0'])
def test_a_verdict_with_the_printed_header_is_allowed(ws, stage, eol):
    ws.approve()
    ws.chain(stage)
    content = head(stage, PASS[stage]).replace('\n', eol)
    if stage == 'brief':
        content += eol + 'free text on line 3' + eol
    assert guard(ws.root, write_payload(ws.rel(f'gates/{GATE[stage]}-{stage}.r1.md'), content)).code == 0


def test_the_next_number_continues_past_the_archive(ws):
    ws.verdict('brief', 1, PASS['brief'], archived=True)
    ws.verdict('brief', 2, BLOCK['brief'], archived=True)
    assert guard(ws.root, write_payload(ws.rel('gates/G0-brief.r1.md'), PASS['brief'] + '\n')).code == 2   # collides with the archive
    assert guard(ws.root, write_payload(ws.rel('gates/G0-brief.r3.md'), head('brief', PASS['brief']))).code == 0


# ---------------- Bash writes ----------------
@pytest.mark.parametrize('command', [
    'echo hi > articles/demo/draft.md',
    'cat <<EOF > articles/demo/draft.md\nx\nEOF',
    'printf x | tee articles/demo/draft.md',
    'cp /tmp/x articles/demo/draft.md',
    'mv /tmp/x articles/demo/draft.md',
    "sed -i 's/a/b/' articles/demo/draft.md",
], ids=['redirect', 'heredoc', 'tee', 'cp', 'mv', 'sed-i'])
def test_a_bash_write_to_a_stage_artifact_follows_the_same_rules(ws, command):
    ws.chain('draft')
    ws.approve('')
    assert guard(ws.root, bash_payload(command)).code == 2
    ws.approve()
    assert guard(ws.root, bash_payload(command)).code == 0


@pytest.mark.parametrize('command', [
    'echo x > articles/demo/gates/G0-brief.r2.md',
    'cat <<EOF > articles/demo/gates/G0-brief.r2.md\nx\nEOF',
    'mv articles/demo/gates/G0-brief.r1.md articles/demo/gates/archive/',
    'rm articles/demo/gates/G0-brief.r1.md',
    'cp articles/demo/gates/G0-brief.r1.md /tmp/copy.md',
    'tee articles/demo/gates/G0-brief.r2.md',
], ids=['redirect', 'heredoc', 'mv', 'rm', 'cp-out', 'tee'])
def test_bash_cannot_touch_the_gates_folder(ws, command):
    ws.verdict('brief', 1, PASS['brief'])
    r = guard(ws.root, bash_payload(command))
    assert r.code == 2 and 'gates' in r.err


@pytest.mark.parametrize('command', [
    'ls articles/demo/gates/',
    'cat articles/demo/gates/G0-brief.r1.md',
    'grep BLOCK articles/demo/gates/*.md',
    'git status',
    'head -3 articles/demo/gates/G0-brief.r1.md | wc -l',
    'echo "a -> b" ; echo done',
    'python3 -c "print(1)"',
    'echo hi > /tmp/elsewhere.md',
    'cat <<EOF > /tmp/note.md\nx > y\nEOF',
], ids=['ls', 'cat', 'grep', 'git-status', 'head-pipe', 'arrow-in-text', 'python-c', 'outside-articles', 'heredoc-elsewhere'])
def test_bash_reads_and_unrelated_writes_are_allowed(ws, command):
    ws.verdict('brief', 1, PASS['brief'])
    assert guard(ws.root, bash_payload(command)).code == 0


def test_a_block_message_for_moving_a_verdict_says_to_archive_by_hand(ws):
    ws.verdict('brief', 1, PASS['brief'])
    r = guard(ws.root, bash_payload('mv articles/demo/gates/G0-brief.r1.md articles/demo/gates/archive/'))
    assert 'by hand' in r.err


# ---------------- scope and failure ----------------
@pytest.mark.parametrize('rel', ['notes.md', 'articles/demo/outline.prev.1.md', 'articles/demo/draft.prev.1.md', 'articles/demo/final.prev.2.md', 'docs/x.md'])
def test_paths_that_are_not_guarded_are_allowed(ws, rel):
    assert guard(ws.root, write_payload(rel)).code == 0


def test_an_absolute_path_outside_the_workspace_is_allowed(ws, tmp_path_factory):
    other = tmp_path_factory.mktemp('elsewhere')
    assert guard(ws.root, write_payload(str(other / 'articles' / 'demo' / 'draft.md'))).code == 0


@pytest.mark.parametrize('raw', ['not json', '', '[]', '{"tool_name": "Write", "tool_input": []}'], ids=['garbage', 'empty', 'list', 'bad-tool-input'])
def test_a_hook_that_cannot_read_its_input_allows_the_action(ws, raw):
    assert guard(ws.root, None, raw=raw).code == 0


# ---------------- record-verdict (PostToolUse on Write) ----------------
def post(rel):
    return {'hook_event_name': 'PostToolUse', 'tool_name': 'Write', 'tool_input': {'file_path': rel, 'content': 'x'}}


def test_a_saved_verdict_gets_a_sidecar_with_the_artifact_hash_and_the_upstream_verdict(ws):
    ws.verdict('brief', 1, PASS['brief'], sidecar=True)
    name = ws.verdict('research', 1, PASS['research'])
    assert run('record-verdict.py', post(ws.rel(f'gates/{name}')), ws.root).code == 0
    sc = json.loads((ws.art / 'gates' / 'G1-research.r1.json').read_text())
    assert sc['artifact_sha256'] == writer.artifact_hash(str(ws.root), ws.slug, 'research')
    assert sc['upstream'] == 'G0-brief.r1.md'


def test_the_first_gate_has_no_upstream(ws):
    name = ws.verdict('brief', 1, PASS['brief'])
    run('record-verdict.py', post(ws.rel(f'gates/{name}')), ws.root)
    assert json.loads((ws.art / 'gates' / 'G0-brief.r1.json').read_text())['upstream'] is None


@pytest.mark.parametrize('rel', ['articles/demo/outline.md', 'articles/demo/gates/notes.md', 'notes.md'])
def test_record_verdict_ignores_other_writes(ws, rel):
    assert run('record-verdict.py', post(rel), ws.root).code == 0
    assert not list((ws.art / 'gates').glob('*.json'))


def test_the_artifact_hash_ignores_the_approval_lines():
    a = writer.strip_approval('# T\n\nApproved-by:\n\nbody\n')
    b = writer.strip_approval('# T\n\nApproved-by: Someone 2026-11-13\n\nbody\n')
    c = writer.strip_approval('# T\n\nSigned-off-by: Someone\n\nbody\n')
    assert a == b and 'Signed-off-by' not in c
    # adding an approval line where there was none must not change what a verdict covers either
    assert writer.strip_approval('# T\n\nbody\n') == writer.strip_approval('# T\n\nbody\n\nSigned-off-by: Someone\n')
    assert writer.strip_approval('# T\n\nbody changed\n') != a


# ---------------- contracts shared with the rest of the repo ----------------
def test_the_verdict_pattern_equals_the_one_in_the_skill_contract_tests():
    from test_skills import VERDICT_LINE
    assert writer.VERDICT_LINE.pattern == VERDICT_LINE.pattern


def test_hooks_json_registers_the_guard_and_the_recorder_on_the_tools_that_exist():
    hooks = json.loads((PLUGIN / 'hooks' / 'hooks.json').read_text())['hooks']
    pre = [g for g in hooks['PreToolUse'] if any('guard-stage-order' in h['command'] for h in g['hooks'])]
    post_ = [g for g in hooks['PostToolUse'] if any('record-verdict' in h['command'] for h in g['hooks'])]
    assert pre and post_
    # MultiEdit does not exist in this build (ADR-009). The MCP tools parsed are the Drive create and update calls, for FLOW-6 on a Doc title (ADR-012).
    # WHY: the guard now judges every Drive and Docs connector call that names a Doc (ADR-016, R3), so the matcher is the two server prefixes
    assert pre[0]['matcher'] == 'Edit|Write|Bash|mcp__claude_ai_Google_Drive__.*|mcp__claude_ai_Google_Docs__.*'
    assert post_[0]['matcher'] == 'Write'


# ---------------- session-context (SessionStart) ----------------
def session(root, state_dir, session_id='s1', source='startup'):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root), WRITER_PLUGIN_STATE_DIR=str(state_dir))
    payload = json.dumps({'hook_event_name': 'SessionStart', 'session_id': session_id, 'source': source, 'cwd': str(root)})
    r = subprocess.run([sys.executable, str(BIN / 'session-context.py')], input=payload, capture_output=True, text=True, env=env, cwd=str(root))
    return Result(r.returncode, r.stdout, r.stderr)


def state_file(state_dir, session_id='s1'):
    return Path(state_dir) / f'{session_id}.json'


def test_session_context_is_silent_outside_a_writer_workspace(tmp_path):
    r = session(tmp_path, tmp_path / 'state')
    assert r.code == 0 and r.out == ''


def test_session_context_lists_each_article_with_its_stage_and_what_it_waits_for(ws, tmp_path):
    ws.chain('outline')
    ws.verdict('outline', 1, PASS['outline'], sidecar=True)
    other = Workspace(ws.root, slug='second')
    r = session(ws.root, tmp_path / 'state')
    assert r.code == 0 and r.out.startswith('## Writer workspace')
    assert 'demo' in r.out and 'second' in r.out and len(r.out.strip().split('\n')) <= 30


@pytest.mark.parametrize('setup,expect', [
    ('nothing', 'G0'),
    ('outline-pass-unapproved', 'Approved-by'),
    ('outline-pass-approved', 'G3-draft'),
    ('approved-no-draft', 'draft stage'),
    ('stopped', 'STOPPED'),
    ('block', 'BLOCK'),
    ('stale', 'stale'),
    ('markers', '2 marker'),
], ids=['no-verdict', 'waiting-for-approval', 'approved', 'approved-no-draft', 'stopped', 'block', 'stale', 'markers'])
def test_session_context_says_what_each_article_is_waiting_for(ws, tmp_path, setup, expect):
    if setup == 'nothing':
        pass
    elif setup in ('outline-pass-unapproved', 'outline-pass-approved', 'approved-no-draft', 'markers'):
        ws.chain('outline')
        ws.verdict('outline', 1, PASS['outline'], sidecar=True)
        if setup in ('outline-pass-approved', 'approved-no-draft'):
            ws.approve()
        if setup == 'approved-no-draft':
            (ws.art / 'draft.md').unlink()
            (ws.art / 'final.md').unlink()
        if setup == 'markers':
            (ws.art / 'outline.md').write_text(OUTLINE.format(approval='') + "<Can't be verified. Reason: a.>\n<Can't be verified. Reason: b.>\n")
            ws.verdict('outline', 2, PASS['outline'], sidecar=True)
    elif setup == 'stopped':
        ws.chain('outline')
        ws.verdict('outline', 1, BLOCK['outline'])
        ws.verdict('outline', 2, BLOCK['outline'])
    elif setup == 'block':
        ws.chain('outline')
        ws.verdict('outline', 1, BLOCK['outline'])
    elif setup == 'stale':
        ws.chain('outline')
        ws.verdict('brief', 2, PASS['brief'], sidecar=True)
    assert expect in session(ws.root, tmp_path / 'state').out


def test_session_context_caps_its_output_at_30_lines(tmp_path):
    for i in range(40):
        Workspace(tmp_path, slug=f'article-{i:02d}')
    out = session(tmp_path, tmp_path / 'state').out.strip().split('\n')
    assert len(out) <= 30 and 'more' in out[-1]


def test_the_session_start_is_recorded_once_and_not_moved_by_a_resume(ws, tmp_path):
    state = tmp_path / 'state'
    session(ws.root, state)
    first = json.loads(state_file(state).read_text())['started']
    session(ws.root, state, source='resume')
    assert json.loads(state_file(state).read_text())['started'] == first


# ---------------- verify-final (Stop) ----------------
def stop(root, state_dir, session_id='s1', active=False):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root), WRITER_PLUGIN_STATE_DIR=str(state_dir))
    payload = json.dumps({'hook_event_name': 'Stop', 'session_id': session_id, 'stop_hook_active': active, 'cwd': str(root)})
    r = subprocess.run([sys.executable, str(BIN / 'verify-final.py')], input=payload, capture_output=True, text=True, env=env, cwd=str(root))
    return Result(r.returncode, r.stdout, r.stderr)


def started(state_dir, when, session_id='s1'):
    Path(state_dir).mkdir(parents=True, exist_ok=True)
    state_file(state_dir, session_id).write_text(json.dumps({'started': when, 'blocked': []}))


def test_a_final_written_this_session_without_a_lint_record_blocks_once_and_quotes_the_command(ws, tmp_path):
    state = tmp_path / 'state'
    started(state, 0)
    (ws.art / 'final.md').write_text('# Final\n\nbody\n')
    first = stop(ws.root, state)
    assert first.code == 2 and 'prose-lint.py' in first.err and '--record' in first.err and 'articles/demo/final.md' in first.err
    script = [t for t in first.err.replace('"', ' ').split() if t.endswith('prose-lint.py')][0]
    assert os.path.exists(script), 'the quoted path must exist: bin/ is not in a workspace (ADR-005)'
    assert stop(ws.root, state).code == 0, 'blocked once per article and session, not twice'


def test_stop_hook_active_never_blocks(ws, tmp_path):
    started(tmp_path / 'state', 0)
    (ws.art / 'final.md').write_text('# Final\n')
    assert stop(ws.root, tmp_path / 'state', active=True).code == 0


def test_a_clean_lint_record_lets_the_session_stop(ws, tmp_path):
    started(tmp_path / 'state', 0)
    text = '# Final\n\nbody\n'
    (ws.art / 'final.md').write_text(text)
    (ws.art / '.prose-lint.json').write_text(json.dumps({'file': 'final.md', 'sha256': writer.text_hash(text), 'findings': 3, 'at': 'x'}))
    assert stop(ws.root, tmp_path / 'state').code == 0     # a run is what is required, not zero findings


def test_a_sign_off_only_change_does_not_ask_for_another_lint_run(ws, tmp_path):
    started(tmp_path / 'state', 0)
    text = '# Final\n\nbody\n'
    (ws.art / '.prose-lint.json').write_text(json.dumps({'file': 'final.md', 'sha256': writer.text_hash(text), 'findings': 0, 'at': 'x'}))
    (ws.art / 'final.md').write_text(text + '\nSigned-off-by: Test Human\n')
    assert stop(ws.root, tmp_path / 'state').code == 0


def test_an_edit_after_the_lint_run_asks_for_another(ws, tmp_path):
    started(tmp_path / 'state', 0)
    (ws.art / '.prose-lint.json').write_text(json.dumps({'file': 'final.md', 'sha256': writer.text_hash('# Final\n'), 'findings': 0, 'at': 'x'}))
    (ws.art / 'final.md').write_text('# Final\n\nedited after the run\n')
    assert stop(ws.root, tmp_path / 'state').code == 2


def test_a_final_not_touched_this_session_is_ignored(ws, tmp_path):
    (ws.art / 'final.md').write_text('# Final\n')
    os.utime(ws.art / 'final.md', (1, 1))
    started(tmp_path / 'state', 1000)
    assert stop(ws.root, tmp_path / 'state').code == 0


def test_verify_final_is_silent_outside_a_writer_workspace(tmp_path):
    assert stop(tmp_path, tmp_path / 'state').code == 0


def test_hooks_json_registers_the_session_and_stop_hooks():
    hooks = json.loads((PLUGIN / 'hooks' / 'hooks.json').read_text())['hooks']
    ss = [g for g in hooks['SessionStart'] if any('session-context' in h['command'] for h in g['hooks'])]
    sp = [g for g in hooks['Stop'] if any('verify-final' in h['command'] for h in g['hooks'])]
    assert ss and sp and ss[0]['matcher'] == 'startup|resume|clear|compact'


@pytest.mark.parametrize('command', [
    'echo "note: x > articles/demo/gates/G0-brief.r2.md"',
    "grep -n 'a > articles/demo/draft.md' notes.txt",
], ids=['double-quoted-arrow', 'single-quoted-arrow'])
def test_a_redirect_sign_inside_quotes_is_text_not_a_write(ws, command):
    ws.verdict('brief', 1, PASS['brief'])
    assert guard(ws.root, bash_payload(command)).code == 0


# ---------------- Phase 5 (ADR-010): the G4 save, the lint record and the sign-off ----------------
MARKER = "<Can't be verified. Reason: no source covers it.>"
HUMAN_MARKER = '<Needs to be written by a human. Reason: the owner asked to write this part herself.>'
FINAL = '# T\n\nBody text.\n\nSigned-off-by:{who}\n'


def final_ready(ws, text=None, record=True):
    """A workspace whose G0..G3 stand, a final.md, and (by default) a lint record that matches it."""
    ws.approve()
    ws.chain('final')
    body = text if text is not None else FINAL.format(who='')
    (ws.art / 'final.md').write_text(body)
    if record:
        (ws.art / '.prose-lint.json').write_text(json.dumps({'sha256': writer.text_hash(body), 'findings': 0, 'lines': []}))
    give_approval(ws, 'final', 'Test Human', body)  # the record the recorder would hold once the human signed in the Doc (ADR-016)
    return body


def give_approval(ws, stage, value, text):
    (ws.art / 'approvals').mkdir(exist_ok=True)
    (ws.art / 'approvals' / f'{stage}.r1.json').write_text(json.dumps(
        {'doc_id': 'd1', 'rev': 1, 'artifact_sha256': writer.text_hash(text), 'value': value, 'reason': None, 'at': 't'}))


def g4_save(ws, line=None, k=1):
    return guard(ws.root, write_payload(ws.rel(f'gates/G4-final.r{k}.md'), head('final', line or PASS['final'])))


def edit_final(ws, old, new, replace_all=False):
    return guard(ws.root, {'hook_event_name': 'PreToolUse', 'tool_name': 'Edit', 'tool_input': {
        'file_path': ws.rel('final.md'), 'old_string': old, 'new_string': new, 'replace_all': replace_all}})


def test_a_g4_verdict_is_saved_against_a_matching_lint_record(ws):
    final_ready(ws)
    assert g4_save(ws).code == 0


def test_a_g4_verdict_is_blocked_with_no_lint_record_and_the_message_names_the_command(ws):
    final_ready(ws, record=False)
    r = g4_save(ws)
    assert r.code == 2 and 'prose-lint' in r.err and '--record' in r.err


def test_a_g4_verdict_is_blocked_when_final_changed_after_the_lint(ws):
    final_ready(ws)
    (ws.art / 'final.md').write_text('# T\n\nA different body.\n')
    r = g4_save(ws)
    assert r.code == 2 and 'prose-lint' in r.err


def test_a_sign_off_only_change_after_the_lint_still_matches_the_record(ws):
    final_ready(ws)
    (ws.art / 'final.md').write_text(FINAL.format(who=' Test Human'))
    assert g4_save(ws).code == 0


def test_a_g3_verdict_save_needs_no_lint_record(ws):
    ws.approve()
    ws.chain('draft')
    r = guard(ws.root, write_payload(ws.rel('gates/G3-draft.r1.md'), head('draft', PASS['draft'])))
    assert r.code == 0


@pytest.mark.parametrize('payload', [
    write_payload('articles/demo/.prose-lint.json', '{}'),
    edit_payload('articles/demo/.prose-lint.json'),
    bash_payload('echo {} > articles/demo/.prose-lint.json'),
    bash_payload('cp /tmp/x articles/demo/.prose-lint.json'),
], ids=['write', 'edit', 'redirect', 'cp'])
def test_the_lint_record_is_written_only_by_the_script(ws, payload):
    r = guard(ws.root, payload)
    assert r.code == 2 and '--record' in r.err and 'FLOW-4' in r.err


def test_running_the_lint_script_with_record_is_not_blocked(ws):
    final_ready(ws)
    script = BIN / 'prose-lint.py'
    assert guard(ws.root, bash_payload(f'python3 {script} --record articles/demo/final.md')).code == 0


def test_a_sign_off_is_allowed_against_a_current_g4_pass_and_no_marker(ws):
    final_ready(ws)
    ws.verdict('final', 1, PASS['final'], sidecar=True)
    r = guard(ws.root, write_payload(ws.rel('final.md'), FINAL.format(who=' Test Human')))
    assert r.code == 0, r.err


@pytest.mark.parametrize('setup,expect', [
    ('none', 'no G4 verdict'),
    ('block', 'not a valid PASS'),
], ids=['no-g4', 'g4-block'])
def test_a_sign_off_is_blocked_without_a_g4_pass(ws, setup, expect):
    final_ready(ws)
    if setup == 'block':
        ws.verdict('final', 1, BLOCK['final'], sidecar=True)
    r = guard(ws.root, write_payload(ws.rel('final.md'), FINAL.format(who=' Test Human')))
    assert r.code == 2 and 'FLOW-6' in r.err and expect in r.err


def test_a_sign_off_is_blocked_when_g4_judged_another_text(ws):
    final_ready(ws)
    ws.verdict('final', 1, PASS['final'], sidecar=True)
    r = guard(ws.root, write_payload(ws.rel('final.md'), '# T\n\nA body G4 never saw.\n\nSigned-off-by: Test Human\n'))
    assert r.code == 2 and 'FLOW-6' in r.err


def test_a_sign_off_is_blocked_while_a_marker_remains_even_with_a_g4_pass(ws):
    body = final_ready(ws, text=f'# T\n\nBody {MARKER}\n\nSigned-off-by:\n')
    ws.verdict('final', 1, PASS['final'], sidecar=True)
    r = guard(ws.root, write_payload(ws.rel('final.md'), body.replace('Signed-off-by:', 'Signed-off-by: Test Human')))
    assert r.code == 2 and 'marker' in r.err


def test_a_sign_off_is_blocked_while_a_human_written_marker_remains(ws):
    """ADR-023: a skipped question leaves `<Needs to be written by a human ...>` in the text, and it stops sign-off like the other marker."""
    body = final_ready(ws, text=f'# T\n\nBody {HUMAN_MARKER}\n\nSigned-off-by:\n')
    ws.verdict('final', 1, PASS['final'], sidecar=True)
    r = guard(ws.root, write_payload(ws.rel('final.md'), body.replace('Signed-off-by:', 'Signed-off-by: Test Human')))
    assert r.code == 2 and 'Needs to be written by a human' in r.err, r.err


@pytest.mark.parametrize('text', ['<Needs to be written by the human. Reason: x>', '<Needs To Be Written by a Human. Reason: x>', '<Needs  to be\u00a0written by me. Reason: x>'],
                         ids=['the-human', 'capitals', 'spacing'])
def test_a_paraphrased_human_written_marker_still_blocks_the_sign_off(ws, text):
    body = final_ready(ws, text=f'# T\n\nBody {text}\n\nSigned-off-by:\n')
    ws.verdict('final', 1, PASS['final'], sidecar=True)
    assert guard(ws.root, write_payload(ws.rel('final.md'), body.replace('Signed-off-by:', 'Signed-off-by: Test Human'))).code == 2


def test_a_mangled_marker_still_blocks_the_sign_off(ws):
    body = final_ready(ws, text='# T\n\nBody <Can\u2019t be verified. Reason: x>\n\nSigned-off-by:\n')
    ws.verdict('final', 1, PASS['final'], sidecar=True)
    assert guard(ws.root, write_payload(ws.rel('final.md'), body.replace('Signed-off-by:', 'Signed-off-by: Test Human'))).code == 2


def test_an_empty_sign_off_is_always_allowed_even_with_a_marker(ws):
    ws.approve()
    ws.chain('final')
    assert guard(ws.root, write_payload(ws.rel('final.md'), f'# T\n\nBody {MARKER}\n\nSigned-off-by:\n')).code == 0


def test_an_edit_that_only_adds_the_sign_off_is_allowed_with_a_current_g4_pass(ws):
    final_ready(ws)
    ws.verdict('final', 1, PASS['final'], sidecar=True)
    assert edit_final(ws, 'Signed-off-by:', 'Signed-off-by: Test Human').code == 0


def test_an_edit_that_changes_the_body_of_a_signed_final_is_blocked(ws):
    body = final_ready(ws, text='# T\n\nBody text.\n\nSigned-off-by: Test Human\n')
    ws.verdict('final', 1, PASS['final'], sidecar=True)
    r = edit_final(ws, 'Body text.', 'Body text, changed.')
    assert r.code == 2 and 'FLOW-6' in r.err


def test_replace_all_is_resolved_like_the_edit_tool(ws):
    # G4 judged the text with BOTH occurrences replaced and the sign-off already in it
    final_ready(ws, text='# T\n\nfoo and foo.\n\nSigned-off-by: Test Human\n')
    ws.verdict('final', 1, PASS['final'], sidecar=True)
    judged = '# T\n\nbar and bar.\n\nSigned-off-by: Test Human\n'
    (ws.art / 'gates' / 'G4-final.r1.json').write_text(json.dumps({'artifact_sha256': writer.text_hash(judged), 'upstream': 'G3-draft.r1.md'}))
    give_approval(ws, 'final', 'Test Human', judged)  # the sign-off in the Doc covers the judged text too (ADR-016); this test is about the G4 rule
    edit = {'file_path': ws.rel('final.md'), 'old_string': 'foo', 'new_string': 'bar'}
    assert guard(ws.root, {'tool_name': 'Edit', 'tool_input': dict(edit, replace_all=True)}).code == 0
    r = guard(ws.root, {'tool_name': 'Edit', 'tool_input': dict(edit, replace_all=False)})
    assert r.code == 2 and 'FLOW-6' in r.err


def test_a_commit_trailer_quoted_in_a_code_fence_is_not_the_sign_off(ws):
    ws.approve()
    ws.chain('final')
    body = '# T\n\n```\nSigned-off-by: Jane Dev <j@example.com>\n```\n\nSigned-off-by:\n'
    assert guard(ws.root, write_payload(ws.rel('final.md'), body)).code == 0


@pytest.mark.parametrize('rel', ['articles/demo/.Prose-Lint.json', 'articles/demo/Gates/archive/x.md'])
def test_the_new_rules_are_not_bypassed_by_letter_case(ws, rel):
    assert guard(ws.root, write_payload(rel, '{}')).code == 2


def test_a_sign_off_written_to_a_differently_cased_final_is_still_checked(ws):
    final_ready(ws, text=f'# T\n\nBody {MARKER}\n\nSigned-off-by:\n')
    ws.verdict('final', 1, PASS['final'], sidecar=True)
    r = guard(ws.root, write_payload(ws.rel('Final.md'), f'# T\n\nBody {MARKER}\n\nSigned-off-by: Test Human\n'))
    assert r.code == 2 and 'marker' in r.err


def test_an_edit_that_cannot_be_resolved_is_allowed_and_says_so(ws):
    final_ready(ws)
    r = edit_final(ws, 'text that is not in the file', 'x')
    assert r.code == 0 and 'sign-off check was skipped' in r.err


def test_a_shell_write_of_the_signoff_label_into_the_final_is_refused(ws):
    # WHY: this was the stated gap (ADR-010). The shell command that names an approval label and writes an artifact is now refused (ADR-016);
    # what stays a gap is a write the parser cannot see, pinned below.
    final_ready(ws)
    r = guard(ws.root, bash_payload("sed -i '' 's/Signed-off-by:/Signed-off-by: X/' articles/demo/final.md"))
    assert r.code == 2 and 'FLOW-6' in r.err


def test_a_write_the_shell_parser_cannot_see_stays_a_stated_gap(ws):
    final_ready(ws)
    cmd = "python3 -c \"open('articles/demo/final.md','a').write('Signed-off-by: X')\""
    assert guard(ws.root, bash_payload(cmd)).code == 0


# ---------------- Phase 6 (ADR-011): one article state for the briefing and the orchestrator ----------------
CURLY_MARKER = '<Can’t be verified. Reason: a curly apostrophe the guard still catches.>'


def build_state(ws, state):
    """Leave the workspace the way a real flow would at `state`. Neutral synthetic files only (PLG-1)."""
    art = ws.art

    def drop(*stages):
        for s in stages:
            (art / f'{s}.md').unlink()

    if state == 'nothing':
        drop(*STAGES)
    elif state == 'brief-only':
        drop('research', 'outline', 'draft', 'final')
    elif state == 'brief-passed':
        drop('research', 'outline', 'draft', 'final')
        ws.chain('research')
    elif state in ('one-block', 'two-blocks'):
        ws.chain('outline')
        ws.verdict('outline', 1, BLOCK['outline'])
        if state == 'two-blocks':
            ws.verdict('outline', 2, BLOCK['outline'])
    elif state == 'stale':
        ws.chain('outline')
        ws.verdict('brief', 2, PASS['brief'], sidecar=True)
    elif state == 'two-blocks-then-pass':
        ws.chain('outline')
        ws.verdict('outline', 1, BLOCK['outline'])
        ws.verdict('outline', 2, BLOCK['outline'])
        ws.verdict('outline', 3, PASS['outline'], sidecar=True)
    elif state in ('unapproved', 'approved', 'approved-no-draft', 'stale-unapproved', 'markers-outline'):
        ws.chain('outline')
        if state == 'markers-outline':
            (art / 'outline.md').write_text(OUTLINE.format(approval='') + f"{MARKER}\n<Can't be verified. Reason: b.>\n")
        ws.verdict('outline', 1, PASS['outline'], sidecar=True)
        if state in ('approved', 'approved-no-draft'):
            ws.approve()
        if state == 'approved-no-draft':
            drop('draft', 'final')
        if state == 'stale-unapproved':
            ws.verdict('brief', 2, PASS['brief'], sidecar=True)
    elif state == 'stale-next-missing':
        ws.chain('outline')
        drop('outline', 'draft', 'final')
        ws.verdict('brief', 2, PASS['brief'], sidecar=True)
    elif state in ('final-unsigned', 'signed', 'marker-final', 'human-marker-final', 'malformed-marker-final', 'fenced-sign-off'):
        body = {'final-unsigned': '# T\n\nBody.\n\nSigned-off-by:\n',
                'signed': '# T\n\nBody.\n\nSigned-off-by: Test Human\n',
                'marker-final': f'# T\n\nBody {MARKER}\n\nSigned-off-by:\n',
                'human-marker-final': f'# T\n\nBody {HUMAN_MARKER}\n\nSigned-off-by:\n',
                'malformed-marker-final': f'# T\n\nBody {CURLY_MARKER}\n\nSigned-off-by:\n',
                'fenced-sign-off': '# T\n\n```\ngit commit -s\nSigned-off-by: A Committer\n```\n\nSigned-off-by:\n'}[state]
        ws.approve()
        ws.chain('final')
        (art / 'final.md').write_text(body)
        ws.verdict('final', 1, PASS['final'], sidecar=True)
    else:
        raise AssertionError(f'unknown state {state}')


R1_STATES = ['nothing', 'brief-only', 'brief-passed', 'one-block', 'two-blocks', 'two-blocks-then-pass', 'stale', 'unapproved', 'approved',
             'approved-no-draft', 'stale-unapproved', 'stale-next-missing', 'markers-outline', 'final-unsigned', 'signed',
             'marker-final', 'human-marker-final', 'malformed-marker-final', 'fenced-sign-off']
_STALE = 'STALE: G1-research.r1.md is stale: it relied on G0-brief.r1.md but the latest G0-brief verdict is G0-brief.r2.md'
# The briefing line per state, exactly as session-context prints it. Pinned before article_state() replaced the logic behind
# it, so the refactor cannot change what a writer reads by accident.
BRIEFING = {
    'nothing': 'no brief.md yet: start with the brief stage',
    'brief-only': 'brief.md written, G0-brief not run',
    'brief-passed': 'brief passed; next: the research stage',
    'one-block': 'G2-outline BLOCK (G2-outline.r1.md): the outline stage fixes it and reruns',
    'two-blocks': 'G2-outline STOPPED (FLOW-3): two BLOCK verdicts, a human archives them to resume',
    'stale': f'outline.md written, G2-outline not run · {_STALE}',
    'unapproved': "outline passed G2, waiting for a human's Approved-by",
    'approved': 'draft.md written, G3-draft not run',
    'approved-no-draft': 'outline passed; next: the draft stage',
    'stale-unapproved': f"outline passed G2, waiting for a human's Approved-by · {_STALE}",
    'stale-next-missing': f'research passed; next: the outline stage · {_STALE}',
    'markers-outline': "outline passed G2, waiting for a human's Approved-by · 2 markers to resolve",
    'final-unsigned': "final passed G4, waiting for a human's Signed-off-by",
    'signed': 'final passed G4 and is signed off',
    # WHY: once a final exists its markers are what blocks the sign-off (FLOW-6), so they are counted there, with the guard's
    # own loose pattern, not in the outline (ADR-011). This line said nothing about the marker before.
    'marker-final': "final passed G4, waiting for a human's Signed-off-by · 1 marker to resolve",
    'human-marker-final': "final passed G4, waiting for a human's Signed-off-by · 1 marker to resolve",
    'malformed-marker-final': "final passed G4, waiting for a human's Signed-off-by · 1 marker to resolve",
    # WHY: sign-off is read with the guard's fence-aware is_signed; a commit trailer quoted in a code block is not a sign-off
    # (ADR-011). This line called the article signed off before.
    'fenced-sign-off': "final passed G4, waiting for a human's Signed-off-by",
    # WHY: the guard stops a stage whose gate has two BLOCKs whatever its latest verdict (FLOW-3); the briefing now says the same
    # (ADR-011). New state, no earlier string.
    'two-blocks-then-pass': 'G2-outline STOPPED (FLOW-3): two BLOCK verdicts, a human archives them to resume',
}


@pytest.mark.parametrize('state', R1_STATES)
def test_the_briefing_line_for_each_state_is_exact(ws, state):
    build_state(ws, state)
    assert writer.describe_article(str(ws.root), ws.slug) == BRIEFING[state]


MARKER_B = "<Can't be verified. Reason: b.>"
# state -> (next, stage, markers)
EXPECTED_STATE = {
    'nothing': ('brief', 'brief', []),
    'brief-only': ('brief', 'brief', []),
    'brief-passed': ('research', 'research', []),
    'one-block': ('outline', 'outline', []),
    'two-blocks': ('stopped', 'outline', []),
    'two-blocks-then-pass': ('stopped', 'outline', []),
    'stale': ('stale', 'outline', []),
    'unapproved': ('approve', 'outline', []),
    'approved': ('draft', 'draft', []),
    'approved-no-draft': ('draft', 'draft', []),
    'stale-unapproved': ('stale', 'outline', []),
    'stale-next-missing': ('stale', 'outline', []),
    'markers-outline': ('approve', 'outline', [MARKER, MARKER_B]),
    'final-unsigned': ('sign-off', 'final', []),
    'signed': ('done', 'final', []),
    'marker-final': ('sign-off', 'final', [MARKER]),
    'human-marker-final': ('sign-off', 'final', [HUMAN_MARKER]),
    'malformed-marker-final': ('sign-off', 'final', [CURLY_MARKER]),
    'fenced-sign-off': ('sign-off', 'final', []),
}


@pytest.mark.parametrize('state', R1_STATES)
def test_article_state_gives_the_next_step_the_stage_and_the_markers(ws, state):
    build_state(ws, state)
    s = writer.article_state(str(ws.root), ws.slug)
    assert (s['next'], s['stage'], s['markers']) == EXPECTED_STATE[state]
    assert s['stale'] is (s['next'] == 'stale')


@pytest.mark.parametrize('state', ['two-blocks', 'two-blocks-then-pass'])
def test_a_stopped_article_names_both_block_verdicts_and_how_to_resume(ws, state):
    build_state(ws, state)
    reason = writer.article_state(str(ws.root), ws.slug)['reason']
    assert 'G2-outline.r1.md' in reason and 'G2-outline.r2.md' in reason and 'archive' in reason


@pytest.mark.parametrize('state', ['stale', 'stale-unapproved', 'stale-next-missing'])
def test_a_stale_article_quotes_what_check_gate_says(ws, state):
    build_state(ws, state)
    s = writer.article_state(str(ws.root), ws.slug)
    assert s['reason'] == writer.check_gate(str(ws.root), ws.slug, 'research')


def status(root, *args, cwd=None):
    r = subprocess.run([sys.executable, str(BIN / 'article-status.py'), *args], capture_output=True, text=True,
                       cwd=str(cwd or root))
    return Result(r.returncode, r.stdout, r.stderr)


def tree(root):
    return sorted(str(p.relative_to(root)) for p in Path(root).rglob('*'))


@pytest.mark.parametrize('state', ['nothing', 'unapproved', 'two-blocks', 'stale', 'final-unsigned', 'signed'])
def test_the_status_script_prints_the_state_as_json_and_writes_nothing(ws, state):
    build_state(ws, state)
    before = tree(ws.root)
    r = status(ws.root, ws.slug)
    assert r.code == 0
    out = json.loads(r.out)
    # WHY: `comments` joins the contract, always [] in PR 1 (ADR-016, R4); no key was removed or loosened
    assert set(out) == {'slug', 'stage', 'next', 'reason', 'markers', 'stale', 'comments'}
    assert out['slug'] == ws.slug and out['next'] == EXPECTED_STATE[state][0]
    assert tree(ws.root) == before


def test_the_status_script_takes_a_root_from_anywhere(ws, tmp_path):
    build_state(ws, 'unapproved')
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    assert json.loads(status(ws.root, '--root', str(ws.root), ws.slug, cwd=elsewhere).out)['next'] == 'approve'


def test_a_slug_with_no_folder_starts_at_the_brief(tmp_path):
    (tmp_path / 'articles').mkdir()
    assert json.loads(status(tmp_path, 'new-article').out)['next'] == 'brief'


@pytest.mark.parametrize('args', [[], ['../escape'], ['a/b']], ids=['no-slug', 'dot-dot', 'slash'])
def test_the_status_script_refuses_a_missing_or_unsafe_slug_as_unknown(tmp_path, args):
    (tmp_path / 'articles').mkdir()
    r = status(tmp_path, *args)
    out = json.loads(r.out)
    assert r.code == 0 and out['next'] == 'unknown' and out['reason']


def test_the_status_script_says_unknown_when_the_workspace_cannot_be_read(tmp_path):
    (tmp_path / 'articles').write_text('a file where the folder should be')
    r = status(tmp_path, 'demo')
    out = json.loads(r.out)
    assert r.code == 0 and out['next'] == 'unknown' and 'articles' in out['reason']


@pytest.mark.parametrize('state', R1_STATES)
def test_the_briefing_and_the_status_script_agree(ws, tmp_path, state):
    """One function decides both (AC8): the line a writer reads at session start names what the orchestrator will do."""
    build_state(ws, state)
    nxt = json.loads(status(ws.root, ws.slug).out)['next']
    line = session(ws.root, tmp_path / 'state').out
    assert f'**{ws.slug}**: {BRIEFING[state]}' in line
    assert nxt == EXPECTED_STATE[state][0]


# ---------------- Phase 6 review: guard agreement, root, slug and argument edges ----------------
# state -> (the artifact the probe writes, the guard's exit code). A stage the orchestrator would run must be allowed (0); at
# a stop, the artifact it would otherwise move on to must be refused (2). sign-off and done write no artifact, so they have no row.
GUARD_PROBE = {
    'nothing': ('brief.md', 0), 'brief-only': ('brief.md', 0), 'brief-passed': ('research.md', 0), 'one-block': ('outline.md', 0),
    'approved': ('draft.md', 0), 'approved-no-draft': ('draft.md', 0),
    'two-blocks': ('outline.md', 2), 'two-blocks-then-pass': ('outline.md', 2),
    'unapproved': ('draft.md', 2), 'markers-outline': ('draft.md', 2),
    'stale': ('outline.md', 2), 'stale-unapproved': ('draft.md', 2), 'stale-next-missing': ('outline.md', 2),
}


@pytest.mark.parametrize('state', sorted(GUARD_PROBE))
def test_the_orchestrators_next_step_is_one_the_guard_allows(ws, state):
    """ADR-011 says the orchestrator and the guard agree. A new guard rule that breaks this turns this red."""
    build_state(ws, state)
    artifact, code = GUARD_PROBE[state]
    assert guard(ws.root, write_payload(ws.rel(artifact))).code == code


def test_every_state_that_runs_a_stage_probes_that_stage():
    runs = {s: EXPECTED_STATE[s][0] for s in R1_STATES if EXPECTED_STATE[s][0] in STAGES}
    assert {s: GUARD_PROBE[s] for s in runs} == {s: (f'{n}.md', 0) for s, n in runs.items()}


def test_a_missing_articles_folder_names_the_root_it_looked_under(tmp_path):
    out = json.loads(status(tmp_path, 'demo').out)
    assert out['next'] == 'brief' and str(tmp_path) in out['reason']


@pytest.mark.parametrize('slug,ok', [('demo\n', False), ('.hidden', False), ('My Draft', True), ('demo', True)],
                         ids=['trailing-newline', 'dot-folder', 'space-in-name', 'kebab'])
def test_a_slug_is_one_visible_folder_name(tmp_path, slug, ok):
    (tmp_path / 'articles').mkdir()
    assert (writer.article_state(str(tmp_path), slug)['next'] != 'unknown') is ok


@pytest.mark.parametrize('args', [['demo', '--root'], ['a', 'b']], ids=['root-without-value', 'two-slugs'])
def test_bad_arguments_still_print_json_unknown(tmp_path, args):
    (tmp_path / 'articles').mkdir()
    r = status(tmp_path, *args)
    out = json.loads(r.out)
    assert r.code == 0 and out['next'] == 'unknown' and out['reason']


# ---------------- Phase 7b (R5): the Doc copy is computed by a read-only script, never by the model ----------------
def doc_copy(root, *args):
    r = subprocess.run([sys.executable, str(BIN / 'doc-copy.py'), *args], capture_output=True, text=True, cwd=str(root))
    return Result(r.returncode, r.stdout, r.stderr)


def record_doc(ws, entries):
    (ws.art / 'docs.json').write_text(json.dumps({'revisions': entries}))


@pytest.mark.parametrize('text,expected', [
    ('A claim [F7].', 'A claim.'),
    ('Two facts [F7, F9] here.', 'Two facts here.'),
    ('Spaced [F7,F12] and [F3]: done', 'Spaced and: done'),
    ('[F1] at the start', ' at the start'),
    ('A quote ("x") [F12], then more.', 'A quote ("x"), then more.'),
    ('Not a tag [Figure 2] or [F] or [f7].', 'Not a tag [Figure 2] or [F] or [f7].'),
], ids=['one', 'two', 'spacing', 'line-start', 'before-comma', 'look-alikes'])
def test_fact_ids_are_stripped_and_the_punctuation_stays(text, expected):
    assert writer.strip_fact_ids(text) == expected


def test_fact_ids_inside_a_code_fence_are_left_alone():
    text = 'Claim [F1].\n\n```\nlist[F1] = 0\n```\nAfter [F2].\n'
    assert writer.strip_fact_ids(text) == 'Claim.\n\n```\nlist[F1] = 0\n```\nAfter.\n'


def test_the_next_revision_is_per_stage_and_one_past_the_highest(ws):
    assert writer.next_rev(str(ws.root), ws.slug, 'outline') == 1
    record_doc(ws, [{'stage': 'outline', 'rev': 1}, {'stage': 'outline', 'rev': 3}, {'stage': 'final', 'rev': 7}])
    assert (writer.next_rev(str(ws.root), ws.slug, 'outline'), writer.next_rev(str(ws.root), ws.slug, 'draft')) == (4, 1)


@pytest.mark.parametrize('state,ready', [
    ('signed', True), ('final-unsigned', False), ('marker-final', False), ('human-marker-final', False), ('malformed-marker-final', False),
    ('fenced-sign-off', False), ('stale', False),
])
def test_publish_ready_needs_done_and_no_marker_in_the_final(ws, state, ready):
    build_state(ws, state)
    assert writer.publish_ready(str(ws.root), ws.slug) is ready


def test_a_hand_signed_final_with_a_human_written_marker_is_not_publish_ready(ws):
    build_state(ws, 'signed')
    (ws.art / 'final.md').write_text(f'# T\n\nBody {HUMAN_MARKER}\n\nSigned-off-by: Test Human\n')
    writer.write_sidecar(str(ws.root), ws.slug, 'G4-final.r1.md')
    assert (writer.article_state(str(ws.root), ws.slug)['next'], writer.publish_ready(str(ws.root), ws.slug)) == ('done', False)


def test_a_hand_signed_final_with_a_marker_is_not_publish_ready(ws):
    """G4 may PASS a final that holds a marker (ADR-008) and a hand sign-off skips the guard: `done` alone is not enough."""
    build_state(ws, 'signed')
    (ws.art / 'final.md').write_text(f'# T\n\nBody {MARKER}\n\nSigned-off-by: Test Human\n')
    writer.write_sidecar(str(ws.root), ws.slug, 'G4-final.r1.md')  # the gate judged this text, so the state is `done`
    assert (writer.article_state(str(ws.root), ws.slug)['next'], writer.publish_ready(str(ws.root), ws.slug)) == ('done', False)


def test_the_doc_copy_of_a_final_strips_ids_and_hashes_the_file_on_disk(ws):
    build_state(ws, 'signed')
    body = '# T\n\nBody [F1].\n\nSigned-off-by: Test Human\n'
    (ws.art / 'final.md').write_text(body)
    writer.write_sidecar(str(ws.root), ws.slug, 'G4-final.r1.md')
    r = doc_copy(ws.root, ws.slug, 'final')
    out = json.loads(r.out)
    assert r.code == 0
    uploaded = '# T\n\nBody.\n\nSigned-off-by: Test Human\n'
    assert out == {'text': uploaded, 'sha256': writer.text_hash(body), 'text_sha256': writer.text_hash(uploaded), 'rev': 1,
                   'publish_ready': True, 'title': 'demo · final · r1 · publish-ready', 'skip': False, 'existing_url': None,
                   'folder_path': ['articles', os.path.basename(os.path.realpath(ws.root)), 'demo'], 'folder_id': None}


def test_an_ungated_stage_is_labelled_ungated(ws):
    build_state(ws, 'one-block')
    assert json.loads(doc_copy(ws.root, ws.slug, 'outline').out)['title'] == 'demo · outline · r1 · ungated'


def test_an_unchanged_copy_is_skipped_and_names_the_existing_doc(ws):
    build_state(ws, 'unapproved')
    first = json.loads(doc_copy(ws.root, ws.slug, 'outline').out)
    entry = dict(stage='outline', rev=1, id='d1', url='https://docs.example/d1', at='t', sha256=first['sha256'],
                 text_sha256=first['text_sha256'], title=first['title'], publish_ready=False)
    record_doc(ws, [entry])
    log_created(ws, [entry])
    again = json.loads(doc_copy(ws.root, ws.slug, 'outline').out)
    assert (again['skip'], again['existing_url'], again['rev']) == (True, 'https://docs.example/d1', 2)


def test_an_unchanged_copy_the_recorder_never_logged_is_not_reused(ws):
    """FT-18: a Doc in docs.json that the create hook never logged can never carry an approval, so the next copy is a new Doc."""
    build_state(ws, 'unapproved')
    first = json.loads(doc_copy(ws.root, ws.slug, 'outline').out)
    record_doc(ws, [dict(stage='outline', rev=1, id='d1', url='https://docs.example/d1', at='t', sha256=first['sha256'],
                         text_sha256=first['text_sha256'], title=first['title'], publish_ready=False)])
    again = json.loads(doc_copy(ws.root, ws.slug, 'outline').out)
    assert (again['skip'], again['existing_url'], again['rev'], again['title']) == (False, None, 2, 'demo · outline · r2')


def test_an_unreadable_created_log_stops_the_copy_instead_of_guessing(ws):
    build_state(ws, 'unapproved')
    (ws.art / '.docs-created.json').write_text('{not json')
    r = doc_copy(ws.root, ws.slug, 'outline')
    assert r.code == 1 and 'error' in json.loads(r.out)


def entry_from(out, rev, url):
    return dict(stage='final', rev=rev, id=f'd{rev}', url=url, at='t', sha256=out['sha256'], text_sha256=out['text_sha256'],
                title=out['title'], publish_ready=out['publish_ready'])


def test_a_sign_off_on_unchanged_text_still_makes_a_new_doc(ws):
    """The hash ignores approval lines, so only the label tells the signed copy from the unsigned one."""
    build_state(ws, 'final-unsigned')
    before = json.loads(doc_copy(ws.root, ws.slug, 'final').out)
    record_doc(ws, [entry_from(before, 1, 'https://docs.example/d1')])
    (ws.art / 'final.md').write_text('# T\n\nBody.\n\nSigned-off-by: Test Human\n')
    after = json.loads(doc_copy(ws.root, ws.slug, 'final').out)
    assert (before['sha256'] == after['sha256'], after['skip'], after['title']) == (True, False, 'demo · final · r2 · publish-ready')


def test_an_ungated_copy_that_later_passes_makes_a_new_doc(ws):
    build_state(ws, 'unapproved')
    (ws.art / 'gates' / 'G2-outline.r1.md').unlink()
    (ws.art / 'gates' / 'G2-outline.r1.json').unlink()
    ungated = json.loads(doc_copy(ws.root, ws.slug, 'outline').out)
    record_doc(ws, [dict(entry_from(ungated, 1, 'u'), stage='outline')])
    ws.verdict('outline', 1, PASS['outline'], sidecar=True)
    gated = json.loads(doc_copy(ws.root, ws.slug, 'outline').out)
    assert (ungated['title'], gated['skip'], gated['title']) == ('demo · outline · r1 · ungated', False, 'demo · outline · r2')


@pytest.mark.parametrize('args,why', [
    (['demo', 'summary'], 'not a stage'), (['demo'], 'usage'), (['../x', 'final'], 'slug'), (['demo', 'research'], 'research.md'),
], ids=['bad-stage', 'no-stage', 'bad-slug', 'missing-artifact'])
def test_a_bad_request_prints_an_error_and_exits_1(ws, args, why):
    (ws.art / 'research.md').unlink()
    r = doc_copy(ws.root, *args)
    assert (r.code, why in json.loads(r.out)['error']) == (1, True)


def test_an_unreadable_docs_json_is_an_error_not_an_empty_history(ws):
    (ws.art / 'docs.json').write_text('{not json')
    r = doc_copy(ws.root, ws.slug, 'outline')
    assert (r.code, 'docs.json' in json.loads(r.out)['error']) == (1, True)


def test_the_doc_copy_script_writes_nothing(ws):
    build_state(ws, 'signed')
    before = sorted(p.relative_to(ws.root) for p in ws.root.rglob('*'))
    doc_copy(ws.root, ws.slug, 'final')
    assert sorted(p.relative_to(ws.root) for p in ws.root.rglob('*')) == before


# ---------------- Phase 7b (R8): FLOW-6 on the Doc copy record and on the Doc title itself ----------------
DRIVE_CREATE = 'mcp__claude_ai_Google_Drive__create_file'


def entry(ws, rev=1, ready=True, sha=None, stage='final'):
    art = ws.art / f'{stage}.md'
    shown = writer.doc_text(art.read_text(errors='replace'), stage, keep_signoff=ready) if art.exists() else ''
    return {'stage': stage, 'rev': rev, 'id': f'd{rev}', 'url': f'https://docs.example/d{rev}', 'at': 't',
            'sha256': sha if sha is not None else writer.artifact_hash(str(ws.root), ws.slug, stage),
            'text_sha256': writer.text_hash(shown),
            'title': f'{ws.slug} · {stage} · r{rev}' + (' · publish-ready' if ready else ''), 'publish_ready': ready}


def log_created(ws, entries):
    """What the create hook would have logged for these entries (the guard matches a new docs.json entry to it)."""
    docs = [{'id': e['id'], 'title': e['title'], 'slug': ws.slug, 'stage': e['stage'], 'rev': e['rev'], 'label': '',
             'text_sha256': e.get('text_sha256'), 'approvable': not e['publish_ready'], 'at': 't'} for e in entries]
    (ws.art / '.docs-created.json').write_text(json.dumps({'docs': docs}))


def docs_write(ws, entries, logged=True):
    if logged:
        log_created(ws, entries)
    return guard(ws.root, write_payload(ws.rel('docs.json'), json.dumps({'revisions': entries})))


def docs_edit(ws, old, new):
    return guard(ws.root, {'hook_event_name': 'PreToolUse', 'tool_name': 'Edit', 'tool_input': {
        'file_path': ws.rel('docs.json'), 'old_string': old, 'new_string': new, 'replace_all': False}})


def drive_create(ws, title):
    """A create call that uploads the final exactly as doc-copy.py prints it, so only the title and the article's state decide."""
    final = ws.art / 'final.md'
    # WHY: this helper builds the upload the copy skill makes for this title: the publish-ready final keeps its signed line, any other copy is
    # unapproved (FT-6, ADR-016; docs/features/comment-rerun-and-clean-copies/plan.md R1)
    text = writer.doc_text(final.read_text(errors='replace'), 'final', keep_signoff=writer.claims_publish_ready(title)) if final.exists() else '# T\n'
    parts = writer.parse_doc_title(title)
    if parts and parts['stage'] != 'final' and (ws.art / f'{parts["stage"]}.md').exists():
        text = writer.doc_text((ws.art / f'{parts["stage"]}.md').read_text(errors='replace'), str(parts['stage']))
    return guard(ws.root, {'hook_event_name': 'PreToolUse', 'tool_name': DRIVE_CREATE,
                           'tool_input': {'title': title, 'textContent': text, 'contentMimeType': 'text/markdown'}})


def signed_with_marker(ws, marker=MARKER):
    build_state(ws, 'signed')
    (ws.art / 'final.md').write_text(f'# T\n\nBody {marker}\n\nSigned-off-by: Test Human\n')
    writer.write_sidecar(str(ws.root), ws.slug, 'G4-final.r1.md')


@pytest.mark.parametrize('state,code', [('signed', 0), ('final-unsigned', 2), ('marker-final', 2), ('stale', 2)],
                         ids=['signed', 'unsigned', 'unsigned-marker', 'stale'])
def test_a_publish_ready_entry_needs_a_publish_ready_final(ws, state, code):
    build_state(ws, state)
    assert docs_write(ws, [entry(ws)]).code == code


@pytest.mark.parametrize('marker', [MARKER, HUMAN_MARKER], ids=['unverified', 'human-written'])
def test_a_hand_signed_final_with_a_marker_cannot_be_recorded_publish_ready(ws, marker):
    signed_with_marker(ws, marker)
    r = docs_write(ws, [entry(ws)])
    assert (r.code, 'FLOW-6' in r.err) == (2, True)


def test_a_final_with_fact_tags_is_recorded_against_the_hash_of_the_file_on_disk(ws):
    build_state(ws, 'signed')
    (ws.art / 'final.md').write_text('# T\n\nBody [F1].\n\nSigned-off-by: Test Human\n')
    writer.write_sidecar(str(ws.root), ws.slug, 'G4-final.r1.md')
    assert docs_write(ws, [entry(ws)]).code == 0


def test_a_publish_ready_entry_with_an_older_hash_is_blocked(ws):
    build_state(ws, 'signed')
    assert docs_write(ws, [entry(ws, sha='0' * 64)]).code == 2


def test_an_entry_that_is_not_publish_ready_is_allowed_in_any_state(ws):
    build_state(ws, 'final-unsigned')
    assert docs_write(ws, [entry(ws, ready=False)]).code == 0


def test_only_a_final_can_be_recorded_publish_ready(ws):
    build_state(ws, 'signed')
    assert docs_write(ws, [entry(ws, stage='outline')]).code == 2


def test_appending_keeps_history_and_is_allowed(ws):
    build_state(ws, 'final-unsigned')
    first = entry(ws, ready=False)
    (ws.art / 'docs.json').write_text(json.dumps({'revisions': [first]}))
    assert docs_write(ws, [first, entry(ws, rev=2, ready=False)]).code == 0


@pytest.mark.parametrize('change', ['remove', 'alter', 'reorder'])
def test_an_existing_entry_cannot_be_changed_removed_or_reordered(ws, change):
    build_state(ws, 'signed')
    a, b = entry(ws, ready=False), entry(ws, rev=2, ready=False)
    (ws.art / 'docs.json').write_text(json.dumps({'revisions': [a, b]}))
    new = {'remove': [b], 'alter': [dict(a, url='https://elsewhere'), b], 'reorder': [b, a]}[change]
    r = docs_write(ws, new)
    assert (r.code, 'FLOW-6' in r.err) == (2, True)


def test_an_edit_that_flips_a_recorded_flag_is_blocked_even_on_a_signed_final(ws):
    build_state(ws, 'signed')
    (ws.art / 'docs.json').write_text(json.dumps({'revisions': [entry(ws, ready=False)]}))
    assert docs_edit(ws, '"publish_ready": false', '"publish_ready": true').code == 2


@pytest.mark.parametrize('content', ['{not json', '{}', '{"revisions": {}}', '{"revisions": [1]}', '[]'],
                         ids=['not-json', 'no-revisions', 'revisions-not-list', 'entry-not-object', 'top-level-list'])
def test_a_docs_json_that_is_not_a_revision_list_is_blocked(ws, content):
    assert guard(ws.root, write_payload(ws.rel('docs.json'), content)).code == 2


@pytest.mark.parametrize('command', ['echo x > articles/demo/docs.json', 'cp /tmp/x articles/demo/docs.json'],
                         ids=['redirect', 'cp'])
def test_bash_cannot_write_docs_json(ws, command):
    assert guard(ws.root, bash_payload(command)).code == 2


@pytest.mark.parametrize('state,title,code', [
    ('final-unsigned', 'demo · final · r2 · publish-ready', 2),
    ('signed', 'demo · final · r2 · publish-ready', 0),
    ('signed', 'publish-ready copy', 2),
    ('signed', 'other · final · r1 · publish-ready', 2),
    ('final-unsigned', 'demo · final · r2', 0),
    ('final-unsigned', 'demo · outline · r1 · ungated', 0),
], ids=['unsigned', 'signed', 'no-slug', 'other-article', 'no-label', 'outline'])
def test_a_doc_titled_publish_ready_is_created_only_for_a_publish_ready_final(ws, state, title, code):
    build_state(ws, state)
    assert drive_create(ws, title).code == code


@pytest.mark.parametrize('marker', [MARKER, HUMAN_MARKER], ids=['unverified', 'human-written'])
def test_a_marker_blocks_the_publish_ready_doc_even_when_signed_by_hand(ws, marker):
    signed_with_marker(ws, marker)
    r = drive_create(ws, 'demo · final · r2 · publish-ready')
    assert (r.code, 'FLOW-6' in r.err) == (2, True)


def test_hooks_json_runs_the_guard_on_the_drive_create_tool_the_spike_recorded():
    hooks = json.loads((PLUGIN / 'hooks' / 'hooks.json').read_text())['hooks']['PreToolUse']
    matcher = next(g['matcher'] for g in hooks if any('guard-stage-order' in h['command'] for h in g['hooks']))
    # WHY: the two named Drive tools are still guarded, now through the server prefixes (ADR-016, R3)
    assert set(matcher.split('|')) == {'Edit', 'Write', 'Bash', 'mcp__claude_ai_Google_Drive__.*', 'mcp__claude_ai_Google_Docs__.*'}
    for tool in (DRIVE_CREATE, 'mcp__claude_ai_Google_Drive__update_file', 'mcp__claude_ai_Google_Docs__update_doc'):
        assert re.fullmatch(matcher, tool), tool


# ---------------- Phase 7b review: the label is checked on the text, in every spelling, and never fails open ----------------
READY_TITLE = 'demo · final · r2 · publish-ready'


def drive_create_with(ws, title, **content):
    ti = dict({'title': title, 'contentMimeType': 'text/markdown'}, **content)
    return guard(ws.root, {'hook_event_name': 'PreToolUse', 'tool_name': DRIVE_CREATE, 'tool_input': ti})


def test_a_publish_ready_doc_must_carry_exactly_the_final_as_doc_copy_prints_it(ws):
    build_state(ws, 'signed')
    text = json.loads(doc_copy(ws.root, ws.slug, 'final').out)['text']
    assert drive_create_with(ws, READY_TITLE, textContent=text).code == 0


@pytest.mark.parametrize('content', [
    {'textContent': '# Older draft\n\nSomething else.\n'},
    {'textContent': f'# T\n\nBody {MARKER}\n\nSigned-off-by: Test Human\n'},
    {'base64Content': 'IyBUCg=='},
    {},
], ids=['other-text', 'text-with-marker', 'base64', 'no-content'])
def test_a_publish_ready_doc_with_any_other_content_is_blocked(ws, content):
    build_state(ws, 'signed')
    r = drive_create_with(ws, READY_TITLE, **content)
    assert (r.code, 'FLOW-6' in r.err) == (2, True)


@pytest.mark.parametrize('title', [
    'demo · final · r2 · Publish-Ready', 'demo · final · r2 · publish ready', 'demo · final · r2 · PUBLISH_READY',
    'demo · final · r2 · publish‑ready', 'demo · final · r2 ·  publish-ready ', 'publishready',
], ids=['case', 'space', 'underscore', 'nb-hyphen', 'padded', 'joined'])
def test_every_spelling_of_the_label_is_checked_on_an_unsigned_final(ws, title):
    build_state(ws, 'final-unsigned')
    assert drive_create(ws, title).code == 2


def test_a_final_that_cannot_be_read_is_not_publish_ready_for_the_guard(ws):
    build_state(ws, 'signed')
    (ws.art / 'final.md').write_bytes(b'# T\n\n\xff\xfe broken\n\nSigned-off-by: Test Human\n')
    r_doc, r_rec = drive_create(ws, READY_TITLE), docs_write(ws, [entry(ws, sha='0' * 64)])
    assert (r_doc.code, r_rec.code, 'unexpected error' in r_doc.err) == (2, 2, False)


@pytest.mark.parametrize('bad', [{'publish_ready': 1}, {'publish_ready': 'true'}, {'publish_ready': None}],
                         ids=['int', 'string', 'null'])
def test_a_new_entry_says_publish_ready_as_a_boolean(ws, bad):
    build_state(ws, 'final-unsigned')
    assert docs_write(ws, [dict(entry(ws, ready=False), **bad)]).code == 2


def test_a_new_entry_cannot_carry_the_label_in_its_title_while_saying_false(ws):
    build_state(ws, 'final-unsigned')
    e = dict(entry(ws, ready=False), title='demo · final · r1 · publish-ready')
    assert docs_write(ws, [e]).code == 2


def test_a_docs_json_with_a_duplicate_key_is_blocked(ws):
    build_state(ws, 'final-unsigned')
    body = json.dumps({'revisions': [entry(ws, ready=False)]}).replace('"publish_ready": false', '"publish_ready": true, "publish_ready": false')
    assert guard(ws.root, write_payload(ws.rel('docs.json'), body)).code == 2


def test_a_duplicate_key_makes_the_recorded_history_unreadable(ws):
    (ws.art / 'docs.json').write_text('{"revisions": [], "revisions": []}')
    with pytest.raises(ValueError, match='duplicate'):
        writer.docs_index(str(ws.root), ws.slug)


# ---------------- Phase 7b live run: front matter reads as a list in the Doc, and the skip rule follows the uploaded text ----------------
# The live run showed Google turning `---` into a rule and `title: …` into a heading, so the Doc opened with a stray heading.
FRONT = '---\ntitle: HTTP caching\nmeta_description: How caching works.\nslug: http-caching\n---\n# HTTP caching\n\nBody [F1].\n'


def test_front_matter_becomes_a_list_reviewers_can_read():
    assert writer.doc_text(FRONT) == ('- **Title:** HTTP caching\n- **Meta description:** How caching works.\n- **Slug:** http-caching\n'
                                      '\n# HTTP caching\n\nBody.\n')


# FT-14: a marker stands out in the Doc copy. The comparison of a read-back Doc ignores `*`, so approval still matches.
MARK = "<Can't be verified. Reason: no public source>"


def test_marker_is_bold_in_the_doc_copy_and_a_second_pass_changes_nothing():
    out = writer.doc_text(f'# T\n\nPrice is {MARK} today [F1].\n')
    assert out == f'# T\n\nPrice is **{MARK}** today.\n'
    assert writer.bold_markers(out) == out


def test_the_human_written_marker_is_bold_whole_and_a_second_pass_changes_nothing():
    out = writer.doc_text(f'# T\n\nA part: {HUMAN_MARKER} then more.\n')
    assert f'**{HUMAN_MARKER}**' in out and writer.bold_markers(out) == out
    assert f'**{MARK}**' in writer.doc_text(f'# T\n\nPrice is {MARK} today.\n'), "the Can't form is still bolded whole"


def test_marker_in_a_code_fence_stays_plain_and_front_matter_body_is_bolded():
    fenced = f'# T\n\n```\n{MARK}\n```\n'
    assert writer.doc_text(fenced) == fenced
    assert f'**{MARK}**' in writer.doc_text(f'---\ntitle: T\n---\n# T\n\n{MARK}\n')


def test_bold_marker_does_not_break_the_approval_comparison(tmp_path):
    shown = writer.doc_text(f'# T\n\n{MARK}\n', 'outline')
    assert writer._doc_words(shown, 'outline') == writer._doc_words(f'# T\n\n{MARK}\n', 'outline')


@pytest.mark.parametrize('text', ['# T\n\n---\n\nA rule mid-text.\n', 'No front matter [F2].\n', '---\nnot closed\n'],
                         ids=['rule-later', 'none', 'unclosed'])
def test_only_a_leading_closed_front_matter_block_is_rendered(text):
    assert writer.doc_text(text) == writer.strip_fact_ids(text)


def test_an_entry_from_before_the_text_hash_never_causes_a_skip(ws):
    build_state(ws, 'unapproved')
    first = json.loads(doc_copy(ws.root, ws.slug, 'outline').out)
    old = dict(stage='outline', rev=1, id='d1', url='u', at='t', sha256=first['sha256'], title=first['title'], publish_ready=False)
    record_doc(ws, [old])
    assert json.loads(doc_copy(ws.root, ws.slug, 'outline').out)['skip'] is False


def test_a_change_in_what_reviewers_see_makes_a_new_doc_even_when_the_file_is_unchanged(ws):
    build_state(ws, 'unapproved')
    first = json.loads(doc_copy(ws.root, ws.slug, 'outline').out)
    record_doc(ws, [dict(entry_from(first, 1, 'u'), stage='outline', text_sha256='0' * 64)])
    again = json.loads(doc_copy(ws.root, ws.slug, 'outline').out)
    assert (again['sha256'] == first['sha256'], again['skip']) == (True, False)


def test_a_publish_ready_doc_with_raw_front_matter_is_blocked(ws):
    build_state(ws, 'signed')
    (ws.art / 'final.md').write_text(FRONT + '\nSigned-off-by: Test Human\n')
    writer.write_sidecar(str(ws.root), ws.slug, 'G4-final.r1.md')
    raw = writer.strip_fact_ids((ws.art / 'final.md').read_text())
    assert (drive_create_with(ws, READY_TITLE, textContent=raw).code, drive_create(ws, READY_TITLE).code) == (2, 0)


# ---------------- Phase 7b: no rename onto the label (update_file can retitle an existing Doc; the copy skill never renames) ----------------
DRIVE_UPDATE = 'mcp__claude_ai_Google_Drive__update_file'


def drive_update(ws, **ti):
    return guard(ws.root, {'hook_event_name': 'PreToolUse', 'tool_name': DRIVE_UPDATE, 'tool_input': dict({'fileId': 'd1'}, **ti)})


@pytest.mark.parametrize('state', ['signed', 'final-unsigned'])
@pytest.mark.parametrize('title', ['demo · final · r1 · publish-ready', 'demo · final · r1 · Publish Ready'], ids=['exact', 'variant'])
def test_a_doc_is_never_renamed_onto_the_publish_ready_label(ws, state, title):
    """A rename cannot be checked against the Doc's content, so even a final that qualifies gets its labelled Doc by a new upload."""
    build_state(ws, state)
    r = drive_update(ws, title=title)
    assert (r.code, 'FLOW-6' in r.err) == (2, True)


@pytest.mark.parametrize('ti', [{'title': 'demo · final · r1'}, {'starred': True}, {'readOnly': True}],
                         ids=['plain-title', 'star', 'lock'])
def test_other_doc_updates_are_allowed(ws, ti):
    build_state(ws, 'final-unsigned')
    assert drive_update(ws, **ti).code == 0


# ---------------- Phase 7b: Doc copies go into articles/<workspace folder>/<slug>/ in Drive (approver's request on PR #13) ----------------
def test_a_folder_recorded_before_the_articles_level_is_not_reused(ws):
    build_state(ws, 'unapproved')
    path = f'{os.path.basename(os.path.realpath(ws.root))}/demo'
    (ws.art / 'docs.json').write_text(json.dumps({'folder': {'id': 'F1', 'path': path}, 'revisions': []}))
    assert json.loads(doc_copy(ws.root, ws.slug, 'outline').out)['folder_id'] is None


def test_the_copy_names_the_drive_folder_after_the_workspace_and_the_slug(ws):
    build_state(ws, 'unapproved')
    out = json.loads(doc_copy(ws.root, ws.slug, 'outline').out)
    assert (out['folder_path'], out['folder_id']) == (['articles', os.path.basename(os.path.realpath(ws.root)), 'demo'], None)


def test_a_recorded_folder_for_the_same_path_is_reused(ws):
    build_state(ws, 'unapproved')
    path = f'articles/{os.path.basename(os.path.realpath(ws.root))}/demo'
    (ws.art / 'docs.json').write_text(json.dumps({'folder': {'id': 'F1', 'path': path}, 'revisions': []}))
    assert json.loads(doc_copy(ws.root, ws.slug, 'outline').out)['folder_id'] == 'F1'


def test_a_folder_recorded_for_another_path_is_not_reused(ws):
    """A renamed workspace folder means the Drive folder name no longer matches: look it up again."""
    build_state(ws, 'unapproved')
    (ws.art / 'docs.json').write_text(json.dumps({'folder': {'id': 'F1', 'path': 'articles/old-name/demo'}, 'revisions': []}))
    assert json.loads(doc_copy(ws.root, ws.slug, 'outline').out)['folder_id'] is None


def test_recording_the_folder_beside_an_appended_entry_is_allowed(ws):
    build_state(ws, 'final-unsigned')
    body = {'folder': {'id': 'F1', 'path': 'ws/demo'}, 'revisions': [entry(ws, ready=False)]}
    log_created(ws, body['revisions'])
    assert guard(ws.root, write_payload(ws.rel('docs.json'), json.dumps(body))).code == 0


def test_a_drive_folder_create_is_not_a_labelled_doc(ws):
    build_state(ws, 'final-unsigned')
    r = guard(ws.root, {'hook_event_name': 'PreToolUse', 'tool_name': DRIVE_CREATE,
                        'tool_input': {'title': 'demo', 'contentMimeType': 'application/vnd.google-apps.folder', 'parentId': 'F0'}})
    assert r.code == 0


# ---------------- ADR-015: the G1 save and the quote-check record ----------------
def research_ready(ws, record=True, body=None):
    """G0 stands, a research.md, and (by default) a quote-check record that matches it."""
    ws.chain('research')
    text = body if body is not None else '# research\n\ntext\n'
    (ws.art / 'research.md').write_text(text)
    if record:
        (ws.art / '.quote-check.json').write_text(json.dumps({'file': 'research.md', 'sha256': writer.text_hash(text), 'rows': {}, 'lines': []}))


def g1_save(ws, line=None, k=1, artifact='x'):
    return guard(ws.root, write_payload(ws.rel(f'gates/G1-research.r{k}.md'), head('research', line or PASS['research'], artifact, 'Coverage: n/a' if artifact == 'none' else None)))


def test_a_g1_verdict_is_saved_against_a_matching_quote_record(ws):
    research_ready(ws)
    assert g1_save(ws).code == 0


def test_a_g1_verdict_is_blocked_with_no_quote_record_and_the_message_names_the_command(ws):
    research_ready(ws, record=False)
    r = g1_save(ws)
    assert r.code == 2 and 'quote-check' in r.err and '--record' in r.err and 'FLOW-4' in r.err


def test_a_g1_verdict_is_blocked_when_research_changed_after_the_check(ws):
    research_ready(ws)
    (ws.art / 'research.md').write_text('# research\n\na different dossier\n')
    r = g1_save(ws)
    assert r.code == 2 and 'quote-check' in r.err


def test_a_corrupt_quote_record_blocks_the_g1_save(ws):
    research_ready(ws)
    (ws.art / '.quote-check.json').write_text('not json')
    r = g1_save(ws)
    assert r.code == 2 and 'quote-check' in r.err


def test_an_approval_line_after_the_check_still_matches_the_record(ws):
    research_ready(ws)
    (ws.art / 'research.md').write_text('# research\n\ntext\n\nApproved-by: Test Human\n')
    assert g1_save(ws).code == 0


def test_a_g1_block_is_also_saved_only_against_a_record(ws):
    research_ready(ws, record=False)
    r = g1_save(ws, line=BLOCK['research'])
    assert r.code == 2 and 'quote-check' in r.err


def test_the_g1_block_for_a_missing_research_needs_no_record(ws):
    ws.chain('research')
    (ws.art / 'research.md').unlink()
    assert g1_save(ws, line=BLOCK['research'], artifact='none').code == 0


def test_a_g1_verdict_that_claims_no_artifact_cannot_skip_the_record_while_research_exists(ws):
    research_ready(ws, record=False)
    r = g1_save(ws, line=BLOCK['research'], artifact='none')
    assert r.code == 2 and 'quote-check' in r.err


def test_other_gates_need_no_quote_record(ws):
    ws.approve()
    ws.chain('outline')
    assert guard(ws.root, write_payload(ws.rel('gates/G2-outline.r1.md'), head('outline', PASS['outline']))).code == 0


@pytest.mark.parametrize('payload', [
    write_payload('articles/demo/.quote-check.json', '{}'),
    edit_payload('articles/demo/.quote-check.json'),
    bash_payload('echo {} > articles/demo/.quote-check.json'),
    bash_payload('cp /tmp/x articles/demo/.quote-check.json'),
], ids=['write', 'edit', 'redirect', 'cp'])
def test_the_quote_record_is_written_only_by_the_script(ws, payload):
    r = guard(ws.root, payload)
    assert r.code == 2 and '--record' in r.err and 'FLOW-4' in r.err


def test_running_the_quote_script_with_record_is_not_blocked(ws):
    research_ready(ws)
    assert guard(ws.root, bash_payload(f'python3 {BIN / "quote-check.py"} --record demo')).code == 0


def test_a_pass_that_claims_no_artifact_cannot_skip_the_record_either(ws):
    ws.chain('research')
    (ws.art / 'research.md').unlink()
    r = g1_save(ws, line=PASS['research'], artifact='none')
    assert r.code == 2 and 'quote-check' in r.err


# ---------------- FT-6 (approval in the Doc): a copy is always unapproved and says where to approve ----------------
NOTE_APPROVE = 'To approve, write your name after the Approved-by label below, then run writer-plugin:sync.'
NOTE_SIGN = 'To approve, write your name after the Signed-off-by label below, then run writer-plugin:sync.'
HTML_NOTE = '<!-- A human fills this line to approve the outline. Any non-empty value after the colon means approved (FLOW-2);\n     an empty line is not approval. -->\n'


@pytest.mark.parametrize('value', ['', ' Test Human 2026-11-14'], ids=['empty', 'approved'])
def test_an_outline_copy_always_shows_an_empty_approval_line_and_the_instruction(value):
    text = f'# Outline\n\n{HTML_NOTE}Approved-by:{value}\n\n## Thesis\nA claim [F1].\n'
    assert writer.doc_text(text, 'outline') == f'# Outline\n\n{NOTE_APPROVE}\n\nApproved-by:\n\n## Thesis\nA claim.\n'


def test_an_unsigned_final_copy_names_the_signoff_line():
    text = '# T\n\nBody [F1].\n\nSigned-off-by:\n'
    assert writer.doc_text(text, 'final') == f'# T\n\nBody.\n\n{NOTE_SIGN}\n\nSigned-off-by:\n'


def test_a_publish_ready_final_keeps_its_signed_line_and_gets_no_instruction():
    text = '# T\n\nBody [F1].\n\nSigned-off-by: Test Human\n'
    out = writer.doc_text(text, 'final', keep_signoff=True)
    assert out == '# T\n\nBody.\n\nSigned-off-by: Test Human\n' and 'writer-plugin:sync' not in out


def test_a_copy_of_an_artifact_with_no_approval_line_gets_one_at_the_end():
    assert writer.doc_text('# Draft\n\nBody.\n', 'draft') == f'# Draft\n\nBody.\n\n{NOTE_APPROVE}\n\nApproved-by:\n'


def test_an_approval_word_inside_a_code_fence_is_not_an_approval_line():
    text = '# T\n\n```\nApproved-by: Test Human\n```\n'
    assert 'Approved-by: Test Human' in writer.doc_text(text, 'draft')


def test_without_a_stage_the_text_is_only_stripped_as_before():
    assert writer.doc_text('# T\n\nApproved-by: x\n') == '# T\n\nApproved-by: x\n'


def test_the_instruction_and_the_label_are_separate_paragraphs():
    """Google merges lines without a blank between them into one paragraph (R0), which would hide the label from `sync`."""
    out = writer.doc_text('# T\n\nBody.\nApproved-by:\n', 'outline')
    assert f'{NOTE_APPROVE}\n\nApproved-by:' in out and f'\n\n{NOTE_APPROVE}' in out


def test_the_instruction_is_not_an_approval_line_for_the_hash():
    shown = writer.doc_text('# T\n\nApproved-by:\n', 'outline')
    assert writer.text_hash(shown) != writer.text_hash('# T\n') and 'Approved-by:' not in writer.strip_approval(shown)


@pytest.mark.parametrize('state,stage', [('approved', 'outline'), ('unapproved', 'outline')], ids=['approved-outline', 'unapproved-outline'])
def test_doc_copy_of_an_outline_is_unapproved_whatever_the_file_says(ws, state, stage):
    build_state(ws, state)
    out = json.loads(doc_copy(ws.root, ws.slug, stage).out)
    assert NOTE_APPROVE in out['text'] and 'Approved-by: Test' not in out['text'] and out['text'].rstrip().count('Approved-by:') == 1


def test_doc_copy_of_a_signed_final_with_a_marker_is_unapproved_and_not_labelled(ws):
    signed_with_marker(ws)
    out = json.loads(doc_copy(ws.root, ws.slug, 'final').out)
    assert out['publish_ready'] is False and NOTE_SIGN in out['text'] and 'Signed-off-by: Test Human' not in out['text']


# ---------------- ADR-016 (R2): record the Docs the copy skill created and the approval a Doc carries ----------------
DRIVE_READ = 'mcp__claude_ai_Google_Drive__read_file_content'
APPROVE_NOTE = writer.doc_note('Approved-by')
OUTLINE_BODY = '# Outline\n\nApproved-by:\n\n## Thesis\nA thesis [F1].\n\n## Plan\nTwo `things` to do.\n'


def readback(shown, name='', tags=False):
    """What the connector returns for `shown` once Google has rendered it (R0): HTML comments gone, headings wrapped in `*…*`,
    backticks gone, `name` typed after the Approved-by label."""
    out = []
    for line in re.sub(r'<!--.*?-->', '', shown, flags=re.S).split('\n'):
        if line.startswith('# '):
            line = '# **' + line[2:] + '**'
        elif line.startswith('## '):
            line = '## *' + line[3:] + '*'
        elif line.startswith('Approved-by:') or line.startswith('Signed-off-by:'):
            line = line.rstrip() + (' ' + name if name else '')
        out.append(line.replace('`', ''))
    text = '\n'.join(l for l in out if l.strip() or True)
    return re.sub(r'\n{2,}', '\n', text)


def drive_post(tool, tool_input, response):
    return {'hook_event_name': 'PostToolUse', 'tool_name': tool, 'tool_input': tool_input, 'tool_response': response}


def created(ws, stage='outline', rev=1, label='', doc_id='doc1', text=None, title=None, log=True, record=True):
    """Make one Doc the way the copy skill does: upload doc_text of the artifact, let the hook log it, append docs.json."""
    art = (ws.art / f'{stage}.md')
    shown = text if text is not None else writer.doc_text(art.read_text(), stage)
    title = title if title is not None else f'{ws.slug} · {stage} · r{rev}' + (f' · {label}' if label else '')
    resp = json.dumps({'id': doc_id, 'title': title, 'mimeType': 'application/vnd.google-apps.document'})
    r = run('record-approval.py', drive_post(DRIVE_CREATE, {'title': title, 'textContent': shown, 'contentMimeType': 'text/markdown'}, resp), ws.root) if log else None
    if record:
        rows = json.loads((ws.art / 'docs.json').read_text())['revisions'] if (ws.art / 'docs.json').exists() else []
        rows.append(dict(stage=stage, rev=rev, id=doc_id, url=f'https://docs.example/{doc_id}', at='t', sha256=writer.text_hash(art.read_text()),
                         text_sha256=writer.text_hash(shown), title=title, publish_ready=label == 'publish-ready'))
        record_doc(ws, rows)
    return shown, r


def read(ws, body, doc_id='doc1', threads=None):
    resp = {'fileContent': body, 'title': 't', 'viewUrl': 'https://docs.example/' + doc_id}
    if threads:
        resp['commentThreads'] = threads
    return run('record-approval.py', drive_post(DRIVE_READ, {'fileId': doc_id, 'includeComments': True}, json.dumps(resp)), ws.root)


def approval(ws, stage='outline', rev=1):
    path = ws.art / 'approvals' / f'{stage}.r{rev}.json'
    return json.loads(path.read_text()) if path.exists() else None


@pytest.fixture
def ow(ws):
    (ws.art / 'outline.md').write_text(OUTLINE_BODY)
    return ws


def test_a_name_typed_in_the_latest_doc_of_an_unchanged_outline_is_recorded(ow):
    shown, _ = created(ow)
    assert read(ow, readback(shown, 'Test Human 2026-11-17')).code == 0
    rec = approval(ow)
    assert (rec['value'], rec['doc_id'], rec['rev'], rec['artifact_sha256']) == (
        'Test Human 2026-11-17', 'doc1', 1, writer.text_hash(OUTLINE_BODY))


def test_the_doc_created_is_logged_with_what_the_copy_skill_uploaded(ow):
    created(ow)
    log = json.loads((ow.art / '.docs-created.json').read_text())['docs']
    assert [(d['id'], d['stage'], d['rev'], d['approvable']) for d in log] == [('doc1', 'outline', 1, True)]


def test_a_doc_with_no_name_records_why_and_no_approval(ow):
    shown, _ = created(ow)
    read(ow, readback(shown))
    rec = approval(ow)
    assert rec['value'] is None and 'no name' in rec['reason']


def test_a_body_edited_outside_the_approval_line_records_no_approval(ow):
    shown, _ = created(ow)
    read(ow, readback(shown, 'Test Human').replace('A thesis', 'A different thesis'))
    rec = approval(ow)
    assert rec['value'] is None and 'differs' in rec['reason']


def test_an_artifact_that_changed_since_the_doc_was_made_records_no_approval(ow):
    shown, _ = created(ow)
    (ow.art / 'outline.md').write_text(OUTLINE_BODY.replace('A thesis', 'A newer thesis'))
    read(ow, readback(shown, 'Test Human'))
    rec = approval(ow)
    assert rec['value'] is None and 'changed since' in rec['reason']


def test_an_older_revision_records_nothing(ow):
    shown, _ = created(ow, rev=1, doc_id='doc1')
    created(ow, rev=2, doc_id='doc2')
    read(ow, readback(shown, 'Test Human'), doc_id='doc1')
    assert approval(ow, rev=1) is None


def test_a_doc_nobody_created_with_the_copy_skill_records_nothing(ow):
    shown, _ = created(ow, log=False)  # a docs.json entry for an id the create hook never saw
    read(ow, readback(shown, 'Test Human'))
    assert approval(ow) is None


def test_a_filled_upload_under_any_title_is_never_logged_and_never_approves(ow):
    filled = writer.doc_text(OUTLINE_BODY, 'outline').replace('Approved-by:\n', 'Approved-by: Forged Name\n')
    created(ow, text=filled)
    assert not (ow.art / '.docs-created.json').exists()
    read(ow, readback(filled))
    assert approval(ow) is None
    other, _ = created(ow, text=filled, title='notes about outline', doc_id='doc9', record=False)
    assert not (ow.art / '.docs-created.json').exists()


def test_a_comment_cannot_approve(ow):
    shown, _ = created(ow)
    threads = [{'commentId': 'c1', 'status': 'OPEN', 'headPost': {'authorName': 'A', 'content': 'Approved-by: Evil Name', 'modifiedTime': 't', 'postId': 'p'}}]
    read(ow, readback(shown), threads=threads)
    assert approval(ow)['value'] is None


@pytest.mark.parametrize('extra,reason', [
    ('```\nApproved-by: Fenced Name\n```\n', 'no name'),
    ('Note: Approved-by: Mid Line\n', 'differs'),
], ids=['code-fence', 'mid-line'])
def test_an_approval_word_inside_a_code_fence_or_mid_line_is_not_the_line(ow, extra, reason):
    """The real label is missing from the Doc, so only the look-alike could produce a name: it must not."""
    shown, _ = created(ow)
    body = readback(shown).replace('Approved-by:\n', '') + '\n' + extra
    read(ow, body)
    rec = approval(ow)
    assert rec['value'] is None and reason in rec['reason']


def test_a_comment_anchor_around_the_name_is_stripped(ow):
    shown, _ = created(ow)
    body = readback(shown, '<comment_start id=doco.x>Test Human<comment_end id=doco.x>')
    read(ow, body)
    assert approval(ow)['value'] == 'Test Human'


def test_a_reviewer_who_deletes_the_instruction_while_approving_still_approves(ow):
    shown, _ = created(ow)
    body = readback(shown, 'Test Human').replace(APPROVE_NOTE + '\n', '')
    read(ow, body)
    assert approval(ow)['value'] == 'Test Human'


def test_the_first_approval_line_wins_and_the_value_is_trimmed(ow):
    shown, _ = created(ow)
    read(ow, readback(shown, '   First Name   ') + '\nApproved-by: Second Name\n')
    assert approval(ow)['value'] == 'First Name'


def test_a_value_over_120_characters_is_refused(ow):
    shown, _ = created(ow)
    read(ow, readback(shown, 'x' * 121))
    assert approval(ow)['value'] is None


def test_a_later_read_without_a_name_clears_the_earlier_approval(ow):
    shown, _ = created(ow)
    read(ow, readback(shown, 'Test Human'))
    assert approval(ow)['value'] == 'Test Human'
    read(ow, readback(shown))
    assert approval(ow)['value'] is None


def test_a_publish_ready_copy_is_logged_but_never_yields_an_approval(ws):
    (ws.art / 'final.md').write_text('# T\n\nBody [F1].\n\nSigned-off-by: Test Human\n')
    shown = writer.doc_text((ws.art / 'final.md').read_text(), 'final', keep_signoff=True)
    created(ws, stage='final', label='publish-ready', text=shown)
    assert json.loads((ws.art / '.docs-created.json').read_text())['docs'][0]['approvable'] is False
    read(ws, shown)
    assert approval(ws, 'final') is None


def test_an_ungated_copy_is_logged_with_its_label(ow):
    created(ow, label='ungated')
    assert json.loads((ow.art / '.docs-created.json').read_text())['docs'][0]['id'] == 'doc1'


def test_an_upload_that_is_not_the_artifacts_copy_is_not_logged(ow):
    created(ow, text='# Something else\n')
    assert not (ow.art / '.docs-created.json').exists()


def test_the_final_uses_the_signoff_label(ws):
    (ws.art / 'final.md').write_text('# T\n\nBody [F1].\n\nSigned-off-by:\n')
    shown, _ = created(ws, stage='final')
    read(ws, readback(shown, 'Test Human'))
    assert approval(ws, 'final')['value'] == 'Test Human'


@pytest.mark.parametrize('raw', ['not json', '{}', '[]', '{"hook_event_name": "PostToolUse"}'], ids=['text', 'empty', 'list', 'no-tool'])
def test_the_recorder_fails_open_on_unreadable_input(ow, raw):
    assert run('record-approval.py', {}, ow.root, raw=raw).code == 0


def test_a_tool_response_that_is_not_json_records_nothing(ow):
    created(ow)
    assert run('record-approval.py', drive_post(DRIVE_READ, {'fileId': 'doc1'}, 'plain text'), ow.root).code == 0
    assert approval(ow) is None


def test_other_tools_are_ignored(ow):
    assert run('record-approval.py', drive_post('Write', {'file_path': 'x'}, {}), ow.root).code == 0
    assert not (ow.art / 'approvals').exists()


def test_hooks_json_registers_the_recorder_on_the_two_drive_tools():
    hooks = json.loads((PLUGIN / 'hooks' / 'hooks.json').read_text())['hooks']['PostToolUse']
    entry = next(h for h in hooks if 'record-approval.py' in h['hooks'][0]['command'])
    assert re.fullmatch(entry['matcher'], DRIVE_CREATE) and re.fullmatch(entry['matcher'], DRIVE_READ)
    assert not re.fullmatch(entry['matcher'], 'Write') and not re.fullmatch(entry['matcher'], 'mcp__claude_ai_Google_Drive__search_files')


# ---------------- ADR-016 (R3): the guard for approval in the Doc ----------------
def doc_tool(ws, tool, **ti):
    return guard(ws.root, {'hook_event_name': 'PreToolUse', 'tool_name': f'mcp__claude_ai_Google_{tool}', 'tool_input': ti})


def logged(ws, doc_id='docL', stage='outline'):
    (ws.art / '.docs-created.json').write_text(json.dumps({'docs': [{'id': doc_id, 'title': f'demo · {stage} · r1', 'slug': 'demo', 'stage': stage,
                                                                      'rev': 1, 'label': '', 'text_sha256': 'x', 'approvable': True, 'at': 't'}]}))


@pytest.mark.parametrize('stage,prev', [('research', 'brief'), ('outline', 'research'), ('draft', 'outline'), ('final', 'draft')])
def test_a_stage_is_blocked_until_the_previous_artifact_is_approved(ws, stage, prev):
    ws.chain(stage)
    (ws.art / f'{prev}.md').write_text(OUTLINE.format(approval='') if prev == 'outline' else f'# {prev}\n\ntext\n\nApproved-by:\n')
    r = guard(ws.root, write_payload(ws.rel(f'{stage}.md')))
    assert r.code == 2 and 'FLOW-2' in r.err and f'{prev}.md' in r.err


@pytest.mark.parametrize('stage,body', [('brief', '# Brief\n\ntext\n\nApproved-by: Test Human\n'), ('research', '# R\n\nApproved-by: Test Human\n'),
                                        ('outline', '# O\n\nApproved-by: Test Human\n'), ('draft', '# D\n\nApproved-by: Test Human\n')])
def test_a_tool_cannot_fill_an_approval_without_a_record(ws, stage, body):
    ws.chain('final')
    (ws.art / f'{stage}.md').write_text(body.replace('Test Human', ''))
    r = guard(ws.root, write_payload(ws.rel(f'{stage}.md'), body))
    assert r.code == 2 and 'FLOW-2' in r.err and 'Google Doc' in r.err


def test_an_approval_with_a_matching_record_is_allowed_whole_file_or_edit(ws):
    ws.chain('final')
    (ws.art / 'research.md').write_text('# R\n\nbody\n\nApproved-by:\n')
    signed = '# R\n\nbody\n\nApproved-by: Test Human\n'
    give_approval(ws, 'research', 'Test Human', signed)
    assert guard(ws.root, write_payload(ws.rel('research.md'), signed)).code == 0
    assert edit_final_like(ws, 'research.md', 'Approved-by:\n', 'Approved-by: Test Human\n').code == 0


def edit_final_like(ws, name, old, new):
    return guard(ws.root, {'hook_event_name': 'PreToolUse', 'tool_name': 'Edit', 'tool_input': {
        'file_path': ws.rel(name), 'old_string': old, 'new_string': new, 'replace_all': False}})


@pytest.mark.parametrize('rec_value,rec_text,why', [
    ('Someone Else', '# R\n\nbody\n\nApproved-by: Test Human\n', 'another name'),
    ('Test Human', '# R\n\nan older body\n\nApproved-by: Test Human\n', 'another text (stale)'),
], ids=['other-name', 'stale-hash'])
def test_a_record_for_another_name_or_text_does_not_allow_the_write(ws, rec_value, rec_text, why):
    ws.chain('final')
    (ws.art / 'research.md').write_text('# R\n\nbody\n\nApproved-by:\n')
    give_approval(ws, 'research', rec_value, rec_text)
    assert guard(ws.root, write_payload(ws.rel('research.md'), '# R\n\nbody\n\nApproved-by: Test Human\n')).code == 2, why


def test_clearing_an_approval_and_leaving_an_approved_file_untouched_are_allowed(ws):
    ws.chain('final')
    (ws.art / 'research.md').write_text('# R\n\nbody\n\nApproved-by: Test Human\n')
    assert guard(ws.root, write_payload(ws.rel('research.md'), '# R\n\nbody\n\nApproved-by:\n')).code == 0
    assert guard(ws.root, write_payload(ws.rel('research.md'), '# R\n\nbody\n\nApproved-by: Test Human\n')).code == 0


def test_changing_an_approved_artifact_while_keeping_the_name_is_refused(ws):
    ws.chain('final')
    (ws.art / 'research.md').write_text('# R\n\nbody\n\nApproved-by: Test Human\n')
    r = edit_final_like(ws, 'research.md', 'body', 'a different body')
    assert r.code == 2 and 'FLOW-2' in r.err and 'clears it' in r.err


def test_a_corrupt_approval_record_refuses_instead_of_allowing(ws):
    ws.chain('final')
    (ws.art / 'research.md').write_text('# R\n\nbody\n\nApproved-by:\n')
    (ws.art / 'approvals').mkdir()
    (ws.art / 'approvals' / 'research.r1.json').write_text('not json')
    assert guard(ws.root, write_payload(ws.rel('research.md'), '# R\n\nbody\n\nApproved-by: Test Human\n')).code == 2


def test_a_signoff_needs_the_record_as_well_as_the_g4_pass(ws):
    final_ready(ws)
    ws.verdict('final', 1, PASS['final'], sidecar=True)
    signed = FINAL.format(who=' Test Human')
    assert guard(ws.root, write_payload(ws.rel('final.md'), signed)).code == 0
    (ws.art / 'approvals' / 'final.r1.json').unlink()
    r = guard(ws.root, write_payload(ws.rel('final.md'), signed))
    assert r.code == 2 and 'FLOW-6' in r.err


@pytest.mark.parametrize('payload', [
    write_payload('articles/demo/approvals/outline.r1.json', '{}'),
    edit_payload('articles/demo/approvals/outline.r1.json'),
    bash_payload('echo {} > articles/demo/approvals/outline.r1.json'),
    write_payload('articles/demo/.docs-created.json', '{}'),
    edit_payload('articles/demo/.docs-created.json'),
    bash_payload('cp /tmp/x articles/demo/.docs-created.json'),
], ids=['write-approval', 'edit-approval', 'shell-approval', 'write-log', 'edit-log', 'shell-log'])
def test_no_tool_writes_the_approval_records_or_the_created_log(ws, payload):
    r = guard(ws.root, payload)
    assert r.code == 2 and 'FLOW-4' in r.err and 'sync' in r.err


def create(ws, title, text, **extra):
    return guard(ws.root, {'hook_event_name': 'PreToolUse', 'tool_name': DRIVE_CREATE,
                           'tool_input': dict({'title': title, 'textContent': text, 'contentMimeType': 'text/markdown'}, **extra)})


@pytest.mark.parametrize('title', ['notes', 'demo · outline · r1', 'demo · outline · r1 · ungated'], ids=['other-title', 'article-title', 'ungated'])
def test_an_upload_with_a_name_already_in_the_approval_line_is_refused_under_any_title(ow, title):
    r = create(ow, title, '# Outline\n\nApproved-by: Forged Name\n')
    assert r.code == 2 and 'FLOW-2' in r.err


def test_a_signoff_line_filled_in_an_upload_is_refused_too(ws):
    assert create(ws, 'notes', '# T\n\nSigned-off-by: Forged Name\n').code == 2


def test_an_exact_copy_is_allowed_and_a_look_alike_in_a_fence_is_not_an_approval(ow):
    shown = writer.doc_text(OUTLINE_BODY, 'outline')
    assert create(ow, 'demo · outline · r1', shown).code == 0
    assert create(ow, 'notes', '# Git\n\n```\nSigned-off-by: Jane <j@x.test>\n```\n').code == 0


@pytest.mark.parametrize('text,extra', [('# Something else\n', {}), (None, {'base64Content': 'eA=='}), (None, {'content': 'eA=='})],
                         ids=['other-text', 'base64', 'deprecated-content'])
def test_a_doc_titled_as_the_articles_copy_must_be_exactly_that_copy(ow, text, extra):
    shown = writer.doc_text(OUTLINE_BODY, 'outline')
    ti = {'title': 'demo · outline · r1', 'contentMimeType': 'text/markdown', **({'textContent': text} if text else {}), **extra}
    if text is None and extra:
        ti['textContent'] = shown
    r = guard(ow.root, {'hook_event_name': 'PreToolUse', 'tool_name': DRIVE_CREATE, 'tool_input': ti})
    assert r.code == 2 and 'FLOW-6' in r.err


def test_a_folder_create_and_an_unrelated_doc_pass(ow):
    folder = guard(ow.root, {'hook_event_name': 'PreToolUse', 'tool_name': DRIVE_CREATE, 'tool_input': {
        'title': 'demo', 'contentMimeType': 'application/vnd.google-apps.folder', 'parentId': 'root'}})
    assert folder.code == 0 and create(ow, 'my notes', '# Plain text\n').code == 0


def test_a_new_docs_entry_must_match_a_doc_the_create_hook_logged(ow):
    shown, _ = created(ow, log=True, record=False)
    good = entry(ow, stage='outline', ready=False)
    good['id'], good['title'] = 'doc1', 'demo · outline · r1'
    good['text_sha256'] = writer.text_hash(shown)
    assert docs_write(ow, [good], logged=False).code == 0
    for field, bad in (('id', 'other'), ('title', 'demo · outline · r9'), ('text_sha256', 'f' * 64), ('sha256', 'e' * 64)):
        assert docs_write(ow, [dict(good, **{field: bad})], logged=False).code == 2, field


def test_an_entry_with_no_log_or_a_corrupt_log_is_refused(ow):
    e = entry(ow, stage='outline', ready=False)
    assert docs_write(ow, [e], logged=False).code == 2
    (ow.art / '.docs-created.json').write_text('not json')
    assert docs_write(ow, [e], logged=False).code == 2


def test_the_publish_ready_path_and_an_ungated_copy_pass_the_whole_chain(ws):
    build_state(ws, 'signed')
    final = (ws.art / 'final.md').read_text()
    shown = writer.doc_text(final, 'final', keep_signoff=True)
    title = 'demo · final · r1 · publish-ready'
    assert create(ws, title, shown).code == 0
    run('record-approval.py', drive_post(DRIVE_CREATE, {'title': title, 'textContent': shown}, json.dumps({'id': 'dpr'})), ws.root)
    e = dict(entry(ws, ready=True), id='dpr', text_sha256=writer.text_hash(shown))
    assert docs_write(ws, [e], logged=False).code == 0


@pytest.mark.parametrize('tool', ['Docs__update_doc', 'Drive__update_file', 'Drive__copy_file', 'Drive__trash_file', 'Drive__share_file',
                                  'Drive__a_tool_added_later'], ids=['update-doc', 'update-file', 'copy', 'trash', 'share', 'unknown'])
def test_a_connector_call_that_is_not_a_read_is_refused_on_a_logged_doc(ws, tool):
    logged(ws)
    key = 'documentId' if tool.startswith('Docs') else 'fileId'
    assert doc_tool(ws, tool, **{key: 'docL'}).code == 2
    assert doc_tool(ws, tool, **{key: 'someone elses doc'}).code == 0


@pytest.mark.parametrize('tool', ['Docs__read_doc', 'Drive__read_file_content', 'Drive__get_file_metadata', 'Drive__download_file_content',
                                  'Drive__list_file_revisions'])
def test_reading_a_logged_doc_is_always_allowed(ws, tool):
    logged(ws)
    assert doc_tool(ws, tool, fileId='docL', documentId='docL').code == 0


@pytest.mark.parametrize('tool', ['Docs__update_doc', 'Drive__update_file', 'Drive__copy_file', 'Drive__trash_file', 'Drive__share_file'])
def test_a_write_tool_that_names_no_doc_is_refused(ws, tool):
    assert doc_tool(ws, tool, title='x').code == 2


def test_a_search_with_no_log_and_a_call_outside_a_workspace_pass(ws, tmp_path):
    assert doc_tool(ws, 'Drive__search_files', query="title = 'x'").code == 0
    assert doc_tool(ws, 'Drive__update_file', fileId='any', title='renamed').code == 0  # no log: nothing is protected yet
    elsewhere = tmp_path / 'not-a-workspace'
    elsewhere.mkdir()
    r = guard(elsewhere, {'hook_event_name': 'PreToolUse', 'tool_name': 'mcp__claude_ai_Google_Docs__update_doc', 'tool_input': {'documentId': 'd'}})
    assert r.code == 0


def test_a_corrupt_created_log_refuses_a_write_tool(ws):
    (ws.art / '.docs-created.json').write_text('{broken')
    assert doc_tool(ws, 'Docs__update_doc', documentId='anything').code == 2


@pytest.mark.parametrize('tool', ['mcp__claude_ai_Google_Docs__update_doc', 'mcp__claude_ai_Google_Drive__share_file', DRIVE_CREATE])
def test_input_the_guard_cannot_read_is_refused_for_a_connector_tool(ws, tool):
    assert guard(ws.root, {'hook_event_name': 'PreToolUse', 'tool_name': tool, 'tool_input': 'a string'}).code == 2


FAULTS = [
    ('approval-write', lambda ws: guard(ws.root, write_payload(ws.rel('research.md'), '# R\n'), env={'WRITER_GUARD_TEST_FAULT': 'approval-write'})),
    ('docs-entry', lambda ws: guard(ws.root, write_payload(ws.rel('docs.json'), json.dumps({'revisions': [entry(ws, stage='outline', ready=False)]})),
                                    env={'WRITER_GUARD_TEST_FAULT': 'docs-entry'})),
    ('create', lambda ws: guard(ws.root, {'hook_event_name': 'PreToolUse', 'tool_name': DRIVE_CREATE, 'tool_input': {'title': 'x', 'textContent': 'y'}},
                                env={'WRITER_GUARD_TEST_FAULT': 'create'})),
    ('doc-tool', lambda ws: guard(ws.root, {'hook_event_name': 'PreToolUse', 'tool_name': 'mcp__claude_ai_Google_Docs__update_doc',
                                            'tool_input': {'documentId': 'd'}}, env={'WRITER_GUARD_TEST_FAULT': 'doc-tool'})),
]


@pytest.mark.parametrize('name,call', FAULTS, ids=[f[0] for f in FAULTS])
def test_each_fail_closed_rule_blocks_when_it_hits_an_unexpected_error(ws, name, call):
    ws.chain('final')
    r = call(ws)
    assert r.code == 2 and 'could not be checked' in r.err and 'RuntimeError' in r.err


# ---------------- ADR-016 (R4): every stage waits for its approval, and the status carries `comments` ----------------
NEXT_AFTER = {'brief': 'research', 'research': 'outline', 'outline': 'draft', 'draft': 'final'}


def unapprove(ws, stage):
    (ws.art / f'{stage}.md').write_text(OUTLINE.format(approval='') if stage == 'outline' else f'# {stage}\n\ntext\n\nApproved-by:\n')


@pytest.mark.parametrize('stage', list(NEXT_AFTER))
def test_a_passed_stage_without_its_approval_is_waiting_for_a_human(ws, stage):
    ws.approve()  # the outline defaults to unapproved; only `stage` is left without its approval
    unapprove(ws, stage)
    ws.chain(NEXT_AFTER[stage])
    s = writer.article_state(str(ws.root), ws.slug)
    assert (s['next'], s['stage']) == ('approve', stage)
    assert s['summary'] == f"{stage} passed {GATE[stage]}, waiting for a human's Approved-by"
    assert writer.describe_article(str(ws.root), ws.slug).startswith(s['summary'])


@pytest.mark.parametrize('stage', list(NEXT_AFTER))
def test_an_approved_stage_hands_over_to_the_next(ws, stage):
    ws.chain(NEXT_AFTER[stage])
    if stage == 'outline':
        ws.approve()
    s = writer.article_state(str(ws.root), ws.slug)
    assert s['next'] != 'approve' or s['stage'] != stage


def test_an_unapproved_earlier_stage_holds_the_chain_even_when_later_files_exist(ws):
    unapprove(ws, 'research')
    ws.chain('final')
    s = writer.article_state(str(ws.root), ws.slug)
    assert (s['next'], s['stage']) == ('approve', 'research')


def test_a_stale_verdict_still_outranks_a_missing_approval(ws):
    unapprove(ws, 'research')
    ws.chain('outline')
    (ws.art / 'research.md').write_text('# research\n\nchanged text\n\nApproved-by:\n')
    assert writer.article_state(str(ws.root), ws.slug)['next'] == 'stale'


@pytest.mark.parametrize('state', ['nothing', 'brief-passed', 'unapproved', 'two-blocks', 'stale', 'final-unsigned', 'signed'])
def test_the_status_json_carries_an_empty_comments_list_in_every_state(ws, state):
    build_state(ws, state)
    out = json.loads(subprocess.run([sys.executable, str(BIN / 'article-status.py'), '--root', str(ws.root), ws.slug],
                                    capture_output=True, text=True).stdout)
    assert out['comments'] == [] and 'next' in out


@pytest.mark.parametrize('slug', ['', '../x', 'bad\nslug'], ids=['none', 'dotdot', 'newline'])
def test_an_invalid_slug_still_prints_unknown_with_an_empty_comments_list(ws, slug):
    args = [slug] if slug else []
    out = json.loads(subprocess.run([sys.executable, str(BIN / 'article-status.py'), '--root', str(ws.root), *args], capture_output=True, text=True).stdout)
    assert (out['next'], out['comments']) == ('unknown', [])


# ---------------- ADR-016 self-review findings ----------------
FILLED_OUTLINE = '# O\n\nApproved-by: Mallory\n'


@pytest.mark.parametrize('rel', ['Articles/demo/outline.md', 'ARTICLES/demo/outline.md', 'articles/demo/OUTLINE.md'], ids=['Articles', 'ARTICLES', 'OUTLINE'])
def test_the_guard_reads_the_articles_path_case_insensitively(ws, rel):
    """The default macOS filesystem treats these as the same file, so they must meet the same rules."""
    ws.chain('final')
    (ws.art / 'outline.md').write_text('# O\n\nApproved-by:\n')
    r = guard(ws.root, write_payload(rel, FILLED_OUTLINE))
    assert r.code == 2 and 'FLOW-2' in r.err


def test_a_symlink_to_the_articles_folder_is_guarded_like_the_folder(ws):
    ws.chain('final')
    (ws.art / 'outline.md').write_text('# O\n\nApproved-by:\n')
    os.symlink(ws.root / 'articles', ws.root / 'art2')
    r = guard(ws.root, write_payload('art2/demo/outline.md', FILLED_OUTLINE))
    assert r.code == 2 and 'FLOW-2' in r.err


@pytest.mark.parametrize('command', [
    "sed -i '' 's/^Approved-by:.*$/Approved-by: Mallory/' articles/demo/outline.md",
    "echo 'Approved-by: Mallory' >> articles/demo/outline.md",
    "printf 'Signed-off-by: Mallory\\n' >> articles/demo/final.md",
    "tee -a articles/demo/draft.md <<< 'approved-by: Mallory'",
    "perl -pi -e 's/^Approved-by:/Approved-by: M/' articles/demo/research.md",
], ids=['sed', 'echo-append', 'printf-signoff', 'tee', 'perl'])
def test_a_shell_command_that_writes_an_approval_label_into_an_artifact_is_refused(ws, command):
    ws.chain('final')
    r = guard(ws.root, bash_payload(command))
    assert r.code == 2 and 'Write tool' in r.err and ('FLOW-2' in r.err or 'FLOW-6' in r.err)


@pytest.mark.parametrize('command', [
    "echo 'Approved-by: someone' > articles/demo/notes.md",
    "git commit -m 'Signed-off-by: A'",
    "grep -n 'Approved-by' articles/demo/outline.md",
], ids=['other-file', 'no-target', 'a-read'])
def test_a_shell_command_that_does_not_write_an_artifact_is_not_caught_by_the_label_rule(ws, command):
    ws.chain('final')
    assert guard(ws.root, bash_payload(command)).code == 0


@pytest.mark.parametrize('ti', [
    {'ids': ['docL']}, {'target': {'doc': 'docL'}}, {'url': 'https://docs.google.com/document/d/docL/edit'}, {'fileIds': ['x', 'docL']},
], ids=['list', 'nested', 'url', 'second-item'])
def test_an_unknown_tool_is_refused_whatever_key_carries_a_logged_doc_id(ws, ti):
    logged(ws)
    assert doc_tool(ws, 'Docs__tool_added_later', **ti).code == 2
    assert doc_tool(ws, 'Docs__tool_added_later', **{k: 'someone elses doc' for k in ti}).code == 0


def test_a_read_tool_may_carry_a_logged_id_under_any_key(ws):
    logged(ws)
    assert doc_tool(ws, 'Drive__search_files', query='docL').code == 0


def test_a_text_line_that_ends_in_an_html_comment_is_not_deleted_from_the_copy():
    text = '# T\n\nKeep TTL under 200 ms. <!-- see F3 -->\nApproved-by:\n'
    out = writer.doc_text(text, 'outline')
    assert 'Keep TTL under 200 ms.' in out and f'{NOTE_APPROVE}\n\nApproved-by:' in out


def test_a_multi_line_guidance_comment_directly_above_the_line_is_still_dropped():
    out = writer.doc_text('# T\n\n<!-- one\n     two -->\nApproved-by:\n', 'outline')
    assert 'one' not in out and 'two' not in out


@pytest.mark.parametrize('old,new', [('10.5%', '-10,5%'), ('x < 5', 'x > 5'), ('a = b', 'a ± b'), ('costs $5', 'costs 5'), ('3.14', '314')],
                         ids=['sign-and-decimal', 'less-greater', 'equals-plusminus', 'currency', 'decimal-point'])
def test_an_edit_that_changes_only_a_number_or_an_operator_is_still_an_edit(ow, old, new):
    (ow.art / 'outline.md').write_text(OUTLINE_BODY.replace('A thesis', f'A thesis with {old}'))
    shown, _ = created(ow)
    read(ow, readback(shown, 'Test Human').replace(old, new))
    rec = approval(ow)
    assert rec['value'] is None and 'differs' in rec['reason']


@pytest.mark.parametrize('word', ['max_age', 'a_b_c'])
def test_an_underscore_escaped_by_google_is_not_an_edit(ow, word):
    (ow.art / 'outline.md').write_text(OUTLINE_BODY.replace('A thesis', f'A {word} thesis'))
    shown, _ = created(ow)
    read(ow, readback(shown, 'Test Human').replace(word, word.replace('_', '\\_')))
    assert approval(ow)['value'] == 'Test Human'


def test_a_stage_whose_previous_artifact_cannot_be_read_is_refused_not_allowed(ws):
    ws.chain('outline')
    (ws.art / 'research.md').write_bytes(b'\xff\xfe broken \xff\nApproved-by:\n')
    r = guard(ws.root, write_payload(ws.rel('outline.md')))
    assert r.code == 2 and 'could not be checked' in r.err


def test_the_stage_rule_blocks_when_it_hits_an_unexpected_error(ws):
    ws.chain('outline')
    r = guard(ws.root, write_payload(ws.rel('outline.md')), env={'WRITER_GUARD_TEST_FAULT': 'stage'})
    assert r.code == 2 and 'RuntimeError' in r.err


def test_two_creates_at_once_both_end_up_in_the_created_log(ow):
    shown = writer.doc_text(OUTLINE_BODY, 'outline')
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(ow.root))
    procs = []
    for i in range(8):
        payload = drive_post(DRIVE_CREATE, {'title': f'demo · outline · r{i + 1}', 'textContent': shown}, json.dumps({'id': f'doc{i}'}))
        procs.append(subprocess.Popen([sys.executable, str(BIN / 'record-approval.py')], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True, env=env, cwd=str(ow.root)))
        procs[-1].stdin.write(json.dumps(dict(payload, cwd=str(ow.root))))
        procs[-1].stdin.close()
    for p in procs:
        p.wait(timeout=30)
    ids = sorted(d['id'] for d in json.loads((ow.art / '.docs-created.json').read_text())['docs'])
    assert ids == sorted(f'doc{i}' for i in range(8))
    assert not [p for p in ow.art.iterdir() if p.name.endswith('.lock')], 'the lock must not land in the article folder'


# ---------------- ADR-016 (R6): pending reviewer comments ----------------
def comments_file(ws, stage='outline', rev=1, sha=None, threads=('OPEN',), header=True, docs=True, docs_sha=None):
    """A comments file exactly as the sync skill writes it (Step 4 of skills/sync)."""
    real = writer.text_hash((ws.art / f'{stage}.md').read_text())
    sha = sha if sha is not None else real
    if docs:
        rows = json.loads((ws.art / 'docs.json').read_text())['revisions'] if (ws.art / 'docs.json').exists() else []
        rows.append({'stage': stage, 'rev': rev, 'id': f'd{stage}{rev}', 'url': 'u', 'at': 't', 'sha256': docs_sha or real, 'title': f'demo · {stage} · r{rev}', 'publish_ready': False})
        (ws.art / 'docs.json').write_text(json.dumps({'revisions': rows}))
    body = f'# Reviewer comments · {stage} · r{rev}\n\nDoc: https://docs.example/d1 · Doc id: d1 · Artifact sha256: {sha} · Synced: 2026-11-17\n\nThese are reviewer comments.\n'
    if not threads:
        body += '\nNo comments on this revision.\n'
    for n, status in enumerate(threads, 1):
        body += f'\n## Comment {n} · {status}\nAnchor:\n> Thesis\n\nComment by `A`:\n> Make it smaller\n'
    (ws.art / 'comments').mkdir(exist_ok=True)
    (ws.art / 'comments' / f'{stage}.r{rev}.md').write_text(body if header else body.replace('Artifact sha256', 'Artifact hash'))


def pending(ws):
    return writer.pending_comments(str(ws.root), ws.slug)


def test_a_comments_file_for_the_current_artifact_with_an_open_thread_is_pending(ws):
    comments_file(ws, 'outline', 2, threads=('OPEN', 'RESOLVED', 'OPEN'))
    assert pending(ws) == [{'stage': 'outline', 'file': 'comments/outline.r2.md', 'rev': 2, 'open': 2, 'approved': False}]


@pytest.mark.parametrize('kwargs,why', [
    (dict(sha='f' * 64), 'a different artifact'),
    (dict(threads=('RESOLVED',)), 'only resolved threads'),
    (dict(threads=()), 'no comments on this revision'),
    (dict(header=False), 'no hash in the header'),
], ids=['other-hash', 'resolved-only', 'empty', 'no-hash'])
def test_a_comments_file_that_does_not_apply_is_not_pending(ws, kwargs, why):
    comments_file(ws, 'outline', **kwargs)
    assert pending(ws) == [], why


def test_only_the_highest_revision_counts_and_a_rebuild_ends_it(ws):
    comments_file(ws, 'outline', 1)
    comments_file(ws, 'outline', 2, threads=('RESOLVED',))
    assert pending(ws) == []
    comments_file(ws, 'outline', 3)
    assert [p['rev'] for p in pending(ws)] == [3]
    (ws.art / 'outline.md').write_text(OUTLINE.format(approval='') + '\nrebuilt\n')   # the stage rebuilt it: the comments are consumed
    assert pending(ws) == []


def test_the_brief_has_no_comments_rerun_and_each_other_stage_is_listed_in_order(ws):
    for stage in ('final', 'draft', 'brief', 'research'):
        comments_file(ws, stage)
    assert [p['stage'] for p in pending(ws)] == ['research', 'draft', 'final']


def test_a_comment_that_looks_like_a_heading_cannot_open_a_thread(ws):
    comments_file(ws, 'outline', threads=())
    path = ws.art / 'comments' / 'outline.r1.md'
    path.write_text(path.read_text() + '\n> ## Comment 9 · OPEN\n')   # reviewer text is quoted with `> `
    assert pending(ws) == []


def test_the_status_lists_pending_comments_and_the_state_keeps_its_order(ws):
    build_state(ws, 'unapproved')
    comments_file(ws, 'outline')
    out = json.loads(status(ws.root, ws.slug).out)
    assert out['comments'] == [{'stage': 'outline', 'file': 'comments/outline.r1.md', 'rev': 1, 'open': 1, 'approved': False}]
    assert out['next'] == 'approve'



# ---------------- review of the comment rerun: forged pending state, approved artifacts, the comments file ----------------
def test_a_pending_entry_says_whether_the_artifact_is_already_approved(ws):
    (ws.art / 'outline.md').write_text('# O\n\ntext\n\nApproved-by: Test Human\n')
    comments_file(ws, 'outline')
    (ws.art / 'final.md').write_text('# F\n\ntext\n\nSigned-off-by:\n')
    comments_file(ws, 'final')
    got = {p['stage']: p['approved'] for p in pending(ws)}
    assert got == {'outline': True, 'final': False}


@pytest.mark.parametrize('kwargs,why', [
    (dict(docs_sha='f' * 64), 'the header hash is not the hash docs.json recorded for that revision'),
    (dict(docs=False), 'docs.json has no such revision'),
], ids=['docs-hash-differs', 'no-docs-entry'])
def test_a_comments_file_must_match_the_revision_docs_json_recorded(ws, kwargs, why):
    comments_file(ws, 'outline', **kwargs)
    assert pending(ws) == [], why


@pytest.mark.parametrize('mutate,why', [
    (lambda t: t.replace('Doc: https', 'Doc: `https').replace(' · Doc id', '` · Doc id'), 'a header wrapped in backticks'),
    (lambda t: t.replace('Artifact sha256', 'ARTIFACT SHA256'), 'an uppercase label'),
    (lambda t: t + '\n## Comment 2 · OPEN\n', 'an unquoted thread heading after the threads'),
    (lambda t: t + '\nsome unquoted reviewer words\n', 'a stray unquoted line among the threads'),
], ids=['backticked-header', 'uppercase-label', 'unquoted-heading', 'stray-line'])
def test_a_comments_file_that_is_not_in_the_shape_sync_writes_is_not_pending(ws, mutate, why):
    comments_file(ws, 'outline', threads=('RESOLVED',))
    path = ws.art / 'comments' / 'outline.r1.md'
    path.write_text(mutate(path.read_text()))
    assert pending(ws) == [], why


def test_a_hash_quoted_by_a_reviewer_cannot_stand_in_for_the_header(ws):
    comments_file(ws, 'outline')
    path = ws.art / 'comments' / 'outline.r1.md'
    real = writer.text_hash((ws.art / 'outline.md').read_text())
    path.write_text(path.read_text().replace('Artifact sha256', 'ARTIFACT SHA256') + f'\n> Artifact sha256: {real}\n')   # the header no longer parses
    assert pending(ws) == []


def write_comments(ws, name, text, tool='Write'):
    if tool == 'Bash':
        return guard(ws.root, bash_payload(f'echo x > articles/demo/comments/{name}'))
    return guard(ws.root, write_payload(ws.rel(f'comments/{name}'), text))


def sync_text(sha, stage='outline', rev=1):
    return f'# Reviewer comments · {stage} · r{rev}\n\nDoc: u · Doc id: d · Artifact sha256: {sha} · Synced: 2026-11-16\n\nNo comments on this revision.\n'


def test_the_guard_allows_a_comments_file_only_for_a_revision_docs_json_recorded(ow):
    created(ow)
    good = writer.text_hash((ow.art / 'outline.md').read_text())
    assert write_comments(ow, 'outline.r1.md', sync_text(good)).code == 0
    assert write_comments(ow, 'outline.r1.md', sync_text('f' * 64)).code == 2          # a hash that is not the recorded one
    assert write_comments(ow, 'outline.r2.md', sync_text(good, rev=2)).code == 2       # no such revision in docs.json
    assert write_comments(ow, 'outline.r1.md', 'no header at all').code == 2
    assert write_comments(ow, 'outline.r1.md', '', tool='Bash').code == 2
    assert write_comments(ow, 'my-notes.md', 'anything').code == 0                       # not a sync file: not guarded


def test_a_corrupt_docs_json_refuses_a_comments_write_instead_of_allowing_it(ow):
    (ow.art / 'docs.json').write_text('not json')
    assert write_comments(ow, 'outline.r1.md', sync_text('a' * 64)).code == 2


def test_the_comments_rule_blocks_when_it_hits_an_unexpected_error(ow):
    created(ow)
    r = guard(ow.root, write_payload(ow.rel('comments/outline.r1.md'), sync_text('a' * 64)), env={'WRITER_GUARD_TEST_FAULT': 'comments'})
    assert r.code == 2 and 'RuntimeError' in r.err


def test_the_created_log_lock_leaves_nothing_in_the_article_folder_or_the_temp_folder(ow):
    shown = writer.doc_text(OUTLINE_BODY, 'outline')
    everything = lambda: sorted(str(p) for p in Path(tempfile.gettempdir()).glob('writer-plugin*/**/*'))
    before = everything()
    run('record-approval.py', drive_post(DRIVE_CREATE, {'title': 'demo · outline · r1', 'textContent': shown}, json.dumps({'id': 'x1'})), ow.root)
    assert not [p for p in ow.art.iterdir() if 'lock' in p.name]
    assert everything() == before, 'no lock file anywhere'
