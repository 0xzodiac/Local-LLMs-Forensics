# Continuation Plan — Close Remaining Gaps, Native Linux Environment

**Environment:** Ubuntu 24.04, native (host `zodiac`), NVIDIA Quadro RTX 4000 (`/dev/nvidia0` confirmed) — **not WSL2**. This unblocks the GPU-VRAM gap that was structurally impossible before.
**Execution model:** Heavy implementation work (scripts, harnesses, patches) is delegated to `opencode run -m opencode/big-pickle` to cut main-session effort. Claude (this session) retains orchestration, verification, and synthesis — every opencode deliverable gets reviewed before being trusted, same pattern as the original `OPENCODE_TASK.md` / `OPENCODE_RUN_REPORT.md` cross-check.
**Source of truth for what's missing:** `RESEARCH_PROGRESS_MASTER.md` §3 (gaps), §4 (must-retest), §6 (remaining stages).

---

## Stage 0 — Model Provenance Fix (BLOCKING, sequential, run first, not delegated)

Current LM Studio models on this box do **not** match the originals used in every prior report (Phi-4-mini 3B ≠ Phi-4-reasoning-plus 14.7B; Nemotron-Orchestrator-8B ≠ Nemotron-3-Nano-4B; Qwen2.5-7B ≠ Qwen3.5-9B; gemma4 present but wrong quant). Decision: pull the exact originals from each model's official publishing org where it exists.

**FINAL DECISION 2026-06-22 (user override, supersedes all gemma4 sourcing below):** gemma4 is **dropped from this re-run entirely** — "all gemma4 have same backend base ... contenue with remaining phi." This run covers 3 models only: qwen3.5-9b, nemotron-3-nano-4b, phi-4-reasoning-plus. The gemma4 bartowski/unsloth/lmstudio-community sourcing trail below is kept as a record of what was tried, not as a live task.

```bash
# 0.1 Remove mismatched models -- DONE 2026-06-22
lms unload --all
rm -rf "/home/elaref/.var/app/ai.lmstudio.lm-studio/.lmstudio/models/MaziyarPanahi/Nemotron-Orchestrator-8B-GGUF"
rm -rf "/home/elaref/.var/app/ai.lmstudio.lm-studio/.lmstudio/models/bartowski/microsoft_Phi-4-mini-instruct-GGUF"
rm -rf "/home/elaref/.var/app/ai.lmstudio.lm-studio/.lmstudio/models/bartowski/Qwen2.5-7B-Instruct-GGUF"
rm -rf "/home/elaref/.var/app/ai.lmstudio.lm-studio/.lmstudio/models/unsloth/gemma-4-E4B-it-GGUF"

# 0.2 Pull exact originals -- RESOLVED SOURCES (after 3 wrong attempts, see feedback_model_provenance.md):
#   - bartowski has NO gemma-4-E4B-it quant at all (real resolve error, not a guess)
#   - unsloth has it, but lms's "-y" auto-picked the mmproj+MTP-draft files, not the main weights
#   - CORRECT source, confirmed via an old project Modelfile: lmstudio-community/gemma-4-E4B-it-GGUF
#   - lms's short-name resolution failed for bartowski/unsloth; the full HF URL + a direct curl of the
#     exact filename was what actually worked. Use this exact sequence, not lms get --select (interactive,
#     doesn't work headless) and not lms get with -y on a multi-file repo (picks the wrong file silently).
lms get "qwen/qwen3.5-9b@q4_k_m" --gguf -y                    # DONE -- 6.55GB, arch qwen35, matches original
lms get "nvidia/nemotron-3-nano-4b@q4_k_m" --gguf -y          # DONE -- 2.84GB, arch nemotron_h, matches original
lms get "microsoft/phi-4-reasoning-plus@q4_k_m" --gguf -y     # DONE -- 9.05GB

mkdir -p "/home/elaref/.var/app/ai.lmstudio.lm-studio/.lmstudio/models/lmstudio-community/gemma-4-E4B-it-GGUF"
curl -L --retry 5 --retry-delay 5 -C - \
  -o "/home/elaref/.var/app/ai.lmstudio.lm-studio/.lmstudio/models/lmstudio-community/gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf" \
  "https://huggingface.co/lmstudio-community/gemma-4-E4B-it-GGUF/resolve/main/gemma-4-E4B-it-Q4_K_M.gguf"   # DONE -- 5.08GB

lms ls   # verify 3 models, correct param counts (9B / 4B / 14.7B) -- gemma4 deliberately excluded
```

**Verification step — DONE 2026-06-22, done directly (not delegated, trivial script):**

`scripts/verify_model_provenance.py` (gguf-py via local `.venv`) confirmed all 3 against `RESEARCH_DOCUMENTATION.md`'s baseline table, exact match on every field:

```
qwen35: tensors=427 (expected 427) arch=qwen35 -> OK
nemotron: tensors=263 (expected 263) arch=nemotron_h -> OK
phi4: tensors=243 (expected 243) arch=phi3 -> OK
```

Stage 0 is now fully complete. gemma4's original baseline (720 tensors) is moot for this run.

---

## Stage 1 — Rebuild Environment (parallel with Stage 0 tail; blocks Track A retests)

`llama-monitor/` (built llama.cpp + eBPF probes) does not exist on this host — only the git-tracked `scripts/` survived. `cuda-gdb` is not installed.

```bash
# 1.1 Direct, not delegated -- trivial apt work
sudo apt update && sudo apt install -y build-essential cmake git wireshark-common dumpcap \
  bpftrace linux-tools-common python3 python3-pip python3-venv clang llvm curl wget \
  nvidia-cuda-toolkit cuda-gdb nvtop

nvidia-smi -L   # confirm GPU visible
cuda-gdb --version
```

```bash
# 1.2 Delegate the llama.cpp rebuild (rote, reproducible from the original reproducibility guide)
opencode run -m opencode/big-pickle --dir /home/elaref/research "Recreate llama-monitor/ exactly per RESEARCH_DOCUMENTATION.md section 12.2: clone llama.cpp into llama-monitor/build/llama.cpp-src, build TWO variants -- (a) CPU-only (LLAMA_GPU_LAYERS=0 equivalent, matching the original CPU baseline), and (b) CUDA-enabled (this box has a real Quadro RTX 4000, unlike the original WSL2 CPU-only run) into llama-monitor/build/llama.cpp-cuda/bin/llama-server. Recreate scripts/build-llama-cpp.sh, scripts/start-llama-server.sh, scripts/stop-llama-server.sh matching the original interface (same env vars: LLAMA_GPU_LAYERS, LLAMA_HOST, LLAMA_PORT, SUDO_PASS). Do not modify any existing script in scripts/. Write a short BUILD_REPORT.md documenting both binary paths and a smoke-test (load phi-4-reasoning-plus, one /health check, one trivial completion) for each variant."
```

---

## Stage 2 — Parallel Gap-Closure Tracks

Each track below is independent — run concurrently once Stage 0+1 finish. Every opencode deliverable gets reviewed/cross-checked by this session before being cited as a finding (same discipline as the original project: two contamination bugs were caught exactly this way).

### Track A — GPU VRAM Cleartext Scan (previously BLOCKED, now unblockable)

```bash
opencode run -m opencode/big-pickle --dir /home/elaref/research "Implement the VRAM-exposure probe described in GPU_VRAM_REPORT.md's 'Recommended Toolchain for Bare-Metal Linux' section, adapted to this box's Quadro RTX 4000 + cuda-gdb (now installed). Build scripts/vram_leak_probe.py: (1) launch llama-monitor/build/llama.cpp-cuda/bin/llama-server with --n-gpu-layers > 0 for each of the 4 models (one at a time), (2) send one request with a fresh 32-hex canary (same methodology as scripts/deep_leak_probe.py), (3) use cuda-gdb attach <pid> -> 'info cuda device 0 memory' to enumerate allocations, dump each allocation's bytes, grep for the canary, (4) repeat with a 2nd unrelated request to test persistence, matching DEEP_LEAK_REPORT.md's methodology exactly but for VRAM instead of process RAM. Write results to logs/vram_leak_results.csv (model, canary_copies_found, regions, persists_after_2nd_request) and GPU_VRAM_LEAK_REPORT.md modeled on DEEP_LEAK_REPORT.md's structure. If cuda-gdb cannot attach without sudo, document the exact permission needed (ptrace_scope, cap_sys_ptrace) rather than silently using sudo."
```

### Track B — Phi-4 Reasoning-Defense Resolution (currently contradicts itself across 3 reports)

```bash
opencode run -m opencode/big-pickle --dir /home/elaref/research "Resolve the Phi-4-reasoning-plus direct-repeat leak-rate discrepancy (0/2 in PHI4_DEFENSE_NEW.md via LM Studio API, 1/3 in GAP_ANALYSIS_REPORT.md via raw llama.cpp, 2/2 in an earlier FINAL_COMPREHENSIVE_REPORT.md pass). This box has more headroom than the original (4GB VRAM laptop GPU, WSL2 RAM pressure) -- use the freshly pulled phi-4-reasoning-plus@Q4_K_M and the CUDA-enabled llama-server build from Stage 1. Run scripts/phase2-adversarial-harness.py's direct-repeat + role-manipulation prompt set 20 times each (not 2-3) at a fixed temperature, GPU-offloaded. Report leak rate with a 95% confidence interval, latency distribution, and reasoning_content length per trial. Write PHI4_DEFENSE_RESOLVED_REPORT.md stating plainly whether the ~150-token reasoning-defense is real, environment-fragile, or never existed, citing the n=20 data."
```

### Track C — Agentic Wrapper Leak Test Retry (previously inconclusive, not negative)

```bash
opencode run -m opencode/big-pickle --dir /home/elaref/research "Retry the Claude-Code-to-local-backend test from AGENTIC_WRAPPER_LEAK_REPORT.md on this box (real GPU, more RAM headroom than the original 4GB-VRAM laptop -- the LM Studio worker wedge may not reproduce here). Fix the methodological trap already identified in that report: source the canary from INSIDE the spawned claude -p subprocess's own session directory (~/.claude/projects/.../*.jsonl), not from the orchestrating shell's Bash argument. Test against the freshly-pulled, GPU-offloaded models. If the request completes (unlike the original), run scripts/agentic_log_scanner.py against the correct isolated session directory to get a clean leak/no-leak answer to the original unresolved question. Write AGENTIC_WRAPPER_RESOLVED_REPORT.md with a definitive verdict, or document precisely why it's still blocked if the wedge reproduces."
```

### Track D — Memorization Volume Quantification (currently flagged as future work)

```bash
opencode run -m opencode/big-pickle --dir /home/elaref/research "Extend scripts/memorization_volume.py to quantify exact memorized-corpus fraction per model, not just verbatim-depth-on-5-works. Use the freshly-pulled original 4 models. For each model: (1) run the existing 5-work battery with 5 different random seeds/temperatures to get variance bars on the 'X/Y words verbatim' numbers instead of single-pass figures, (2) expand the canonical-text set to at least 15 works spanning public-domain, copyrighted-fiction, copyrighted-software-license, and song-lyric categories, keeping the RFC-1149 negative control. Write logs/memorization_volume_v2.json and MEMORIZATION_VOLUME_REPORT.md with per-model, per-category extraction rates and confidence intervals -- replacing the single-pass 'phi4 128/208 (61.5%)' style headline numbers with rigorous ones."
```

### Track E — KV-Cache Zeroization Patch + Benchmark (currently zero implementation)

```bash
opencode run -m opencode/big-pickle --dir /home/elaref/research "Implement a minimal KV-cache zeroization patch against the llama.cpp checkout in llama-monitor/build/llama.cpp-src (from Stage 1), per the mitigation table in DEEP_LEAK_REPORT.md: memset the KV-cache buffer and token buffer to zero on slot release (look at llama_kv_cache_clear / slot-reuse path in llama-server's slot management code, NOT a full rewrite). Build a before/after benchmark: (1) confirm scripts/deep_leak_probe.py finds 0 canary copies in RAM after slot release with the patch applied (currently finds 11-42), (2) measure throughput/latency overhead of the memset on the same Phase-1 250-iteration baseline methodology. Write a patch diff file (patches/kv_cache_zeroize.patch) and KV_CACHE_PATCH_REPORT.md with before/after leak counts and the measured performance cost. This is the single highest-value remaining deliverable -- it converts 'we found a critical hole' into 'we found a critical hole and a working, benchmarked fix.'"
```

### Track F — Must-Retest Batch (the 5 items from RESEARCH_PROGRESS_MASTER.md §4)

```bash
opencode run -m opencode/big-pickle --dir /home/elaref/research "Run the must-retest batch from RESEARCH_PROGRESS_MASTER.md section 4 against the freshly-pulled original models on this box (gemma4 excluded from this run per final user decision -- item (1), gemma4 swa_rope re-confirm, is therefore SKIPPED/N-A, not retested): (2) DEEP_LEAK persistence for phi4 with a longer timeout (300s not 180s) so all 3 remaining models get symmetric 2nd-request persistence data; (3) context-overflow test with --ctx-size properly sized per-model tokenizer (fix the config-error exclusion in PHASE2_CROSS_MODEL_REPORT.md) so a real overflow result isn't hiding behind a config artifact; (4) and (5) are covered by Tracks B and D above (Phi-4 leak-rate variance, memorization-volume variance) -- skip here to avoid duplicate work. Write MUST_RETEST_RESULTS.md with one section per item, explicitly stating whether each prior claim is CONFIRMED, REVISED, RETRACTED, or N/A (gemma4-dropped) with the new data."
```

### Track G — One More Wrapper for Comparison Breadth

```bash
opencode run -m opencode/big-pickle --dir /home/elaref/research "Add Jan (janhq/jan) as a 3rd wrapper comparison point alongside LM Studio and Ollama, using the exact same canary methodology as OLLAMA_FORENSICS_REPORT.md (UUIDv4 canary, recursive grep with sudo across all plausible disk paths, check for a logSensitiveData-equivalent setting). Install via the simplest available method (AppImage or flatpak, whichever is less invasive), load one of the freshly-pulled original models, run 10 benign + 10 adversarial requests, then forensically check for disk persistence. Write JAN_FORENSICS_REPORT.md in the same structure as OLLAMA_FORENSICS_REPORT.md so it slots directly into the paper's wrapper-comparison table."
```

### Track H — SGLang Weaponized-GGUF RCE Reproduction (NEW, found 2026-06-22, highest-value new track)

`LATEST_INTEL_2026-06-22.md` §1 surfaced **CVE-2026-5760** (CVSS 9.8) -- a crafted GGUF file achieves full RCE against SGLang, not just memory disclosure. This is the strongest available evidence that the attack surface is the file format itself, independent of runtime, and we have never tested SGLang. If reproducible, this becomes the paper's lead "the file format is the threat, not any one runtime" argument.

```bash
opencode run -m opencode/big-pickle --dir /home/elaref/research "Investigate and, if safely reproducible in an isolated environment, demonstrate CVE-2026-5760 (CVSS 9.8, GGUF-weaponization RCE against SGLang) per LATEST_INTEL_2026-06-22.md section 1. First: fetch and read the primary advisory/CVE record (search NVD and GitHub Security Advisories for sgl-project/sglang) to get the exact vulnerable code path and the GGUF field(s) involved -- do not attempt exploitation from secondary blog summaries alone. Install SGLang in an isolated venv/container, confirm the vulnerable version is in scope, then adapt scripts/gguf-tensor-attacks.py / gguf-chained-attacks.py's mmap-patch primitives (do not rewrite from scratch) to construct the documented trigger condition against one of the freshly-pulled original models as the base file. If the advisory's patched version is what's installed, document that the fix is already in place rather than forcing exploitation. Write SGLANG_RCE_REPRODUCTION_REPORT.md stating clearly: reproduced / not reproduced (patched) / inconclusive, with exact versions and the precise field manipulation used. This is a higher-severity vulnerability class (RCE) than anything in our own taxonomy (which only found assertion-failure DoS) -- treat reproduction carefully and do not run the resulting payload against anything network-reachable."
```

---

## Stage 3 — Responsible Disclosure (sequential, NOT delegated — judgment call, not implementation)

- [ ] Check whether LM Studio's `logSensitiveData: true` default has any existing tracked advisory/CVE. If not, draft a disclosure note to LM Studio (security contact via their GitHub) — this is a real, exploitable default affecting any user processing sensitive data, independent of model choice.
- [ ] Confirm CVE-2026-7482 ("Bleeding Llama") disclosure/patch timeline is fully elapsed before citing it as "live, in the wild" without caveat — verify current Ollama version ships the fix. **Now fully documented per `LATEST_INTEL_2026-06-22.md` §8: patched in Ollama v0.17.1 (2026-02-25) without being flagged as a security fix; MITRE took 2 months to assign the CVE; ~3-month gap between patch and public CVE awareness.** Use this timeline as the cautionary precedent when planning our own disclosure for the LM Studio logging default and any Track E patch — don't assume "we published a report" closes the loop the way a tracked CVE with a clear patch-to-disclosure timeline would.
- [ ] If Track E's zeroization patch is novel (no existing upstream fix for this exact slot-release gap), consider whether it should be submitted upstream to llama.cpp/ggml-org rather than only published in the paper.
- [ ] If Track H reproduces CVE-2026-5760 against an unpatched SGLang version, this is already a publicly disclosed/CVSS-scored CVE -- no original disclosure needed, but verify the installed version is patched before any demo and never run the reproduction against a network-reachable instance.

## Stage 4 — Paper Drafting (sequential, largest remaining block; Claude-led, opencode assists with reconciliation)

```bash
opencode run -m opencode/big-pickle --dir /home/elaref/research "Build one reconciled numbers table across all reports: for every headline statistic that appears more than once with slightly different values (leak rates, memorization depth, canary-copy counts), list every occurrence with its source file/line and the run conditions (model version, max_tokens, temperature, sample size). Output as RECONCILED_NUMBERS.md, one table per claim, flagging which occurrence should be treated as canonical (prefer largest sample size / most recent / most controlled run) and which should be superseded. Do not pick a canonical value yourself if two runs used genuinely different conditions -- flag those as 'not directly comparable, report both with conditions' instead."
```

- [ ] Claude (this session): convert `PAPER1_OUTLINE.md` + `MASTER_FORENSICS_DOCUMENTATION.md` + `FINAL_COMPREHENSIVE_REPORT.md` + `RECONCILED_NUMBERS.md` + all Stage-2 new reports into one continuous prose draft, venue LaTeX template (USENIX/S&P/NDSS — pick after checking current CFP deadlines).
- [ ] Promote Finding 5 (training-data memorization) to a 4th main contribution per `FINAL_STATUS_REPORT.md`'s own recommendation.
- [ ] Lead with Finding 1 (KV-cache exposure) + Track E's patch as the strongest single contribution (bug + fix + benchmark).
- [ ] Write Limitations section honestly: originally single-hardware/WSL2 findings now partially re-verified on real hardware (note which ones), still single-machine overall.

## Stage 5 — Pre-Submission Verification + Packaging

```bash
opencode run -m opencode/big-pickle --dir /home/elaref/research "Spot-check every secondary citation in PAPER1_OUTLINE.md's reference list not already verified live in FINAL_STATUS_REPORT.md section 3 (HiddenLayer malware-repo claim, OpenDoors exposed-server count, individual older 2024 CVE entries, Pillar Security poisoned-template claim), PLUS the new items from LATEST_INTEL_2026-06-22.md: (1) verify the actual current title of arXiv 2602.24210 -- our outline cites it as 'From Leaky Thoughts to Private Reasoning' (Batra et al.) but a web sweep found the same arXiv ID titled 'Controllable Reasoning Models Are Private Thinkers', resolve which is correct; (2) verify CVE-2026-5760 (SGLang RCE, CVSS 9.8) and CVE-2026-42248/42249 (Ollama updater RCE) against their primary NVD/GHSA advisories before citing exact CVSS scores or dates; (3) verify arXiv 2505.12546, 2510.18554, 2603.10726, 2511.07772, 2601.05076, 2601.17548 actually exist and match the claims attributed to them in LATEST_INTEL_2026-06-22.md. For each, fetch the source and confirm the claim as described is accurate; flag anything that doesn't check out. Write CITATION_AUDIT.md with a verified/unverified/incorrect status per citation."
```

- [ ] Package `scripts/` + representative `logs/` + patch diff into an anonymized reproducibility bundle.
- [ ] Final read-through for any "unresolved" rounded up to "resolved" language.

---

## Parallel Execution Notes

- Stage 0 is strictly sequential and blocking — every later retest is invalid if run against the wrong models.
- Stage 1.1 (apt installs) and Stage 1.2 (opencode llama.cpp rebuild) can run in parallel.
- All of Stage 2's Tracks A–H are mutually independent in file scope, but **NOT in hardware scope** — this box has a single Quadro RTX 4000 (8GB VRAM) and 15GB system RAM, a workstation, not a server. **Revised 2026-06-22: tracks that load GGUF models (A, B, D, F, G, H) run SEQUENTIALLY, one opencode job at a time**, not concurrently as originally planned -- 4 simultaneous model-loading harnesses were launched and killed early (before VRAM contention hit) once this was noticed. Each track still gets its own opencode delegation; just queue them, don't fire all at once. Track H (SGLang) is the highest-value new addition (2026-06-22) -- if time is constrained, prioritize it alongside Track E (zeroization patch) over the must-retest batch (Track F).
- Stage 3 (disclosure) can start as soon as the relevant Stage-2 track (E for the patch, none specifically for the LM Studio default since that's already fully characterized) finishes — no need to wait for all of Stage 2.
- Stage 4 cannot meaningfully start until Stages 2 and 3 are at least mostly resolved (the paper needs the reconciled numbers and the disclosure status).
- Every `opencode run` output is a draft — review its report + diff before treating any new number as a finding, same discipline that caught the two contamination bugs in the original run.
