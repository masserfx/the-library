---
name: inferbox-mimoni
description: Self-contained mimoni runner — autonomní one-shot orchestrace "popis úkolu -> draft PR" s git worktree izolací, TDD a validačním fix-loopem. Nezávislé na plné the-library instalaci.
---

# inferbox-mimoni

Standalone varianta mimoni orchestrace pro projekty, které nechtějí celý the-library skill. Task dovnitř → draft PR ven, bez zásahu člověka.

## Co obsahuje

- `mimoni-run.md` — slash command runner (worktree izolace, TDD, fix-loop max 2, draft PR). Zkopíruj do `.claude/commands/`.
- `mimoni.example.yaml` — šablona configu (blueprint, validation příkazy, PR nastavení, context include/exclude).

## Instalace do projektu

1. Zkopíruj `mimoni-run.md` do `.claude/commands/`.
2. Zkopíruj `mimoni.example.yaml` do rootu jako `mimoni.yaml` a uprav validaci na stack projektu (lint/typecheck/test příkazy, které reálně procházejí).
3. Zkopíruj blueprinty (`standard/bugfix/test/migration`) do `.claude/mimoni/blueprints/` — jsou v the-library repu (`blueprints/`) nebo je runner očekává na `$CLAUDE_PROJECT_DIR/.claude/mimoni/blueprints/`.
4. Přidej `.mimoni/` do `.gitignore`.

## Spuštění

```
/mimoni-run "popis úkolu"
```

## Precondition

Validační příkazy z `mimoni.yaml` musí na hlavní branchi procházet zeleně (jinak se každý běh zastaví ve validaci — by design). Runner to kontroluje a při nepřipraveném env hlásí a zastaví.

Vyžaduje: git, gh CLI, uv (pro YAML parse).
