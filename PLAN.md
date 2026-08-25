# Unified Project Plan — LLM Security Research (GGUF + ACTS-RAG)

## Context

This project has two tracks under one roof (`/home/sharks/research`):

- **Track A — GGUF model-file security.** Can a malicious `.gguf` crash or corrupt
  `llama.cpp`? Phases 1–2 + weight analysis + four fuzzing deep-dives are **done**:
  180+32 tests, 9 assertion crashes (SIGABRT), **zero memory corruption (SIGSEGV)**.
  The parser is memory-safe under all inputs tried; the only unguarded field
  (`rope.dimension_count_swa`) reaches an assertion, not a bypass.

- **Track B — Phase 3: ACTS-RAG (NEW, by MKh).** A different question: does
  retrieval-augmented cryptographic knowledge improve an LLM's ability to *identify*
  a cipher from ciphertext-only input? Built **on top of** the existing
  `github.com/youseefhamdi/ACTS-Benchmark` (ESWA reproducibility package: 840
  ciphertext files, tiers, classical-ML baseline). The honest framing (and the only
  publishable one) is: RAG may improve *classification/calibration*, but must **not**
  claim to break encryption.

**Decisions locked:** continue from the existing ACTS-Benchmark repo · evaluate
**local models only** (free, offline, reproducible — ollama `deepseek-r1`, `gemma4`,
opencode) · this is a **unified whole-project** doc.

Legend: `- [x]` done · `- [ ]` remaining.

---

## Track A — GGUF Model Security  *(COMPLETE)*

- [x] **Phase 1 — Baseline telemetry** (`scripts/phase1-auto-harness.py`, 250 iters) → `PHASE1_FULL_REPORT.md`
- [x] **Phase 2 — Adversarial prompt injection** (8 vectors, all resisted) → `PHASE2_ADVERSARIAL_REPORT.md`
- [x] **Weight backdoor analysis** (`scripts/weight-backdoor-analysis.py`) — 6 quantization artifacts, no backdoor
- [x] **GGUF fuzzing — surgical / novel / chained** (`gguf-fuzzer.py`, `gguf-novel-attacks.py`, `gguf-chained-attacks.py`) → `GGUF_SURGICAL_REPORT.md`, `GGUF_NOVEL_ATTACKS_REPORT.md`, `GGUF_CROSS_MODEL_REPORT.md` — 9 SIGABRT, 0 SIGSEGV
- [x] **Tensor-field attack pass** (`scripts/gguf-tensor-attacks.py`, 32 tests, 4 models) → `GGUF_TENSOR_REPORT.md` — tensor-info is the best-guarded surface; all rejected `exit(1)`
- [ ] **Resolve gemma4 `swa_rope` determinism (open).** big-pickle's report logged a SIGABRT (`ggml-cpu/ops.cpp:5856: GGML_ASSERT(n_dims <= ne0)`) and called it non-deterministic, but that run was contaminated by a leftover `llama-server` (negative elapsed time); the clean re-run returned `OK`. *Task:* one isolated re-test of gemma4 `swa_rope` with a guaranteed-clean port to confirm artifact vs. real intermittent crash. Update the report's conclusion accordingly.

## Session Infrastructure  *(COMPLETE)*

- [x] Copy WSL `~/.claude/skills/*` → Windows `C:\Users\w.i\.claude\skills\`
- [x] Author `/opencode` delegation skill (`skills/opencode/SKILL.md`)
- [x] Run tensor task through opencode `big-pickle` (cross-checked my results; independently caught + corrected the leftover-server artifact)

---

## Track B — Phase 3: ACTS-RAG  *(NEW — all remaining)*

**Naming fix:** the repo already defines **Tier 6 = classical ML**. The docx's
"Tier-6: Knowledge Retrieval Stress Test" collides — call it **Tier-7** throughout.

**Core comparison:** every existing ACTS tier gets two conditions —
**A: no retrieval** (existing behavior) and **B: RAG** (model is handed relevant
crypto references before answering). Headline metric is **KUG = Accuracy_RAG − Accuracy_Base**.

### P3.0 — Setup & grounding
- [ ] Clone `github.com/youseefhamdi/ACTS-Benchmark` into `research/acts/` and reproduce its Tier-3 (blind LLM, 25.0%) and Tier-6 (RandomForest, 61.6%) baselines locally to confirm the harness runs. *(Reuse: `run_expanded_tier5.py`, `run_expanded_tier6.py`, `final_validation.py`.)*
- [ ] Point its model worker at a **local** backend. Identify which `worker_*_v2b.py` is the inference runner and add a local-ollama / opencode endpoint (OpenAI-compatible `http://localhost:11434/v1`). No cloud keys.

### P3.1 — CryptoRAG corpus
- [ ] Build a small retrieval corpus `research/acts/cryptorag/` from public crypto references: AES (FIPS-197), NIST SP 800-38 modes, ChaCha20/RSA/ML-KEM specs, PKCS#7 / ANSI X9.23 / ISO 10126 padding notes, entropy/fingerprint cheatsheets.
- [ ] Index it. *Ladder check first:* start with the **simplest retriever that works** — keyword/BM25 over chunked markdown (stdlib + `rank_bm25` or sqlite FTS5), **not** a vector DB. Add embeddings only if BM25 measurably underperforms. `# ponytail: BM25 first, vectors only if recall is the bottleneck`.

### P3.2 — Condition B (RAG) runner
- [ ] Wrap the local worker so that, per ciphertext sample, it retrieves top-k crypto refs and prepends them to the prompt. Keep Condition A (no retrieval) as the untouched baseline path — one flag switches them.
- [ ] Log per-query: #retrievals, retrieved doc ids, final classification, reasoning. (Feeds Tier-7 + RQ4.)

### P3.3 — Tier-7: Knowledge Retrieval Stress Test
- [ ] Ciphertext-only, model **may query** the CryptoRAG corpus on demand (agentic). Measure retrieval count, retrieval quality, final accuracy, reasoning consistency — isolates whether retrieval is actually *used* vs. ignored.

### P3.4 — Metrics & research questions
- [ ] Implement **KUG** and the **metadata gap** (Tier1−Tier3) for both ACTS and ACTS-RAG. *(Extend `statistical_analysis.py`.)*
- [ ] Answer the RQs from the artifacts: **RQ1** RAG vs base accuracy/F1/calibration · **RQ2** RAG reduces metadata dependency? · **RQ3** retrieval helps bigger local models more? · **RQ4** does RAG reduce confabulation (confident-wrong, fabricated properties)?

### P3.5 — Write-up
- [ ] `ACTS_RAG_REPORT.md`: KUG table per tier/model, RQ findings, and the honest bound — *retrieval improves explanation/calibration/marginal classification; it does not overcome ciphertext-only information limits; metadata stays dominant.*

---

## Critical files

| Path | Role |
|------|------|
| `research/acts/` (to be cloned) | ACTS-Benchmark harness + 840 ciphertext `.bin` |
| `research/acts/worker_*_v2b.py` | model inference runner — **add local backend here** |
| `research/acts/run_expanded_tier{5,6}.py`, `statistical_analysis.py` | reused baseline + metrics |
| `research/acts/cryptorag/` (new) | RAG corpus + index |
| `scripts/gguf-tensor-attacks.py` | Track A harness (done; one open retest) |

## Verification

- **Track A close-out:** `python3 scripts/gguf-tensor-attacks.py --models gemma4` on a clean port; confirm `swa_rope` result is stable; finalize `GGUF_TENSOR_REPORT.md`.
- **Phase 3 sanity gate:** reproduced ACTS Tier-3 ≈ 25% and Tier-6 RF ≈ 61.6% locally **before** adding RAG (proves the harness works unmodified).
- **Phase 3 result gate:** KUG computed per tier×model on local models; a small positive KUG on classification with larger gains on calibration/confabulation = expected, publishable outcome. Any claim of key/plaintext recovery = red flag, must not appear.
- **Cost gate:** all model calls hit `localhost` — no external API spend.
