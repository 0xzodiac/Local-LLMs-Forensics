#!/usr/bin/env bash
# 06_build_netns_harness.sh -- rebuild the missing network-isolation telemetry
# harness that the repo snapshot does not ship (it lived at
#   ~/research/.agents/skills/local-llm-telemetry-audit/scripts/
#   {telemetry_harness.py, telemetry_harness_ollama.py, netns_isolate.sh}
# and produced the TELEMETRY_RUN_* directories).
#
# What the original did (reconstructed from meta.json + reports; see manual):
#   netns_isolate.sh up:
#     ip netns add lmns
#     ip link add lmns-br type bridge; ip link set lmns-br up
#     ip link add veth0 type veth peer name veth1
#     ip link set veth1 netns lmns
#     ip addr add 10.99.0.1/24 dev lmns-br; ip link set veth0 master lmns-br
#     ip netns exec lmns ip addr add 10.99.0.2/24 dev veth1
#     ip netns exec lmns ip link set lo up; ip netns exec lmns ip link set veth1 up
#     ip netns exec lmns ip route add default via 10.99.0.1
#     iptables -t nat -A POSTROUTING -s 10.99.0.0/24 -o <host-default-iface> -j MASQUERADE
#     sysctl -w net.ipv4.ip_forward=1
#   harness: run the tool INSIDE the namespace (ip netns exec) with tcpdump on
#   lmns-br as L1 ground truth + LD_PRELOAD libc hook as L2 (LMS only).
set -u
ROOT="${RESEARCH_ROOT:-$HOME/research}"
HARN="$ROOT/.agents/skills/local-llm-telemetry-audit/scripts"
mkdir -p "$HARN"

cat > "$HARN/netns_isolate.sh" <<'EOF'
#!/usr/bin/env bash
# netns_isolate.sh up|down -- lmns bridge-isolated namespace
set -u
NS=lmns; BR=lmns-br; VETH_HOST=veth0; VETH_NS=veth1; SUBNET=10.99.0.0/24
up() {
  ip netns add $NS 2>/dev/null || true
  ip link add $BR type bridge 2>/dev/null || true; ip link set $BR up
  ip link add $VETH_HOST type veth peer name $VETH_NS 2>/dev/null || true
  ip link set $VETH_HOST master $BR; ip link set $VETH_HOST up
  ip addr add 10.99.0.1/24 dev $BR 2>/dev/null || true
  ip link set $VETH_NS netns $NS
  ip netns exec $NS ip addr add 10.99.0.2/24 dev $VETH_NS
  ip netns exec $NS ip link set lo up; ip netns exec $NS ip link set $VETH_NS up
  ip netns exec $NS ip route add default via 10.99.0.1
  DEF_IF=$(ip route show default | awk '{print $5; exit}')
  iptables -t nat -A POSTROUTING -s $SUBNET -o "$DEF_IF" -j MASQUERADE
  sysctl -wq net.ipv4.ip_forward=1
  echo "[netns] $NS up (egress: $VETH_HOST -> $BR -> NAT via $DEF_IF)"
}
down() {
  ip netns del $NS 2>/dev/null || true
  ip link del $BR 2>/dev/null || true; ip link del $VETH_HOST 2>/dev/null || true
  echo "[netns] $NS down"
}
case "${1:-}" in up) up;; down) down;; *) echo "usage: netns_isolate.sh up|down"; exit 2;; esac
EOF
chmod +x "$HARN/netns_isolate.sh"

cat > "$HARN/telemetry_harness_ollama.py" <<'EOF'
#!/usr/bin/env python3
"""Rebuilt D5 Ollama netns telemetry harness (see manual: original not shipped).

Protocol per model (matches TELEMETRY_RUN_*_ollama_<model>/meta.json schema):
  1. netns up; tcpdump starts on lmns-br (L1 ground truth, sole egress)
  2. ollama serve + model load + /api/generate benign prompt
  3. canary prompt: "Remember this token: TELEMETRY_CANARY_<uuid>"
  4. idle hold (default --idle-min minutes) then teardown
  5. artifacts: meta.json, pcap/, pcap_quick.json, idle_snapshots.json,
     triggers.jsonl, canary_report.md
Ollama is a Go binary: LD_PRELOAD (L2) is skipped -- wire capture only.
"""
import argparse, json, subprocess, sys, time, uuid, shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]          # ~/research
NS, BR, SCRIPT = "lmns", "lmns-br", Path(__file__).parent
MODELS = {"nemotron": "nemotron-3-nano-4b-local", "qwen35": "qwen3.5-9b-local",
          "gemma4": "gemma-4-e4b-it-local", "phi4": "phi-4-reasoning-plus-local"}

def sudo(args, timeout=60, check=True):
    r = subprocess.run(["sudo", *args], capture_output=True, text=True, timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError(f"rc={r.returncode}: {' '.join(args[:6])}: {r.stderr.strip()[:200]}")
    return r

def run_in_ns(cmd, timeout=120, check=True):
    return sudo(["ip", "netns", "exec", NS, *cmd], timeout=timeout, check=check)

def http_ok_in_ns(url):
    r = run_in_ns(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url], check=False)
    return r.stdout.strip().startswith("2")

def parse_pcap(pcap_dir: Path, canary: str, out_json: Path):
    r = subprocess.run(["tshark", "-r", str(pcap_dir / "capture.pcap"),
                        "-T", "fields", "-e", "ip.dst", "-e", "dns.qry.name", "-e", "tls.handshake.extensions_server_name"],
                       capture_output=True, text=True)
    flows, dns, sni = set(), set(), set()
    for line in r.stdout.splitlines():
        f = line.split("\t")
        if len(f) > 0 and f[0]: flows.add(f[0])
        if len(f) > 1 and f[1]: dns.add(f[1])
        if len(f) > 2 and f[2]: sni.add(f[2])
    res = {"unique_dst_ips": len(flows), "dns_queries": sorted(dns), "tls_sni": sorted(sni),
           "canary_in_pcap": canary, "canary_found": False}
    grep = subprocess.run(["grep", "-a", "-c", canary, str(pcap_dir / "capture.pcap")], capture_output=True, text=True)
    res["canary_found"] = (grep.returncode == 0 and grep.stdout.strip() not in ("0", ""))
    out_json.write_text(json.dumps(res, indent=2))

def run_one_model(name: str, model: str, idle_min: int, keep_ns=False):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"{ts}_ollama_{name}"
    run_dir = ROOT / f"TELEMETRY_RUN_{run_id}"; run_dir.mkdir(parents=True, exist_ok=True)
    canary = f"TELEMETRY_CANARY_{uuid.uuid4().hex[:12]}"
    pcap_dir = run_dir / "pcap"; pcap_dir.mkdir(exist_ok=True)
    print(f"[{run_id}] model={model} canary={canary}", file=sys.stderr)

    sudo(["bash", str(SCRIPT / "netns_isolate.sh"), "up"], check=True)
    tcpdump = sudo(["ip", "netns", "exec", NS, "tcpdump", "-i", BR, "-w",
                    str(pcap_dir / "capture.pcap"), "-U"], check=False) if False else subprocess.Popen(
        ["sudo", "ip", "netns", "exec", NS, "tcpdump", "-i", BR, "-w", str(pcap_dir / "capture.pcap"), "-U"],
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    time.sleep(2)
    # run ollama serve INSIDE the namespace; talk to it via ns curl
    srv = subprocess.Popen(["sudo", "ip", "netns", "exec", NS, "ollama", "serve"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    for _ in range(60):
        if http_ok_in_ns("http://127.0.0.1:11434/api/tags"): break
        time.sleep(2)
    gen = {"model": model, "prompt": f"Remember this token: {canary}", "stream": False}
    run_in_ns(["curl", "-s", "-X", "POST", "http://127.0.0.1:11434/api/generate",
               "-d", json.dumps(gen), "-H", "Content-Type: application/json"], timeout=300)
    time.sleep(idle_min * 60)
    parse_pcap(pcap_dir, canary, run_dir / "pcap_quick.json")
    (run_dir / "triggers.jsonl").write_text(json.dumps({"ts": datetime.now().isoformat(), "event": "idle_hold_done", "canary": canary}) + "\n")
    meta = {"run_id": run_id, "tool": "ollama", "canary": canary, "model": model, "port": 11434,
            "netns": NS, "capture_iface": BR, "duration_sec": idle_min * 60, "hook": False,
            "architecture": "netns-isolated", "started_iso": datetime.now().isoformat(),
            "layers": {"L1_packet_capture_lmns_br": True, "L2_ld_preload_hook": False}}
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    srv.terminate(); tcpdump.terminate()
    if not keep_ns:
        sudo(["bash", str(SCRIPT / "netns_isolate.sh"), "down"], check=False)
    return run_dir

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--idle-min", type=int, default=3)
    ap.add_argument("--models", default="nemotron,qwen35,gemma4,phi4")
    ap.add_argument("--keep-ns", action="store_true")
    a = ap.parse_args()
    rundirs = []
    for name in [m.strip() for m in a.models.split(",") if m.strip()]:
        rundirs.append(run_one_model(name, MODELS[name], a.idle_min, keep_ns=a.keep_ns))
    print(json.dumps([str(r) for r in rundirs], indent=2))

if __name__ == "__main__":
    sys.exit(main())
EOF
chmod +x "$HARN/telemetry_harness_ollama.py"

# The LM Studio variant (telemetry_harness.py) adds layer L2 (LD_PRELOAD libc
# hook net_hooks.so) because LMS is a libc-linked binary -- see 07 for the hook.
cat > "$HARN/README-rebuilt.md" <<'EOF'
# Rebuilt telemetry harness

The original harness scripts (`telemetry_harness.py`, `telemetry_harness_ollama.py`,
`netns_isolate.sh`, `net_hooks.c`) were not committed to the public dataset
(they lived under a private skill directory). These are faithful reconstructions
from the run artifacts (`TELEMETRY_RUN_*/meta.json`, `pcap_quick.json`) and the
methodology in `TELEMETRY_FINDINGS_4MODELS.md` / `TELEMETRY_FINDINGS_OLLAMA.md`.

Differences vs. original (documented in the paper):
- L2 LD_PRELOAD hook for LM Studio runs is built separately (07_build_ld_hook.sh)
- Idle hold default 3 min (original: 4 min LMS / 3 min Ollama; both documented)
EOF
echo "[harness] rebuilt -> $HARN"
