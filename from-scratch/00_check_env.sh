#!/usr/bin/env bash
# 00_check_env.sh -- verify hardware + software prerequisites for the
# Local-LLMs-Forensics experiments. Run this FIRST on a fresh machine.
set -u
PASS=0; FAIL=0
ok()   { printf "  [OK]   %s\n" "$1"; PASS=$((PASS+1)); }
bad()  { printf "  [FAIL] %s -- %s\n" "$1" "$2"; FAIL=$((FAIL+1)); }
hdr()  { printf "\n== %s ==\n" "$1"; }

hdr "Hardware"
RAM_GB=$(awk '/MemTotal/ {printf "%d", $2/1024/1024}' /proc/meminfo 2>/dev/null || echo 0)
DISK_GB=$(df -BG "$HOME" | awk 'NR==2 {gsub("G","",$4); print $4}')
[ "$RAM_GB" -ge 16 ] && ok "RAM ${RAM_GB} GB (>=16 needed for 9B Q4_K_M)" || bad "RAM ${RAM_GB} GB" "need >=16 GB for Qwen3.5-9B; >=32 GB comfortable"
[ "$DISK_GB" -ge 40 ] && ok "Free disk ${DISK_GB} GB (>=40)" || bad "Free disk ${DISK_GB} GB" "4 models ~21 GB + Ollama copies ~21 GB + runs"

hdr "Core tools"
for t in python3 curl git tcpdump tshark ip iptables cmake tmux; do
  command -v "$t" >/dev/null 2>&1 && ok "$t ($(command -v $t))" || bad "$t" "install: see 02_install_prereqs.sh"
done
python3 -c "import json,urllib.request,subprocess" 2>/dev/null && ok "python3 stdlib OK" || bad "python3 stdlib" "check python3 install"
command -v sudo >/dev/null && ok "sudo present (netns/tcpdump need root)" || bad "sudo" "required for ip netns + iptables + tcpdump"
sudo -n true 2>/dev/null && ok "passwordless sudo" || echo "  [note] sudo will prompt; original harness used a cached .sudo-helper"

hdr "Runtimes under test"
LMS_BIN="${HOME}/.lmstudio/bin/lms"
[ -x "$LMS_BIN" ] && ok "LM Studio CLI at $LMS_BIN" || bad "LM Studio CLI" "install LM Studio (https://lmstudio.ai) + headless 'lms' CLI"
command -v ollama >/dev/null && ok "Ollama ($(ollama -v 2>/dev/null | head -1))" || bad "Ollama" "install: curl -fsSL https://ollama.com/install.sh | sh"

hdr "Models (checked later by 03_download_models.sh)"
for f in NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf \
         Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf \
         gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf \
         Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf; do
  p="${HOME}/.lmstudio/models/lmstudio-community/$f"
  [ -f "$p" ] && ok "$(basename "$f")" || echo "  [todo] missing: $f  (03_download_models.sh)"
done

printf "\n== RESULT: %d ok, %d fail ==\n" "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] && echo "Environment ready. Next: bash 01_layout.sh" || { echo "Fix FAILs above, then re-run."; exit 1; }
