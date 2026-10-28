# Three independent simulated T-IFS reviews

These are simulated judgments, not predictions of editorial decisions. All
reviewers assessed the frozen canonical manuscript and retained evidence; none
modified files or ran experiments. They were deliberately assigned different
specialisms.

## Reviewer 1 — Systems security and empirical measurement

### Overall recommendation

**Major revision; borderline weak reject in the current positioning.**

### Novelty

The four-boundary organization (`T-IFS.tex:170--185`, `212--283`) is coherent,
but naming integrity, lifetime, persistence, and isolation does not establish a
new security abstraction. Murtuza's local-runner forensic study and Chung &
Badhe's OS-integrated privacy taxonomy overlap with the conceptual premise.
LLAnalyzer's possible increment is the evidence-bounded operational workflow,
not the categories themselves.

The strongest empirical contribution is the combination of UUID attribution,
post-inference writable-memory recovery, later-request persistence, and
in-process model-swap residue (`T-IFS.tex:709--924`). The D4 family is the most
distinctive dimension, but it remains a residual-state observation rather than
an isolation attack.

### Technical significance and evidence

The two Nemotron twelve-tenant records are valuable as conditional forensic
recoverability evidence, but (F) is not the unprivileged (A_1) attacker. The
paper must keep this distinction prominent. The exact 110/10834 and 78/3352
observations are descriptive single-run records and cannot establish a causal
sanitization effect (`T-IFS.tex:724--744`, `1000--1042`).

The slot result is not a cross-principal vulnerability: one loopback server,
one Python process, no key, no ownership check, and an `n_saved == n_restored`
oracle (`T-IFS.tex:1236--1247`). The July 126/200 continuation is more
informative but is also one-process and unauthenticated. Wu et al. already
demonstrate a stronger mutually distrustful-tenant KV-cache attack.

### Methodology and reproducibility

Canary attribution is sound, but the claim that LLAnalyzer “traces” a failure to
a software layer (`T-IFS.tex:412--460`) exceeds what exact canary recovery alone
proves. The mechanism sections (`T-IFS.tex:805--910`) need “consistent with”
language unless retained debugger evidence localizes allocation sites.

The artifact URL is `TODO` (`T-IFS.tex:1364`), June binaries were not hashed,
CUDA revision is unknown, timing vectors and original analysis are absent, and
the GGUF corpus is not retained. This limits a reusable-tool contribution.

### Strongest contribution

An evidence-bounded local-serving lifecycle study showing that prompt material
can remain recoverable across requests and an in-process model replacement.

### Most serious weakness

The manuscript defines isolation as client separation but does not instantiate
two clients or credentials. A reviewer could read the title and contribution
list as claiming a vulnerability that the experiment did not test.

### Major-revision requests

1. Recast the contribution as lifecycle measurement plus local-serving case
   study.
2. Add a boundary/actor/evidence/oracle/untested-control table.
3. Separate explicit canary-echo controls from unsolicited injection results.
4. Downgrade root-cause attribution where debugger evidence is incomplete.
5. State independence assumptions for proportions and sequential same-process
   trials.
6. Add direct comparison with Wu, Luo, Xu, Murtuza, Chung/Badhe, Early Bird,
   and Gao.

## Reviewer 2 — LLM inference infrastructure and runtime isolation

### Overall recommendation

**Major revision; weak-reject risk unless repositioned as an empirical case study.**

### Novelty

The four-boundary framework is a useful synthesis but overlaps existing local
privacy and serving-cache work. The 126/200 continuation result is not a first
KV-cache leakage result: Wu et al. (NDSS 2025), Luo et al. (NDSS 2026), SafeKV,
and PrefixWall already occupy that security space. The distinctive question is
whether local `llama-server` state restoration and process lifetime exhibit
implementation-specific residue; the manuscript should say exactly that.

### Technical significance

The host-memory result under Nemotron partial CUDA offload is useful because it
shows that moving model computation does not remove host-side prompt-processing
paths. It does not show device-memory recovery, full-offload behavior, or a
universal GPU property (`T-IFS.tex:1066--1142`).

The D4 result is precise (200 primary records, 50 per fixed pair at
`T-IFS.tex:917--925`) and may be the most interesting systems observation. It
does not show model-B output disclosure, cross-principal leakage, persistence
after process restart, or a mechanism beyond allocator/runtime retention.

LM Studio logging is practical but configuration-specific to llmster 0.0.15-2 /
backend 2.17.0; Murtuza already surveys local-runner artifacts. Ollama's
206-record accounting is reproducibility context rather than a standalone
security contribution.

### Threat model and methodology

The paper's (A_2) network-client definition is not exercised by the retained
slot or continuation workload (`T-IFS.tex:572--576`, `1236--1262`). The authors
should say that the isolation boundary is defined analytically but only
partially operationalized. The slot equality oracle is token-count equality,
not secret content.

The direct injection workload is potentially confounded: prompt templates that
explicitly request a canary are instruction-following controls, not unsolicited
disclosure. The manuscript should expose per-template outcomes before retaining
the 150/200 any-channel union as a security observation.

### Strongest contribution

The integrated combination of model-labelled residue, lifecycle timing, and
host-side evidence across consumer local-serving components.

### Most serious weakness

The closest isolation literature demonstrates a stronger attacker capability
than LLAnalyzer. If LLAnalyzer is read as an isolation-vulnerability paper, its
central experiment is underpowered by design.

### Major-revision requests

1. Explicitly state “same-process state behavior” at the first slot result.
2. Remove any implication that the 126/200 result is a new cross-tenant attack.
3. Add per-template direct-injection accounting or narrow the claim to the
   exact oracle tested.
4. Position GPU evidence as Nemotron host-memory scope only.
5. Compare with Wu, Luo, Early Bird, SafeKV, PrefixWall, and Gao.
6. Distinguish model-family breadth from generality of Nemotron/Phi-only rows.

## Reviewer 3 — Security methodology, reproducibility, and scientific novelty

### Overall recommendation

**Major revision, with a credible reject-and-resubmit risk if novelty remains
framed as a broad security-boundary failure paper.**

### Novelty

The strongest defensible contribution is a retrospective, evidence-bounded
measurement study showing that local execution is not a complete prompt-
confidentiality guarantee. The four-boundary abstraction is closer to a
synthesis than a new ontology unless the paper formalizes boundary semantics,
common schemas, and transferability.

The model-swap workload is a potentially novel empirical dimension. Its
scientific contribution is “residue survives a controlled in-process model
transition,” not “a model can read another tenant's state.”

### Methodological validity

The manuscript correctly separates byte occurrences, tenants, model-output
canaries, token-count equality, and wrapper artifacts. However, the study mixes
June and July records, CPU and CUDA configurations, model-specific offload,
Nemotron-only blast-radius rows, Phi-4-only diagnostics, and aggregate-only
allocator summaries (`T-IFS.tex:498--521`; Supplementary Methods `473--501`).
The paper should make “controlled within-family comparison” versus
“heterogeneous historical observation” a first-class distinction.

Wilson intervals require an independence unit. Sequential same-process requests
may share allocator and process history, so model-level 50-trial proportions are
not automatically independent deployment samples.

### Reproducibility

Missing binary hashes/CUDA revision, timing vectors, raw GGUF mutation corpus,
allocator repetitions, original LM Studio plaintext log, and linked Ollama
executable version materially limit exact replication. The public artifact URL
remains unresolved. The current manuscript is honest about these gaps, but they
reduce the strength of the “framework” contribution.

### Strongest contribution

The explicit evidence-to-claim accounting and process-lifetime observation across
later requests and model replacement.

### Most serious weakness

The paper's general framework language outruns its evidence: a boundary can be
defined without being directly validated against the corresponding attacker.

### Major-revision requests

1. Formalize what counts as boundary definition, boundary observation, and
   security-boundary validation.
2. Add the claim/actor/evidence/oracle matrix.
3. State process-level clustering and denominator limits for repeated requests.
4. Replace causal mechanism verbs with evidence-strength qualifiers.
5. Add the closest-prior comparison and public-version consistency note.

## Cross-reviewer consensus

All three reviewers agree that:

- The paper has a credible and useful empirical story.
- The strongest contribution is lifecycle evidence integration, not any one
  individual attack result.
- D4 model-swap residue is potentially distinctive but must remain a residue
  observation.
- Slot/continuation do not establish cross-principal authorization.
- Runtime findings must remain scoped to the authorized collector and retained
  configurations.
- Related work is too compressed for the novelty burden.
- Missing provenance and raw artifacts weaken claims of a reusable framework.
- Major revision is required before a defensible T-IFS submission.

## Reviewer disagreement

The reviewers differ mainly in emphasis, not conclusion:

- Reviewer 1 sees the integrated workflow as moderate potential novelty.
- Reviewer 2 gives the weakest novelty assessment for KV/isolation because prior
  attacks are substantially stronger.
- Reviewer 3 sees the evidence ledger and formal separation of observation types
  as the most publishable methodological contribution.

No reviewer found evidence for a new general KV-cache attack, universal GPU
confidentiality result, or validated causal sanitization effect.

