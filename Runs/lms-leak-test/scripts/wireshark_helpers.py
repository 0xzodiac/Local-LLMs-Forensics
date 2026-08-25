"""Wireshark helpers for agentic traffic analysis.

This module wraps tshark and pyshark for common analysis tasks.
Designed to be called by Claude (or any agent) via Bash or Python.

Privilege model — two functions, two modes, no negotiation:

    READ  (analyzing existing pcaps):    calls `tshark` directly, no sudo.
    WRITE (live capture, capture_live):   calls `sudo tshark`, no fallback.

There is no auto-detection, no permission-error string-matching, and no
askpass helper. If you are in the `wireshark` group with dumpcap set up
correctly and you want unprivileged capture, call `tshark` yourself and
point the helpers at the resulting pcap.

Usage examples:
    from wireshark_helpers import capture_live, read_pcap, top_talkers

    # Live capture — runs `sudo tshark`. Needs a usable sudo context.
    pcap = capture_live(iface="eth0", count=100, bpf_filter="tcp port 443")

    # Read existing pcap — no sudo.
    summary = read_pcap("/tmp/web.pcap")

    # Get top talkers
    top = top_talkers("/tmp/web.pcap", direction="src", n=10)

    # Extract DNS queries
    domains = extract_dns_queries("/tmp/web.pcap")

    # Extract TLS SNI values
    sni_list = extract_tls_sni("/tmp/web.pcap")
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import Optional


# --- Privilege handling -----------------------------------------------------
#
# Two functions, two modes, no negotiation:
#   - _run_tshark:  `tshark` directly, for read operations on existing pcaps.
#   - _capture_tshark: `sudo tshark`, for live capture.
#
# There is no auto-detection, no permission-error string-matching, and no
# askpass helper. If you want unprivileged capture (e.g. you are in the
# `wireshark` group with dumpcap set up correctly), call `tshark` yourself
# and point the helpers at the resulting pcap.


def _run_tshark(args: list[str], timeout: Optional[int] = None) -> subprocess.CompletedProcess:
    """Run tshark unprivileged. For read operations on existing pcaps."""
    return subprocess.run(
        ["tshark", *args],
        capture_output=True, text=True, timeout=timeout,
    )


def _capture_tshark(args: list[str], timeout: Optional[int] = None) -> subprocess.CompletedProcess:
    """Run tshark with sudo for live capture.

    The caller is responsible for the sudo authentication context
    (attached terminal, NOPASSWD sudo, or running inside a privileged
    shell). This function does not negotiate — if sudo fails, the
    caller sees the raw sudo error.

    The pcap is chmod'd to 0644 *inside the sudo invocation* so the
    file is readable by the user after capture. Doing it from Python
    as the non-root user would fail with PermissionError on a
    root-owned file.
    """
    return subprocess.run(
        ["sudo", "sh", "-c", f"tshark {' '.join(args)} && chmod 0644 {args[args.index('-w') + 1]}"],
        capture_output=True, text=True, timeout=timeout,
    )


# --- Public API -------------------------------------------------------------

def list_interfaces() -> list[str]:
    """Return a list of capture interface descriptions.

    Example:
        >>> list_interfaces()
        ['1. eth0', '2. any', '3. lo (Loopback)', ...]
    """
    result = _run_tshark(["-D"])
    if result.returncode != 0:
        raise RuntimeError(f"tshark -D failed: {result.stderr}")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def capture_live(
    iface: str = "any",
    count: Optional[int] = None,
    duration: Optional[int] = None,
    bpf_filter: Optional[str] = None,
    display_filter: Optional[str] = None,
    out_dir: str = "/tmp",
    prefix: str = "wireshark",
) -> str:
    """Capture live traffic to a pcap file. Returns the path.

    Args:
        iface: Capture interface name (e.g. 'eth0', 'any'). Run list_interfaces() to see options.
        count: Stop after N packets.
        duration: Stop after N seconds.
        bpf_filter: Capture filter (BPF syntax, kernel-level). Use for performance.
        display_filter: Display filter (Wireshark syntax, userspace). Slower.
        out_dir: Where to write the pcap. Defaults to /tmp.
        prefix: Filename prefix.

    Either count or duration should be set; if both, the first to hit wins.

    Note: 'any' interface on Linux does NOT support BPF filters. If you need
    a BPF filter, pick a specific interface.

    Example:
        >>> pcap = capture_live(iface="eth0", count=100, bpf_filter="tcp port 443")
    """
    if count is None and duration is None:
        raise ValueError("set count or duration to bound the capture")
    if iface == "any" and bpf_filter:
        raise ValueError("BPF filters don't work on the 'any' interface; pick a real interface")

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    # Let tshark create the file. We can't pre-create it: sudo tshark
    # runs as root, and root can't overwrite a file with mode 0600 owned
    # by the current user.
    path = str(Path(out_dir) / f"{prefix}-{os.getpid()}-{os.urandom(3).hex()}.pcap")

    args = ["-i", iface, "-w", path]
    if count is not None:
        args += ["-c", str(count)]
    if duration is not None:
        args += [f"-a", f"duration:{duration}"]
    if bpf_filter:
        args += ["-f", bpf_filter]
    if display_filter:
        args += ["-Y", display_filter]

    result = _capture_tshark(args, timeout=(duration or 0) + 10 if duration else None)
    if result.returncode != 0:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
        raise RuntimeError(
            f"tshark capture failed (rc={result.returncode}): "
            f"{(result.stderr or '').strip() or '(no stderr)'}"
        )

    return path  # chmod 0644 was done inside the sudo invocation


def read_pcap(path: str) -> dict:
    """Read a pcap and return a summary dict.

    Returns:
        {
            'packets': int,
            'protocols': Counter,    # protocol → packet count
            'duration_sec': float,
            'top_src': list[tuple[str, int]],
            'top_dst': list[tuple[str, int]],
        }

    Example:
        >>> stats = read_pcap("/tmp/web.pcap")
        >>> stats['packets'], stats['protocols']['TCP']
        (1234, 1100)
    """
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    # Protocol hierarchy
    phs_proc = _run_tshark(["-r", path, "-q", "-z", "io,phs"])
    protocols = Counter()
    if phs_proc.returncode == 0:
        for line in phs_proc.stdout.splitlines():
            line = line.strip()
            if "frames" in line and "bytes" in line:
                proto = line.split("frames:")[0].split("  ")[0].strip().rstrip(".").strip()
                if proto:
                    try:
                        count = int(line.split("frames:")[1].split()[0])
                        protocols[proto] = count
                    except (IndexError, ValueError):
                        pass

    # Top talkers
    src_proc = _run_tshark(["-r", path, "-T", "fields", "-e", "ip.src"])
    src_counter: Counter = Counter()
    for line in (src_proc.stdout or "").splitlines():
        line = line.strip()
        if line:
            src_counter[line] += 1

    dst_proc = _run_tshark(["-r", path, "-T", "fields", "-e", "ip.dst"])
    dst_counter: Counter = Counter()
    for line in (dst_proc.stdout or "").splitlines():
        line = line.strip()
        if line:
            dst_counter[line] += 1

    # Duration
    dur_proc = _run_tshark(["-r", path, "-T", "fields", "-e", "frame.time_relative"])
    duration = 0.0
    times = []
    for line in (dur_proc.stdout or "").splitlines():
        try:
            times.append(float(line.strip()))
        except ValueError:
            pass
    if times:
        duration = max(times) - min(times)

    return {
        "packets": sum(protocols.values()) or 0,
        "protocols": protocols,
        "duration_sec": duration,
        "top_src": src_counter.most_common(10),
        "top_dst": dst_counter.most_common(10),
    }


def top_talkers(path: str, direction: str = "src", n: int = 10) -> list[tuple[str, int]]:
    """Return the top N IP addresses by packet count.

    Args:
        path: Pcap file path.
        direction: 'src' or 'dst'.
        n: How many results to return.

    Example:
        >>> top_talkers("/tmp/web.pcap", direction="src", n=5)
        [('192.168.1.5', 4321), ('10.0.0.1', 1234), ...]
    """
    if direction not in ("src", "dst"):
        raise ValueError("direction must be 'src' or 'dst'")
    field = f"ip.{direction}"
    proc = _run_tshark(["-r", path, "-T", "fields", "-e", field])
    counter: Counter = Counter()
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if line:
            counter[line] += 1
    return counter.most_common(n)


def extract_dns_queries(path: str) -> list[str]:
    """Extract all unique DNS query names from a pcap.

    Example:
        >>> extract_dns_queries("/tmp/web.pcap")
        ['example.com', 'cdn.example.com', ...]
    """
    proc = _run_tshark([
        "-r", path,
        "-Y", "dns.flags.response == 0",
        "-T", "fields", "-e", "dns.qry.name",
    ])
    domains = set()
    for line in (proc.stdout or "").splitlines():
        line = line.strip().lower().rstrip(".")
        if line:
            domains.add(line)
    return sorted(domains)


def extract_tls_sni(path: str) -> list[str]:
    """Extract all unique TLS SNI (Server Name Indication) values from a pcap.

    Useful for finding what domains a host is talking to over TLS.

    Example:
        >>> extract_tls_sni("/tmp/web.pcap")
        ['google.com', 'github.com', ...]
    """
    proc = _run_tshark([
        "-r", path,
        "-Y", "tls.handshake.extensions_server_name",
        "-T", "fields", "-e", "tls.handshake.extensions_server_name",
    ])
    snis = set()
    for line in (proc.stdout or "").splitlines():
        line = line.strip().lower()
        if line:
            snis.add(line)
    return sorted(snis)


def extract_http_hosts(path: str) -> list[tuple[str, int]]:
    """Extract HTTP Host headers from a pcap, with request counts.

    Example:
        >>> extract_http_hosts("/tmp/web.pcap")
        [('example.com', 42), ('cdn.example.com', 8), ...]
    """
    proc = _run_tshark([
        "-r", path,
        "-Y", "http.request",
        "-T", "fields", "-e", "http.host",
    ])
    counter: Counter = Counter()
    for line in (proc.stdout or "").splitlines():
        line = line.strip().lower()
        if line:
            counter[line] += 1
    return counter.most_common()


def apply_filter(path: str, display_filter: str, fields: Optional[list[str]] = None) -> list[dict]:
    """Apply a Wireshark display filter to a pcap and return rows.

    Args:
        path: Pcap file path.
        display_filter: Wireshark display filter string.
        fields: If given, return only these fields. Otherwise returns full packet list.

    Returns:
        List of dicts (one per packet) with field → value mapping.

    Example:
        >>> apply_filter("/tmp/web.pcap", "http.request", fields=["http.host", "http.request.uri"])
        [{'http.host': 'example.com', 'http.request.uri': '/login'}, ...]
    """
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    args = ["-r", path, "-Y", display_filter, "-T", "fields"]
    if fields:
        for f in fields:
            args += ["-e", f]
    else:
        args += ["-e", "_ws.col.Protocol", "-e", "_ws.col.Info"]

    proc = _run_tshark(args)
    if proc.returncode != 0:
        raise RuntimeError(f"filter failed: {proc.stderr}")

    rows = []
    field_names = fields or ["protocol", "info"]
    for line in (proc.stdout or "").splitlines():
        values = line.split("\t")
        if len(values) == len(field_names):
            rows.append(dict(zip(field_names, values)))
    return rows


def check_toolchain() -> dict:
    """Verify tshark, pyshark, scapy are all available. Returns status dict.

    Reports what is installed and whether each operation works on this host:

        tshark:           installed version, or None
        pyshark:          bool
        scapy:            installed version, or None
        interfaces:       list of capture interfaces (needs dumpcap access)
        read_pcap_works:  bool, whether `tshark -r file.pcap` runs unprivileged
        capture_needs:    'sudo' if live capture needs elevation, or 'unprivileged'

    Example:
        >>> check_toolchain()
        {'tshark': '4.2.2', 'pyshark': True, 'scapy': '2.7.0',
         'interfaces': [], 'read_pcap_works': True, 'capture_needs': 'sudo'}
    """
    status = {
        "tshark": None,
        "pyshark": False,
        "scapy": None,
        "interfaces": [],
        "read_pcap_works": False,
        "capture_needs": "unknown",
    }

    # tshark version
    proc = subprocess.run(["tshark", "--version"], capture_output=True, text=True)
    if proc.returncode == 0:
        first = (proc.stdout.splitlines() or [""])[0]
        m = re.search(r"TShark.*?(\d+\.\d+\.\d+(?:-\d+\S*)?)", first)
        status["tshark"] = m.group(1) if m else None

    # Python libraries
    try:
        import pyshark  # noqa: F401
        status["pyshark"] = True
    except ImportError:
        pass
    try:
        import scapy  # noqa: F401
        status["scapy"] = getattr(scapy, "__version__", "unknown")
    except ImportError:
        pass

    # READ path probe: `tshark -r <small file>` does NOT need dumpcap.
    # We test by piping /dev/null (it'll fail with "no input" but on
    # different grounds than a permission error).
    if status["tshark"]:
        read_probe = subprocess.run(
            ["tshark", "-r", "/dev/null", "-c", "1"],
            capture_output=True, text=True, timeout=5,
        )
        # rc != 0 is fine — we just want to see if the error is a
        # permission one (dumpcap) or a regular "no input" one.
        err = (read_probe.stderr or "").lower()
        if "permission" not in err and "dumpcap" not in err:
            status["read_pcap_works"] = True

    # INTERFACE LIST probe: `tshark -D` requires dumpcap. If it fails
    # on permission grounds, capture will too. Surface the actual
    # error so the user can see it.
    if status["tshark"]:
        try:
            status["interfaces"] = list_interfaces()
            status["capture_needs"] = "unprivileged"
        except RuntimeError as e:
            msg = str(e).lower()
            if "permission" in msg or "dumpcap" in msg:
                status["capture_needs"] = "sudo"
            else:
                # Some other error — leave "unknown" so the user knows
                # the probe didn't conclusively say.
                status["capture_needs"] = "unknown"

    return status
