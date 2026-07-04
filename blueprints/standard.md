# Standard Blueprint

General-purpose workflow for code changes — feature additions, improvements, refactoring. This is the default blueprint used when no specific workflow is required.

## Steps

### 1. Context Gathering [agent]

Read and internalize all relevant context before planning:

- **Rule files**: Read every file matched by `config.agent.rule_files` (e.g., `CLAUDE.md`, `AGENTS.md`, `.cursor/rules/*.md`). These contain project conventions, constraints, and coding standards.
- **Configuration**: Read `mimoni.yaml` to understand validation commands, PR settings, and context rules.
- **Project structure**: List the top-level directory tree. Identify the language, framework, and build system (e.g., `package.json` → Node.js, `Cargo.toml` → Rust, `setup.py` → Python).
- **Relevant source files**: Based on the task description and `config.context.include` / `config.context.exclude` patterns, identify the files most likely to be read or modified. Read key files to understand existing patterns, imports, and conventions.
- **Existing tests**: Locate the test directory and understand the testing framework and patterns used.

**Output**: A mental model of the codebase sufficient to plan and implement the task.

### 2. Planning [agent]

Create a concrete implementation plan:

- Break the task into discrete, ordered steps.
- For each step, identify which files will be created or modified.
- Identify any new dependencies that need to be added.
- Plan the test strategy: what tests to write, what existing tests to update.
- Consider edge cases and error handling.
- Ensure the plan respects conventions discovered in context gathering.

**Output**: A numbered list of implementation steps with file-level detail.

### 3. Branch Creation [deterministic]

Create a new git branch for this run. **On failure, halt execution immediately.**

```bash
git checkout -b ${config.pr.branch_prefix}<run-id>-<slug>
```

Where `<run-id>` is the unique run identifier and `<slug>` is a short kebab-case summary derived from the task description (e.g., `add-user-auth`, `fix-timeout-bug`).

Example:
```bash
git checkout -b mimoni/20260317-143022-add-user-auth
```

### 4. TDD Implementation [agent]

Implement the planned changes using a test-driven approach:

1. **Write or update tests first** — add test cases that define the expected behavior of the new code. Tests should fail initially (red phase).
2. **Implement the code** — write the minimal code to make the tests pass (green phase).
3. **Refactor** — clean up the implementation while keeping tests passing (refactor phase).

Follow all conventions from rule files. Match existing code style, patterns, and directory structure. Use existing libraries and utilities — do not introduce new dependencies unless the plan explicitly calls for it.

### 5. Local Validation [deterministic]

Run all validation commands from the project configuration. **Each command must pass (exit code 0).**

```bash
# Lint check
${config.validation.lint}

# Type check
${config.validation.typecheck}

# Test suite
${config.validation.test}
```

If **any** command fails (non-zero exit code), proceed to the Fix Loop. If all commands pass, skip the Fix Loop and proceed to Step 6.

**Fix Loop** (conditional, max 2 iterations):

**Trigger condition**: Step 5 (Local Validation) failed — one or more validation commands returned a non-zero exit code.

**Max iterations**: `config.pr.max_retries` (default: 2)

Repeat the following sub-steps up to max iterations:

#### 6.1. Diagnose & Fix [agent]

Analyze the validation output to identify the root cause of each failure. Apply targeted fixes — modify code, update tests, fix lint issues, resolve type errors. Do not make sweeping changes; fix only what the validation output identifies.

#### 6.2. Re-validate [deterministic]

Re-run all validation commands:

```bash
${config.validation.lint}
${config.validation.typecheck}
${config.validation.test}
```

If all pass → exit the loop and proceed to Step 6.
If any fail → continue to next iteration (or exhaust retries).

**Post-exhaustion behavior**: If validation still fails after exhausting all retry iterations:
- Set the run state to `failed` in the state file.
- Record the failing validation output in the state file.
- Do **not** push broken code to remote.
- Do **not** create a PR.
- Leave the local branch intact for manual inspection.
- Halt execution.

### 6. Commit & Push [deterministic]

Stage, commit, and push all changes. **On failure, halt execution immediately.**

```bash
git add -A
git commit -m "mimoni: <concise summary of changes>"
git push -u origin ${config.pr.branch_prefix}<run-id>-<slug>
```

The commit message should start with `mimoni:` prefix followed by a concise description of what was done.

### 7. PR Creation [deterministic]

Create a pull request using the GitHub CLI. **On failure, halt execution immediately.**

```bash
gh pr create \
  --title "<task summary>" \
  --body "<description of changes, approach taken, and validation results>" \
  --base main \
  --draft=${config.pr.draft} \
  --label "${config.pr.labels}" \
  --reviewer "${config.pr.reviewers}"
```

The PR body should include:
- What was changed and why (from the task description).
- A summary of the approach taken.
- Validation results (lint, typecheck, test — all passing).
- The blueprint used (`standard`).

**Failure handling for all deterministic steps**: If any deterministic step outside the Fix Loop exits with a non-zero code (e.g., `git push` fails, `gh pr create` fails), the blueprint halts execution immediately. The run state is set to `failed` with the failing step recorded, and the error is surfaced to the user.
