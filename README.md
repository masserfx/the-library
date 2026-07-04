# The Library

A meta-skill for private-first distribution of agentics (skills, agents, and prompts) across agents, devices, and teams.

![The Library](images/10_meta_skill.svg)

## Who This Is For

If you're an engineer working on 10+ codebases with agents and you're building specialized private skills, agents, and prompts — this was made for you.

If you work in one or two repos, you don't need this. If you install skills from the public internet without reviewing them, this isn't for you either.

The Library solves a specific problem: you've built powerful agentics scattered across repos, devices, and teams. They're duplicated, out of sync, and hard to coordinate. This gives you a single reference catalog to distribute them privately.

## What It Is

The Library is a single skill whose only job is to manage other skills. It's a catalog of references — local file paths and GitHub repo URLs — that point to where your agentics live. Nothing is copied or installed until you ask for it.

Think of it as a `package.json` for agent capabilities — but instead of packages, you're managing skills, agents, and prompts. Instead of a registry, you're pointing at your own private GitHub repos and local paths.

**This is a pure agent application.** There are no scripts, no CLIs, no dependencies, no build tools. The entire application is encoded in `SKILL.md` and a set of cookbook instructions that teach the agent exactly what to do. The agent IS the runtime. This matters because:

- Any agent harness that reads skill files can run it (Claude Code, Pi, etc.)
- You can modify behavior by editing markdown, not code
- The skill can be extended, forked, and adapted instantly
- An orchestrator agent can chain library commands without any tooling overhead

## Why It Exists

![The Problem: Skill Sprawl](images/26_problem_skill_sprawl.svg)

As you build with AI agents, you accumulate skills, custom agents, and prompts — potentially hundreds of them. You need to:

- **Reuse** them across projects without copy-pasting
- **Distribute** them to your agents running on other devices (Mac mini, remote servers, cloud sandboxes)
- **Share** them with your team without making everything public
- **Keep them private** — these are specialized capabilities built for competitive edge
- **Stay in sync** — one source of truth, not 10 stale copies

![The Problem: Siloed Teams](images/32_problem_team_sharing.svg)

Existing solutions don't fit:
- **Global `~/.claude/*`** — exposes everything to every agent. Global is the opposite of specialized.
- **Claude Code plugins** — requires marketplace infrastructure, manifests, and locks you into one platform.
- **Single monorepo** — doesn't reflect reality. You build agentics in specific codebases for specific use cases.

## How It Works

![The Solution: The Library](images/27_solution_library_workflow.svg)

### The Catalog (`library.yaml`)

```yaml
default_dirs:
  skills:
    - default: .claude/skills/
    - global: ~/.claude/skills/
  agents:
    - default: .claude/agents/
    - global: ~/.claude/agents/
  prompts:
    - default: .claude/commands/
    - global: ~/.claude/commands/

library:
  skills:
    - name: my-skill
      description: What this skill does
      source: /Users/me/projects/tools/skills/my-skill/SKILL.md
      requires: [agent:helper-agent]
    - name: remote-skill
      description: A skill from a private repo
      source: https://github.com/myorg/private-skills/blob/main/skills/remote-skill/SKILL.md
  agents: []
  prompts: []
```

The catalog stores pointers, not copies. Skills live in their source repos. You pull on demand.

### Source Formats

| Format             | Example                                                            |
| ------------------ | ------------------------------------------------------------------ |
| Local filesystem   | `/absolute/path/to/SKILL.md`                                       |
| GitHub browser URL | `https://github.com/org/repo/blob/main/path/to/SKILL.md`           |
| GitHub raw URL     | `https://raw.githubusercontent.com/org/repo/main/path/to/SKILL.md` |

The source points to a specific file. The system pulls the entire parent directory (skills include scripts, references, assets — not just the markdown file).

For private repos, authentication uses SSH keys or `GITHUB_TOKEN` automatically.

### Typed Dependencies

Dependencies use typed references to avoid name collisions:

```yaml
requires: [skill:base-utils, agent:reviewer, prompt:task-router]
```

Dependencies are resolved and pulled first, recursively.

## Prerequisites

- **Claude Code** (or a compatible agent harness that reads `.claude/skills/` — e.g., Pi)
- **git** — for cloning sources and syncing the catalog
- **gh** (optional) — GitHub CLI for forking, cloning, and private repo access. Install: `brew install gh` or see [gh docs](https://cli.github.com)
- **GitHub SSH key or `GITHUB_TOKEN`** — for accessing private repos (not needed if using `gh auth login`)
- **just** (optional) — for justfile shortcuts. Install: `brew install just` or see [just docs](https://github.com/casey/just)

## Installation

This is a template repo. You fork it, clone it into your global skills directory, and it becomes a `/library` slash command available in every Claude Code session.

### 1. Fork This Repo

Fork to your own GitHub account (private repo recommended). This fork is your personal library catalog — you'll push catalog updates to it.

```bash
# Using GitHub CLI
gh repo fork disler/the-library --private --clone=false
```

Or fork manually via the GitHub UI.

### 2. Clone to Global Skills Directory

Clone your fork into `~/.claude/skills/library`. This path is what makes `/library` available as a global slash command in Claude Code.

```bash
# Using git
mkdir -p ~/.claude/skills/library
git clone <your-fork-url> ~/.claude/skills/library

# Or using GitHub CLI
gh repo clone <yourname>/the-library ~/.claude/skills/library
```

### 3. Configure

Open `~/.claude/skills/library/SKILL.md` and update the `## Variables` section with your fork URL. The agent reads these variables at runtime to know where to sync the catalog.

```markdown
# Before (template defaults)
- **LIBRARY_REPO_URL**: `<your forked repo url>`

# After (your values)
- **LIBRARY_REPO_URL**: `https://github.com/yourname/the-library.git`
```

The other two variables (`LIBRARY_YAML_PATH` and `LIBRARY_SKILL_DIR`) are correct by default if you cloned to `~/.claude/skills/library/`.

### 4. Verify

Start a new Claude Code session anywhere. `/library list` should work and show an empty catalog.

## Quick Start

![Full Workflow](images/45_solution_full_workflow.svg)

Here's the typical workflow: **build → catalog → distribute → use**.

### Add a skill to the catalog

You built a deploy skill in one of your repos. Register it:

```
/library add deploy skill from https://github.com/yourorg/infra-tools/blob/main/skills/deploy/SKILL.md
```

This adds a reference to `library.yaml` and pushes the update to your fork.

### Use it in another project

On another device, repo, or agent:

```
/library use deploy
```

This pulls the skill from the source repo into `.claude/skills/deploy/`.

Want it globally available on this machine?

```
/library use deploy install globally
```

### Push changes back

You improved the skill locally. Push the update to the source repo:

```
/library push deploy
```

Now every device that runs `/library sync` gets the latest version.

### Sync everything

Pull the latest version of all installed items:

```
/library sync
```

## Commands

| Command                      | What It Does                                               |
| ---------------------------- | ---------------------------------------------------------- |
| `/library install`           | First-time setup — fork, clone, configure                  |
| `/library add <details>`     | Register a new entry in the catalog                        |
| `/library use <name>`        | Pull from source into local directory (install or refresh) |
| `/library push <name>`       | Push local changes back to the source                      |
| `/library remove <name>`     | Remove from catalog and optionally delete local copy       |
| `/library list`              | Show full catalog with install status                      |
| `/library sync`              | Re-pull all installed items from source                    |
| `/library search <keyword>`  | Find entries by name or description                        |
| `/library mimoni run <task>` | Start a new mimoni orchestration run                       |
| `/library mimoni init`       | Initialize mimoni.yaml in current project                  |
| `/library mimoni status`     | Check status of running mimoni(s)                          |
| `/library mimoni list`       | List available blueprints                                  |

### Justfile Shortcuts

The included `justfile` lets you run library commands from your terminal without an interactive Claude session.

```bash
just list                  # List catalog
just use my-skill          # Pull a skill
just push my-skill         # Push changes back
just add "name: foo, description: bar, source: /path/to/SKILL.md"
just sync                  # Re-pull all installed items
just search "keyword"
```

> **Note:** Justfile recipes use `--dangerously-skip-permissions` because the agent needs filesystem and git access to clone, copy, and push. Review the `justfile` if you want to modify this behavior.

## Architecture

```
~/.claude/skills/library/     # The Library skill (globally installed)
    SKILL.md                  # Agent instructions — the brain
    library.yaml              # Your catalog of references
    cookbook/                  # Step-by-step guides for each command
        install.md
        add.md
        use.md
        push.md
        remove.md
        list.md
        sync.md
        search.md
        mimoni-run.md         # Mimoni orchestration run
        mimoni-init.md        # Mimoni project initialization
        mimoni-status.md      # Mimoni run status checking
        mimoni-list.md        # Mimoni blueprint listing
        mimoni-state.md       # Mimoni state management reference
    blueprints/               # Mimoni workflow templates
        standard.md           # General code changes
        bugfix.md             # Bug fix workflow
        migration.md          # Code migration workflow
        test.md               # Test writing workflow
    mimoni.example.yaml       # Mimoni configuration template
    justfile                  # CLI shorthand for all commands
    README.md                 # This file
```

## Design Principles

- **Private-first**: Built for your specialized, competitive-edge agentics. Not a public marketplace.
- **Reference-based**: The catalog stores pointers, not copies. Skills live in their source repos.
- **Pure agent**: No scripts, no build tools. The SKILL.md teaches the agent everything it needs to know.
- **Agent-agnostic**: Default target is `.claude/skills/` but supports any directory for any agent harness.
- **Catalog, not manifest**: Entries define what's available, not what's installed. Pull on demand.

## The Agentic Stack

![The Agentic Stack](images/03_agentic_stack.svg)

| Layer           | Purpose                                        |
| --------------- | ---------------------------------------------- |
| **Skills**      | Raw capabilities — what an agent can do        |
| **Agents**      | Scale + parallelism + specialization           |
| **Prompts**     | Orchestration — coordinate skills and agents   |
| **Justfile**    | Terminal access without an interactive session |
| **The Library** | Distribution across devices, teams, and agents |

## Mimoni

**Mimoni** is an agent orchestration system inspired by [Stripe's Minions](https://www.infoq.com/news/2025/04/stripe-agent-minions/) — one-shot, unattended coding agent runs. Task description in → pull request out, no human interaction in between.

Following The Library's pure-agent philosophy, the entire orchestration logic is encoded in markdown blueprints, cookbook instructions, and YAML configuration. No scripts, no CLIs, no dependencies. The agent IS the runtime.

### Blueprints

Blueprints are markdown-defined workflows that mix **deterministic nodes** (git operations, lint, test — exact shell commands) with **agent nodes** (planning, implementation, fixing — LLM-driven). This is the core architectural pattern from Stripe's Minions.

Every blueprint follows the canonical Stripe pattern: context gathering → planning → branch creation → TDD implementation → local validation → fix loop (max 2 retries) → commit & push → PR creation.

| Blueprint    | File                      | Use Case                                                          |
| ------------ | ------------------------- | ----------------------------------------------------------------- |
| **standard** | `blueprints/standard.md`  | General code changes — features, improvements, refactoring        |
| **bugfix**   | `blueprints/bugfix.md`    | Bug fixes — reproduce → diagnose → fix → verify                  |
| **migration**| `blueprints/migration.md` | Code migrations — analyze → plan → migrate → validate            |
| **test**     | `blueprints/test.md`      | Test writing — analyze coverage → write tests → verify            |

### Mimoni Commands

| Command                      | What It Does                              |
| ---------------------------- | ----------------------------------------- |
| `/library mimoni run <task>` | Start a new mimoni orchestration run      |
| `/library mimoni init`       | Initialize mimoni.yaml in current project |
| `/library mimoni status`     | Check status of running mimoni(s)         |
| `/library mimoni list`       | List available blueprints                 |

### Justfile Shortcuts for Mimoni

```bash
just mimoni "add user authentication"   # Run a single mimoni task
just mimoni-batch "task1" "task2"        # Run multiple tasks in parallel
just mimoni-status                       # Check status of all runs
just mimoni-init                         # Initialize mimoni.yaml in current project
```

### Quick Start

**1. Initialize mimoni in your project:**

```bash
just mimoni-init
```

This creates a `mimoni.yaml` configuration file with auto-detected defaults for your project (e.g., npm commands for Node.js projects, cargo for Rust, pytest for Python).

**2. Edit the config:**

Open `mimoni.yaml` and adjust validation commands, PR settings, and context rules for your project:

```yaml
blueprint: standard
validation:
  lint: npm run lint
  typecheck: npm run typecheck
  test: npm test
pr:
  branch_prefix: "mimoni/"
  max_retries: 2
  draft: true
```

**3. Run a mimoni task:**

```bash
just mimoni "add a /health endpoint that returns JSON status"
```

Mimoni reads your config, selects the blueprint, creates a branch, implements the task, runs validation with fix loops, and opens a PR — all unattended.

**4. Check status:**

```bash
just mimoni-status
```

View progress and results of running or completed mimoni runs.

### mimoni.yaml Configuration

The `mimoni.yaml` file configures how mimoni operates in your project. See `mimoni.example.yaml` for the full template.

| Section        | Purpose                                                           |
| -------------- | ----------------------------------------------------------------- |
| `blueprint`    | Which workflow to use (`standard`, `bugfix`, `migration`, `test`) |
| `validation`   | Shell commands for lint, typecheck, and test                      |
| `pr`           | Branch prefix, max retries, draft mode, labels, reviewers         |
| `agent`        | Model selection and rule files to include as context              |
| `context`      | Include/exclude glob patterns for project files                   |

## Master Agentic Coding
> Prepare for the future of software engineering

Agentic Engineering is a NEW SKILL for software engineers. And soon it will be a required skill for software engineers. Master it before the masses with [Tactical Agentic Coding](https://agenticengineer.com/tactical-agentic-coding?y=tlibms)

Follow the [IndyDevDan YouTube channel](https://www.youtube.com/@indydevdan) to improve your agentic coding advantage.
