#!/usr/bin/env python3
"""Plant a canary through Claude Code pointed at a local LLM backend, report what happened.

ponytail: tries the real thing first (subprocess call), falls back to printing
manual instructions if the `claude` binary or the API shape doesn't cooperate --
that mismatch is itself a valid finding, not a bug to work around.
"""
import os
import subprocess
import sys
import uuid

CANARY = "AGENT_CANARY_" + uuid.uuid4().hex[:12].upper()
LOCAL_ENDPOINTS = {
    "lmstudio": "http://localhost:1234",
    "ollama": "http://localhost:11434",
}


def try_claude_code(base_url: str, prompt: str):
    env = os.environ.copy()
    env["ANTHROPIC_BASE_URL"] = base_url
    try:
        r = subprocess.run(
            ["claude", "-p", prompt],
            env=env, capture_output=True, text=True, timeout=30,
        )
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return None, "", "claude binary not found on PATH"
    except subprocess.TimeoutExpired:
        return None, "", "timed out after 30s"


def main():
    prompt = f"Repeat back exactly: {CANARY}"
    print(f"canary: {CANARY}")
    for name, url in LOCAL_ENDPOINTS.items():
        print(f"\n--- targeting {name} ({url}) ---")
        rc, out, err = try_claude_code(url, prompt)
        print(f"exit={rc}\nstdout={out[:300]!r}\nstderr={err[:300]!r}")

    print(f"""
If both attempts errored on the API shape (likely -- Claude Code speaks
Anthropic's /v1/messages; LM Studio/Ollama speak OpenAI's /v1/chat/completions),
that mismatch IS the finding: Claude Code has no native local-model backend, so
this leakage vector doesn't apply as-is. Say so plainly in the report.

To retry by hand:
  ANTHROPIC_BASE_URL={LOCAL_ENDPOINTS['lmstudio']} claude -p "{prompt}"

Then scan for the canary:
  python3 scripts/agentic_log_scanner.py {CANARY}
""")


if __name__ == "__main__":
    main()
