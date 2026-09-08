#!/usr/bin/env bash
# 08_run_all.sh -- master entrypoint: the full from-scratch pipeline end-to-end
# (mirrors Runs/experiments/scripts/run_all_n50_audits.sh, the paper's N50
# statistical-power audit, ~25-30h unattended). Stages are individually
# runnable -- see RUN_FROM_SCRATCH.md. Put this in tmux/nohup, NOT an agent.
#
# Usage:
#   tmux new -s n50audit
#   RESEARCH_ROOT=~/research bash 08_run_all.sh 2>&1 | tee n50.log
# Resume after crash: PHASES_SKIP="injection_ALL4 kv_overhead_ALL" bash 08_run_all.sh
set -u
ROOT="${RESEARCH_ROOT:-$HOME/research}"
cd "$ROOT"
N="${N:-50}"
AUDIT_ID=$(date +%Y%m%d_%H%M%S)
LOGDIR="$ROOT/logs/n50_audit_master_${AUDIT_ID}"; mkdir -p "$LOGDIR" "$ROOT/logs/n50_audit"
PROGRESS="$LOGDIR/progress.jsonl"; PHASES_SKIP="${PHASES_SKIP:-}"
log()    { echo "[$(date '+%F %T')] $*" | tee -a "$LOGDIR/orchestrator.log"; }
record() { printf '{"ts":"%s","phase":"%s","status":"%s","detail":"%s"}\n' "$(date -Iseconds)" "$1" "$2" "${3:-}" >> "$PROGRESS"; }
skipq()  { [[ " $PHASES_SKIP " == *" $1 "* ]]; }
cleanup(){ pkill -9 -f "bin/llama-server" 2>/dev/null || true; "$HOME/.lmstudio/bin/lms" unload --all >/dev/null 2>&1 || true; sleep 3; }
step()   { local n="$1"; shift; if skipq "$n"; then log "SKIP $n"; return; fi
           log "=== START $n ==="; cleanup
           if timeout 14400 "$@" >> "$LOGDIR/$n.log" 2>&1; then record "$n" ok; log "=== OK $n ==="
           else record "$n" failed "rc=$?"; log "=== FAILED $n (continuing) ==="; fi
           cleanup; }

MODELS="nemotron qwen35 gemma4 phi4"
MROOT="$HOME/.lmstudio/models/lmstudio-community"
declare -A GGUF
GGUF[nemotron]="$MROOT/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf"
GGUF[qwen35]="$MROOT/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf"
GGUF[gemma4]="$MROOT/gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf"
GGUF[phi4]="$MROOT/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf"
HARN="$ROOT/.agents/skills/local-llm-telemetry-audit/scripts"

log "=== from-scratch N50 audit start. audit_id=$AUDIT_ID (~25-30h) ==="
[ -x "$HARN/telemetry_harness_ollama.py" ] || log "WARN: rebuilt harness missing (06_build_netns_harness.sh)"

# P1 canary-injection leak rate (all 4 models, ~60-90 min)
step injection_ALL4 python3 "$ROOT/scripts/n50_audit/run_injection_test.py" --iterations "$N" --run-id "$AUDIT_ID"
# P2 patched-vs-unpatched KV overhead (8 combos, ~30-40 min)
step kv_overhead_ALL  python3 "$ROOT/scripts/n50_audit/run_kv_overhead.py" --iterations "$N" --run-id "$AUDIT_ID"
# P3 D4 cross-model heap residue (4 pairs x N, ~8-10h)
for pair in nemotron:qwen35 qwen35:gemma4 gemma4:phi4 phi4:nemotron; do
  ma="${pair%%:*}"; mb="${pair##*:}"
  for i in $(seq 1 "$N"); do
    step "d4_${ma}_${mb}_${i}" env D4_MODEL_A="${GGUF[$ma]}" D4_MODEL_B="${GGUF[$mb]}" \
      python3 "$ROOT/scripts/d4_cross_model_residue.py" "${AUDIT_ID}_d4_${ma}_${mb}_${i}"
  done
done
# P4 D7 PII attack chain (4 models x N, ~4-6h)
declare -A D7ID=([nemotron]=nvidia/nemotron-3-nano-4b [qwen35]=qwen/qwen3.5-9b [gemma4]=gemma-4-e4b-it [phi4]=microsoft/phi-4-reasoning-plus)
for m in $MODELS; do for i in $(seq 1 "$N"); do
  step "d7_${m}_${i}" env D7_MODEL="${D7ID[$m]}" python3 "$ROOT/scripts/d7_pii_attack_chain.py" "${AUDIT_ID}_d7_${m}_${i}"
done; done
# P5 cross-tenant /slots restore exploit (all 4, ~1h)
step slot_exploit_ALL4 python3 "$ROOT/scripts/n50_audit/run_slot_exploit.py" --iterations "$N" --run-id "$AUDIT_ID"
# P6 GPU VRAM bypass probe x N
for i in $(seq 1 "$N"); do step "gpuvram_${i}" python3 "$ROOT/scripts/gpu_vram_v5.py" "${AUDIT_ID}_gpuvram_${i}"; done
# P7 D5 Ollama netns cleanliness control (4 models x N, ~15-20h dominant)
for m in $MODELS; do for i in $(seq 1 "$N"); do
  step "d5_ollama_${m}_${i}" python3 "$HARN/telemetry_harness_ollama.py" --idle-min 3 --models "$m"
done; done

log "=== ALL PHASES COMPLETE. results: logs/n50_audit/*${AUDIT_ID}* ; $PROGRESS ==="
# Regenerate the summary tables from the new TELEMETRY_RUN_* dirs:
cd "$ROOT" && python3 experiments/build_index.py
