#!/usr/bin/env bash
# run_p2_n20_matrix.sh -- sequential driver for P2 scaled to n=20/config,
# all 4 models. One long-running job instead of 4 manually-relaunched ones.
# Models run one at a time (not parallel): CPU contention on this 16-thread
# host was already observed to slow concurrent runs without saving real
# wall-clock time (see RESEARCH_DEEPENING_PLAN.md P2 concurrency note).
set -e
cd /home/elaref/research/tifs

for model in nemotron qwen35 gemma4 phi4; do
  echo "=== [$(date -Iseconds)] starting $model ==="
  python3 scripts/arena_mitigation_probe.py --model "$model" \
    --configs baseline arena1 perturb --reps 25
  echo "=== [$(date -Iseconds)] finished $model ==="
done

echo "=== [$(date -Iseconds)] ALL 4 MODELS DONE ==="
