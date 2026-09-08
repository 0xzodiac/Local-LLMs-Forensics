#!/usr/bin/env bash
# 03_download_models.sh -- fetch the four Q4_K_M GGUFs audited in the paper
# (byte-exact per Runs/provenance/model_digests.json) into the exact layout
# the scripts expect, and sha256-verify them.
#
# Designed for ANYONE reproducing from scratch: missing files are downloaded
# automatically. Already-present + verified files are never re-downloaded.
#
# Modes:
#   bash 03_download_models.sh              # download missing models (asks once, ~21 GB total)
#   bash 03_download_models.sh --yes       # download missing models, no prompt (CI/unattended)
#   bash 03_download_models.sh --check     # verify only, NEVER download
#
# Files land in ~/.lmstudio/models/lmstudio-community/<Repo>/<File>.gguf
# (same path LM Studio uses, and the path every research script references).
set -u
MODE="download"; YES=0
for a in "$@"; do
  case "$a" in
    --check) MODE="check" ;;
    --yes|-y) YES=1 ;;
    *) echo "unknown arg: $a (use --check | --yes)"; exit 2 ;;
  esac
done
DEST="$HOME/.lmstudio/models/lmstudio-community"

# rel-path | hf-repo | bytes | sha256   (source: Runs/provenance/model_digests.json)
cat > /tmp/_models.tsv <<'EOF'
NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf|lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF|2837072896|083af225449463dd7c38bebc888f9dcad187b834d8b15e08c297dda37c968b50
Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf|lmstudio-community/Qwen3.5-9B-GGUF|5627044256|cd76ec205963b3b33350093e6904d9de16c4e666fd104e1f632d25c7f15f2a13
gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf|lmstudio-community/gemma-4-E4B-it-GGUF|5335289664|3f72a20a06f626c78e6c475ae07a64c88b2663149c0f6197b56bf7cf1f37585c
Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf|lmstudio-community/Phi-4-reasoning-plus-GGUF|9053116128|6f10ded0197863aa0641e2451688ac8025c95ff7c948e23f1089d173e6834768
EOF

gb() { echo $(( $1 / 1024 / 1024 / 1024 )); }

# Pass 1: inventory
declare -A MISSING_BYTES; N_MISSING=0; DL_BYTES=0
while IFS='|' read -r rel repo bytes sha; do
  out="$DEST/$rel"
  if [ ! -f "$out" ]; then
    N_MISSING=$((N_MISSING+1)); MISSING_BYTES["$rel"]="$bytes"; DL_BYTES=$((DL_BYTES+bytes))
  fi
done < /tmp/_models.tsv

if [ "$MODE" = "check" ] || [ "$N_MISSING" -gt 0 ]; then
  echo "[models] $( ( [ "$N_MISSING" -eq 0 ] && echo "all 4 present" ) || echo "$N_MISSING/4 missing" ) (mode=$MODE)"
fi

# Confirm before a big pull (unless --yes or nothing to do)
if [ "$N_MISSING" -gt 0 ] && [ "$MODE" = "download" ] && [ "$YES" -ne 1 ]; then
  echo "[models] about to download $(gb "$DL_BYTES") GB (Nemotron 2.8 + Qwen 5.6 + Gemma 5.3 + Phi-4 9.0, Q4_K_M)"
  printf "[models] proceed? [y/N] "; read -r ans
  case "$ans" in y|Y|yes|YES) ;; *) echo "[models] aborted (use --yes to skip this prompt)"; exit 1 ;; esac
fi

FAIL=0
while IFS='|' read -r rel repo bytes sha; do
  out="$DEST/$rel"; base="$(basename "$rel")"; dir="$(dirname "$out")"
  if [ ! -f "$out" ]; then
    if [ "$MODE" = "check" ]; then
      echo "[models] MISSING (check mode, not downloading): $base"
      echo "          get: https://huggingface.co/$repo  ->  \$HOME/.lmstudio/models/lmstudio-community/$rel"
      FAIL=1; continue
    fi
    echo "[models] downloading $(gb "$bytes") GB: $base"
    mkdir -p "$dir"
    url="https://huggingface.co/$repo/resolve/main/$base"
    if curl -L --fail --retry 3 --progress-bar -o "$out.part" "$url"; then
      mv "$out.part" "$out"
    else
      echo "[models] DOWNLOAD FAILED: $base ($url)"; rm -f "$out.part"; FAIL=1; continue
    fi
  fi
  got=$(sha256sum "$out" | awk '{print $1}')
  if [ "$got" = "$sha" ]; then
    echo "[models] sha256 OK: $base"
  else
    echo "[models] sha256 MISMATCH: $base"
    echo "          want $sha"
    echo "          got  $got"
    if [ "$MODE" = "download" ]; then
      echo "          deleting and re-downloading..."
      rm -f "$out"
      curl -L --fail --retry 3 --progress-bar -o "$out.part" "https://huggingface.co/$repo/resolve/main/$base" \
        && mv "$out.part" "$out" || { echo "[models] RETRY FAILED: $base"; rm -f "$out.part"; FAIL=1; }
      got2=$(sha256sum "$out" 2>/dev/null | awk '{print $1}')
      [ "${got2:-}" = "$sha" ] && echo "[models] sha256 OK after retry: $base" || { echo "[models] still bad: $base -- report upstream"; FAIL=1; }
    else
      FAIL=1
    fi
  fi
done < /tmp/_models.tsv
rm -f /tmp/_models.tsv

if [ "$FAIL" = 1 ]; then
  echo "[models] INCOMPLETE -- resolve the issues above, then re-run."
  exit 1
fi
echo "[models] all 4 present + sha256-verified. Next: 04_import_models.sh"
