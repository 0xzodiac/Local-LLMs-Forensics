# Experimental methodology master record

## Design principle

LLAnalyzer is not an accuracy benchmark. It uses boundary-specific workloads
with known canaries or malformed artifacts and measures whether the target
component preserves the intended confidentiality property. Each protocol keeps
the model, prompt sequence, inference parameters, and runtime configuration
fixed across the relevant comparison unless the experiment explicitly tests a
configuration change.

## Environment and software

The supplement records a dedicated bare-metal Ubuntu workstation for the
principal experiments:

- Intel Core i7-9850H CPU at 2.60 GHz;
- 16 GB system memory, approximately 15 GiB reported;
- CUDA-capable GPU with 8 GB VRAM;
- NVIDIA driver 595.84 and CUDA 12.0 (V12.0.140);
- ext4 filesystem;
- reported Python 3.14.6 and GDB 15.1.

The core runtime is `llama.cpp`/`llama-server`; LM Studio and Ollama are used
for wrapper measurements. Four GGUF model families are named in the
manuscript: Gemma, Qwen, Nemotron, and Phi-4. The retained model metadata is in
`Runs/provenance/model_digests.json`; model files and historical executable
hashes are not currently present.

The historical source identifier `388d39f3e` does not resolve. Commit
`721354fbdfb7743e2be2183d918a3cdb9276c70f` is a verified later engineering
candidate used by Remediation 2 and must not be relabeled as the historical
source.

## Canaries and controls

Each confidentiality trial generates a fresh UUID canary, verifies that it is
absent from the relevant pre-experiment evidence source, embeds it in a
controlled prompt, and records the originating request. An exact recovery is
scored in the boundary-specific output channel: process memory, wrapper file,
network artifact, protocol response, reasoning field, or another client's
continuation.

Controls include positive canary generation, clean server/process setup where
documented, baseline versus patched conditions, unmodified versus explicit
logging settings, and separate direct-transfer versus continuation outcomes.

## Statistical treatment

Binary outcomes use `p-hat = x/n` and two-sided 95% Wilson intervals. The
200/200 transfer estimate has Wilson interval approximately [0.9811547, 1.0].
The 126/200 continuation estimate is 0.63 with Wilson interval approximately
[0.5612263, 0.6938739]. These intervals describe observed trial proportions;
the trials remain subject to shared-server and sequential-dependence caveats.

Memory reductions use `100*(baseline - condition)/baseline`:

- copies: `100*(110-78)/110 = 29.090909%`;
- recorded matching-region KB: `100*(10834-3352)/10834 = 69.060366%`.

The KB field is retained recorded matching-region volume. It is not asserted to
be the exact number of secret bytes physically resident.

Patched/unpatched KV benchmark vectors contain 50 observations per model and
reproduce their stored descriptive means. The differences are small and their
descriptive normal/Welch intervals cross zero; this is not an equivalence test
and not the missing cached/uncached TTFT dataset used for the historical AUC.

## Protocol summaries

| Protocol | Core sequence | Primary output |
|---|---|---|
| GGUF integrity | mutate valid artifacts, run C++/Python loaders, fuzz with sanitizer instrumentation | loader status, crash/sanitizer outcome, campaign scale |
| Memory residue | launch server as child, submit canary prompts, release/session sequence, acquire writable memory | canary copies, recorded matching-region volume, tenant recovery |
| KV zeroisation | inspect targeted cells immediately before the zero write; compare benchmark conditions | 56/56 nonzero pre-zero cells; descriptive latency vectors |
| Wrapper persistence | submit canary prompts, inspect LM Studio/Ollama artifacts, change logging setting and restart | file canary presence/absence, telemetry, configuration scope |
| Saved slots | victim prompt, save state, second authenticated client restores state | direct transfer and model continuation separately |
| Timing | cached and uncached prefix requests under evaluated loopback/LAN setup | historical TTFT separation and AUC report |

## Reproducibility boundary

The local audit independently recomputed selected retained records but did not
recover the historical source checkout, binary hash, full acquisition metadata,
or timing vectors. Dr. Ikram's full rerun is author-reported and must be
presented as corroborating collaborative evidence until server-side records are
inspected. The complete provenance request is in
`remediation2b_historical_evidence/IKRAM_EVIDENCE_REQUEST.md`.

