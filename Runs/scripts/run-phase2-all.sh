#!/usr/bin/env bash
# run-phase2-all.sh — Run all three Phase 2 analyses sequentially.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MONITOR_ROOT="$ROOT/llama-monitor"
LOG_DIR="$ROOT/logs"
SUDO_BIN="${SUDO_BIN:-sudo}"

mkdir -p "$LOG_DIR"

echo "=== Phase 2: Adversarial Analysis ==="
# Check server health
if ! curl -sf http://127.0.0.1:8080/health >/dev/null 2>&1; then
  echo "[phase2] Starting llama-server..."
  LLAMA_HOST="${LLAMA_HOST:-127.0.0.1}" LLAMA_PORT="${LLAMA_PORT:-8080}" \
    "$MONITOR_ROOT/scripts/start-llama-server.sh"
fi

python3 "$ROOT/scripts/phase2-adversarial-harness.py" \
  --iterations 2 --max-tokens 80
echo ""

echo "=== Phase 2: Weight Backdoor Analysis ==="
python3 "$ROOT/scripts/weight-backdoor-analysis.py"
echo ""

echo "=== Phase 2: GGUF Fuzzing ==="
python3 "$ROOT/scripts/gguf-fuzzer.py"
echo ""

echo "=== Phase 2 Complete ==="
echo "Results:"
ls -la "$LOG_DIR"/phase2_*.csv "$LOG_DIR"/weights_*.csv "$LOG_DIR"/gguf_fuzz_results.csv "$LOG_DIR"/weights_backdoor_report.txt 2>/dev/null || true
