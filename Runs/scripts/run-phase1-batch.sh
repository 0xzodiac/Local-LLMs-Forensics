#!/usr/bin/env bash
# run-phase1-batch.sh — Run Phase 1 harness under Wireshark, memory, and eBPF monitors.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MONITOR_ROOT="$ROOT/llama-monitor"
LOG_DIR="$ROOT/logs"
ITERATIONS="${ITERATIONS:-250}"
EXTRACT_FEATURES="${EXTRACT_FEATURES:-1}"
SUDO_BIN="${SUDO_BIN:-sudo}"
USE_SUDO_PASS=0
if [[ -n "${SUDO_PASS+x}" ]]; then
  USE_SUDO_PASS=1
fi

mkdir -p "$LOG_DIR" "$MONITOR_ROOT/logs/wireshark" "$MONITOR_ROOT/logs/mem" "$MONITOR_ROOT/logs/ebpf"
PCAP_TMP="${PCAP_TMP:-/tmp/llama-monitor-phase1-wireshark}"
mkdir -p "$PCAP_TMP"
chmod 0777 "$PCAP_TMP" "$MONITOR_ROOT/logs/wireshark" "$MONITOR_ROOT/logs/mem" "$MONITOR_ROOT/logs/ebpf" 2>/dev/null || true

PIDS=()
PGIDS=()
SERVER_STARTED_BY_BATCH=0

ensure_server() {
  if curl -sf "http://127.0.0.1:${LLAMA_PORT:-8080}/health" >/dev/null 2>&1; then
    echo "[phase1-batch] Reusing healthy llama-server"
    return 0
  fi

  echo "[phase1-batch] Starting llama-server before monitors so PID-based probes can attach"
  LLAMA_HOST="${LLAMA_HOST:-127.0.0.1}" LLAMA_PORT="${LLAMA_PORT:-8080}" "$MONITOR_ROOT/scripts/start-llama-server.sh"
  SERVER_STARTED_BY_BATCH=1
}

stop_monitors() {
  echo "[phase1-batch] Stopping monitors..."
  for pgid in "${PGIDS[@]:-}"; do
    kill -INT "$pgid" 2>/dev/null || true
  done
  for pid in "${PIDS[@]:-}"; do
    kill -INT "$pid" 2>/dev/null || true
  done

  sleep 2

  for pgid in "${PGIDS[@]:-}"; do
    kill -TERM "$pgid" 2>/dev/null || true
  done
  for pid in "${PIDS[@]:-}"; do
    kill -TERM "$pid" 2>/dev/null || true
  done

  for pid in "${PIDS[@]:-}"; do
    wait "$pid" 2>/dev/null || true
  done
}

cleanup() {
  local status=$?
  trap - EXIT INT TERM
  stop_monitors
  if (( SERVER_STARTED_BY_BATCH == 1 )); then
    echo "[phase1-batch] Stopping llama-server..."
    "$MONITOR_ROOT/scripts/stop-llama-server.sh" || true
  fi
  echo "[phase1-batch] Exit status: $status"
  exit "$status"
}
trap cleanup EXIT INT TERM

start_monitor() {
  local name="$1"
  local use_sudo="$2"
  shift 2
  local log="$LOG_DIR/phase1-$name.log"
  echo "[phase1-batch] Starting $name -> $log"
  if (( use_sudo == 1 )); then
    if [[ "$name" == "wireshark" ]]; then
      local pcap_base="$PCAP_TMP/capture-$(date +%Y%m%d-%H%M%S)"
    else
      local pcap_base=""
    fi
    if (( USE_SUDO_PASS == 1 )); then
      if [[ -n "$pcap_base" ]]; then
        printf '%s\n' "$SUDO_PASS" | setsid "$SUDO_BIN" -S env PCAP_OUT_BASE="$pcap_base" "$@" >"$log" 2>&1 &
      else
        printf '%s\n' "$SUDO_PASS" | setsid "$SUDO_BIN" -S "$@" >"$log" 2>&1 &
      fi
    else
      if [[ -n "$pcap_base" ]]; then
        setsid "$SUDO_BIN" env PCAP_OUT_BASE="$pcap_base" "$@" >"$log" 2>&1 &
      else
        setsid "$SUDO_BIN" "$@" >"$log" 2>&1 &
      fi
    fi
    local pid=$!
    PIDS+=("$pid")
    PGIDS+=("-$pid")
  else
    "$@" >"$log" 2>&1 &
    local pid=$!
    PIDS+=("$pid")
  fi
}

ensure_server
start_monitor "wireshark" 1 "$MONITOR_ROOT/scripts/start-wireshark.sh"
start_monitor "mem" 0 "$MONITOR_ROOT/scripts/mem-monitor.sh"
start_monitor "ebpf" 1 "$MONITOR_ROOT/scripts/run-ebpf.sh"

sleep 3
for pid in "${PIDS[@]}"; do
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "[phase1-batch] Monitor exited during startup" >&2
    for log in "$LOG_DIR"/phase1-*.log; do
      [[ -f "$log" ]] || continue
      echo "--- $log ---" >&2
      tail -20 "$log" >&2 || true
    done
    exit 1
  fi
done

echo "[phase1-batch] Running harness for $ITERATIONS iterations"
python3 "$ROOT/scripts/phase1-auto-harness.py" --iterations "$ITERATIONS"
HARNESS_STATUS=$?

stop_monitors

if [[ "$EXTRACT_FEATURES" == "1" ]]; then
  echo "[phase1-batch] Extracting baseline features"
  python3 "$ROOT/scripts/extract-baseline-features.py"
fi

echo "[phase1-batch] Done. Artifacts:"
find "$LOG_DIR" -maxdepth 1 -type f \( -name 'phase1_*' -o -name 'phase1_baseline_*' \) -printf '%f\n' | sort

exit "$HARNESS_STATUS"
