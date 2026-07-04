#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///
"""Pre-tool-use bezpečnostní hook pro infer-forge.

Blokuje destruktivní `rm -rf` a přístup k .env souborům s tajemstvími.
Portováno z indy/agent-experts, .env ochrana ZAPNUTÁ (na rozdíl od originálu).
Exit code 2 = zablokuje tool call a vrátí chybu agentovi.
"""

import json
import re
import sys
from pathlib import Path


def is_dangerous_rm_command(command: str) -> bool:
    """Detekce nebezpečných rm příkazů (rm -rf a varianty na kritické cesty)."""
    normalized = " ".join(command.lower().split())

    patterns = [
        r"\brm\s+.*-[a-z]*r[a-z]*f",       # rm -rf, rm -Rf
        r"\brm\s+.*-[a-z]*f[a-z]*r",       # rm -fr
        r"\brm\s+--recursive\s+--force",
        r"\brm\s+--force\s+--recursive",
        r"\brm\s+-r\s+.*-f",
        r"\brm\s+-f\s+.*-r",
    ]
    for pattern in patterns:
        if re.search(pattern, normalized):
            return True

    dangerous_paths = [r"/", r"/\*", r"~", r"~/", r"\$HOME", r"\.\.", r"\*", r"\.", r"\.\s*$"]
    if re.search(r"\brm\s+.*-[a-z]*r", normalized):
        for path in dangerous_paths:
            if re.search(path, normalized):
                return True
    return False


def is_env_file_access(tool_name: str, tool_input: dict) -> bool:
    """Blokuje čtení/zápis .env (povoluje .env.sample a .env.example)."""
    allowed_suffixes = (".env.sample", ".env.example")

    if tool_name in ("Read", "Edit", "MultiEdit", "Write"):
        file_path = tool_input.get("file_path", "")
        if ".env" in file_path and not file_path.endswith(allowed_suffixes):
            return True

    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        env_patterns = [
            r"\b\.env\b(?!\.sample|\.example)",
            r"cat\s+.*\.env\b(?!\.sample|\.example)",
            r"echo\s+.*>\s*\.env\b(?!\.sample|\.example)",
            r"touch\s+.*\.env\b(?!\.sample|\.example)",
            r"cp\s+.*\.env\b(?!\.sample|\.example)",
            r"mv\s+.*\.env\b(?!\.sample|\.example)",
        ]
        for pattern in env_patterns:
            if re.search(pattern, command):
                return True
    return False


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        if is_env_file_access(tool_name, tool_input):
            print("BLOKOVÁNO: přístup k .env souborům s tajemstvími není povolen.", file=sys.stderr)
            print("Pro šablony použij .env.sample / .env.example.", file=sys.stderr)
            sys.exit(2)

        if tool_name == "Bash":
            command = tool_input.get("command", "")
            if is_dangerous_rm_command(command):
                print("BLOKOVÁNO: detekován nebezpečný rm příkaz.", file=sys.stderr)
                sys.exit(2)

        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "pre_tool_use.json"

        if log_path.exists():
            try:
                log_data = json.loads(log_path.read_text())
            except (json.JSONDecodeError, ValueError):
                log_data = []
        else:
            log_data = []

        log_data.append(input_data)
        log_path.write_text(json.dumps(log_data, indent=2, ensure_ascii=False))
        sys.exit(0)

    except json.JSONDecodeError:
        sys.exit(0)
    except Exception:
        sys.exit(0)


if __name__ == "__main__":
    main()
