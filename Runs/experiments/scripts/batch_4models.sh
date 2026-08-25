#!/usr/bin/env bash
# batch_4models.sh — run the netns telemetry harness across 4 diverse models.
#
# Rationale: the first (nemotron) measurement proved startup-only telemetry on
# ONE model. For a fair, defensible claim we must show the behavior is a property
# of the TOOL (daemon), not an artefact of one model's load/chat path. So we
# measure 4 models spanning 4 architectures and 4 size classes, each under the
# identical isolated-harness protocol. Each run gets its own canary + run dir.
#
# Idle hold = 4 min per model (the nemotron 9-min run already proved the idle
# window is silent well past 4 min; 4 min still catches a slow beacon).
set -u

HARNESS=/home/elaref/research/.agents/skills/local-llm-telemetry-audit/scripts/telemetry_harness.py
MODELS=(
  "nvidia/nemotron-3-nano-4b"        # 4B  nemotron_h  (repeat for variance)
  "gemma-4-e4b-it"                   # 7.5B gemma4
  "microsoft/phi-4-reasoning-plus"   # 15B  Phi-3
  "qwen/qwen3.5-9b"                  # 9B   qwen35
)
DURATION=4   # minutes idle hold per model
RESULTS=/home/elaref/research/BATCH_RESULTS.txt
: > "$RESULTS"

for M in "${MODELS[@]}"; do
  echo "====================================================" | tee -a "$RESULTS"
  echo "[batch] measuring model: $M  (idle ${DURATION}m)" | tee -a "$RESULTS"
  echo "====================================================" | tee -a "$RESULTS"
  python3 "$HARNESS" --tool lms --duration-min "$DURATION" --model "$M" >>"$RESULTS" 2>&1
  RC=$?
  echo "[batch] $M done, harness exit=$RC" | tee -a "$RESULTS"
  echo "" >> "$RESULTS"
  # small breather between runs so netns teardown/recreate is clean
  sleep 5
done

echo "====================================================" | tee -a "$RESULTS"
echo "[batch] ALL 4 MEASUREMENTS COMPLETE" | tee -a "$RESULTS"
echo "====================================================" | tee -a "$RESULTS"
