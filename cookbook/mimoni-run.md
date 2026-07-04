# Run a Mimoni Orchestration

## Context

Execute an unattended, one-shot coding agent run: task description in → pull request out, with no human interaction in between. This is the core orchestration command that reads the project's `mimoni.yaml` configuration, selects a blueprint workflow, executes each blueprint step sequentially, handles validation failures with a fix/retry loop, and produces a pull request on success.

The entire flow runs autonomously. Deterministic steps (git, lint, test) are executed as shell commands with exit code checks. Agent steps (planning, implementation, fixing) are handled by the LLM with accumulated context. State is tracked in `.mimoni/` so parallel runs can coexist and progress can be inspected.

**Parallel run isolation**: Each run uses a **git worktree** (`/tmp/mimoni-<run-id>`) instead of checking out a branch in the original working tree. This ensures concurrent runs operate in complete isolation — one run's changes never appear in another's commits, and the original working tree is never modified. State files are always written to the **original project's** `.mimoni/` directory so that `mimoni status` can find them regardless of which worktree created them.

## Input

The user provides a **task description** — a natural-language string describing what to implement, fix, migrate, or test.

Examples:
- `"Add user authentication with JWT tokens"`
- `"Fix the timeout bug in the API client"`
- `"Migrate database from v1 to v2 schema"`
- `"Add unit tests for the payment module"`

## Steps

### 1. Read and Validate Configuration

Read the project's `mimoni.yaml` configuration file. Validate it before proceeding.

**Check if config exists:**

```bash
test -f mimoni.yaml
```

- **If `mimoni.yaml` does not exist** → stop immediately and tell the user:
  > `mimoni.yaml not found. Run /library mimoni init to initialize mimoni configuration for this project.`
- **If `mimoni.yaml` exists** → read and parse it.

**Parse the YAML:**

```bash
python3 -c "import yaml; config = yaml.safe_load(open('mimoni.yaml')); print('Config loaded successfully')"
```

- **If YAML is malformed** (parse error) → stop immediately and show the parse error:
  > `Failed to parse mimoni.yaml: <parse error message>. Fix the YAML syntax and try again.`

**Validate required fields:**

Check that these required fields are present and non-empty:
- `blueprint` — which workflow to use
- `validation.lint` — linter command
- `validation.typecheck` — type-checker command
- `validation.test` — test-runner command
- `pr.branch_prefix` — branch naming prefix
- `pr.max_retries` — fix loop iteration limit

- **If any required field is missing** → stop immediately and report which field(s) are missing:
  > `mimoni.yaml is missing required field(s): <field1>, <field2>. See mimoni.example.yaml for the expected schema.`

**Store the parsed config** in memory for use throughout the remaining steps.

### 2. Select Blueprint

Determine which blueprint workflow to execute for this run.

- Read the `blueprint` field from `mimoni.yaml` (e.g., `standard`, `bugfix`, `migration`, `test`).
- Optionally, if the config value is `auto`, select a blueprint based on task keywords:
  - Task contains "fix", "bug", "broken", "error", "crash" → `bugfix`
  - Task contains "migrate", "migration", "upgrade", "convert" → `migration`
  - Task contains "test", "tests", "coverage", "spec" → `test`
  - Otherwise → `standard`

**Locate the blueprint file:**

Blueprints are part of The Library skill, not the target project. Resolve the path using the `LIBRARY_SKILL_DIR` variable from SKILL.md (e.g., `~/.claude/skills/library/`):

```bash
ls <LIBRARY_SKILL_DIR>/blueprints/${blueprint}.md
```

- **If the blueprint file does not exist** → stop and report:
  > `Blueprint '${blueprint}' not found. Available blueprints: $(ls <LIBRARY_SKILL_DIR>/blueprints/*.md | xargs -I{} basename {} .md | tr '\n' ', ')`

**Read the blueprint file** from `<LIBRARY_SKILL_DIR>/blueprints/${blueprint}.md` to understand the step sequence, node types, and instructions for this run.

### 3. Check Working Tree and Record Project Root

Record the original project directory — this is needed later for writing state files (which must go to the original project, not the worktree):

```bash
PROJECT_ROOT=$(pwd)
```

Since mimoni uses **git worktrees** for branch isolation, the original working tree is never modified during a run. This means:
- **No stashing is needed** — uncommitted changes in the original working tree are left untouched.
- **No risk of cross-contamination** — each run gets its own isolated copy of the repo at `/tmp/mimoni-<run-id>`.
- **Parallel safety** — multiple concurrent runs can start from the same project without interfering with each other.

> **Note**: With worktrees, uncommitted changes in the original tree do not affect the run. The worktree is created from the default branch HEAD, so the run always starts from a clean, up-to-date state.

Ensure the default branch is up to date before creating the worktree:

```bash
default_branch=$(git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@')
git fetch origin "$default_branch"
```

### 4. Generate Run ID and Create Worktree

Generate a unique run identifier and create an isolated git worktree for this run.

**Generate the run ID:**

```bash
# Generate timestamp
timestamp=$(date +%Y%m%d-%H%M%S)

# Generate slug from task description (lowercase, kebab-case, max 5 words)
slug=$(echo "<task description>" | tr '[:upper:]' '[:lower:]' | tr -cs '[:alnum:]' '-' | sed 's/^-//;s/-$//' | cut -d'-' -f1-5)

# Generate random 4-char hex suffix for collision resistance
random4=$(head -c 4 /dev/urandom | xxd -p | head -c 4)

# Assemble run ID
run_id="${timestamp}-${slug}-${random4}"
```

**Create the worktree with a new branch:**

Instead of checking out a branch in the shared working tree, create a **git worktree** — a separate working directory with its own branch. This ensures complete isolation between concurrent runs.

```bash
git worktree add "/tmp/mimoni-${run_id}" -b "${config.pr.branch_prefix}${run_id}" "origin/${default_branch}"
```

This creates:
- A new working directory at `/tmp/mimoni-<run-id>` with a full copy of the repo
- A new branch `mimoni/<run-id>` based on the latest default branch

Example:
```bash
git worktree add /tmp/mimoni-20260317-143022-add-user-auth-a7f3 -b mimoni/20260317-143022-add-user-auth-a7f3 origin/main
```

If worktree creation fails (non-zero exit code), halt immediately and report the error.

**Switch to the worktree directory** — all subsequent steps (blueprint execution, validation, commits) happen inside the worktree:

```bash
cd "/tmp/mimoni-${run_id}"
```

### 5. Initialize State File

Create a state file in the **original project's** `.mimoni/` directory (not the worktree) to track this run's progress. This enables parallel run tracking and status inspection — `mimoni status` reads from `$PROJECT_ROOT/.mimoni/`, so state files must live there.

```bash
mkdir -p "${PROJECT_ROOT}/.mimoni"
```

Create the state file at `${PROJECT_ROOT}/.mimoni/${run_id}.yaml` with the initial schema:

```yaml
run_id: "<run_id>"
task: "<task description>"
blueprint: "<blueprint name>"
branch: "<branch_prefix><run_id>"
status: running
started_at: "<ISO 8601 timestamp>"
completed_at: null
current_step: "<first step name>"
steps:
  - name: "<step 1 name>"
    type: <agent|deterministic>
    status: pending
  - name: "<step 2 name>"
    type: <agent|deterministic>
    status: pending
  # ... one entry per blueprint step
pr_url: null
```

Populate the `steps` array by reading the blueprint file's step headings and node type markers (`[agent]` or `[deterministic]`). The Fix Loop is listed as a single step entry with type `agent`.

### 6. Execute Blueprint Steps

All blueprint steps execute inside the **worktree directory** (`/tmp/mimoni-<run-id>`), not the original project directory. This is where all code changes, validation commands, and git operations happen.

Walk through each step in the blueprint sequentially. For each step:

**Update the state file** (at `${PROJECT_ROOT}/.mimoni/${run_id}.yaml`) — set the step's status to `running` and update `current_step`.

**Check the node type** from the blueprint step heading:

#### For `[deterministic]` steps:

Run the shell command(s) specified in the blueprint's code blocks. Check the exit code of each command.

```bash
# Example: run a deterministic step's command
<command from blueprint>
echo "Exit code: $?"
```

- **Exit code 0** → mark the step as `completed` in the state file. Proceed to the next step.
- **Non-zero exit code** → this is a failure. If the step is **Local Validation**, proceed to the Fix Loop (step 7). For any other deterministic step, mark the step as `failed` with the error message, set run status to `failed`, and **halt execution immediately**. Do not push broken code.

#### For `[agent]` steps:

Execute the agent task described in the blueprint step. Provide the agent with:
- The original task description.
- All context gathered so far (rule files, project structure, relevant source files).
- The blueprint step's specific instructions and expected output.
- The output/results from all previous steps.

The agent performs the work (planning, coding, diagnosing, fixing) and produces the output described in the blueprint step.

Mark the step as `completed` in the state file and proceed.

**Variable substitution**: When blueprint steps reference config values like `${config.validation.lint}`, substitute them with the actual values from the parsed `mimoni.yaml`. For example:
- `${config.validation.lint}` → `npm run lint` (from config)
- `${config.validation.typecheck}` → `npm run typecheck` (from config)
- `${config.validation.test}` → `npm test` (from config)
- `${config.pr.branch_prefix}` → `mimoni/` (from config)
- `${config.pr.draft}` → `true` (from config)
- `${config.pr.labels}` → `mimoni` (from config)
- `${config.pr.reviewers}` → reviewer list (from config)

### 7. Handle Fix/Retry Loop

The fix loop is triggered when the **Local Validation** step fails (one or more validation commands return non-zero exit codes). This implements the Stripe-pattern feedback loop: validate → diagnose/fix → re-validate.

**Max iterations:** `config.pr.max_retries` (default: 2)

**For each iteration** (up to max retries):

**7a. Diagnose & Fix [agent]:**
- Read the validation output to identify what failed (lint errors, type errors, test failures).
- Analyze the root cause of each failure.
- Apply targeted fixes — modify code, update tests, fix lint issues, resolve type errors.
- Do not make sweeping changes; fix only what the validation output identifies.

**7b. Re-validate [deterministic]:**
- Re-run all validation commands:

```bash
${config.validation.lint}
${config.validation.typecheck}
${config.validation.test}
```

- **If all pass (exit code 0)** → exit the loop. Mark the Fix Loop step as `completed` in the state file. Proceed to the next blueprint step (Commit & Push).
- **If any fail** → continue to the next iteration.

**After exhausting all retries** (validation still failing):
- Set the Fix Loop step status to `failed` with the error message from the last validation output (in `${PROJECT_ROOT}/.mimoni/${run_id}.yaml`).
- Set the overall run status to `failed` in the state file.
- Set `completed_at` to the current ISO 8601 timestamp.
- Do **not** push broken code to the remote.
- Do **not** create a PR.
- Clean up the worktree (since the code is broken and won't be pushed):

```bash
cd "${PROJECT_ROOT}"
git worktree remove "/tmp/mimoni-${run_id}" --force
```

- Report to the user:
  > `Fix loop exhausted after ${max_retries} retries. Validation still failing. The branch '${branch}' is preserved locally for manual inspection. Worktree cleaned up. Run state: ${PROJECT_ROOT}/.mimoni/${run_id}.yaml`
- **Halt execution.**

### 8. Commit, Push, and Clean Up Worktree

Stage, commit, and push all changes to the remote. This step executes only when all validation has passed. All commands run inside the worktree directory.

```bash
git add -A
git commit -m "mimoni: <concise summary of changes>"
git push -u origin "${config.pr.branch_prefix}${run_id}"
```

The commit message starts with the `mimoni:` prefix followed by a concise description of what was done, derived from the task and the implementation.

**On failure** (non-zero exit code from any command): mark the step as `failed`, set run status to `failed` in the state file (`${PROJECT_ROOT}/.mimoni/${run_id}.yaml`), clean up the worktree, and halt execution. Do not proceed to PR creation.

**After successful push**, clean up the worktree — it is no longer needed since all changes are on the remote:

```bash
cd "${PROJECT_ROOT}"
git worktree remove "/tmp/mimoni-${run_id}"
```

Update the state file: mark the Commit & Push step as `completed`.

### 9. Create Pull Request

Create a pull request using the GitHub CLI. This runs from the **original project directory** (`${PROJECT_ROOT}`) after the worktree has been cleaned up — the branch is already pushed to the remote.

```bash
cd "${PROJECT_ROOT}"
gh pr create \
  --head "${config.pr.branch_prefix}${run_id}" \
  --title "<task summary>" \
  --body "<description of changes, approach taken, and validation results>" \
  --base "${default_branch}" \
  --draft \
  --label "mimoni"
```

Adapt the flags based on the project's `mimoni.yaml` configuration:
- `--draft` → only if `config.pr.draft` is `true`
- `--label` → use labels from `config.pr.labels`
- `--reviewer` → use reviewers from `config.pr.reviewers` (omit flag if empty)

The PR body should include:
- **Task**: The original task description.
- **Blueprint**: Which blueprint was used (e.g., `standard`).
- **Changes**: Summary of what was implemented.
- **Validation**: Confirmation that lint, typecheck, and test all pass.

**On failure** (non-zero exit code): mark the step as `failed`, set run status to `failed` in the state file (`${PROJECT_ROOT}/.mimoni/${run_id}.yaml`), and halt execution.

**On success**: capture the PR URL from the `gh pr create` output.

Update the state file (`${PROJECT_ROOT}/.mimoni/${run_id}.yaml`):
- Mark the PR Creation step as `completed`.
- Set `pr_url` to the URL returned by `gh pr create`.
- Set overall run `status` to `completed`.
- Set `completed_at` to the current ISO 8601 timestamp.

### 10. Report Results

Report the final outcome to the user.

**On success (all steps completed):**

> ✅ **Mimoni run complete.**
> - **Task**: <task description>
> - **Blueprint**: <blueprint name>
> - **Branch**: <branch name>
> - **PR**: <pr_url>
> - **Validation**: All checks passed (lint ✓, typecheck ✓, test ✓)
> - **Worktree**: cleaned up
> - **State file**: ${PROJECT_ROOT}/.mimoni/<run_id>.yaml

**On failure (run halted at a step):**

> ❌ **Mimoni run failed.**
> - **Task**: <task description>
> - **Blueprint**: <blueprint name>
> - **Failed at**: <step name>
> - **Error**: <error details>
> - **Branch**: <branch name> (preserved locally)
> - **Worktree**: cleaned up
> - **State file**: ${PROJECT_ROOT}/.mimoni/<run_id>.yaml
