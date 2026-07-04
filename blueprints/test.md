# Test Blueprint

Specialized workflow for writing tests — improving coverage, adding missing test cases, creating test suites for untested code. Extends the standard Stripe pattern with analyze-coverage → write-tests → verify steps.

## Steps

### 1. Context Gathering [agent]

Read and internalize all relevant context before analyzing test coverage:

- **Rule files**: Read every file matched by `config.agent.rule_files` (e.g., `CLAUDE.md`, `AGENTS.md`, `.cursor/rules/*.md`). These contain project conventions, constraints, and coding standards.
- **Configuration**: Read `mimoni.yaml` to understand validation commands, PR settings, and context rules.
- **Project structure**: List the top-level directory tree. Identify the language, framework, and build system.
- **Relevant source files**: Based on the task description and `config.context.include` / `config.context.exclude` patterns, identify the source files that need test coverage.
- **Existing tests**: Read the test directory structure, understand the testing framework (Jest, pytest, Go test, etc.), test file naming conventions, helper utilities, and fixture patterns. Read representative test files to understand the style.
- **Test configuration**: Identify test config files (jest.config.js, pytest.ini, etc.) and understand any special setup, mocking patterns, or test environment requirements.

**Output**: A thorough understanding of the testing patterns, framework, and current coverage state.

### 2. Planning [agent]

Create a test writing plan:

- Identify which source files or modules need test coverage.
- For each, determine what behaviors to test (happy paths, edge cases, error conditions).
- Plan test file structure — follow existing conventions (co-located vs. separate test dir, naming patterns).
- Identify any test utilities or fixtures that need to be created.
- Prioritize: critical paths first, edge cases second, exhaustive coverage third.

**Output**: A numbered list of test files to create/update with the behaviors each will cover.

### 3. Branch Creation [deterministic]

Create a new git branch for this test run. **On failure, halt execution immediately.**

```bash
git checkout -b ${config.pr.branch_prefix}<run-id>-<slug>
```

Example:
```bash
git checkout -b mimoni/20260317-143022-add-auth-tests
```

### 4. TDD Implementation [agent]

Implement the planned changes using a test-driven approach:

1. **Write or update tests first** — add test cases that define the expected behavior of the new code. Tests should fail initially (red phase).
2. **Implement the code** — write the minimal code to make the tests pass (green phase).
3. **Refactor** — clean up the implementation while keeping tests passing (refactor phase).

Follow all conventions from rule files. Match existing code style, patterns, and directory structure. Use existing libraries and utilities — do not introduce new dependencies unless the plan explicitly calls for it.

### 5. Analyze Coverage [agent]

Perform a detailed analysis of the current test coverage gaps:

- If a coverage tool is available, run it and analyze the report.
- Otherwise, manually compare source files against test files to identify untested code.
- Categorize gaps: completely untested modules, partially tested modules (missing edge cases), and well-tested modules.
- For each gap, note the specific functions, methods, or code paths that lack coverage.
- Identify any code that is difficult to test (complex dependencies, side effects) and plan how to make it testable.

**Output**: A coverage gap report listing specific untested functions and code paths.

### 6. Write Tests [agent]

Write the test cases following the plan and coverage analysis:

- Create or update test files following existing naming conventions and directory structure.
- Write clear, descriptive test names that document the expected behavior.
- Follow the Arrange-Act-Assert (or Given-When-Then) pattern.
- Use existing test utilities, fixtures, and mocking patterns — do not invent new patterns when existing ones work.
- Group related tests logically (by function, by feature, by scenario).
- Include both positive tests (expected behavior) and negative tests (error handling, edge cases).
- Keep tests focused — each test should verify one behavior.

**Output**: New or updated test files with comprehensive test cases.

### 7. Verify [agent]

Review the written tests for quality and completeness:

- Verify each test actually tests what it claims to (not just running code without meaningful assertions).
- Check that assertions are specific — avoid overly broad matchers that would pass even with wrong behavior.
- Confirm test isolation — tests should not depend on execution order or shared mutable state.
- Verify that the tests cover the gaps identified in the coverage analysis (Step 4).
- Ensure no source code was accidentally modified (this is a test-only change).

**Output**: Confidence that the tests are correct, meaningful, and cover the identified gaps.

### 8. Local Validation [deterministic]

Run all validation commands from the project configuration. **Each command must pass (exit code 0).**

```bash
# Lint check
${config.validation.lint}

# Type check
${config.validation.typecheck}

# Test suite
${config.validation.test}
```

If **any** command fails (non-zero exit code), proceed to the Fix Loop. If all commands pass, skip the Fix Loop and proceed to Step 9.

**Fix Loop** (conditional, max 2 iterations):

**Trigger condition**: Step 8 (Local Validation) failed — one or more validation commands returned a non-zero exit code.

**Max iterations**: `config.pr.max_retries` (default: 2)

Repeat the following sub-steps up to max iterations:

#### 9.1. Diagnose & Fix [agent]

Analyze the validation output to identify the root cause of each failure. Apply targeted fixes — modify test code, fix lint issues in tests, resolve type errors in tests. Do not modify source code unless a test reveals an actual bug (in which case, note it in the PR description). Fix only what the validation output identifies.

#### 9.2. Re-validate [deterministic]

Re-run all validation commands:

```bash
${config.validation.lint}
${config.validation.typecheck}
${config.validation.test}
```

If all pass → exit the loop and proceed to Step 9.
If any fail → continue to next iteration (or exhaust retries).

**Post-exhaustion behavior**: If validation still fails after exhausting all retry iterations:
- Set the run state to `failed` in the state file.
- Record the failing validation output in the state file.
- Do **not** push broken code to remote.
- Do **not** create a PR.
- Leave the local branch intact for manual inspection.
- Halt execution.

### 9. Commit & Push [deterministic]

Stage, commit, and push all changes. **On failure, halt execution immediately.**

```bash
git add -A
git commit -m "mimoni: add tests for <concise test scope summary>"
git push -u origin ${config.pr.branch_prefix}<run-id>-<slug>
```

### 10. PR Creation [deterministic]

Create a pull request using the GitHub CLI. **On failure, halt execution immediately.**

```bash
gh pr create \
  --title "test: <test scope summary>" \
  --body "<coverage gaps addressed, tests added, and validation results>" \
  --base main \
  --draft=${config.pr.draft} \
  --label "${config.pr.labels}" \
  --reviewer "${config.pr.reviewers}"
```

The PR body should include:
- Coverage gaps that were addressed.
- Summary of test files created/updated and behaviors tested.
- Validation results (lint, typecheck, test — all passing).
- The blueprint used (`test`).

**Failure handling for all deterministic steps**: If any deterministic step outside the Fix Loop exits with a non-zero code (e.g., `git push` fails, `gh pr create` fails), the blueprint halts execution immediately. The run state is set to `failed` with the failing step recorded, and the error is surfaced to the user.
