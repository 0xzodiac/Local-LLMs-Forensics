# Discussion and limitations: author-editable draft

## Discussion

The results support a lifecycle interpretation of local privacy. B1's bounded
negative result does not constrain B2--B4. Runtime sanitisation reduces recorded
residue but does not change the observed tenant-level recovery outcome. Wrapper
logging can preserve the same prompt independently of runtime memory. Shared
saved-state transfer can violate confidentiality even when a client is properly
authenticated. The security recommendation is therefore compositional:
operators must control artifact admission, prompt-bearing allocations,
persistent logging, slot/cache ownership, and deployment exposure separately.

The model-specific continuation rates are also informative. Direct state
transfer is uniform in the retained trials, while generated secret recovery
depends strongly on model behavior. This is why a protocol-level isolation
result must not be reduced to a model-output success rate.

## Limitations and wording

### Historical source and binary provenance

The original source identifier is unresolved, and the historical executable hash
and startup manifest are absent. Claim: retained records and arithmetic remain
usable with provenance qualification. Do not claim exact historical binary
reproduction. Qualify in Methods and the artifact statement.

### Historical prompt patch

The retained prompt patch is malformed. Remediation 2 verifies a new pinned
implementation but did not perform a model-backed experiment. Claim: the new
engineering mechanism is separate evidence. Do not attribute the old aggregate
reduction causally to an identified historical patch. Qualify in RQ2 and the
Supplement.

### Timing data

The original TTFT vectors and AUC script are absent. Claim: AUC=1.000 is a
historical evaluated-condition result. Do not call it independently recomputed or
WAN-general. Qualify in RQ4 and Open Science.

### Forensic permissions

F's authorized parent-child acquisition path establishes residual existence and
conditional recoverability. Claim: canaries survived in process memory. Do not
say every same-UID user can read arbitrary memory. Qualify in Threat Model and
RQ2.

### Tenant identity

Different API keys are recorded, but distinct security principals and resource
ownership are not independently established. Claim: shared-server state crossed
the tested credential contexts. Do not equate keys with tenants. Qualify in RQ4.

### Product and configuration scope

LM Studio persistence is tied to the evaluated sensitive-data logging setting;
Ollama is a bounded monitored control. Claim: these configurations behaved as
observed. Do not generalize to every product version or storage channel. Qualify
in RQ3.

### Negative results

RQ1 and Ollama are state-space/channel-bounded negative observations. Claim: no
failure or canary was observed under the documented instrumentation. Do not
claim universal parser safety or universal absence. Qualify beside each result.

### Ikram artifacts

The author reports a complete cross-machine rerun by Dr. Mohammed Ikram. Claim:
the replication history exists and is corroborating author-reported evidence.
Do not claim local artifact inspection, exact rerun values, or third-party
independent reproduction. Qualify in Open Science and Supplement.

