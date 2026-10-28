# Updated scientific readiness after the Ikram clarification

## Executive status

**The complete LLAnalyzer contribution remains in scope. A full cross-machine
rerun is now author-reported, but artifact-verified replication is not yet
established from the inspected workspace.**

This is an update to the previous readiness assessment, not a declaration that
the experiments were never rerun. The author clarification materially changes
the replication narrative, while leaving the local provenance and statistical
verification boundaries intact.

## Updated classification

| Evidence layer | Current status | What it supports |
|---|---|---|
| Original retained records | Mixed, strongest for selected memory, slot, continuation, KV-vector, and telemetry records | Local arithmetic and bounded archival observations |
| Author-reported Ikram rerun | Full framework reported as matching original results | The existence and claimed outcome of a collaborator rerun |
| Ikram artifact verification | Not available in inspected workspace | No experiment-specific cross-machine numeric verification yet |
| Sharma expert review | Secondary arithmetic/documentation review; no independent execution documented | Consistency checks and scope limitations |
| Independent third-party reproduction | Not evidenced | No external execution claim |

## RQ-level readiness

| RQ | Local evidence grade from prior audit | Ikram replication status | Updated readiness |
|---|---|---|---|
| RQ1 GGUF integrity | E4 for headline campaign; E3 for source inspection | Author-reported match; no Ikram corpus or sanitizer artifacts | Preserve RQ1, but do not call the cross-machine match artifact-verified |
| RQ2 memory/sanitisation | E1 for selected aggregate arithmetic; E4/E5 boundary for historical causal attribution | Author-reported match; no Ikram acquisition/provenance bundle | Preserve observed results and report the replication with explicit artifact limitation |
| RQ3 persistence/network | E4 for LM Studio historical log persistence; E2 for bounded Ollama monitoring | Author-reported match; no Ikram product/config/log bundle | Preserve configuration- and version-bounded claims |
| RQ4 slots/timing | E1 for slot/continuation arithmetic; E4 for timing AUC | Author-reported match; no Ikram slot or timing artifacts | Preserve both; keep timing independently unrecomputable locally |

## What is resolved and what is not

Resolved at the narrative level:

- It is no longer accurate to say that LLAnalyzer has no replication history.
- The paper may distinguish a reported full cross-machine collaborative rerun
  from local archival recomputation and from Sharma's secondary review.
- The full four-boundary structure should be preserved pending author approval.

Not resolved by the clarification alone:

- historical source-to-binary linkage;
- exact Ikram source, patch, build, model, and server configuration;
- exact rerun counts, confidence intervals, and model-specific results;
- raw Ikram GGUF, memory, persistence, slot, and timing outputs;
- independent recomputation of the timing AUC; and
- independent third-party reproduction.

## Readiness decision

The manuscript is **eligible for a full-contribution revision that transparently
reports the author-reported rerun**, but it is **not yet eligible for a claim
that the cross-machine replication has been independently artifact-verified**.
The minimum remaining action is evidence recovery, not a new experimental
campaign. The exact request is in `IKRAM_EVIDENCE_REQUEST.md`.

No manuscript source or historical result was modified by this update.

