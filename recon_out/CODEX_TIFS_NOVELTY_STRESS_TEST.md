# LLAnalyzer IEEE T-IFS novelty and scientific-contribution stress test

Date: 2026-10-11. This assessment treats retained experimental evidence as
frozen and does not modify the manuscript or run experiments. It reads the
canonical main source, supplementary sources, active figures, bibliography,
model-coverage reports, and the latest double-check report. Related work was
checked against official venue pages, publisher pages, or primary arXiv records.

## Executive assessment

LLAnalyzer has a defensible empirical systems-security story, but the current
non-incremental novelty is not yet demonstrated strongly enough for a confident
T-IFS submission. The strongest contribution is an evidence-bounded
measurement/case-study workflow that follows UUID-attributed prompt material
through several local-serving lifecycle surfaces and explicitly separates:

1. residual-data existence;
2. conditional forensic recoverability through the researcher-controlled
   collector;
3. model-visible or wrapper-visible recovery; and
4. demonstrated unauthorized access by a distinct principal.

That separation is scientifically valuable. It is not, by itself, a new attack
class. Prior work already demonstrates local-LLM artifact recovery, mobile LLM
memory forensics, unprivileged local side channels, multi-tenant KV-cache prompt
reconstruction, and defenses for shared-cache leakage. The paper's strongest
position is therefore **empirical systems-security measurement of prompt-data
lifetime and serving-state exposure in consumer local-LLM stacks**, not a new
cross-tenant attack, parser vulnerability, GPU-isolation result, or validated
sanitization defense.

Overall judgment: **major revision**. In the current framing, the paper has a
credible weak-reject risk because the title and four-boundary contribution list
can make reviewers expect four demonstrated security failures. Repositioning the
work around evidence-bounded lifecycle measurement, clearer comparison with the
closest five papers, and strict attacker/evidence separation would materially
improve defensibility. No acceptance prediction is made.

## What the manuscript claims

The active contribution list is at `LLAnalyzer-revised-10point/T-IFS.tex:178--196`.
The framework is defined at `T-IFS.tex:212--285`, the threat model at
`:287--324`, the measurement workflow at `:337--460`, and RQ1--RQ4 at
`:598--1305`. The supplement gives the operational protocols at
`TIFS_Supplementary_Methods.tex:413--553` and the statistical limitations at
`:632--702`.

### Contribution extraction and novelty challenge

| Claimed contribution | Type | Evidence-grounded value | Novelty dependency | Stress-test judgment |
|---|---|---|---|---|
| Four-boundary model: integrity, lifetime, persistence, isolation (`T-IFS.tex:170--185`, `212--283`) | Conceptual framework | Gives each experiment a security objective and evidence source. | Novelty depends on being more than lifecycle relabeling. | **Weak-to-moderate conceptual novelty.** Chung & Badhe already argue that local execution is not a sufficient privacy boundary; Murtuza and Xu cover artifact/memory surfaces. Claim it as an operational synthesis unless a formal ontology or transfer study is added. |
| LLAnalyzer canary/evidence workflow (`T-IFS.tex:337--460`) | Measurement methodology/tool | UUID attribution, boundary-specific evidence, explicit outcome limits. | Novelty depends on reusable interfaces, schemas, provenance checks, and portability. | **Moderate potential, not yet established.** The components (fuzzing, memory scans, artifact inspection, API probes) are familiar. The public artifact URL is still `TODO` (`T-IFS.tex:1364`) and historical binaries/vectors are incomplete. |
| Empirical local-serving study across four models/two platforms (`T-IFS.tex:188--195`) | Empirical study | Retained four-model families exist for slot equality, July continuation, injection, KV overhead, D4, hooks, and Ollama; heterogeneous Nemotron/Phi-only families are labeled. | Novelty cannot be “four models were tested.” | **Useful breadth, not novelty by itself.** The contribution must identify which observation changes prior understanding. |
| Post-inference writable-memory residue (`T-IFS.tex:709--797`) | Empirical security finding | UUID canaries recovered after inference; two Nemotron 12-tenant rows recover 11/12 tenants. | Novelty depends on being distinct from local-LLM memory forensics and on correct attacker scope. | **Moderate empirical extension.** Strongest direct result, but it establishes conditional forensic recoverability under the documented collector (F), not arbitrary unprivileged (A_1) access. |
| Mechanism analysis: prompt duplication plus allocator retention (`T-IFS.tex:805--924`) | Mechanistic interpretation | Multilayer diagnostics and GDB reports support a lifecycle/allocator hypothesis. | Novelty depends on causal proof and retained debugger traces. | **Promising but overclaim-sensitive.** Use “evidence-consistent attribution”; retained GDB material does not pinpoint every allocation site. |
| Sanitization/allocator comparison (`T-IFS.tex:929--1042`) | Mitigation analysis | Exact descriptive rows: 110/10834 and 78/3352, both 11/12; model-specific latency arrays. | Novelty depends on causal matched controls. | **Descriptive only.** Two single-run Nemotron configurations with differing settings cannot establish an effect size or mitigation efficacy. |
| GPU-v5 host-memory observation (`T-IFS.tex:1051--1142`) | Infrastructure finding | 50 Nemotron partial-CUDA trials with field-specific host-memory observations. | Novelty depends on device-memory evidence and model/runtime breadth. | **Narrow value.** Host-side request processing under partial offload is useful context, not a new GPU isolation attack. |
| Wrapper persistence (`T-IFS.tex:1146--1220`) | Practical security observation | Configuration-specific LM Studio logging toggle; Ollama telemetry accounting; hooks show external hosts but no visible canary. | Novelty depends on clean-install/default controls and retained logs. | **Incremental/configuration-specific.** Murtuza already studies the same local-runner artifact ecosystem. |
| Slot restore and continuation (`T-IFS.tex:1222--1305`) | Serving-state observation | 200/200 equality in one unauthenticated process; separate July 126/200 KV and 200/200 memory hits. | Novelty depends on two-principal authorization and disclosure oracle. | **Low security novelty as tested.** No second client, key, wrong-key, ownership, or secret-content control. This is same-process state transfer and continuation, not a cross-principal authorization finding. |
| D4 model-swap residue (`T-IFS.tex:917--925`) | Empirical runtime-state finding | 200 primary same-process model-pair swaps with positive model-A canary observations. | Novelty depends on distinguishing allocator residue from known memory behavior and showing an access consequence. | **Potentially distinctive, still limited.** It adds a controlled model-transition dimension to memory forensics, but does not show model-generated disclosure, cross-principal leakage, or persistence across restart. |
| GGUF parser observations (`T-IFS.tex:598--683`) | Robustness evidence | Retained reports contain SIGABRT observations and no recorded SIGSEGV; fourth label `phi3`/script key `phi4` unresolved. | Novelty depends on a retained mutation corpus and defensible crash aggregation. | **Weak as a primary contribution.** Hardening evidence, not a demonstrated vulnerability or reproducible campaign. |

## What is genuinely informative

Three observations can change a careful reader's understanding if framed
precisely:

1. **Prompt lifetime is not a single runtime object.** Exact canaries remain
   recoverable through later requests and after an in-process model swap. This
   connects serving lifecycle and allocator-managed residue rather than merely
   stating that memory can contain stale bytes.
2. **A local serving API can expose state-transfer primitives independently of
   model output.** The slot result is a deterministic state-management observation
   under a shared process, although its security consequence remains untested
   across principals.
3. **Evidence units matter.** The manuscript's best methodological insight is
   the explicit distinction among byte occurrences, tenants, model-output hits,
   token-count equality, persistent artifacts, and attacker-visible disclosure.

These are useful systems-security results. They become a non-incremental paper
only if the workflow itself is made portable/reusable or if one result is given a
proper principal-boundary control that existing work does not already provide.

## What does not establish novelty

- Four-model breadth is external-validity support, not a novelty claim.
- 126/200 continuation is not a first KV-cache leakage result; Wu et al. already
  demonstrate stronger mutually distrustful-tenant prompt reconstruction.
- 200/200 token-count equality is not secret disclosure and is not a cross-client
  authorization test.
- D4 residue is not a new isolation mechanism without a model-visible or
  cross-principal oracle.
- LM Studio 10/10 logging behavior is configuration-specific and overlaps local
  runner forensic studies.
- Assertion aborts are important robustness evidence but not proof of memory
  corruption or a parser vulnerability.
- Partial CUDA host-memory observations do not generalize to GPU memory or other
  serving architectures.
- The sanitization rows cannot support causal mitigation claims.

## Threat-model credibility

The threat model correctly distinguishes (A_1), (F), (A_2), and (A_3) at
`T-IFS.tex:287--324`. The key validity issue is that the most security-sensitive
boundary, isolation, is defined in terms of client separation while the retained
slot and continuation workloads use one unauthenticated server/process. Thus:

- Lifetime results support conditional forensic recoverability through (F).
- Persistence results support configuration-specific wrapper retention.
- Integrity results support malformed-input robustness observations.
- Isolation results support same-process state transfer and continuation, not
  an (A_2) authorization result.

The paper should say “four defined boundaries, with heterogeneous direct evidence
and a same-process isolation probe,” rather than allowing “all four boundaries
were independently validated” to be inferred.

## Reproducibility and provenance impact on novelty

The current source transparently states that June binaries were not hashed or
retained, CUDA revision is unknown, timing vectors are absent, allocator
per-repetition records are aggregate-only, raw GGUF corpus is absent, and the
`phi3`/`phi4` identity is unresolved. These limitations lower the framework/tool
novelty claim because a reviewer cannot independently reproduce every historical
measurement. A stale `TASK7_REPRODUCIBILITY_CLOSURE.md` makes stronger retained
binary/model-digest assertions than the current frozen evidence baseline; this
conflict should be treated as a report-version/provenance issue, not as evidence
that the executed June binaries are identified.

The public arXiv version (arXiv:2609.18526, [record](https://arxiv.org/abs/2609.18526))
also retains older AFL++, authorization, and WAN-timing claims that do not match
the canonical source. A reviewer may compare versions; novelty and contribution
claims should be version-consistent before submission.

## Best T-IFS positioning

Recommended primary framing:

> An empirical systems-security measurement framework and case study for
> prompt confidentiality across consumer local-LLM serving lifecycles.

Secondary framing: inference-state lifetime and forensic evidence-boundary
analysis.

Avoid framing as a new KV-cache attack, a demonstrated cross-principal
authorization vulnerability, a universal GPU isolation result, a parser-security
paper, or a validated sanitization defense.

Title directions that better match the evidence:

- “Measuring Prompt Confidentiality Boundaries in Consumer Local-LLM Serving
  Systems”
- “Prompt Residue and Serving-State Exposure in Consumer Local-LLM Systems”

The existing title can remain only if “boundary failures” is explicitly defined
to include confidentiality-relevant residual states and configuration
observations, not only attacker-demonstrated vulnerabilities.

## Minimum changes with existing evidence

1. Add a compact novelty table comparing LLAnalyzer with Wu, Luo, Xu, Murtuza,
   Chung/Badhe, Early Bird, and Gao.
2. Add a claim matrix with boundary, tested actor, evidence source, oracle,
   observed result, untested boundary, and provenance status.
3. Replace “exercises these boundaries independently” with language distinguishing
   logical decomposition from direct principal-boundary validation.
4. Rename D4 as in-process model-swap residue and weaken mechanism verbs from
   “identify” to “support” or “are consistent with” where debugger evidence is
   incomplete.
5. Explain the direct-injection oracle: template rows that explicitly request a
   canary are controls, not unsolicited disclosure evidence; do not pool them
   without showing the per-template distinction.
6. State that Wilson intervals require an independence unit and that sequential
   same-process requests may be clustered.
7. Add an artifact-completeness table and resolve the public-preprint/current-
   manuscript version mismatch.

## Bottom line

LLAnalyzer is not merely a collection of random measurements: its canary
attribution and cross-layer evidence accounting are useful. However, the
current manuscript has not yet shown that this synthesis is a fundamentally new
security abstraction rather than a careful integration of established methods.
The paper can be competitive if it makes that narrower contribution explicit;
the existing evidence alone cannot support a stronger isolation-vulnerability
or KV-attack novelty claim.

