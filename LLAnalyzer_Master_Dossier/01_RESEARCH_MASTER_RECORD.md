# Research master record

## Working title and question

**Title:** *The Illusion of Local Privacy: Confidentiality Boundary Failures in
Consumer LLM Serving Systems*

The paper asks whether keeping inference on a user's machine is sufficient to
protect prompt confidentiality once the entire serving lifecycle is considered.
The answer is no in the evaluated configurations: locality removes a cloud
provider from the immediate computation path, but prompt data can still be
copied, retained, persisted, shared through serving state, or exposed through a
timing signal.

## Central argument

“Local” describes the location of computation. It does not by itself specify:

- whether model artifacts are admitted safely;
- how many prompt-bearing representations are created in runtime memory;
- whether released objects are physically overwritten;
- whether wrappers write requests or responses to disk;
- whether shared serving state has resource-level ownership; or
- whether cache reuse creates an observable signal.

LLAnalyzer makes these decisions visible by measuring four boundaries rather
than treating the whole local stack as a single trusted component.

## Four-boundary contribution

| Boundary | Security question | Main instrument | Principal result |
|---|---|---|---|
| B1, model-artifact integrity | Can malformed GGUF inputs bypass validation or trigger relevant memory-safety failures before inference? | Structured mutations, GGUF tooling, coverage-guided fuzzing, sanitizer instrumentation | No relevant failure observed in the reported explored state space; the claim is bounded, not universal |
| B2, runtime memory lifetime | Does prompt plaintext remain recoverable after inference and logical release? | UUID canaries, authorized parent-child `/proc` acquisition, heap/KV probes, mitigation comparisons | 11/12 sequential logical clients remained recoverable; sanitisation reduced recorded exposure but not tenant-level recovery |
| B3, wrapper-managed persistence | Do consumer applications retain prompt material in files or transmit it externally? | Canary-bearing requests, file inspection, configuration changes, network telemetry | LM Studio persistence is configuration-specific; 205 bounded Ollama monitoring sessions yielded no captured canary egress |
| B4, shared-state isolation | Can an authenticated client access another client's saved state or infer prior prompt processing? | Shared `llama-server`, saved-slot transfers, continuation scoring, TTFT timing record | 200/200 direct transfers, 126/200 model continuations; AUC=1.000 remains historical |

## Canonical retained results

| Result | Value | Evidence status | Interpretation |
|---|---:|---|---|
| Structured GGUF battery | 80 cases | Historical/source-supported | Bounded corpus result; no universal parser guarantee |
| Structural-header corpus | 21 files | Historical/source-supported | Inputs and full per-file raw chain are not retained in the local audit |
| Coverage-guided campaign | >1.2e7 executions / 24 h | Historical report | No observed failure in explored state space; campaign manifest is incomplete |
| Baseline recovered tenants | 11/12 | Raw-record-backed aggregate | Under authorized forensic acquisition and the recorded configuration |
| Baseline canary copies | 110 | Raw-record-backed aggregate | Matching copies in retained recorded fields |
| Sanitised canary copies | 78 | Raw-record-backed aggregate | 29.090909% reduction from recorded baseline |
| Baseline recorded matching-region KB | 10,834 | Raw-record-backed aggregate | Recorded matching-region metric, not literal secret-byte volume |
| Sanitised recorded matching-region KB | 3,352 | Raw-record-backed aggregate | 69.060366% reduction in the recorded metric |
| Tenant recovery after sanitisation | 11/12 | Raw-record-backed aggregate | Tenant-level outcome unchanged |
| KV cells with nonzero pre-zero data | 56/56 | Mechanism-level retained report | Direct patch instrumentation; not the historical memory reduction result |
| KV overhead benchmark | n=50/model | Raw-vector-backed descriptive result | Patched-minus-unpatched means cross zero descriptively; not the missing timing AUC data |
| LM Studio persistence | canary recovered with sensitive logging enabled | Configuration-specific historical report | Do not call it a clean-install default |
| Ollama monitoring | 205 valid sessions | Retained bounded telemetry | No captured canary in monitored egress/artifacts; not every channel/version |
| Direct saved-slot transfers | 200/200 | Raw-record-backed calculation | Protocol-level transfer under shared-server configuration |
| Model continuations | 126/200 | Raw-record-backed calculation | Gemma 50/50, Qwen 50/50, Nemotron 25/50, Phi 1/50 |
| Timing discrimination | AUC=1.000 | Historical report | Cached/uncached TTFT vectors and original AUC script unavailable locally |

## Replication history

Three histories must remain separate in the rewrite:

1. **Primary execution:** the original LLAnalyzer experiments and retained local
   artifacts.
2. **Author-reported collaborative rerun:** Dr. Mohammed Ikram reportedly
   reran the complete framework on a separate research server and obtained
   matching results. The server-side artifacts were not found locally.
3. **Independent audit/recomputation:** the current workspace audit recomputed
   selected original arithmetic from retained records. This is not the Ikram
   rerun and not a third-party experimental reproduction.

P. K. Sharma's article is a secondary technical review that checked arithmetic,
documentation, source, policy, and limitations. The Korean discussion is a
secondary summary. Neither is experimental replication.

## What the paper can claim

The defensible thesis is a lifecycle-wide measurement result: across four
boundaries, confidentiality properties differ sharply. The paper can preserve
the complete contribution and report the collaborator's cross-machine rerun as
corroborating author-reported evidence. It must not convert that statement into
uninspected exact rerun numbers, a bit-for-bit claim, or a third-party
reproduction claim.

