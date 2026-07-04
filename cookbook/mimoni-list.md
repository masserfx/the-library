# List Available Blueprints

## Context

Display the available mimoni blueprint workflows. This reads blueprint files from the `blueprints/` directory in The Library's skill directory (`LIBRARY_SKILL_DIR`), parses each file to extract its name and description, and presents them in a formatted table.

Blueprints are markdown-defined workflows that mix deterministic nodes (git, lint, test) with agent nodes (planning, implementation, fixing). Each blueprint is designed for a specific type of coding task.

## Steps

### 1. Read Blueprints Directory

List all markdown files in the `blueprints/` directory within the Library skill directory:

```bash
ls <LIBRARY_SKILL_DIR>/blueprints/*.md
```

- **If the `blueprints/` directory does not exist or contains no `.md` files** → display a friendly message and stop:
  > 📭 **No blueprints found.**
  > No blueprint files found in `<LIBRARY_SKILL_DIR>/blueprints/`. The Library installation may be incomplete — try running `/library sync` or reinstalling with `/library install`.
- **If blueprint files are found** → proceed to step 2.

### 2. Parse Blueprint Metadata

For each `.md` file in `blueprints/`, extract the name and description:

- **Name**: Derive from the filename by stripping the `.md` extension (e.g., `standard.md` → `standard`).
- **Description**: Read the first H1 heading (`# Title`) from the file. The H1 title serves as the human-readable description of the blueprint.

```bash
python3 -c "
import glob, os

files = sorted(glob.glob('<LIBRARY_SKILL_DIR>/blueprints/*.md'))
for f in files:
    name = os.path.splitext(os.path.basename(f))[0]
    description = ''
    with open(f) as fh:
        for line in fh:
            line = line.strip()
            if line.startswith('# '):
                description = line[2:]
                break
    print(f'{name}|{description}')
"
```

### 3. Display Blueprints Table

Present the parsed blueprint data as a formatted table:

| Blueprint | Description |
| --------- | ----------- |
| `bugfix` | Bugfix Blueprint |
| `migration` | Migration Blueprint |
| `standard` | Standard Blueprint |
| `test` | Test Blueprint |

After the table, display a usage hint:

> **Usage**: Set the `blueprint` field in `mimoni.yaml` to one of the names above, or use `auto` for automatic selection based on task keywords.
>
> To start a run: `/library mimoni run "<task description>"`

### 4. Handle No-Blueprints Case

This step is reached only if steps 1 and 2 did not already exit early. If blueprint files exist but none contain a valid H1 heading, display:

> ⚠️ **No valid blueprints found.**
> Blueprint files exist in `<LIBRARY_SKILL_DIR>/blueprints/` but none contain a valid H1 heading. Blueprint files should start with `# Blueprint Title`.
