#!/usr/bin/env bash
set -euo pipefail

# Run Phase 1 + Phase 2 for a single model.
# Usage: MODEL_SHORT=M7B MODEL_PATH=/path/to/model.gguf bash run-model-pipeline.sh

MODEL_SHORT="${MODEL_SHORT:?Set MODEL_SHORT e.g. nemotron-nano}"
MODEL_PATH="${MODEL_PATH:?Set MODEL_PATH}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8080}"
ITERATIONS="${ITERATIONS:-250}"

REPO="/home/sharks/research"
SERVER_BIN="$REPO/llama-monitor/build/llama.cpp/bin/llama-server"
LOG="$REPO/logs/llama/${MODEL_SHORT}_pipeline.log"
PHASE1_CSV="$REPO/logs/phase1_${MODEL_SHORT}_results.csv"
PHASE1_FEATURES="$REPO/logs/phase1_${MODEL_SHORT}_features.csv"
PHASE2_CSV="$REPO/logs/phase2_${MODEL_SHORT}_results.csv"
PHASE2_ANOMALIES="$REPO/logs/phase2_${MODEL_SHORT}_anomalies.csv"

echo "=== Pipeline start: $MODEL_SHORT ===" | tee -a "$LOG"

# Kill any existing server
pkill -f "llama-server" 2>/dev/null || true
sleep 2

# Start server
echo "Starting server..." | tee -a "$LOG"
setsid "$SERVER_BIN" --model "$MODEL_PATH" --host "$HOST" --port "$PORT" \
  --ctx-size 2048 --n-gpu-layers 0 --jinja > "$REPO/logs/llama/${MODEL_SHORT}_server.log" 2>&1 &
SERVER_PID=$!

# Wait for healthy
for i in $(seq 1 60); do
  sleep 3
  curl -so /dev/null -w "%{http_code}" "http://$HOST:$PORT/health" 2>/dev/null | grep -q 200 && break
done
echo "Server healthy (PID $SERVER_PID)" | tee -a "$LOG"

# Phase 1
echo "--- Phase 1: $ITERATIONS iterations ---" | tee -a "$LOG"
LLAMA_MODEL_NAME="$MODEL_SHORT" python3 "$REPO/scripts/phase1-auto-harness.py" \
  --iterations "$ITERATIONS" \
  --host "$HOST" --port "$PORT" \
  --max-tokens 128 \
  --results-csv "$PHASE1_CSV" \
  --features "$PHASE1_FEATURES" \
  --timeout 120 --stabilize-seconds 0.5 2>&1 | tee -a "$LOG"
echo "Phase 1 complete" | tee -a "$LOG"

# Phase 2
echo "--- Phase 2: $ITERATIONS jailbreak_dan ---" | tee -a "$LOG"
LLAMA_MODEL_NAME="$MODEL_SHORT" python3 "$REPO/scripts/phase2-adversarial-harness.py" \
  --iterations "$ITERATIONS" \
  --start-iteration 1 \
  --max-tokens 128 \
  --host "$HOST" --port "$PORT" \
  --results-csv "$PHASE2_CSV" \
  --anomalies-csv "$PHASE2_ANOMALIES" \
  --baseline-features-csv "$PHASE1_FEATURES" \
  --timeout 120 --stabilize-seconds 0.5 2>&1 | tee -a "$LOG"
echo "Phase 2 complete" | tee -a "$LOG"

# Stop server
kill "$SERVER_PID" 2>/dev/null || true
echo "=== Pipeline done: $MODEL_SHORT ===" | tee -a "$LOG"
