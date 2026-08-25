#!/usr/bin/env bash
# run_d2_measurements.sh — runs the patched-vs-unpatched heap-string leak
# measurement that D2 needs. Run this DIRECTLY IN YOUR OWN TERMINAL (not via
# the agent's sandbox), because the sandbox kills child processes when a tool
# call returns. Each multilayer_v2.py run takes ~2-5 min on Phi-4 (CPU).
#
# Usage:  bash run_d2_measurements.sh
# Then tell the agent "done" and it will parse logs/multilayer_v2_patched_run*.json
set -u
cd /home/elaref/research
pkill -9 -f llama-server 2>/dev/null; sleep 2

echo "============================================================"
echo "D2 measurement: PATCHED binary, 3 runs (variance bars)"
echo "============================================================"
for i in 1 2 3; do
  echo ""
  echo "--- patched run $i/3 ---"
  python3 -u scripts/multilayer_v2.py patched_run${i}
  pkill -9 -f llama-server 2>/dev/null; sleep 3
done

echo ""
echo "============================================================"
echo "D2 part 2: 12-tenant blast-radius (WITH retained JSON)"
echo "============================================================"
pkill -9 -f llama-server 2>/dev/null; sleep 2
# leak_blast_radius.py uses nemotron (fast). Run patched.
MODEL="/home/elaref/.lmstudio/models/lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf"
python3 -u scripts/leak_blast_radius.py "$MODEL" nemotron_12t_patched
pkill -9 -f llama-server 2>/dev/null

echo ""
echo "============================================================"
echo "ALL DONE. Artifacts:"
echo "  patched multilayer: logs/multilayer_v2_patched_run{1,2,3}.json"
echo "  blast radius:       logs/leak_blast_radius_*.json (newest)"
echo "Tell the agent 'done' to parse results."
echo "============================================================"
