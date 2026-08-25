#!/usr/bin/env bash
# run_all_n50_audits.sh -- unattended master orchestrator for the n>=50 /
# 4-of-4-model statistical-power audit across every sub-50-sample or
# sub-4-model finding in the corpus. Designed to run for many hours
# unattended (estimated ~25-30h total, dominated by D5's idle-hold windows
# and D4's cross-model swap cycles) inside nohup/tmux/screen, NOT inside an
# interactive agent session.
#
# Usage:
#   tmux new -s n50audit
#   nohup bash run_all_n50_audits.sh > /home/elaref/research/logs/n50_audit_master.out 2>&1 &
#   # detach (Ctrl-b d); reattach later with: tmux attach -t n50audit
#
# Resumability: each phase writes its own timestamped JSON under
# logs/n50_audit/ and logs/n50_audit_master_<id>/progress.jsonl is
# append-only -- if the script dies partway, check progress.jsonl for which
# phases completed and re-run with PHASES_SKIP set to a space-separated list
# of phase names already done (see bottom of this file for the full phase
# name list).
set -uo pipefail   # NOT -e: one phase's failure must not kill the whole run

ROOT=/home/elaref/research
cd "$ROOT"
N=50
AUDIT_ID=$(date +%Y%m%d_%H%M%S)
LOGDIR="$ROOT/logs/n50_audit_master_${AUDIT_ID}"
mkdir -p "$LOGDIR" "$ROOT/logs/n50_audit"
PROGRESS="$LOGDIR/progress.jsonl"
PHASES_SKIP="${PHASES_SKIP:-}"

LMS="/home/elaref/.lmstudio/bin/lms"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGDIR/orchestrator.log"
}

record() {
  # $1=phase $2=status(ok|failed|skipped) $3=detail(optional)
  printf '{"ts":"%s","phase":"%s","status":"%s","detail":"%s"}\n' \
    "$(date -Iseconds)" "$1" "$2" "${3:-}" >> "$PROGRESS"
}

is_skipped() {
  [[ " $PHASES_SKIP " == *" $1 "* ]]
}

cleanup_processes() {
  # SAFETY: never kill by a pattern broad enough to catch unrelated host
  # services. bin/llama-server here only ever matches OUR research binary
  # (absolute path under llama-cpp-build/), never a system service.
  pkill -9 -f "bin/llama-server" 2>/dev/null || true
  "$LMS" unload --all >/dev/null 2>&1 || true
  sleep 3
}

# run_step <phase_name> <command...>
# Wraps a step with: skip-if-already-done, cleanup before+after, timeout,
# non-fatal failure (logged and recorded, orchestrator continues),
# and a 4-hour per-step ceiling so one hung step can't stall everything else.
run_step() {
  local name="$1"; shift
  if is_skipped "$name"; then
    log "SKIP (requested via PHASES_SKIP): $name"
    record "$name" "skipped"
    return 0
  fi
  log "=== START: $name ==="
  cleanup_processes
  if timeout 14400 "$@" >> "$LOGDIR/${name}.log" 2>&1; then
    log "=== OK: $name ==="
    record "$name" "ok"
  else
    local rc=$?
    log "=== FAILED (rc=$rc): $name -- continuing to next phase ==="
    record "$name" "failed" "rc=$rc see ${name}.log"
  fi
  cleanup_processes
}

log "=== n>=50 / 4-of-4 statistical-power audit starting. audit_id=$AUDIT_ID ==="
log "Estimated total runtime: ~25-30h (D5 idle-hold windows and D4 cross-model"
log "swap cycles dominate). Progress: $PROGRESS"

MODELS="nemotron qwen35 gemma4 phi4"

declare -A GGUF
GGUF[nemotron]="/home/elaref/.lmstudio/models/lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf"
GGUF[qwen35]="/home/elaref/.lmstudio/models/lmstudio-community/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf"
GGUF[gemma4]="/home/elaref/.lmstudio/models/lmstudio-community/gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf"
GGUF[phi4]="/home/elaref/.lmstudio/models/lmstudio-community/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf"

# ---------------------------------------------------------------------------
# Phase 1: direct-repeat canary injection leak rate, n=50, 4/4 models
# (replaces phi4-only n=20; cheap, ~60-90 min total)
# ---------------------------------------------------------------------------
# (script handles all 4 models in one invocation; no per-model loop needed)
run_step "injection_ALL4" \
  python3 "$ROOT/scripts/n50_audit/run_injection_test.py" --iterations "$N" --run-id "$AUDIT_ID"

# ---------------------------------------------------------------------------
# Phase 2: KV-cache patch overhead, n=50 (was n=20), patched+unpatched x 4
# models (script handles all 8 combos in one invocation)
# (cheap, ~30-40 min total)
# ---------------------------------------------------------------------------
run_step "kv_overhead_ALL" \
  python3 "$ROOT/scripts/n50_audit/run_kv_overhead.py" --iterations "$N" --run-id "$AUDIT_ID"

# ---------------------------------------------------------------------------
# Phase 3: D4 cross-model heap residue, n=50 per pair, 4-model cycle
# (was n=1, one pair). A 4-pair cycle (nemotron->qwen35->gemma4->phi4->
# nemotron) touches every model at least twice without the combinatorial
# cost of all 6 unordered pairs. Heaviest phase besides D5: ~8-10h.
# ---------------------------------------------------------------------------
D4_PAIRS=("nemotron:qwen35" "qwen35:gemma4" "gemma4:phi4" "phi4:nemotron")
for pair in "${D4_PAIRS[@]}"; do
  ma="${pair%%:*}"; mb="${pair##*:}"
  for i in $(seq 1 "$N"); do
    run_id="${AUDIT_ID}_d4_${ma}_${mb}_${i}"
    D4_MODEL_A="${GGUF[$ma]}" D4_MODEL_B="${GGUF[$mb]}" run_step "d4_${ma}_${mb}_${i}" \
      python3 "$ROOT/scripts/d4_cross_model_residue.py" "$run_id"
  done
done

# ---------------------------------------------------------------------------
# Phase 4: D7 PII attack-chain demo, n=50, 4/4 models (was n=1, 1 model)
# (~4-6h)
# ---------------------------------------------------------------------------
D7_LMS_ID_nemotron="nvidia/nemotron-3-nano-4b"
D7_LMS_ID_qwen35="qwen/qwen3.5-9b"
D7_LMS_ID_gemma4="gemma-4-e4b-it"
D7_LMS_ID_phi4="microsoft/phi-4-reasoning-plus"
for m in $MODELS; do
  lms_id_var="D7_LMS_ID_${m}"
  for i in $(seq 1 "$N"); do
    run_id="${AUDIT_ID}_d7_${m}_${i}"
    D7_MODEL="${!lms_id_var}" run_step "d7_${m}_${i}" \
      python3 "$ROOT/scripts/d7_pii_attack_chain.py" "$run_id"
  done
done

# ---------------------------------------------------------------------------
# Phase 5: cross-tenant /slots restore exploit, n=50, 4/4 models
# (was n=1, 3/4 models -- gemma4 added here). Cheap relative to its
# importance: model loaded once per model, then 50 fast save/restore
# cycles -- ~10-15 min/model, ~1h total.
# ---------------------------------------------------------------------------
# (script handles all 4 models in one invocation; no per-model loop needed)
run_step "slot_exploit_ALL4" \
  python3 "$ROOT/scripts/n50_audit/run_slot_exploit.py" --iterations "$N" --run-id "$AUDIT_ID"

# ---------------------------------------------------------------------------
# Phase 6: GPU VRAM bypass probe, n=50 (was n=3)
# (existing script already takes a run_id positional arg; loop it directly)
# ---------------------------------------------------------------------------
for i in $(seq 1 "$N"); do
  run_id="${AUDIT_ID}_gpuvram_${i}"
  run_step "gpuvram_${i}" python3 "$ROOT/scripts/gpu_vram_v5.py" "$run_id"
done

# ---------------------------------------------------------------------------
# Phase 7: D5 Ollama netns network-cleanliness control, n=50/model, 4/4
# models (was n=1/model, already 4/4 models). DOMINANT cost: each rep
# includes a multi-minute idle-hold window. ~15-20h total -- the reason
# this whole audit runs overnight, not in an afternoon.
# ---------------------------------------------------------------------------
for m in $MODELS; do
  for i in $(seq 1 "$N"); do
    run_step "d5_ollama_${m}_${i}" \
      python3 "$ROOT/.agents/skills/local-llm-telemetry-audit/scripts/telemetry_harness_ollama.py" \
      --idle-min 3 --models "$m"
  done
done

log "=== ALL PHASES COMPLETE. audit_id=$AUDIT_ID ==="
log "Progress log: $PROGRESS"
log "Per-phase logs: $LOGDIR/*.log"
log "Result JSON files: $ROOT/logs/n50_audit/*${AUDIT_ID}* and matching D4/D7/D5/GPU-VRAM run dirs"

# ---------------------------------------------------------------------------
# Full phase-name reference (for PHASES_SKIP on a re-run after a crash):
#   injection_ALL4                               (1 phase, all 4 models internally)
#   kv_overhead_ALL                              (1 phase, 8 combos internally)
#   d4_<modelA>_<modelB>_<1..50>                 (200 phases)
#   d7_<model>_<1..50>                           (200 phases)
#   slot_exploit_ALL4                            (1 phase, all 4 models internally)
#   gpuvram_<1..50>                              (50 phases)
#   d5_ollama_<model>_<1..50>                    (200 phases)
# ---------------------------------------------------------------------------
