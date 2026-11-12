## <type>: <title>

### What changed
-

### Why
<one or two lines; link the DESIGN.md phase or decision if there is one>

### Verification
<!-- Required. Real commands and real output. -->
- tests: `.venv/bin/python -m pytest`
- plugin validate: `claude plugin validate ./`
- executed: <the skill, hook or script actually run on a sample, and what it did>

### Not verified
<!-- Never delete this section. Write "nothing" only if that is true. -->
-

### Checklist
- [ ] A hook change has a test case; a new skill is in `COMMANDS` and out of `PLANNED`
- [ ] No client-specific content (PLG-1)
- [ ] Gate skills keep `context: fork`, `background: false` and a write-free agent
- [ ] `CHANGELOG.md` updated, leading with what was deleted
- [ ] Opened as a draft; a human marks it ready
