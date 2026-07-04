# Mimoni State Management Conventions

## Context

Mimoni supports parallel, unattended runs — multiple agents can work simultaneously on different tasks in the same project. Each run needs isolated state tracking so that runs don't collide and their progress can be inspected at any time.

This document defines the conventions for the `.mimoni/` state directory, per-run state file naming, and the state file schema. It is the canonical reference consumed by the `mimoni-run` and `mimoni-status` cookbooks.

## Directory Structure

### `.mimoni/` Directory

Mimoni creates a `.mimoni/` directory at the **target project root** (the project where the agent is executing tasks — not The Library repo itself).

```
my-project/
├── .mimoni/
│   ├── 20260317-143022-add-user-auth-a7f3.yaml
│   ├── 20260317-143540-fix-login-bug-b2e1.yaml
│   └── 20260317-150100-migrate-to-v2-c9d4.yaml
├── src/
├── package.json
└── mimoni.yaml
```

### `.gitignore` Guidance

The `.mimoni/` directory contains local run state and should **not** be committed to the target project's repository. When `mimoni init` sets up a project, it should add `.mimoni/` to the project's `.gitignore` if not already present:

```gitignore
# Mimoni run state (local, not committed)
.mimoni/
```

> **Note**: `.mimoni/` is gitignored in **target projects** where mimoni runs tasks. It is not relevant to The Library repository itself.

## State File Naming

Each mimoni run creates a **single YAML state file** in `.mimoni/` with a collision-resistant name that combines a timestamp, slug, and random suffix:

```
YYYYMMDD-HHMMSS-<slug>-<random4>.yaml
```

| Component    | Description                                                                 |
| ------------ | --------------------------------------------------------------------------- |
| `YYYYMMDD`   | Date of run start (e.g., `20260317`)                                        |
| `HHMMSS`     | Time of run start in 24-hour format (e.g., `143022`)                        |
| `<slug>`     | Short kebab-case summary derived from the task description (e.g., `add-user-auth`) |
| `<random4>`  | 4-character random hex string for collision resistance (e.g., `a7f3`)       |

The random suffix can be generated with:

```bash
random4=$(head -c 4 /dev/urandom | xxd -p | head -c 4)
```

**Examples:**
- `20260317-143022-add-user-auth-a7f3.yaml`
- `20260317-143540-fix-login-bug-b2e1.yaml`
- `20260317-150100-migrate-to-v2-c9d4.yaml`

The timestamp prefix provides chronological ordering, the slug provides human-readable identification without opening the file, and the random suffix ensures that even identical tasks starting in the same second produce distinct filenames.

### Slug Generation Rules

- Lowercase, kebab-case (words separated by hyphens)
- Maximum 5 words
- Derived from the task description by extracting key action and subject words
- Strip articles, prepositions, and filler words

## State File Schema

Each state file is a YAML document tracking the full lifecycle of a single mimoni run.

```yaml
# Unique identifier for this run — matches the state file name (without .yaml extension)
run_id: "20260317-143022-add-user-auth-a7f3"

# The original task description provided by the user
task: "Add user authentication with JWT tokens"

# Which blueprint workflow is being executed
blueprint: standard

# Git branch created for this run
branch: "mimoni/20260317-143022-add-user-auth-a7f3"

# Overall run status
# Values: pending | running | completed | failed
status: running

# ISO 8601 timestamps
started_at: "2026-03-17T14:30:22Z"
completed_at: null                      # null until run finishes (completed or failed)

# Name of the blueprint step currently executing
current_step: "Local Validation"

# Ordered array of blueprint steps with per-step tracking
steps:
  - name: "Context Gathering"
    type: agent                         # node type: agent | deterministic
    status: completed                   # step status: pending | running | completed | failed
  - name: "Planning"
    type: agent
    status: completed
  - name: "Branch Creation"
    type: deterministic
    status: completed
  - name: "TDD Implementation"
    type: agent
    status: completed
  - name: "Local Validation"
    type: deterministic
    status: running
  - name: "Fix Loop"
    type: agent                         # mixed cycle, tracked as agent
    status: pending
  - name: "Commit & Push"
    type: deterministic
    status: pending
  - name: "PR Creation"
    type: deterministic
    status: pending
    error: null                         # error message if step failed (null otherwise)

# URL of the created pull request (null until PR is created)
pr_url: null
```

### Field Reference

| Field           | Type     | Required | Description                                                                 |
| --------------- | -------- | -------- | --------------------------------------------------------------------------- |
| `run_id`        | string   | yes      | Unique run identifier (`YYYYMMDD-HHMMSS-<slug>-<random4>`) — matches the state file name without `.yaml` |
| `task`          | string   | yes      | Original task description from the user                                     |
| `blueprint`     | string   | yes      | Blueprint name used for this run (`standard`, `bugfix`, `migration`, `test`) |
| `branch`        | string   | yes      | Git branch name created for this run                                        |
| `status`        | string   | yes      | Overall run status: `pending`, `running`, `completed`, or `failed`          |
| `started_at`    | string   | yes      | ISO 8601 timestamp of when the run started                                  |
| `completed_at`  | string?  | yes      | ISO 8601 timestamp of completion, or `null` if still running                |
| `current_step`  | string   | yes      | Name of the currently executing step, or last executed step if finished     |
| `steps`         | array    | yes      | Ordered array of step objects (see below)                                   |
| `pr_url`        | string?  | yes      | URL of the created PR, or `null` if not yet created                         |

### Step Object Schema

Each entry in the `steps` array:

| Field    | Type    | Required | Description                                                        |
| -------- | ------- | -------- | ------------------------------------------------------------------ |
| `name`   | string  | yes      | Step name matching the blueprint step heading                      |
| `type`   | string  | yes      | Node type: `agent` or `deterministic`                              |
| `status` | string  | yes      | Step status: `pending`, `running`, `completed`, or `failed`        |
| `error`  | string? | no       | Error message if the step failed — omitted or `null` on success    |

## Status Transitions

A run progresses through these states:

```
pending → running → completed
                  → failed
```

- **pending**: State file created, run not yet started.
- **running**: At least one step is executing.
- **completed**: All steps finished successfully, PR created.
- **failed**: A step failed and could not be recovered (e.g., fix loop exhausted, deterministic step error).

Steps follow the same transitions independently:

```
pending → running → completed
                  → failed
```

## Example: Completed Run

```yaml
run_id: "20260317-143022-add-user-auth-a7f3"
task: "Add user authentication with JWT tokens"
blueprint: standard
branch: "mimoni/20260317-143022-add-user-auth-a7f3"
status: completed
started_at: "2026-03-17T14:30:22Z"
completed_at: "2026-03-17T14:45:18Z"
current_step: "PR Creation"
steps:
  - name: "Context Gathering"
    type: agent
    status: completed
  - name: "Planning"
    type: agent
    status: completed
  - name: "Branch Creation"
    type: deterministic
    status: completed
  - name: "TDD Implementation"
    type: agent
    status: completed
  - name: "Local Validation"
    type: deterministic
    status: completed
  - name: "Fix Loop"
    type: agent
    status: completed
  - name: "Commit & Push"
    type: deterministic
    status: completed
  - name: "PR Creation"
    type: deterministic
    status: completed
pr_url: "https://github.com/org/my-project/pull/42"
```

## Example: Failed Run (Fix Loop Exhausted)

```yaml
run_id: "20260317-150100-migrate-to-v2-c9d4"
task: "Migrate database from v1 to v2 schema"
blueprint: migration
branch: "mimoni/20260317-150100-migrate-to-v2-c9d4"
status: failed
started_at: "2026-03-17T15:01:00Z"
completed_at: "2026-03-17T15:23:45Z"
current_step: "Fix Loop"
steps:
  - name: "Context Gathering"
    type: agent
    status: completed
  - name: "Planning"
    type: agent
    status: completed
  - name: "Branch Creation"
    type: deterministic
    status: completed
  - name: "TDD Implementation"
    type: agent
    status: completed
  - name: "Analyze"
    type: agent
    status: completed
  - name: "Plan"
    type: agent
    status: completed
  - name: "Migrate"
    type: agent
    status: completed
  - name: "Validate"
    type: agent
    status: completed
  - name: "Local Validation"
    type: deterministic
    status: failed
    error: "typecheck failed: Property 'oldField' does not exist on type 'SchemaV2'"
  - name: "Fix Loop"
    type: agent
    status: failed
    error: "Fix loop exhausted after 2 retries — typecheck still failing"
  - name: "Commit & Push"
    type: deterministic
    status: pending
  - name: "PR Creation"
    type: deterministic
    status: pending
pr_url: null
```
