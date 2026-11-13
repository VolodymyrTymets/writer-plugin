"""Hook behaviour against throwaway workspaces. Run: python -m pytest tests/test_hooks.py

Each test builds a small content workspace under tmp_path (neutral synthetic articles, PLG-1) and runs the real script as a
subprocess with the JSON payload Claude Code sends, the way the hooks run in a session. Payload shapes were observed with a
probe plugin (docs/decisions/ADR-009): Write has file_path and content, Edit has file_path/old_string/new_string/replace_all,
Bash has command; a block is exit 2 with the reason on stderr.
"""
import json
import os
import subprocess
import sys
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
}
BLOCK = {
    'brief': '## G0 brief gate: BLOCK (1 blocking, 0 advisory)',
    'research': '## G1 research gate: BLOCK (1 blocking, 0 advisory)',
    'outline': '## G2 outline gate: BLOCK (2 blocking, 0 advisory)',
}
GATE = {'brief': 'G0', 'research': 'G1', 'outline': 'G2', 'draft': 'G3', 'final': 'G4'}
STAGES = ['brief', 'research', 'outline', 'draft', 'final']
OUTLINE = '# Outline\n\nApproved-by:{approval}\n\n## Thesis\nA thesis.\n'


def run(script, payload, root, raw=None):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root))
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


def guard(root, payload, **kw):
    return run('guard-stage-order.py', payload, root, **kw)


class Workspace:
    def __init__(self, root: Path, slug='demo'):
        self.root, self.slug = root, slug
        self.art = root / 'articles' / slug
        (self.art / 'gates').mkdir(parents=True)
        for stage in STAGES:
            (self.art / f'{stage}.md').write_text(OUTLINE.format(approval='') if stage == 'outline' else f'# {stage}\n\ntext\n')

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
    r = guard(ws.root, write_payload(ws.rel('gates/G0-brief.r2.md'), BLOCK['brief'] + '\nArtifact: x\n'))
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


def test_the_next_number_continues_past_the_archive(ws):
    ws.verdict('brief', 1, PASS['brief'], archived=True)
    ws.verdict('brief', 2, BLOCK['brief'], archived=True)
    assert guard(ws.root, write_payload(ws.rel('gates/G0-brief.r1.md'), PASS['brief'] + '\n')).code == 2   # collides with the archive
    assert guard(ws.root, write_payload(ws.rel('gates/G0-brief.r3.md'), PASS['brief'] + '\n')).code == 0


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
@pytest.mark.parametrize('rel', ['notes.md', 'articles/demo/outline.prev.1.md', 'articles/demo/.prose-lint.json', 'docs/x.md'])
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
    assert pre[0]['matcher'] == 'Edit|Write|Bash', 'MultiEdit does not exist in this build; mcp tools are not parsed (ADR-009)'
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
