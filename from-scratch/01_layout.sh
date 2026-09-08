#!/usr/bin/env bash
# 01_layout.sh -- recreate the working-directory layout the research scripts
# expect. The repo snapshot puts everything under Runs/, but every script was
# written against a live workspace rooted at ~/research with the GGUFs under
# ~/.lmstudio/models/. This script mirrors that layout on a fresh machine.
#
# Two options:
#   MODE=link   (default) create ~/research as symlinks into this repo clone
#   MODE=copy   copy the script/patch/report files into a real ~/research
set -u
MODE="${MODE:-link}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"      # the Local-LLMs-Forensics clone
ROOT="${RESEARCH_ROOT:-$HOME/research}"        # workspace root scripts expect

mkdir -p "$ROOT"/{logs,scripts,experiments,patches,provenance}
mkdir -p "$ROOT"/logs/{n50_audit,cross_tenant_extract}
mkdir -p "$HOME/.lmstudio/models/lmstudio-community" 2>/dev/null || true

if [ "$MODE" = "link" ]; then
  echo "[layout] linking repo content into $ROOT (edit-in-place stays in the clone)"
  ln -sfn "$REPO/Runs/scripts/"*                "$ROOT/scripts/" 2>/dev/null || true
  ln -sfn "$REPO/Runs/experiments/scripts"      "$ROOT/experiments/scripts" 2>/dev/null || true
  ln -sfn "$REPO/Runs/experiments/build_index.py" "$ROOT/experiments/build_index.py" 2>/dev/null || true
  ln -sfn "$REPO/Runs/patches"                  "$ROOT/patches" 2>/dev/null || true
  ln -sfn "$REPO/Runs/provenance"               "$ROOT/provenance" 2>/dev/null || true
else
  echo "[layout] copying repo content into $ROOT"
  cp -r "$REPO/Runs/scripts/"*            "$ROOT/scripts/"
  cp -r "$REPO/Runs/experiments/scripts"  "$ROOT/experiments/scripts"
  cp "$REPO/Runs/experiments/build_index.py" "$ROOT/experiments/"
  cp -r "$REPO/Runs/patches"              "$ROOT/patches"
  cp -r "$REPO/Runs/provenance"           "$ROOT/provenance"
fi

# The original harness (telemetry / D5 Ollama phase) lived inside a skill dir:
#   /home/elaref/research/.agents/skills/local-llm-telemetry-audit/scripts/
# The repo snapshot does not ship it, so create the path so master scripts that
# reference it fail loudly instead of silently -- and see the manual, section
# "Missing harness", for the rebuilt equivalent.
HARN="$ROOT/.agents/skills/local-llm-telemetry-audit/scripts"
mkdir -p "$HARN"

printf "[layout] done.\n"
printf "  workspace root : %s\n" "$ROOT"
printf "  models dir     : %s/.lmstudio/models/lmstudio-community\n" "$HOME"
printf "  telemetry path : %s (populate -- see manual 'Missing harness')\n" "$HARN"
