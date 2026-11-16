# Contributing to writer-plugin

How the plugin is built and what a change needs before it merges. The *why* — flow, rule IDs, hooks, Google Docs
approach and the build plan — is in [docs/DESIGN.md](docs/DESIGN.md).

## Layout

| Path | Contents | Loaded by Claude Code? |
|------|----------|------------------------|
| `.claude-plugin/` | `plugin.json` (name, version), `marketplace.json` | yes |
| `skills/` | **flat**: one directory per skill, `SKILL.md` plus `references/` | yes |
| `agents/` | write-free gate agents (`gate`, `fact-gate`) | yes |
| `hooks/hooks.json` + `bin/` | the hooks, `prose-lint.py`, `quote-check.py`, `article-status.py` and the shared `bin/lib/writer.py`, stdlib-only Python 3.9+; every hook has a pytest case in `tests/test_hooks.py` | yes |
| `rules/core/` | the editorial constitution template with rule IDs | no — copied into a workspace by the setup skill |
| `templates/` | brief, research dossier, outline, style guide templates | no — read at run time by the stage skills (ADR-005) |
| `tests/` | pytest: structure guard, library shape, skill and verdict contracts, hook behaviour, the eval suite's shape | no |
| `evals/` | `claude plugin eval` cases for the gates and the brief stage, with synthetic briefs and a fixture article (ADR-013) | no |
| `docs/` | design | no |

### Command names

A plugin skill takes its command from frontmatter `name:`, not its directory. The map is `COMMANDS` in
`tests/test_structure.py`; commands not built yet are in `PLANNED`. The test fails when a skill's `name:` drifts from
the map, when a name collides with a built-in, or when a document presents a command that does not exist. Planned
commands may appear only in `README.md`, `CHANGELOG.md` and `docs/DESIGN.md`.

### Gates are forked by construction

A gate asked to "use a fresh context" in prose is a request. `context: fork` plus a scoped, write-free `agent:` is the
mechanism, and `background: false` keeps the caller waiting for the verdict. The structure test enforces all three for
every skill in `GATE_SKILLS`.

## Testing

```bash
python -m pytest
claude plugin validate ./ --strict
```

A hook change without a test case is not accepted: a false block wastes a writer's turn, and a missed block means the
rule quietly stopped existing.

### Evals (ADR-013)

`evals/` holds `claude plugin eval` cases for the gates and the brief stage. They are built on three synthetic, public-topic
briefs (`evals/briefs/`) and one sourced article that goes through every stage (`evals/fixtures/http-caching/`). Each gate has a
PASS case and a BLOCK case that seeds one defect. Every run is a real `claude` session on your credential, so evals are local
and never run in CI. `tests/test_evals.py` checks the suite's shape for free.

```bash
# gate cases: the two source domains are the only web access G1 and G4 get
claude plugin eval ./ --tag gate --runs 1 --ablation none --scaffold --no-publish --max-cost-usd 10 \
  --allow-tools "WebFetch(domain:www.rfc-editor.org)" "WebFetch(domain:developer.mozilla.org)" \
  --output-dir /tmp/writer-evals --report /tmp/writer-evals/report.html
# brief-stage cases: the actor writes files and saves a verdict
claude plugin eval ./ --tag actor --runs 1 --ablation none --scaffold --no-publish --max-cost-usd 5 --allow-tools Write Edit
```

- `--ablation none`: a no-plugin baseline means nothing for a gate verdict and would double the cost.
- `--scaffold` runs each case's `scaffold.sh`, a shared script that only copies files from `evals/` into the empty workspace.
- The first run in a directory asks you to trust the plugin; answer it yourself.
- **A gate or checklist change reruns that gate's cases**, PASS and BLOCK, before the PR. A case below 1.0 is reported, never
  retried until it turns green.
- New material stays synthetic and public: the allowlist in `tests/test_evals.py` holds the only domains an eval file may name (PLG-1).

## Adding to this plugin

1. Client-specific knowledge never enters this repo (PLG-1). Generalise it, or put it in a workspace's `style.md`.
2. A new skill: add it to `COMMANDS` (and to `GATE_SKILLS` if it judges an artifact), remove it from `PLANNED`.
3. Prefer a script or a hook over a prompt rule. The orchestrator follows this: it decides from `bin/article-status.py`, not from
   its own reading of the verdicts (ADR-011). A skill that dispatches other skills writes nothing itself.
4. Both checks above before opening a PR. `CHANGELOG.md` leads with what was deleted.
