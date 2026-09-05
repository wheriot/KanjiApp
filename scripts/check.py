"""Run the full local quality gate: ruff, ruff format, mypy, pytest.

Usage:
    uv run python scripts/check.py
"""

from __future__ import annotations

import subprocess

CHECKS: list[list[str]] = [
    ["ruff", "check", "."],
    ["ruff", "format", "--check", "."],
    ["mypy"],
    ["pytest"],
]


def main() -> int:
    failed: list[str] = []
    for cmd in CHECKS:
        print(f"\n=== {' '.join(cmd)} ===", flush=True)
        if subprocess.run(cmd, check=False).returncode != 0:
            failed.append(cmd[0])
    if failed:
        print(f"\nFAILED: {', '.join(failed)}")
        return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
