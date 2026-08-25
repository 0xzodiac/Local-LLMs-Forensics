# Shared model path table for the n>=50 / 4-of-4 statistical-power audit.
NEMOTRON_GGUF="/home/elaref/.lmstudio/models/lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf"
QWEN35_GGUF="/home/elaref/.lmstudio/models/lmstudio-community/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf"
GEMMA4_GGUF="/home/elaref/.lmstudio/models/lmstudio-community/gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf"
PHI4_GGUF="/home/elaref/.lmstudio/models/lmstudio-community/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf"
ALL_MODELS="nemotron qwen35 gemma4 phi4"
model_path() {
  case "$1" in
    nemotron) echo "$NEMOTRON_GGUF" ;;
    qwen35)   echo "$QWEN35_GGUF" ;;
    gemma4)   echo "$GEMMA4_GGUF" ;;
    phi4)     echo "$PHI4_GGUF" ;;
    *) echo "unknown model: $1" >&2; return 1 ;;
  esac
}
