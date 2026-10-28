# RQ2 dossier: runtime memory lifetime

## 1. Research question

Does runtime memory preserve prompt confidentiality after inference, or does
prompt plaintext remain recoverable beyond execution completion and logical
state release?

## 2. Security hypothesis

Prompt processing creates multiple representations: request JSON, formatted
chat templates, token and text buffers, response strings, slot metadata, and
KV-cache tensors. C++ object destruction or slot release may remove bookkeeping
without overwriting the underlying bytes. A prompt can therefore outlive the
request from the application's perspective.

## 3. Evaluated software, models, and environment

The core runtime is `llama-server`/`llama.cpp`; the manuscript evaluates four
model families, and the memory reports contain model-specific and aggregate
experiments. The supplement describes a bare-metal Ubuntu workstation with an
Intel Core i7-9850H, 16 GB RAM, an 8 GB CUDA-capable GPU, and native Ubuntu for
headline measurements. Early WSL2 work is not silently pooled with the native
headline results.

The collector is a research-authorized process, usually the parent of the
serving process. It reads writable regions listed by `/proc/<pid>/maps` through
`/proc/<pid>/mem` under the reported Linux/Yama conditions. This establishes F's
conditional forensic recoverability, not arbitrary A1 same-UID access.

## 4. Canary workload and sequence

Each client/trial receives a fresh UUID canary. The harness checks that the
canary is absent from the pre-run evidence source, embeds it in the controlled
prompt, runs inference, releases or advances session state, and acquires the
documented writable regions. An exact canary match is attributed to the
originating request.

The sequential-tenant experiment uses twelve logical clients in one long-lived
server. The acquisition occurs after the sequence, so it tests historical
residue rather than only the immediately preceding prompt.

## 5. Subquestions and instruments

### RQ2.1: post-inference plaintext

The collector counts exact canary matches and associates them with tenants. The
retained aggregate records report recovery from 11 of 12 tenants in baseline
and sanitised conditions.

### RQ2.2: persistence mechanism

Source inspection and probes distinguish ordinary heap-string/request-response
copies from KV-cache tensor state. The literal canary is not expected inside
floating-point KV tensors after tokenisation. This distinction is essential:
the literal-canary memory scan can continue to find string buffers even when KV
cell bytes are zeroised.

### RQ2.3: mitigation

The historical comparison contrasts baseline and a sanitised condition. The
retained records report the aggregate changes below. The historical source,
binary, startup manifest, and valid prompt patch are incomplete, so numerical
agreement is not treated as causal attribution to a fully identified historical
binary.

### RQ2.4: GPU-assisted execution

The evaluation examines host-side persistence under partial CUDA offload for
the documented configuration. It does not establish behavior for full offload,
all GPU backends, or device-memory access by an unprivileged process. `cuda-gdb`
denials and host-side parent-child scans are separate evidence classes.

## 6. Canonical recorded comparison

| Metric | Baseline | Sanitised | Interpretation |
|---|---:|---:|---|
| Recovered historical clients | 11/12 | 11/12 | Tenant-level recovery outcome unchanged |
| Canary copies | 110 | 78 | Recorded copy count reduced 29.090909% |
| Recorded matching-region volume | 10,834 KB | 3,352 KB | Recorded metric reduced 69.060366% |

The `KB` field is a recorded aggregate associated with matching regions in the
retained JSON. It is not silently relabeled as literal secret-byte volume, total
resident memory, or a physical-page measurement.

The two primary records are:

- `Runs/logs/leak_blast_radius_20260623_213831.json`;
- `Runs/logs/leak_blast_radius_20260624_120421.json`.

The existing independent reanalysis verifies their stored arithmetic, maps, and
recovery rates. It cannot reconstruct raw regions, offsets, acquisition trace,
or causal patch attribution.

## 7. KV-cache zeroisation and latency

The retained `KV_CACHE_PATCH_REPORT.md` documents direct instrumentation in
which 56/56 targeted cells contained nonzero data immediately before the zero
write. That is mechanism evidence for the patch's targeted KV tensor path. It
does not prove that the historical prompt-zeroisation patch caused the aggregate
110-to-78 result.

The retained patched/unpatched latency vectors have n=50 per model and support
descriptive means. They are not the cached-versus-uncached TTFT vectors used for
the manuscript's AUC claim.

## 8. Reproducibility status

Status: **E1 for selected aggregate arithmetic; E2 for retained structured
observations; E4/E5 boundary for historical causal attribution.** Remediation 2
verified a new pinned prompt-zeroisation implementation and buffer controls but
did not run a model-backed forensic campaign. Dr. Ikram's complete rerun is
reported as a matching cross-machine result; its memory acquisition records were
not found locally.

## 9. Publication-ready interpretation

> Under the authorized forensic acquisition path used here, prompt canaries
> remained recoverable from the long-lived serving process after inference. The
> evaluated sanitisation reduced recorded matching-copy and matching-region
> metrics but did not change the number of historical tenants from which a
> canary was recovered. This is evidence of residual lifetime exposure and a
> bounded mitigation effect, not proof of arbitrary same-UID access, complete
> erasure, or universal confidentiality restoration.

