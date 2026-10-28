# LLAnalyzer high-impact research gaps and minimum improvement plan

Date: 2026-10-11. This plan is evidence-grounded and deliberately prioritizes
information gain over larger sample counts. It does not authorize or perform
new experiments, disclosure, or manuscript edits.

## A. Changes possible with retained evidence and manuscript revision

### A1. Reframe the contribution

Use the following hierarchy:

1. **Primary:** evidence-bounded empirical systems-security measurement of
   prompt-data lifetime and serving-state exposure in consumer local-LLM stacks.
2. **Secondary:** boundary-oriented evidence accounting that separates residual
   bytes, conditional forensic recoverability, model/wrapper-visible recovery,
   and unauthorized principal access.
3. **Not claimed:** a new KV-cache attack, cross-principal authorization flaw,
   universal GPU result, parser vulnerability, or validated causal mitigation.

Relevant source locations: `T-IFS.tex:170--196`, `337--460`, `498--521`,
`917--925`, `1222--1305`, `1313--1327`.

### A2. Add a novelty/evidence matrix

Add a compact table with columns: boundary; tested actor; evidence source; exact
oracle; result; what is not tested; provenance status; closest prior work. This
would make the paper's strongest methodological contribution visible without
inflating its security interpretation.

### A3. Make the isolation limitation immediate

At the first slot result, say that one unauthenticated process and one client
were used; no distinct credentials, wrong-key, ownership, or second-client
control exists. Call the result same-process state transfer. Keep 200/200, but
do not use it as evidence of authorization bypass.

### A4. Separate direct-injection controls from disclosure evidence

The five-template injection workload includes templates whose instructions ask
the model to quote the canary. Those rows are instruction-following/positive
controls. The 150/200 union should be labelled according to the exact per-template
oracle, with unsolicited and explicit-echo outcomes separated if the retained
records permit. If the retained records do not permit that split, keep the union
as a workload observation and do not call it direct privacy leakage.

### A5. Downgrade mechanism verbs

At `T-IFS.tex:805--910`, distinguish:

- directly observed canary bytes and mapping locations;
- source-informed candidate duplication paths;
- allocator behavior consistent with retention; and
- causal allocation-site proof.

Use “supports” or “is consistent with” where retained GDB evidence does not
pinpoint an allocation source.

### A6. Expand related-work positioning

The current paragraph at `T-IFS.tex:1309--1327` should explicitly compare the
paper with:

- Murtuza (local-runner forensics);
- Xu et al. (mobile local-LLM memory forensics);
- Chung & Badhe (local privacy boundary framework);
- Wu et al. / PROMPTPEEK (mutually distrustful KV-cache leakage);
- Luo et al. / Shadow in the Cache (KV reconstruction and KV-Cloak);
- Song et al. / Early Bird (timing leakage);
- Gao et al. (unprivileged local hardware-cache side channel);
- SafeKV and PrefixWall (selective cache isolation).

The [closest-prior matrix](CODEX_CLOSEST_PRIOR_WORK_MATRIX.md) contains the
comparison text and primary links.

### A7. Add artifact-completeness and version-consistency notes

Explicitly list missing executable hashes, CUDA revision, timing vectors,
allocator repetitions, raw GGUF corpus, original LM Studio plaintext log, and
Ollama executable version. Also reconcile the canonical source with the public
arXiv record at [arXiv:2609.18526](https://arxiv.org/abs/2609.18526), which still
contains older AFL++, authorization, and WAN-timing claims.

### A8. State statistical units of independence

The supplement's Wilson-interval discussion (`TIFS_Supplementary_Methods.tex:642--659`)
should state whether the independent unit is a request, a process, a model
block, or a deployment. Sequential requests in one process may share allocator
history, so a request-level interval is not automatically a deployment-level
uncertainty statement.

## B. Improvements requiring missing historical artifacts

These cannot be settled through prose alone:

1. **Executed binary identity:** June executable SHA-256, exact CUDA revision,
   startup command, build flags, and run-local model hashes.
2. **GGUF campaign:** raw mutation corpus, deduplication manifest, per-input
   exit status, and the artifact identity behind the `phi3` report label.
3. **Timing:** per-request vectors, ordering/randomization manifest, and the
   original analysis script.
4. **Allocator:** per-repetition JSONs rather than an aggregate-only summary.
5. **LM Studio:** original plaintext log and clean-install/default configuration
   record for the tested daemon/backend.
6. **Mechanism attribution:** complete debugger traces with allocation-site
   evidence for each claimed prompt-bearing representation.
7. **Ollama provenance:** linked executable/version metadata.

Retrieving these artifacts would improve reproducibility and claim strength, but
would not automatically create a new scientific contribution.

## C. New experiments with genuinely high information gain

More trials of the same one-process protocol are not the priority. The following
experiments test boundaries that the current evidence leaves unresolved.

### C1. Two-principal saved-state authorization test

**Hypothesis.** A saved state created by client A can be restored or continued
by client B when both interact with the same server and client B lacks ownership.

**Threat model.** Two mutually distrustful network clients, distinct valid API
keys or credentials, one serving process, no filesystem or process-memory access
for B.

**Necessary controls.** Same-key baseline; distinct valid key; invalid key;
ownership-matched file; ownership-mismatched file; wrong-key file; nonexistent
file; same-slot and different-slot restore; separate-server control; authentication
enabled and disabled.

**Independent success oracle.** Exact victim UUID appears in B's model-visible
continuation or returned content, plus an independently logged unauthorized
restore operation. Token-count equality alone is insufficient.

**Minimal matrix.** Two clients × two credentials × two slot IDs × correct/wrong
ownership × four models, with separate server/process controls. A small balanced
matrix is preferable to more same-process repetitions.

**Expected contribution.** Converts the current same-process state-transfer
observation into a genuine isolation-security result, if positive.

**Could it change novelty?** Yes. This is the single experiment most likely to
move the paper from an empirical case study toward a new serving-isolation
finding, because prior work's main advantage is a real mutually distrustful
principal boundary.

### C2. Process-restart versus in-process model-swap residue

**Hypothesis.** Model-A canary residue survives an in-process A→B replacement
but not a process restart, distinguishing allocator/runtime residue from
persistent storage or model-file state.

**Threat model.** A forensic collector or controlled B request; no claim of
arbitrary unprivileged access unless a separate attacker path is tested.

**Controls.** A→scan; A→B in-process swap→scan; terminate/restart with B→scan;
fresh B process without A→scan; same-model reload; matched prompt length and
allocator settings.

**Independent success oracle.** Exact model-A UUID in B-process memory with
mapping identity, scan scope, and process identity recorded. Separately test
whether B's model-visible output contains A's UUID.

**Minimal evaluation matrix.** Four model-pair blocks used by D4, two process
conditions (in-process/restart), and one matched fresh-process control per pair.

**Expected contribution.** Determines whether D4 is a general runtime-lifetime
effect or merely an allocator artifact and clarifies whether it creates a serving
security consequence.

**Could it change novelty?** Moderately. It would strengthen the distinctive
model-transition mechanism, but would not by itself establish cross-principal
disclosure.

### C3. Pinned provenance replication

**Hypothesis.** The headline residue and state-transfer observations reproduce
under a hash-linked source, binary, model, and runtime manifest.

**Threat model.** Same as the original controlled collector and serving client;
this is a reproducibility question, not a new attacker.

**Controls.** Exact source revision; executable SHA-256; model SHA-256; OS/kernel;
allocator; startup flags; raw per-trial records; analysis script; clean process
and repeated process controls.

**Success oracle.** Predefined agreement of raw observation fields and exact
canary outcomes, not merely matching summary percentages.

**Minimal evaluation matrix.** One representative four-model family and one
Nemotron twelve-tenant or D4 protocol with full provenance.

**Expected contribution.** Raises confidence in the existing result and makes
the framework reproducible.

**Could it change novelty?** No direct novelty increase, but it can prevent
reviewers from discounting the existing contribution as a historical artifact.

### C4. One common boundary across runtimes

**Hypothesis.** A sharply defined boundary, such as post-request prompt lifetime,
exhibits the same evidence-unit behavior under pinned `llama-server`, Ollama,
and LM Studio configurations.

**Threat model.** Same controlled collector and model-visible wrapper tests,
with platform-specific surfaces documented.

**Controls.** Same model hash, prompt canary, prompt length, response settings,
process lifetime, scan scope, and logging configuration wherever the platform
permits; platform-specific negative controls.

**Success oracle.** Exact canary recovery from the same evidence class, with
separate persistence and memory outcomes.

**Minimal evaluation matrix.** Three runtimes × one model × one boundary ×
matched clean/unmodified configurations, repeated across a small number of
independent processes.

**Expected contribution.** Tests whether LLAnalyzer generalizes beyond a
collection of historical protocols.

**Could it change novelty?** Yes, if the same measurement schema transfers
cleanly and reveals a previously unreported common failure pattern; otherwise
it would expose the framework as runtime-specific.

## What not to do

- Do not add more same-process slot trials solely to enlarge 200/200.
- Do not pool byte occurrences, tenants, model outputs, and token-count checks.
- Do not call the authorized memory collector an unprivileged attacker.
- Do not present the historical timing value without its vectors and script.
- Do not infer a causal sanitization effect from the two single-run rows.
- Do not add a new security-vulnerability label without principal, access,
  oracle, and provenance controls.

## Recommended contribution structure

1. **Problem and boundary model:** local execution is not a complete
   confidentiality guarantee; define four lifecycle boundaries and their
   evidence classes.
2. **Measurement method:** UUID attribution, boundary-specific acquisition,
   evidence ledger, and explicit stopping rules.
3. **Empirical findings:** runtime residue and D4 model-swap residue as the
   central result; wrapper, GGUF, GPU, and telemetry results as scoped supporting
   observations.
4. **Security-boundary limits:** same-process slot behavior is not principal
   isolation; timing, authorization, and device-memory claims remain untested.
5. **Reproducibility and deployment implications:** exact retained evidence,
   missing artifacts, and concrete controls for lifecycle-wide prompt handling.

