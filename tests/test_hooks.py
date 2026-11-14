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
    'final': '## G4 final gate: PASS (0 blocking, 0 advisory)',
}
BLOCK = {
    'brief': '## G0 brief gate: BLOCK (1 blocking, 0 advisory)',
    'research': '## G1 research gate: BLOCK (1 blocking, 0 advisory)',
    'outline': '## G2 outline gate: BLOCK (2 blocking, 0 advisory)',
    'final': '## G4 final gate: BLOCK (1 blocking, 0 advisory)',
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


@pytest.mark.parametrize('command', [
    'echo "note: x > articles/demo/gates/G0-brief.r2.md"',
    "grep -n 'a > articles/demo/draft.md' notes.txt",
], ids=['double-quoted-arrow', 'single-quoted-arrow'])
def test_a_redirect_sign_inside_quotes_is_text_not_a_write(ws, command):
    ws.verdict('brief', 1, PASS['brief'])
    assert guard(ws.root, bash_payload(command)).code == 0


# ---------------- Phase 5 (ADR-010): the G4 save, the lint record and the sign-off ----------------
MARKER = "<Can't be verified. Reason: no source covers it.>"
FINAL = '# T\n\nBody text.\n\nSigned-off-by:{who}\n'


def final_ready(ws, text=None, record=True):
    """A workspace whose G0..G3 stand, a final.md, and (by default) a lint record that matches it."""
    ws.approve()
    ws.chain('final')
    body = text if text is not None else FINAL.format(who='')
    (ws.art / 'final.md').write_text(body)
    if record:
        (ws.art / '.prose-lint.json').write_text(json.dumps({'sha256': writer.text_hash(body), 'findings': 0, 'lines': []}))
    return body


def g4_save(ws, line=None, k=1):
    return guard(ws.root, write_payload(ws.rel(f'gates/G4-final.r{k}.md'), (line or PASS['final']) + '\nArtifact: x\n'))


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
    assert g4_save(ws).code == 2


def test_a_sign_off_only_change_after_the_lint_still_matches_the_record(ws):
    final_ready(ws)
    (ws.art / 'final.md').write_text(FINAL.format(who=' Test Human'))
    assert g4_save(ws).code == 0


def test_a_g3_verdict_save_needs_no_lint_record(ws):
    ws.approve()
    ws.chain('draft')
    r = guard(ws.root, write_payload(ws.rel('gates/G3-draft.r1.md'), PASS['draft'] + '\nArtifact: x\n'))
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


def test_a_shell_write_to_final_is_allowed_by_the_sign_off_rule_a_stated_gap(ws):
    final_ready(ws)
    assert guard(ws.root, bash_payload("sed -i '' 's/Signed-off-by:/Signed-off-by: X/' articles/demo/final.md")).code == 0


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
    elif state in ('final-unsigned', 'signed', 'marker-final', 'malformed-marker-final', 'fenced-sign-off'):
        body = {'final-unsigned': '# T\n\nBody.\n\nSigned-off-by:\n',
                'signed': '# T\n\nBody.\n\nSigned-off-by: Test Human\n',
                'marker-final': f'# T\n\nBody {MARKER}\n\nSigned-off-by:\n',
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
             'marker-final', 'malformed-marker-final', 'fenced-sign-off']
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
    assert set(out) == {'slug', 'stage', 'next', 'reason', 'markers', 'stale'}
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
