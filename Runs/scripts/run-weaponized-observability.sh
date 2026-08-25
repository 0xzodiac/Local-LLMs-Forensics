#!/usr/bin/env bash
# run-weaponized-observability.sh — wrapper that adds crash-tuned observability
# around the weaponized GGUF test runner.
#
# Starts dumpcap on loopback, runs the Python test runner, captures all output.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"
OBS_DIR="$LOG_DIR/weaponized_observability"
mkdir -p "$OBS_DIR"

TS="$(date +%Y%m%d-%H%M%S)"
PCAP="$OBS_DIR/loopback-$TS.pcap"
MEM_LOG="$OBS_DIR/mem-spike-detect-$TS.log"

echo "[obs] Starting crash-tuned observability wrapper"

# --- Dumpcap on loopback ---
DUMPCAP_PID=""
if command -v dumpcap >/dev/null 2>&1; then
    echo "[obs] Starting dumpcap on lo -> $PCAP"
    dumpcap -i lo -f "tcp port 9999 or tcp port 18100 or tcp port 18101 or tcp port 18102 or tcp port 18103 or tcp port 18104 or tcp port 18105" \
        -w "$PCAP" -q &
    DUMPCAP_PID=$!
    sleep 0.5
    echo "[obs] dumpcap PID=$DUMPCAP_PID"
else
    echo "[obs] WARNING: dumpcap not found, skipping network capture" >&2
fi

# --- Memory spike watcher (inline, lightweight) ---
# Polls /proc/meminfo and system-wide RSS for explosive growth
{
    echo "ts_epoch,mem_free_kb,mem_available_kb,swap_free_kb" > "$MEM_LOG"
    for i in $(seq 1 120); do
        ts=$(date +%s)
        free_k=$(awk '/^MemFree:/ {print $2}' /proc/meminfo)
        avail_k=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)
        swap_k=$(awk '/^SwapFree:/ {print $2}' /proc/meminfo)
        echo "$ts,${free_k:-0},${avail_k:-0},${swap_k:-0}" >> "$MEM_LOG"
        sleep 1
    done
} &
MEM_WATCHER_PID=$!

# --- Run the actual test runner ---
RUNNER_ARGS=(
    "--results-csv" "$LOG_DIR/gguf_weaponization_results.csv"
    "--iterations" "5"
    "--base-port" "18100"
)

# Pass through any extra args
RUNNER_ARGS+=("$@")

echo "[obs] Launching weaponized-test-runner.py"
python3 "$ROOT/scripts/weaponized-test-runner.py" "${RUNNER_ARGS[@]}" \
    2>&1 | tee "$OBS_DIR/runner-$TS.log"
RUNNER_EXIT=${PIPESTATUS[0]}

# --- Cleanup ---
echo "[obs] Stopping observability tools"
kill "$MEM_WATCHER_PID" 2>/dev/null || true
if [[ -n "$DUMPCAP_PID" ]]; then
    kill "$DUMPCAP_PID" 2>/dev/null || true
    wait "$DUMPCAP_PID" 2>/dev/null || true
fi

echo "[obs] Results:"
echo "  Runner CSV: $LOG_DIR/gguf_weaponization_results.csv"
echo "  Runner log: $OBS_DIR/runner-$TS.log"
echo "  Memory log: $MEM_LOG"
[[ -n "$DUMPCAP_PID" ]] && echo "  PCAP: $PCAP"
echo "[obs] Done (exit=$RUNNER_EXIT)"
exit "$RUNNER_EXIT"
