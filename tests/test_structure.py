"""Structure guard. Run: python -m pytest tests/test_structure.py

Adapted from rln-agent. It is written to pass on the Phase 1 skeleton (no skills, agents or hooks yet) and to start
enforcing each rule the moment the thing it guards exists - so a gate skill added in Phase 3 is checked for
`context: fork` from its first commit, not from whenever someone remembers to add a test.
"""
import json
import os
import re
import warnings
from pathlib import Path

from conftest import PLUGIN as ROOT

# A plugin skill takes its command from frontmatter `name:` (unlike a project skill, where the directory name wins).
# COMMANDS is the single source of truth for what exists: directory -> command.
COMMANDS = {
    'intake-brief': 'brief',
    'check-brief': 'check-brief',
    'research': 'research',
    'check-research': 'check-research',
    'outline': 'outline',
    'check-outline': 'check-outline',
    'check-draft': 'check-draft',
    'draft': 'draft',
    'check-final': 'check-final',
    'edit-final': 'edit',
    'article': 'article',
}
# Built next, in the order of docs/DESIGN.md. Move an entry from PLANNED to COMMANDS in the commit that adds the skill.
PLANNED = {
    'setup-workspace': 'setup',
    'publish': 'publish',
    'sync-comments': 'sync',
}
# Planned commands may be named only where a roadmap lives.
PLANNED_OK_IN = ['README.md', 'CHANGELOG.md', 'docs/DESIGN.md']
# Skills that judge an artifact. They must fork into a write-free agent and make the caller wait.
GATE_SKILLS = ['check-brief', 'check-research', 'check-outline', 'check-draft', 'check-final']
# Agents that gates fork into. They must have no write tool.
GATE_AGENTS = ['gate', 'fact-gate']
WRITE_TOOLS = re.compile(r'\b(Edit|Write|MultiEdit|NotebookEdit)\b')
# Claude Code's own commands. Referencing them is fine; naming a skill after one is not.
BUILTINS = ['mcp', 'context', 'plugin', 'compact', 'clear', 'config', 'init', 'help', 'rewind', 'agents', 'doctor',
            'review', 'code-review', 'security-review', 'login', 'logout', 'feedback', 'loop', 'schedule', 'resume',
            'rename', 'model', 'memory', 'permissions', 'hooks', 'status', 'cost', 'usage', 'export', 'add-dir',
            'ide', 'vim', 'bug', 'upgrade', 'statusline', 'output-style', 'release-notes', 'todos']
BUILTIN_AGENTS = ['Explore', 'Plan', 'general-purpose']
RULE_ID = re.compile(r'\b(BRF|FACT|STR|VOI|SEO|FLOW|PLG)-\d+\b')

SKIP_DIRS = {'.git', 'node_modules', '__pycache__', '.pytest_cache', '.venv', '.idea'}


def read(path) -> str:
    return Path(path).read_text(encoding='utf-8')


def frontmatter(path):
    t = read(path)
    if not t.startswith('---\n'):
        return None
    end = t.find('\n---\n', 3)
    return None if end < 0 else t[4:end]


def keys(block: str) -> dict:
    return {m.group(1): m.group(2).strip() for m in re.finditer(r'^([a-zA-Z_-]+):\s*(.*)$', block, re.M)}


def listdir(directory) -> list:
    d = ROOT / directory
    return sorted(os.listdir(d)) if d.is_dir() else []


def walk(directory) -> list:
    out = []
    for name in sorted(os.listdir(directory)):
        p = Path(directory) / name
        if name in SKIP_DIRS:
            continue
        out.extend(walk(p) if p.is_dir() else [p])
    return out


def rel(p) -> str:
    return os.path.relpath(p, ROOT).replace(os.sep, '/')


def report(fails, warns=()):
    for w in warns:
        warnings.warn(w)
    assert not fails, '\n' + '\n'.join(f'FAIL: {f}' for f in fails)


PLUGIN_JSON = json.loads(read(ROOT / '.claude-plugin' / 'plugin.json'))
PLUGIN_NAME = PLUGIN_JSON['name']
SKILL_DIRS = [d for d in listdir('skills') if not d.startswith('.')]
AGENT_FILES = [f[:-3] for f in listdir('agents') if f.endswith('.md')]


# ---------------- manifest and marketplace ----------------

def test_manifest_and_marketplace_agree():
    fails = []
    if PLUGIN_NAME != 'writer-plugin':
        fails.append(f'plugin.json name is "{PLUGIN_NAME}", expected "writer-plugin" - agent ids and the install command depend on it')
    if not re.fullmatch(r'\d+\.\d+\.\d+', PLUGIN_JSON.get('version', '')):
        fails.append('plugin.json version is not MAJOR.MINOR.PATCH')
    market = json.loads(read(ROOT / '.claude-plugin' / 'marketplace.json'))
    entries = [p for p in market.get('plugins', []) if p.get('name') == PLUGIN_NAME]
    if len(entries) != 1:
        fails.append(f'marketplace.json must list "{PLUGIN_NAME}" exactly once')
    elif entries[0].get('source') != './':
        fails.append('marketplace.json: the plugin source must be "./" - this repo is its own marketplace')
    report(fails)


# ---------------- command map hygiene ----------------

def test_command_map_has_no_collisions():
    fails = []
    names = list(COMMANDS.values()) + list(PLANNED.values())
    for n in sorted({n for n in names if names.count(n) > 1}):
        fails.append(f'command "/{n}" is declared twice across COMMANDS and PLANNED')
    for d in sorted(set(COMMANDS) & set(PLANNED)):
        fails.append(f'skills/{d} is in both COMMANDS and PLANNED - move it, do not copy it')
    for n in names:
        if n in BUILTINS:
            fails.append(f'"/{n}" collides with a Claude Code built-in - the bare command would never reach the skill')
    for g in GATE_SKILLS:
        if g not in COMMANDS and g not in PLANNED:
            fails.append(f'gate "{g}" is in GATE_SKILLS but in neither COMMANDS nor PLANNED')
    report(fails)


# ---------------- skills (flat) ----------------

def test_skills_are_flat_named_and_complete():
    fails = []
    for d in SKILL_DIRS:
        sd = ROOT / 'skills' / d
        f = sd / 'SKILL.md'
        if not sd.is_dir():
            fails.append(f'skills/{d} is not a directory')
            continue
        if not f.exists():
            fails.append(f'skills/{d} has no SKILL.md')
            continue
        b = frontmatter(f)
        if not b:
            fails.append(f'skills/{d}/SKILL.md has no frontmatter')
            continue
        k = keys(b)
        expected = COMMANDS.get(d)
        if expected is None:
            hint = ' (it is still in PLANNED - move it to COMMANDS)' if d in PLANNED else ''
            fails.append(f'skills/{d}: not in the COMMANDS map{hint}')
        elif k.get('name') != expected:
            fails.append(f'skills/{d}: frontmatter name "{k.get("name")}" but COMMANDS says "{expected}"')
        if len(k.get('description') or '') < 40:
            fails.append(f'skills/{d}: description too short to trigger reliably')
        text = read(f)
        if len(text.split('\n')) > 500:
            fails.append(f'skills/{d}/SKILL.md is over the 500-line budget - move depth into references/')
        for ref in re.finditer(r'@(references/[\w./-]+\.md)', text):
            if not (sd / ref.group(1)).exists():
                fails.append(f'skills/{d}: missing {ref.group(1)}')
        for sub in os.listdir(sd):
            if sub != 'references' and (sd / sub).is_dir():
                fails.append(f'skills/{d}/{sub}: only references/ may be nested inside a skill')
    for d in COMMANDS:
        if d not in SKILL_DIRS:
            fails.append(f'COMMANDS lists skills/{d}, which does not exist')
    report(fails)


# ---------------- gates fork into a write-free agent ----------------

def test_gate_skills_fork_into_a_write_free_agent():
    fails = []
    for d in SKILL_DIRS:
        f = ROOT / 'skills' / d / 'SKILL.md'
        b = f.exists() and frontmatter(f)
        if not b:
            continue
        k = keys(b)
        forked = k.get('context') == 'fork'
        if d in GATE_SKILLS and not forked:
            fails.append(f'skills/{d}: a gate needs "context: fork" - a fresh reader asked for in prose is not a mechanism')
        if not forked:
            for field in ('agent', 'background'):
                if k.get(field):
                    fails.append(f'skills/{d}: "{field}:" without "context: fork" has no effect')
            continue
        a = k.get('agent')
        if not a:
            fails.append(f'skills/{d}: forked with no "agent:" - it would run as general-purpose, which can write')
        elif a not in BUILTIN_AGENTS:
            if not a.startswith(f'{PLUGIN_NAME}:'):
                fails.append(f'skills/{d}: agent "{a}" must be scoped as "{PLUGIN_NAME}:<name>"')
            elif a.split(':', 1)[1] not in AGENT_FILES:
                fails.append(f'skills/{d}: agent "{a}" has no agents/{a.split(":", 1)[1]}.md - the fork would silently fall back to general-purpose')
        if d in GATE_SKILLS and k.get('background') != 'false':
            fails.append(f'skills/{d}: a gate must set "background: false" so the caller waits for the verdict')
    report(fails)


# ---------------- agents ----------------

def test_agents_are_well_formed_and_gate_agents_cannot_write():
    fails = []
    for a in AGENT_FILES:
        b = frontmatter(ROOT / 'agents' / f'{a}.md')
        if not b:
            fails.append(f'agents/{a}.md has no frontmatter')
            continue
        k = keys(b)
        if k.get('name') != a:
            fails.append(f'agents/{a}.md: name "{k.get("name")}" does not match the file name')
        if len(k.get('description') or '') < 40:
            fails.append(f'agents/{a}.md: description too short')
        if a in GATE_AGENTS:
            if not k.get('tools'):
                fails.append(f'agents/{a}.md: a gate agent must list its tools - no list means every tool, including Write')
            elif WRITE_TOOLS.search(k['tools']):
                fails.append(f'agents/{a}.md: a gate agent has a write tool ({WRITE_TOOLS.search(k["tools"]).group(0)}) - rule FLOW-4')
    report(fails)


# ---------------- hooks ----------------

def test_hooks_json_points_at_scripts_that_exist():
    fails = []
    hooks = json.loads(read(ROOT / 'hooks' / 'hooks.json')).get('hooks')
    if not isinstance(hooks, dict):
        report(['hooks/hooks.json must have a top-level "hooks" object'])
    for event, groups in hooks.items():
        for g in groups:
            for h in g.get('hooks', []):
                for script in re.findall(r'\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+)', h.get('command', '')):
                    if not (ROOT / script).exists():
                        fails.append(f'{event} hook runs {script}, which does not exist')
    report(fails)


# ---------------- rule IDs are defined ----------------

def test_cited_rule_ids_are_defined():
    constitution = ROOT / 'rules' / 'core' / 'CLAUDE.template.md'
    defined = set(m.group(0) for m in RULE_ID.finditer(read(constitution))) if constitution.exists() \
        else set(m.group(0) for m in RULE_ID.finditer(read(ROOT / 'docs' / 'DESIGN.md')))
    fails = []
    for top in ('skills', 'agents', 'bin', 'templates'):
        if not (ROOT / top).is_dir():
            continue
        for p in walk(ROOT / top):
            if p.suffix not in ('.md', '.py', '.txt', '.json'):
                continue
            for i, line in enumerate(read(p).split('\n'), 1):
                for m in RULE_ID.finditer(line):
                    if m.group(0) not in defined:
                        fails.append(f'./{rel(p)}:{i} cites {m.group(0)}, which the constitution does not define')
    report(fails)


# ---------------- documented commands must exist ----------------
KNOWN = set(COMMANDS.values()) | set(BUILTINS)


def code_spans(line: str) -> list:
    return [s for i, s in enumerate(line.split('`')) if i % 2 == 1]


def test_every_documented_command_exists():
    fails = []
    planned = set(PLANNED.values())
    for p in (p for p in walk(ROOT) if p.suffix == '.md'):
        where_file = rel(p)
        planned_ok = where_file in PLANNED_OK_IN
        history_ok = where_file == 'CHANGELOG.md'
        for i, line in enumerate(read(p).split('\n'), 1):
            refs = []
            for sp in code_spans(line):
                m = re.match(r'^/([a-z][a-z-]*)(?:\s.*)?$', sp)
                if m:
                    refs.append(m.group(1))
            refs.extend(re.findall(r'^\s{0,4}/([a-z][a-z-]*)(?=\s|$)', line))
            for r in dict.fromkeys(refs):
                if r in KNOWN or history_ok:
                    continue
                where = f'./{where_file}:{i}'
                if r in planned:
                    if not planned_ok:
                        fails.append(f'{where} presents /{r} as available, but it is only planned')
                else:
                    fails.append(f'{where} references /{r}, which is neither a skill in this plugin nor a built-in')
    report(fails)


# ---------------- secrets (PLG-1) ----------------
FORBIDDEN = re.compile(r'''\b(api[_-]?key\s*[:=]\s*['"][\w-]{16,}|secret\s*[:=]\s*['"][\w-]{16,}|client_secret\s*[:=]\s*['"][\w-]{16,})''', re.I)


def test_no_secret_is_committed():
    fails = []
    for p in (p for p in walk(ROOT) if re.search(r'\.(md|json|py|ya?ml|txt)$', p.name)):
        for i, line in enumerate(read(p).split('\n'), 1):
            if FORBIDDEN.search(line) and 'scan-ok:' not in line:
                fails.append(f'possible secret at ./{rel(p)}:{i}')
    report(fails)
