# Abstract and contributions: author-editable draft

## Draft abstract

Local inference is often treated as a privacy guarantee because prompts need
not leave the user's device. Local execution, however, specifies where
computation occurs, not how serving software handles prompt data before,
during, or after inference. We present LLAnalyzer, a measurement framework that
traces prompt exposure across four confidentiality boundaries: model-artifact
integrity, runtime lifetime, wrapper-managed persistence, and shared-client
isolation. Across four open-weight model families and two consumer deployment
platforms, we combine controlled artifact fuzzing, authorized memory forensics,
persistent-artifact inspection, and shared-serving experiments. In the
reported integrity campaign, no parser crash, sanitizer violation, or malformed
model load was observed within the explored state space. Under the authorized
memory-acquisition path, prompt canaries remained recoverable from 11 of 12
sequential tenants; the evaluated sanitisation reduced recorded matching-copy
and matching-region metrics by approximately 29% and 69%, respectively, without
changing tenant-level recovery. In the evaluated LM Studio configuration,
sensitive-data logging persisted prompt material, whereas bounded Ollama
monitoring yielded no captured canary in the examined channels. Shared saved-
state restoration succeeded in 200/200 trials, and subsequent model-mediated
secret continuation occurred in 126/200 trials. The retained timing record
reports AUC=1.000 under the evaluated loopback/LAN conditions, but its raw
per-request vectors are unavailable for local recomputation. These results show
that locality is a deployment property rather than a complete prompt-
confidentiality guarantee.

## Contribution bullets

1. A four-boundary model that makes prompt confidentiality a lifecycle property
   spanning admission, lifetime, persistence, and isolation.
2. LLAnalyzer, a boundary-oriented measurement framework that links controlled
   inputs to boundary-specific evidence.
3. An empirical study showing an uneven security picture: a bounded RQ1
   negative result, runtime residue, configuration-dependent persistence, and
   shared-state exposure.
4. Mechanism and mitigation evidence that separates ordinary heap-string
   residue from KV-cache tensor state and distinguishes direct transfer from
   model continuation.
5. A provenance-aware research record that preserves the reported full
   cross-machine collaborator rerun without presenting it as uninspected
   third-party reproduction.

