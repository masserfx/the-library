# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

The Library is a **pure agent application** — no scripts, no CLIs, no dependencies. The entire runtime is encoded in `SKILL.md` + `cookbook/*.md` markdown files that teach the agent what to do. The agent IS the runtime.

It's a meta-skill for private-first distribution of agentics (skills, agents, prompts) across agents, devices, and teams. Think `package.json` for agent capabilities, but pointing at private GitHub repos and local paths.

## Key Files

- `SKILL.md` — The brain. Agent instructions, variables, commands, source parsing rules. **This is the entry point the agent reads when `/library` is invoked.**
- `library.yaml` — The catalog of references (pointers, not copies). Skills live in their source repos.
- `cookbook/*.md` — Step-by-step guides for each command. **Always read the relevant cookbook file before executing a command.**
- `justfile` — Terminal shortcuts that invoke `claude --dangerously-skip-permissions` for non-interactive use.

## Commands

All commands are invoked via `/library <command>`:

| Command | Cookbook | Purpose |
|---------|---------|---------|
| `install` | `cookbook/install.md` | First-time setup (fork, clone, configure) |
| `add <details>` | `cookbook/add.md` | Register new entry in catalog |
| `use <name>` | `cookbook/use.md` | Pull from source into local dir |
| `push <name>` | `cookbook/push.md` | Push local changes back to source |
| `remove <name>` | `cookbook/remove.md` | Remove from catalog |
| `list` | `cookbook/list.md` | Show catalog with install status |
| `sync` | `cookbook/sync.md` | Re-pull all installed items |
| `search <keyword>` | `cookbook/search.md` | Find entries by keyword |

## Justfile

```bash
just list                  # List catalog
just use my-skill          # Pull a skill
just push my-skill         # Push changes back
just add "name: foo, ..."  # Add entry
just sync                  # Re-pull all
just search "keyword"      # Search
```

## Architecture Notes

- `library.yaml` stores **pointers, not copies**. `source` field supports local paths (`/absolute/path`), GitHub browser URLs, and raw GitHub URLs.
- When pulling from GitHub: shallow clone → copy parent directory of referenced file → cleanup temp dir.
- Dependencies use typed references: `skill:name`, `agent:name`, `prompt:name`. Resolved recursively before the requested item.
- Default install targets are in `library.yaml` under `default_dirs`. "global" keyword → `~/.claude/skills/` etc.
- After modifying `library.yaml` (e.g., `add`), always git pull → change → commit → push to keep catalog synced across devices.
- `SKILL.md` has a `## Variables` section that must be configured after forking (LIBRARY_REPO_URL, LIBRARY_YAML_PATH, LIBRARY_SKILL_DIR).

## Making Changes

Since this is a pure markdown-based agent application:
- Modify behavior by editing `SKILL.md` or `cookbook/*.md` — no code to compile or test.
- The `justfile` recipes all delegate to `claude --dangerously-skip-permissions --model opus`.
- No build step, no tests, no linting. Validation is manual: invoke the `/library` command and verify behavior.
