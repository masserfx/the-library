# Bugfix Blueprint

Specialized workflow for bug fixes. Extends the standard Stripe pattern with reproduce → diagnose → fix → verify steps to ensure the bug is understood before fixing and confirmed resolved after.

## Steps

### 1. Context Gathering [agent]

Read and internalize all relevant context before diagnosing the bug:

- **Rule files**: Read every file matched by `config.agent.rule_files` (e.g., `CLAUDE.md`, `AGENTS.md`, `.cursor/rules/*.md`). These contain project conventions, constraints, and coding standards.
- **Configuration**: Read `mimoni.yaml` to understand validation commands, PR settings, and context rules.
- **Project structure**: List the top-level directory tree. Identify the language, framework, and build system.
- **Relevant source files**: Based on the bug description and `config.context.include` / `config.context.exclude` patterns, identify the files most likely related to the bug. Read the suspected area of code.
- **Existing tests**: Locate tests related to the buggy area to understand what is and isn't covered.
- **Bug description**: Parse the task description to extract: what the expected behavior is, what the actual behavior is, and any reproduction steps provided.

**Output**: A mental model of the buggy area and the conditions under which the bug manifests.

### 2. Planning [agent]

Create a concrete plan for reproducing, diagnosing, and fixing the bug:

- Outline how to reproduce the bug (test case or manual steps).
- Identify the likely root cause area based on context.
- Plan the fix approach.
- Plan a regression test to prevent recurrence.

**Output**: A numbered list of steps covering reproduction, diagnosis, fix, and verification.

### 3. Branch Creation [deterministic]

Create a new git branch for this bugfix run. **On failure, halt execution immediately.**

```bash
git checkout -b ${config.pr.branch_prefix}<run-id>-<slug>
```

Example:
```bash
git checkout -b mimoni/20260317-143022-fix-timeout-bug
```

### 4. TDD Implementation [agent]

Implement the planned changes using a test-driven approach:

1. **Write or update tests first** — add test cases that define the expected behavior of the new code. Tests should fail initially (red phase).
2. **Implement the code** — write the minimal code to make the tests pass (green phase).
3. **Refactor** — clean up the implementation while keeping tests passing (refactor phase).

Follow all conventions from rule files. Match existing code style, patterns, and directory structure. Use existing libraries and utilities — do not introduce new dependencies unless the plan explicitly calls for it.

### 5. Reproduce [agent]

Write a failing test case or script that demonstrates the bug:

- Create a test that captures the expected behavior described in the bug report.
- Run it to confirm it fails — this proves the bug exists and provides a regression gate.
- If the bug cannot be reproduced with a test, document the manual reproduction steps and proceed with diagnosis.

**Output**: A failing test case or documented reproduction steps.

### 6. Diagnose [agent]

Identify the root cause of the bug:

- Trace the execution path from the reproduction case.
- Examine the code in the suspected area.
- Identify the exact line(s) or logic error causing the bug.
- Understand why the bug was introduced (missing edge case, incorrect assumption, etc.).

**Output**: Root cause identified with specific file and line references.

### 7. Fix [agent]

Implement the fix:

- Apply the minimal change needed to resolve the root cause.
- Do not refactor unrelated code — keep the fix focused.
- Update or add tests to cover the fix (the reproduction test from Step 4 should now pass).
- Ensure the fix handles edge cases identified during diagnosis.

**Output**: Code changes that resolve the bug with passing regression test.

### 8. Verify [agent]

Verify the fix is complete:

- Confirm the reproduction test from Step 4 now passes.
- Review the fix for unintended side effects — check that no existing functionality is broken.
- Ensure the fix is consistent with project conventions from rule files.

**Output**: Confidence that the fix resolves the bug without introducing regressions.

### 9. Local Validation [deterministic]

Run all validation commands from the project configuration. **Each command must pass (exit code 0).**

```bash
# Lint check
${config.validation.lint}

# Type check
${config.validation.typecheck}

# Test suite
${config.validation.test}
```

If **any** command fails (non-zero exit code), proceed to the Fix Loop. If all commands pass, skip the Fix Loop and proceed to Step 10.

**Fix Loop** (conditional, max 2 iterations):

**Trigger condition**: Step 9 (Local Validation) failed — one or more validation commands returned a non-zero exit code.

**Max iterations**: `config.pr.max_retries` (default: 2)

Repeat the following sub-steps up to max iterations:

#### 10.1. Diagnose & Fix [agent]

Analyze the validation output to identify the root cause of each failure. Apply targeted fixes — modify code, update tests, fix lint issues, resolve type errors. Do not make sweeping changes; fix only what the validation output identifies.

#### 10.2. Re-validate [deterministic]

Re-run all validation commands:

```bash
${config.validation.lint}
${config.validation.typecheck}
${config.validation.test}
```

If all pass → exit the loop and proceed to Step 10.
If any fail → continue to next iteration (or exhaust retries).

**Post-exhaustion behavior**: If validation still fails after exhausting all retry iterations:
- Set the run state to `failed` in the state file.
- Record the failing validation output in the state file.
- Do **not** push broken code to remote.
- Do **not** create a PR.
- Leave the local branch intact for manual inspection.
- Halt execution.

### 10. Commit & Push [deterministic]

Stage, commit, and push all changes. **On failure, halt execution immediately.**

```bash
git add -A
git commit -m "mimoni: fix <concise bug summary>"
git push -u origin ${config.pr.branch_prefix}<run-id>-<slug>
```

### 11. PR Creation [deterministic]

Create a pull request using the GitHub CLI. **On failure, halt execution immediately.**

```bash
gh pr create \
  --title "fix: <bug summary>" \
  --body "<bug description, root cause, fix approach, and validation results>" \
  --base main \
  --draft=${config.pr.draft} \
  --label "${config.pr.labels}" \
  --reviewer "${config.pr.reviewers}"
```

The PR body should include:
- Bug description (what was broken).
- Root cause analysis.
- Fix approach and changes made.
- Validation results (lint, typecheck, test — all passing).
- The blueprint used (`bugfix`).

**Failure handling for all deterministic steps**: If any deterministic step outside the Fix Loop exits with a non-zero code (e.g., `git push` fails, `gh pr create` fails), the blueprint halts execution immediately. The run state is set to `failed` with the failing step recorded, and the error is surfaced to the user.
