"""Cross-OS utilities for LM Studio forensics (WSL2 -> Windows)."""

from __future__ import annotations

import re
import socket
from pathlib import Path


def auto_detect_windows_host() -> str:
    """Detect Windows host IP from WSL2 /etc/resolv.conf gateway IP."""
    try:
        content = Path("/etc/resolv.conf").read_text()
        m = re.search(r"nameserver\s+(\d+\.\d+\.\d+\.\d+)", content)
        if m:
            return m.group(1)
    except Exception:
        pass
    return "172.22.240.1"


def verify_host_reachable(host: str, port: int = 1234, timeout: float = 3.0) -> bool:
    """Check if host:port is reachable via TCP handshake."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


WINDOWS_PROFILE_DIRS: list[Path] = [
    Path("/mnt/c/Users/w.i/AppData/Roaming/LM Studio"),
    Path("/mnt/c/Users/w.i/.cache/lm-studio"),
]
