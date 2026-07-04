---
name: inferbox-hooks
description: Bezpečnostní Claude Code hooks pro libovolný projekt — blokace rm -rf a přístupu k .env, audit log tool callů. Součást inferbox orchestration frameworku.
---

# inferbox-hooks

Deterministická bezpečnostní vrstva pro Claude Code. Znovupoužitelné jádro (tenant-agnostic) inferbox orchestration frameworku.

## Co obsahuje

- `hooks/pre_tool_use.py` — blokuje nebezpečné `rm -rf` a přístup k `.env` souborům (povoluje `.env.sample`/`.env.example`). Exit code 2 = zablokuje tool call.
- `hooks/post_tool_use.py` — audit log dokončených tool callů do `.claude/logs/`.

## Instalace do projektu

1. Zkopíruj `hooks/` do `.claude/hooks/` cílového projektu.
2. Přidej do `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash|Read|Edit|Write|MultiEdit",
        "hooks": [{ "type": "command", "command": "uv run --script \"$CLAUDE_PROJECT_DIR/.claude/hooks/pre_tool_use.py\"" }] }
    ],
    "PostToolUse": [
      { "matcher": "Bash|Edit|Write|MultiEdit",
        "hooks": [{ "type": "command", "command": "uv run --script \"$CLAUDE_PROJECT_DIR/.claude/hooks/post_tool_use.py\"" }] }
    ]
  }
}
```

3. Ujisti se, že `logs/` (nebo `.claude/logs/`) je v `.gitignore`.

## Ověření

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/x"}}' | uv run --script .claude/hooks/pre_tool_use.py; echo "exit=$?"  # očekává exit=2
echo '{"tool_name":"Read","tool_input":{"file_path":".env"}}' | uv run --script .claude/hooks/pre_tool_use.py; echo "exit=$?"          # očekává exit=2
```

Vyžaduje `uv` (Astral). Žádné další závislosti.
