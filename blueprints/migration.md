# Migration Blueprint

Specialized workflow for code migrations — framework upgrades, API changes, dependency swaps, refactoring patterns across multiple files. Extends the standard Stripe pattern with analyze → plan → migrate → validate steps for systematic, safe migration.

## Steps

### 1. Context Gathering [agent]

Read and internalize all relevant context before analyzing the migration:

- **Rule files**: Read every file matched by `config.agent.rule_files` (e.g., `CLAUDE.md`, `AGENTS.md`, `.cursor/rules/*.md`). These contain project conventions, constraints, and coding standards.
- **Configuration**: Read `mimoni.yaml` to understand validation commands, PR settings, and context rules.
- **Project structure**: List the top-level directory tree. Identify the language, framework, and build system.
- **Relevant source files**: Based on the migration description and `config.context.include` / `config.context.exclude` patterns, identify all files affected by the migration. Read representative samples to understand current patterns.
- **Existing tests**: Locate test files to understand coverage of the areas being migrated.
- **Migration scope**: Parse the task description to understand what is being migrated (old API → new API, old framework → new framework, etc.).

**Output**: A complete picture of the current codebase state relative to the migration target.

### 2. Planning [agent]

Create a high-level migration strategy:

- Define the overall migration approach (big-bang vs. incremental).
- Identify the order of operations and any dependencies between migration steps.
- Plan for backward compatibility if needed.
- Estimate the scope (number of files, patterns to change).

**Output**: A migration strategy document outlining approach and sequence.

### 3. Branch Creation [deterministic]

Create a new git branch for this migration run. **On failure, halt execution immediately.**

```bash
git checkout -b ${config.pr.branch_prefix}<run-id>-<slug>
```

Example:
```bash
git checkout -b mimoni/20260317-143022-migrate-to-v3-api
```

### 4. TDD Implementation [agent]

Implement the planned changes using a test-driven approach:

1. **Write or update tests first** — add test cases that define the expected behavior of the new code. Tests should fail initially (red phase).
2. **Implement the code** — write the minimal code to make the tests pass (green phase).
3. **Refactor** — clean up the implementation while keeping tests passing (refactor phase).

Follow all conventions from rule files. Match existing code style, patterns, and directory structure. Use existing libraries and utilities — do not introduce new dependencies unless the plan explicitly calls for it.

### 5. Analyze [agent]

Perform a detailed analysis of the migration scope:

- Enumerate every file that needs to change, grouped by type of change.
- Identify patterns to search-and-replace vs. patterns requiring manual rewriting.
- Document any breaking changes that require special handling.
- Identify tests that will need updating after the migration.
- Flag any areas where the migration is ambiguous or risky.

**Output**: A file-by-file migration manifest listing what changes in each file and why.

### 6. Plan [agent]

Create a detailed, file-level migration plan from the analysis:

- Order the changes to minimize broken intermediate states.
- Group related changes that must be applied together (atomic groups).
- Plan test updates alongside code changes — tests should be updated in the same step as the code they cover.
- Define validation checkpoints within the migration (e.g., after migrating the core module, validate before migrating consumers).

**Output**: An ordered, granular plan with explicit file paths and change descriptions.

### 7. Migrate [agent]

Execute the migration plan step by step:

- Apply changes in the planned order.
- For each atomic group: make the code changes, then update the corresponding tests.
- After each major group, do a quick mental check that the changes are internally consistent.
- Keep the migration focused — do not fix unrelated issues or make style improvements beyond what the migration requires.

**Output**: All migration changes applied to the codebase.

### 8. Validate [agent]

Review the migration for completeness and correctness:

- Verify that all files identified in the analysis (Step 4) have been migrated.
- Check for any remaining references to the old pattern (search for deprecated APIs, old imports, etc.).
- Review the test changes to ensure they test the new behavior, not the old.
- Confirm no files outside the migration scope were accidentally modified.

**Output**: Confidence that the migration is complete with no stragglers.

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
git commit -m "mimoni: migrate <concise migration summary>"
git push -u origin ${config.pr.branch_prefix}<run-id>-<slug>
```

### 11. PR Creation [deterministic]

Create a pull request using the GitHub CLI. **On failure, halt execution immediately.**

```bash
gh pr create \
  --title "migrate: <migration summary>" \
  --body "<migration scope, approach, files changed, and validation results>" \
  --base main \
  --draft=${config.pr.draft} \
  --label "${config.pr.labels}" \
  --reviewer "${config.pr.reviewers}"
```

The PR body should include:
- Migration scope (what was migrated from/to).
- Approach taken (big-bang vs. incremental).
- Summary of files changed and patterns replaced.
- Validation results (lint, typecheck, test — all passing).
- The blueprint used (`migration`).

**Failure handling for all deterministic steps**: If any deterministic step outside the Fix Loop exits with a non-zero code (e.g., `git push` fails, `gh pr create` fails), the blueprint halts execution immediately. The run state is set to `failed` with the failing step recorded, and the error is surfaced to the user.
