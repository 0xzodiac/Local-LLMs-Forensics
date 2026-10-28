# Evaluation: author-editable draft

## RQ1: model-artifact integrity

We first test whether malformed model artifacts compromise the loading path. The
structured battery mutates semantic GGUF fields and the structural corpus
exercises tensor dimensions, names, metadata lengths, offsets, and related
header constraints. The reported 24-hour coverage-guided campaign exceeds
1.2e7 executions under sanitizer instrumentation. No parser crash, sanitizer
violation, or successful malformed load was observed within the explored state
space. The correct conclusion is a bounded negative observation; the evidence
does not certify global parser safety or replace the parser's CVE history.

The local audit retains scripts and reports but not a complete machine-generated
80/21 campaign manifest, sanitizer bundle, coverage record, or binary hash. The
author-reported Ikram rerun covers the complete framework at the reported level,
but no Ikram per-case corpus artifact was inspected.

## RQ2: runtime memory lifetime

After successful admission, the same request can exist in several runtime
representations. Under the authorized forensic collector, sequential-tenant
experiments recovered prompt canaries from 11 of 12 tenants. The retained
baseline and sanitised records report 110 and 78 matching copies and 10,834 and
3,352 recorded matching-region KB, respectively. These correspond to
approximately 29.09% and 69.06% reductions in recorded metrics, while the
11/12 tenant-level recovery outcome is unchanged.

The result is strongest as evidence of residual existence and a descriptive
mitigation effect. It does not prove arbitrary same-UID access, literal secret
byte volume, complete erasure, or causal attribution to a fully identified
historical binary. The direct KV mechanism record separately reports 56/56
targeted cells nonzero immediately before the zero write. The literal-canary
scan's continued matches identify a separate heap-string surface and must not be
used as a KV-tensor test.

Under partial CUDA offload, host-side prompt representations remain relevant.
This result does not establish device-memory access or universal behavior across
GPU architectures.

## RQ3: wrapper-managed persistence

In the evaluated LM Studio configuration with sensitive-data logging enabled,
prompt canaries appeared in wrapper-managed server logs. After the setting was
disabled and the server restarted, the new test canary was not found in the
searched logs. Existing logs remained on disk, and the prediction-history TTL
setting did not control those server-log files. The claim is configuration-
specific and should not be rewritten as a clean-install default.

The bounded Ollama monitoring set contains 205 valid sessions plus one
incomplete directory. No canary appeared in captured external egress or the
examined artifacts. Loopback inference traffic was excluded. This negative
result is useful as a control contrast, but it is not a product-wide guarantee.

## RQ4: shared-state isolation

The saved-slot protocol transferred state in 200/200 trials across four models,
50 per model. Subsequent model-mediated secret continuation occurred in 126/200
trials: Gemma 50/50, Qwen 50/50, Nemotron 25/50, and Phi-4 1/50. The direct
transfer result and continuation result are separate. The former is a protocol
observation; the latter depends on model stopping and response behavior.

The pooled continuation proportion is 0.63 with Wilson interval
[0.5612263, 0.6938739]. The direct-transfer interval is approximately
[0.9811547, 1.0]. Different valid API keys establish authentication inputs, not
independent tenant resource ownership. The result is therefore a shared-state
isolation hazard under the evaluated configuration, not a maintainer-acknowledged
CVE.

The historical timing result reports AUC=1.000 for cached versus uncached TTFT
under loopback/LAN conditions. The raw vectors, request order, and original
analysis script are unavailable locally, so this result remains a historical
record and not an independently recomputed statistic.

## Cross-boundary synthesis

The four RQs do not produce one “secure/insecure” label. They show that model
admission, runtime lifetime, wrapper persistence, and shared-state isolation are
independent conditions. Local execution can satisfy the network-locality
intuition while leaving the remaining boundaries exposed.

