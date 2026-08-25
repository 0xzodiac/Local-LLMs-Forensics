#!/usr/bin/env bash
# run_secure_allocator_test.sh — PROVES the zero-on-free allocator closes the
# 13-copy heap-string leak. Run in YOUR terminal (not the agent sandbox).
#
# Binary under test: llama-cpp-build/build/bin/llama-server (freshly built with
# secure-allocator.cpp: global operator delete override that explicit_bzeros
# every freed chunk >= 4 KB before returning it to glibc).
#
# Expected outcome: the 13-14 persistent copies/tenant drop to 0.
set -u
cd /home/elaref/research
pkill -9 -f llama-server 2>/dev/null; sleep 2

echo "============================================================"
echo "SECURE-ALLOCATOR TEST: 3 runs (variance), Phi-4, max_tokens=8"
echo "Binary: $(./llama-cpp-build/build/bin/llama-server --version 2>&1 | head -1)"
echo "============================================================"
for i in 1 2 3; do
  echo ""
  echo "--- secure-alloc run $i/3 ---"
  python3 -u scripts/multilayer_v2.py securealloc_run${i}
  pkill -9 -f llama-server 2>/dev/null; sleep 3
done

echo ""
echo "============================================================"
echo "BONUS: 12-tenant blast-radius with secure allocator (nemotron)"
echo "============================================================"
pkill -9 -f llama-server 2>/dev/null; sleep 2
MODEL="/home/elaref/.lmstudio/models/lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf"
python3 -u scripts/leak_blast_radius.py "$MODEL" nemotron_12t_securealloc
pkill -9 -f llama-server 2>/dev/null

echo ""
echo "============================================================"
echo "ALL DONE. Artifacts:"
echo "  secure-alloc multilayer: logs/multilayer_v2_securealloc_run{1,2,3}.json"
echo "  blast radius:            logs/leak_blast_radius_*.json (newest)"
echo ""
echo "Parse with: tell the agent 'done'"
echo "============================================================"
