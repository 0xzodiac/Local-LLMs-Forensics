#!/usr/bin/env python3
"""Scan Claude Code / OpenClaw local state for a leaked canary string.

ponytail: deliberately skips credential/auth files by name -- never reads or
prints their contents, even though a random canary is never going to be in
them. This is a trust-boundary line, not a feature to relax later.
"""
import sys
from pathlib import Path

SKIP_NAMES = {".credentials.json", "auth.json"}
SCAN_DIRS = [Path.home() / ".claude", Path.home() / ".openclaw"]


def scan(canary: str) -> list[str]:
    hits = []
    for base in SCAN_DIRS:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.name in SKIP_NAMES:
                continue
            try:
                text = path.read_text(errors="ignore")
            except OSError:
                continue
            if canary in text:
                hits.append(str(path))
    return hits


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: agentic_log_scanner.py <canary>")
    canary = sys.argv[1]
    hits = scan(canary)
    if hits:
        print(f"LEAKED -- canary found in {len(hits)} file(s):")
        for h in hits:
            print(f"  {h}")
    else:
        print("CLEAN -- canary not found in ~/.claude or ~/.openclaw")


if __name__ == "__main__":
    main()
