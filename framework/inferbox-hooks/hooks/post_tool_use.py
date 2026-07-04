#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///
"""Post-tool-use audit log pro infer-forge. Loguje dokončené tool cally do .claude/logs/."""

import json
import sys
from pathlib import Path


def main() -> None:
    try:
        input_data = json.load(sys.stdin)

        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "post_tool_use.json"

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
