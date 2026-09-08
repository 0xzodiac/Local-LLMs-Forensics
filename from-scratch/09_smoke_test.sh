#!/usr/bin/env bash
# 09_smoke_test.sh -- 10-minute sanity pass proving every moving part works
# BEFORE committing to the 25-30h full audit. One tiny iteration of each
# experiment class. Run this after 00-07, before 08.
set -u
ROOT="${RESEARCH_ROOT:-$HOME/research}"; cd "$ROOT"
MROOT="$HOME/.lmstudio/models/lmstudio-community"
PHI4="$MROOT/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf"
NEMOTRON="$MROOT/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf"
LMS="$HOME/.lmstudio/bin/lms"; HARN="$ROOT/.agents/skills/local-llm-telemetry-audit/scripts"
pass(){ echo "  [PASS] $1"; }; fail(){ echo "  [FAIL] $1 -- $2"; FAILED=1; }; FAILED=0

echo "== 1. llama-server patched binary boots =="
SERVER="$ROOT/llama-cpp-build/build/bin/llama-server"
if [ ! -x "$SERVER" ]; then SERVER="$ROOT/llama-cpp-build/src/build/bin/llama-server"; fi
[ -x "$SERVER" ] && "$SERVER" --version >/dev/null 2>&1 && pass "binary at $SERVER" || fail "llama-server" "run 05_build_llamacpp_patched.sh"

echo "== 2. GGUFs load + chat (llama-server, slot 0) =="
if [ -x "$SERVER" ] && [ -f "$PHI4" ]; then
  SECURE_ALLOC=0 "$SERVER" --model "$PHI4" --host 127.0.0.1 --port 8099 --ctx-size 2048 --n-gpu-layers 0 --threads 8 --jinja --parallel 1 >/dev/null 2>&1 &
  SRV=$!; ok=0
  for i in $(seq 1 60); do curl -s http://127.0.0.1:8099/health >/dev/null 2>&1 && { ok=1; break; }; sleep 2; done
  if [ "$ok" = 1 ]; then
    R=$(curl -s http://127.0.0.1:8099/v1/chat/completions -d '{"model":"local","messages":[{"role":"user","content":"Say OK"}],"max_tokens":5,"temperature":0}')
    echo "$R" | grep -q '"content"' && pass "phi4 chat round-trip" || fail "chat" "$R"
    post(){ curl -s -X POST "http://127.0.0.1:8099$1" -d "$2"; }
    S=$(post "/slots/0?action=save" '{"filename":"smoke.bin"}'); RS=$(post "/slots/1?action=restore" '{"filename":"smoke.bin"}')
    echo "$S$RS" | grep -q "n_restored" && pass "/slots save+restore API present" || fail "/slots" "$S$RS"
  else fail "server health" "never came up in 120s"; fi
  kill $SRV 2>/dev/null; wait $SRV 2>/dev/null
else fail "GGUF chat test" "phi4 gguf missing"; fi

echo "== 3. LM Studio CLI + injection script (1 iteration) =="
[ -x "$LMS" ] && "$LMS" status >/dev/null 2>&1 && pass "lms CLI" || fail "lms" "LM Studio not running"
python3 "$ROOT/scripts/n50_audit/run_injection_test.py" --model nemotron --iterations 2 --run-id smoke >/dev/null 2>&1 \
  && pass "run_injection_test.py (n=2, nemotron)" || fail "injection" "check lms daemon + model ids"

echo "== 4. D4 residue script (1 run) =="
D4_MODEL_A="$NEMOTRON" D4_MODEL_B="$PHI4" timeout 600 python3 "$ROOT/scripts/d4_cross_model_residue.py" smoke_d4 >/dev/null 2>&1 \
  && pass "d4_cross_model_residue.py" || echo "  [warn] d4 slow/failed -- inspect before full run"

echo "== 5. netns + tcpdump ground truth =="
sudo bash "$HARN/netns_isolate.sh" up >/dev/null 2>&1 && pass "netns up" || fail "netns" "check ip/iptables perms"
sudo ip netns exec lmns ping -c1 -W2 10.99.0.1 >/dev/null 2>&1 && pass "intra-ns connectivity" || fail "netns conn" "veth/bridge setup"
sudo bash "$HARN/netns_isolate.sh" down >/dev/null 2>&1 && pass "netns down" || fail "netns teardown" "manual cleanup: ip netns del lmns"

echo "== 6. rebuilt Ollama harness (short hold) =="
timeout 600 python3 "$HARN/telemetry_harness_ollama.py" --idle-min 0 --models nemotron >/dev/null 2>&1 \
  && pass "telemetry_harness_ollama.py" || fail "ollama harness" "ollama service + sudo"

echo; [ "$FAILED" = 0 ] && echo "SMOKE TEST: ALL PASS -> safe to start 08_run_all.sh" || { echo "SMOKE TEST: FAILURES -> fix before the full audit"; exit 1; }
