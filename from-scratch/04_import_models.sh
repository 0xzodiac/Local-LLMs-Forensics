#!/usr/bin/env bash
# 04_import_models.sh -- make the downloaded GGUFs visible to both runtimes:
#   1) LM Studio: point its model root at ~/.lmstudio/models (default, may
#      already be correct after 03_download_models.sh)
#   2) Ollama: OFFLINE import of the same .gguf files via Modelfile + FROM
#      (zero network pull -- the Ollama telemetry control D5 depends on this)
set -u
LMS="${HOME}/.lmstudio/bin/lms"

echo "== LM Studio =="
if [ -x "$LMS" ]; then
  "$LMS" status 2>/dev/null || true
  echo "[lms] index models from ~/.lmstudio/models (scans automatically; verify with 'lms ls')"
  "$LMS" ls 2>/dev/null | head -10 || true
else
  echo "[lms] lms CLI not found -- install LM Studio first (00_check_env.sh flags it)"
fi

echo ""
echo "== Ollama (offline import) =="
command -v ollama >/dev/null || { echo "[ollama] not installed"; exit 1; }
service ollama start 2>/dev/null || sudo systemctl start ollama 2>/dev/null || true
sleep 2

import() {  # $1=model name $2=gguf path
  local name="$1" gguf="$2"
  if ollama show "$name" >/dev/null 2>&1; then echo "[ollama] $name already present"; return; fi
  printf 'FROM %s\n' "$gguf" > /tmp/Modelfile
  if ollama create "$name" -f /tmp/Modelfile 2>&1; then echo "[ollama] imported: $name"; else echo "[ollama] FAILED: $name"; fi
  rm -f /tmp/Modelfile
}
MODELS_ROOT="${HOME}/.lmstudio/models/lmstudio-community"
import nemotron-3-nano-4b-local "$MODELS_ROOT/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf"
import qwen3.5-9b-local        "$MODELS_ROOT/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf"
import gemma-4-e4b-it-local    "$MODELS_ROOT/gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf"
import phi-4-reasoning-plus-local "$MODELS_ROOT/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf"
ollama list
