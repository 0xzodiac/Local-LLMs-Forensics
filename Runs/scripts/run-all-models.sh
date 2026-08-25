#!/bin/bash
set -euo pipefail

MODELS=(
  "Qwen3.5-9B|/mnt/c/Users/w.i/.lmstudio/models/lmstudio-community/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf"
  "Nemotron-3-Nano-4B|/mnt/c/Users/w.i/.lmstudio/models/lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf"
  "Phi-4-reasoning-plus|/mnt/c/Users/w.i/.lmstudio/models/lmstudio-community/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf"
  "gemma-4-E4B-it|/mnt/c/Users/w.i/.lmstudio/models/lmstudio-community/gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf"
)

PHASE1_ITER=250
PHASE2_ITER=250
MAX_TOKENS=128
PORT=8080
HOST=127.0.0.1
CTX=2048

LOG_DIR="/home/sharks/research/logs"
SCRIPT_DIR="/home/sharks/research/scripts"
LLAMA_SERVER="/home/sharks/research/llama-monitor/build/llama.cpp/bin/llama-server"

start_server() {
  local model_path="$1"
  echo "[orchestrator] Starting llama-server with $model_path"
  LLAMA_MODEL="$model_path" LLAMA_HOST="$HOST" LLAMA_PORT="$PORT" LLAMA_GPU_LAYERS=0 LLAMA_CTX="$CTX" \
    "$LLAMA_SERVER" > "$LOG_DIR/llama-server-${model_name}.log" 2>&1 &
  SERVER_PID=$!
  echo "[orchestrator] Server PID: $SERVER_PID"
  
  for i in {1..60}; do
    if curl -sf "http://$HOST:$PORT/v1/models" >/dev/null 2>&1; then
      echo "[orchestrator] Server ready"
      return 0
    fi
    sleep 1
  done
  echo "[orchestrator] ERROR: Server failed to start"
  kill $SERVER_PID 2>/dev/null
  return 1
}

stop_server() {
  echo "[orchestrator] Stopping server PID $SERVER_PID"
  kill $SERVER_PID 2>/dev/null
  wait $SERVER_PID 2>/dev/null || true
  sleep 2
}

run_phase1() {
  local model_name="$1"
  echo "[orchestrator] Phase 1 baseline: $model_name ($PHASE1_ITER iterations)"
  cd "$SCRIPT_DIR"
  python3 phase1-auto-harness.py \
    --iterations "$PHASE1_ITER" \
    --host "$HOST" \
    --port "$PORT" \
    --output "$LOG_DIR/phase1_${model_name}_results.csv" \
    --features "$LOG_DIR/phase1_${model_name}_features.csv" \
    2>&1 | tee "$LOG_DIR/phase1_${model_name}.log"
}

run_phase2() {
  local model_name="$1"
  echo "[orchestrator] Phase 2 adversarial: $model_name ($PHASE2_ITER iterations, max_tokens=$MAX_TOKENS)"
  cd "$SCRIPT_DIR"
  MAX_TOKENS="$MAX_TOKENS" python3 phase2-adversarial-harness.py \
    --iterations "$PHASE2_ITER" \
    --host "$HOST" \
    --port "$PORT" \
    --results "$LOG_DIR/phase2_${model_name}_results.csv" \
    --anomalies "$LOG_DIR/phase2_${model_name}_anomalies.csv" \
    2>&1 | tee "$LOG_DIR/phase2_${model_name}.log"
}

aggregate() {
  echo "[orchestrator] Aggregating all models into final_multimodel_features.csv"
  cd "$SCRIPT_DIR"
  python3 -c "
import pandas as pd
import glob

all_dfs = []
for f in glob.glob('$LOG_DIR/phase1_*_features.csv'):
    model = f.split('phase1_')[1].split('_features.csv')[0]
    df = pd.read_csv(f)
    df['model_name'] = model
    df['phase'] = 'baseline'
    all_dfs.append(df)
    print(f'  Loaded {len(df)} rows from {model} baseline')

for f in glob.glob('$LOG_DIR/phase2_*_results.csv'):
    model = f.split('phase2_')[1].split('_results.csv')[0]
    df = pd.read_csv(f)
    df['model_name'] = model
    df['phase'] = 'adversarial'
    all_dfs.append(df)
    print(f'  Loaded {len(df)} rows from {model} adversarial')

if all_dfs:
    combined = pd.concat(all_dfs, ignore_index=True)
    combined.to_csv('$LOG_DIR/final_multimodel_features.csv', index=False)
    print(f'[orchestrator] Aggregated {len(combined)} total rows -> final_multimodel_features.csv')
    print(combined.groupby(['model_name', 'phase']).size())
else:
    print('[orchestrator] ERROR: No feature files found')
"
}

for entry in "${MODELS[@]}"; do
  model_name="${entry%%|*}"
  model_path="${entry##*|}"
  
  echo "========================================"
  echo "[orchestrator] Processing model: $model_name"
  echo "========================================"
  
  start_server "$model_path"
  run_phase1 "$model_name"
  run_phase2 "$model_name"
  stop_server
  
  echo "[orchestrator] Completed $model_name"
  echo ""
done

aggregate
echo "[orchestrator] ALL DONE"