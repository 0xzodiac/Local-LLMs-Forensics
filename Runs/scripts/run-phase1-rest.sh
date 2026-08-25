#!/usr/bin/env bash
# ponytail: direct batch loop for the 2 models missing Phase 1 (nemotron, phi4).
# opencode kept dying on this fixed multi-hour job; an LLM agent adds nothing here.
cd /home/sharks/research
for m in nemotron phi4; do
  pkill -f llama-server 2>/dev/null; sleep 2
  echo "[batch] === START  14:49:34 ===" >> logs/phase1_batch.log
  LLAMA_MODEL=/home/sharks/research/logs/ultimate/models/.gguf LLAMA_GPU_LAYERS=0     ITERATIONS=250 MAX_TOKENS=80 LLAMA_PORT=8080 LLAMA_MODEL_NAME=     python3 scripts/phase1-auto-harness.py       --output logs/phase1__results.csv       --features logs/phase1__features.csv >> logs/phase1_batch.log 2>&1
  echo "[batch] === DONE  rows=-1 14:49:34 ===" >> logs/phase1_batch.log
done
echo "[batch] ALL DONE 14:49:34" >> logs/phase1_batch.log
