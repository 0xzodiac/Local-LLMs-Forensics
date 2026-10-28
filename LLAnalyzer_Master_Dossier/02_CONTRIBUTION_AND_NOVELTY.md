# Contributions, novelty, and claim boundaries

## Contribution 1: a four-boundary confidentiality model

LLAnalyzer's primary conceptual contribution is to decompose “local prompt
confidentiality” into four independently testable boundaries: model-artifact
integrity, runtime lifetime, wrapper persistence, and shared-state isolation.
The decomposition is useful because a clean result at one boundary does not
repair a failure at another. A safe model load does not remove heap residue; a
memory mitigation does not delete wrapper logs; and authentication does not
necessarily provide resource ownership.

## Contribution 2: a boundary-oriented measurement framework

The framework combines controlled malformed artifacts, UUID canaries,
authorized memory acquisition, wrapper artifact inspection, network telemetry,
saved-slot protocol tests, and timing measurements. Its distinctive property is
the mapping from an observation to a specific boundary and measurement point.
The framework is not a claim that every instrument is a new attack primitive.

## Contribution 3: an uneven empirical security picture

The retained results show four different outcomes rather than one binary verdict:

- no relevant failure in the explored RQ1 state space;
- persistent runtime prompt residue under the authorized forensic collector;
- configuration-dependent wrapper persistence;
- cross-client state transfer and model-dependent continuation in a shared
  serving configuration.

This heterogeneity is the scientific result. The paper should avoid presenting
the four boundaries as equally strong vulnerability claims.

## Contribution 4: mechanism and mitigation evidence

The memory work separates heap-string residue from KV-cache tensor data. The
retained KV patch directly verified 56/56 nonzero cells immediately before
zeroisation, while the literal-canary memory scan continued to observe a
separate string-buffer surface. The baseline/sanitised historical aggregate
shows a reduction in recorded exposure, but missing historical binary linkage
prevents a strong causal attribution to the original patch.

## Contribution 5: deployment guidance

The paper translates observations into controls: treat model admission,
prompt-bearing allocations, wrapper logging, slot ownership, and cache-sharing
policy as separate security decisions. It does not claim a CVE, vendor
acknowledgement, or universal product defect for the saved-slot observation.

## Novelty positioning

| Existing research family | What it usually isolates | LLAnalyzer's additional position |
|---|---|---|
| Model memorisation/privacy | Training-data extraction or memorisation | Studies prompt confidentiality after the request enters a local serving stack |
| Parser and model-artifact CVEs | Specific malformed input and memory-safety paths | Uses a bounded validation-gap campaign as B1, without claiming global parser safety |
| Memory forensics | Process or mobile-app artefact recovery | Connects prompt lifecycle, allocator/KV state, and mitigation evidence |
| Wrapper logging studies | Product-specific persistence | Places logging beside runtime and server-state boundaries and compares LM Studio with Ollama |
| KV-cache side channels | Timing or state reuse in shared inference | Connects prefix-cache timing with saved-state restoration and resource-level authorization |
| Prompt-injection work | Model or agent instruction following | Uses canaries as controlled provenance markers rather than treating injection resistance as confidentiality |

## Claims to avoid

- “First vulnerability in local LLMs.”
- “Local wrappers universally log prompts.”
- “The parser is memory-safe.”
- “Same-UID users can read arbitrary process memory.”
- “Separate API keys create isolated tenants.”
- “The sanitized build restores confidentiality.”
- “AUC=1.000 proves a WAN attack.”
- “Dr. Ikram independently reproduced the study as a third party.”

## Recommended novelty sentence

> LLAnalyzer contributes a boundary-oriented measurement framework that
> connects model admission, runtime data lifetime, wrapper persistence, and
> shared serving-state isolation in one confidentiality analysis, and uses
> boundary-specific evidence to show why local execution alone is not a
> complete prompt-confidentiality guarantee.

