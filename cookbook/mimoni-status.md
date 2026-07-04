# Check Mimoni Run Status

## Context

Display the status of running and completed mimoni orchestration runs. This reads state files from the `.mimoni/` directory in the target project, parses each YAML state file, and presents a summary table showing all runs with their current progress.

This is useful for monitoring parallel mimoni runs, checking if a run completed successfully, or diagnosing where a failed run stopped.

## Steps

### 1. Check .mimoni/ Directory

Verify the `.mimoni/` state directory exists in the current project:

```bash
test -d .mimoni
```

- **If `.mimoni/` does not exist** → no mimoni runs have been started in this project. Display a friendly message and stop:
  > 📭 **No mimoni runs found.**
  > No `.mimoni/` directory exists in this project. Start a run with `/library mimoni run <task>`.
- **If `.mimoni/` exists** → proceed to step 2.

### 2. Read and Parse State Files

List all YAML state files in `.mimoni/`:

```bash
ls .mimoni/*.yaml
```

- **If no `.yaml` files are found** → display a friendly message and stop:
  > 📭 **No mimoni runs found.**
  > The `.mimoni/` directory exists but contains no run state files. Start a run with `/library mimoni run <task>`.
- **If state files are found** → read and parse each one.

For each `.yaml` file in `.mimoni/`, parse the YAML to extract run metadata. Wrap parsing in try/except so that a single malformed file does not abort the entire status display — skip invalid files with a warning:

```bash
python3 -c "
import yaml, glob, os, sys

files = sorted(glob.glob('.mimoni/*.yaml'))
runs = []
skipped = []
for f in files:
    try:
        with open(f) as fh:
            data = yaml.safe_load(fh)
            if data:
                runs.append(data)
    except Exception as e:
        skipped.append((f, str(e)))
        print(f'⚠️  Skipping {f}: invalid YAML ({e})', file=sys.stderr)

for r in runs:
    task = r.get('task', 'N/A')
    # Truncate task to 40 characters
    if len(task) > 40:
        task = task[:37] + '...'
    print(f\"{r.get('run_id', 'unknown')}|{task}|{r.get('blueprint', 'N/A')}|{r.get('status', 'N/A')}|{r.get('current_step', 'N/A')}|{r.get('started_at', 'N/A')}\")
"
```

### 3. Display Status Table

Present the parsed run data as a formatted table:

| Run ID | Task | Blueprint | Status | Current Step | Started |
| ------ | ---- | --------- | ------ | ------------ | ------- |
| `20260317-143022-add-user-auth-a7f3` | Add user authentication wi... | standard | running | Local Validation | 2026-03-17T14:30:22Z |
| `20260317-143540-fix-login-bug-b2e1` | Fix the timeout bug in the... | bugfix | completed | PR Creation | 2026-03-17T13:35:40Z |
| `20260317-150100-migrate-to-v2-c9d4` | Migrate database from v1 t... | migration | failed | Fix Loop | 2026-03-17T15:01:00Z |

**Status indicators** for readability:

- `running` → ⏳ running
- `completed` → ✅ completed
- `failed` → ❌ failed
- `pending` → 🕐 pending

After the table, display a summary line:

> **Total: N runs** — X running, Y completed, Z failed

### 4. Handle No-Runs Case

This step is reached only if steps 1 and 2 did not already exit early. If some files failed to parse (the `skipped` list from step 2 is non-empty), include a warning after the table:

> ⚠️ **N file(s) skipped due to invalid YAML.** Check the warnings above for details.

If the directory and files exist but **all** files fail to parse (no valid runs and all were skipped), display:

> ⚠️ **No valid run state files found.**
> The `.mimoni/` directory contains files, but none could be parsed as valid YAML. State files may be corrupted.
