# LLAnalyzer novelty-rescue decision gate

Date: 2026-10-11

Scope: decision analysis only. This report does not modify the manuscript,
historical records, experiment scripts, or figures, and no experiment or server
was executed.

## Decision

Candidate **A (cross-principal saved-state authorization and isolation)** is the
stronger novelty-rescue experiment, but only as a new, provenance-pinned
experiment. The smallest meaningful gate is a two-principal API test on one
pinned model and one server, with two distinct valid keys, an exact canary
disclosure oracle, and authentication/ownership controls. If that test is
positive, it can convert the current same-process state-transfer observation
into a genuine serving-isolation result. If it is negative, the paper should
retain the current scoped state-transfer claim and should not claim an
authorization failure.

Candidate **B (controlled lifecycle residual-state sanitization)** is a weaker
novelty rescue. It could establish a causal mitigation result, but it would
mainly strengthen an existing runtime-memory finding and would require a larger
matched treatment/control study. Existing Remediation 2 artifacts are synthetic
buffer controls, not model-backed memory evidence (`remediation2/README.md:10--24`).

The recommendation is therefore: **GO for a small A feasibility experiment;
DO NOT expand to a four-model campaign unless the principal-boundary oracle is
positive and the provenance gate passes.**

## 1. Candidate comparison against closest prior work

| Candidate | What it would add | Overlap risk | Minimum evidence needed | Novelty judgment |
|---|---|---|---|---|
| A. Two-principal saved-state authorization | Whether a valid authenticated client B can use a saved state created by valid client A, and whether A's exact canary reaches B's response | PROMPTPEEK and related work already demonstrate stronger mutually distrustful multi-tenant KV leakage; a same-process, same-credential result is not competitive | Distinct valid credentials; B has no filesystem or process-memory access; API-level unauthorized restore; exact canary in B-visible output; invalid-key and separate-server controls | **Highest potential**. It tests the missing principal boundary directly and differentiates LLAnalyzer from its current one-client protocol |
| B. Controlled lifecycle sanitization | Whether a specified zeroization intervention changes canary recoverability under matched runtime conditions | Sanitization and cache-isolation defenses are already active prior-work areas; a confounded 110/78 single-run comparison cannot establish efficacy | Hash-linked binary/patch; identical model and startup flags; randomized treatment/control processes; repeated memory scans; process-restart and clean-process controls | **Moderate methodological value**, lower novelty per unit effort |

The closest-work matrix already identifies PROMPTPEEK, Shadow in the Cache,
Cache Me, Catch You, local-LLM memory forensics, and local-privacy frameworks as
the comparison set. PROMPTPEEK's defining advantage is an actual mutually
distrustful principal boundary, not merely cache-state recovery
([NDSS paper](https://www.ndss-symposium.org/ndss-paper/i-know-what-you-asked-prompt-leakage-via-kv-cache-sharing-in-multi-tenant-llm-serving/)).
Shadow in the Cache evaluates direct KV privacy attacks and a defense
([NDSS paper](https://www.ndss-symposium.org/ndss-paper/shadow-in-the-cache-unveiling-and-mitigating-privacy-risks-of-kv-cache-in-llm-inference/)).
Local memory-forensics work already establishes that local LLM artifacts can be
recoverable ([Murtuza](https://arxiv.org/abs/2603.23996),
[Xu et al.](https://sp2026.ieee-security.org/program.html)). Candidate A
therefore targets the clearest untested distinction; candidate B mostly makes
the existing residue result more causal.

## 2. Candidate A: security-boundary feasibility

### 2.1 What the local server contract actually exposes

The retained Remediation 2 source provides a concrete, inspectable API
contract, but it is a later engineering source and is **not evidence that the
June executed binary was identical**. It is useful for feasibility and test
design, not historical provenance.

* Authentication is a server-wide bearer-key gate. The middleware accepts no
  key when the configured key list is empty; otherwise it reads `Authorization`
  or `X-Api-Key`, strips `Bearer `, and authorizes when the presented value is
  a member of the configured list (`remediation2/source/combined/tools/server/server-http.cpp:191--217`).
  The command-line documentation permits multiple comma-separated keys
  (`remediation2/source/combined/tools/server/README.md:200--201`).
* The middleware runs before route dispatch for non-public requests
  (`server-http.cpp:270--287`). Thus a distinct valid key can be used as a
  network-level client identity for the experiment, but the inspected code does
  not attach an identity to a slot or saved file.
* The `/slots/{id_slot}` route exposes save, restore, and erase actions when
  `--slot-save-path` is configured (`server-context.cpp:4559--4589`; README
  `:213`, `:1069--1109`).
* Save and restore accept a validated filename, concatenate it with the one
  server-wide slot-save directory, and enqueue the action
  (`server-context.cpp:5166--5219`). The inspected handler has no key-to-file,
  key-to-slot, ownership, or tenant lookup.
* The task executor loads the named file into the requested slot and returns
  `n_restored` when the load succeeds (`server-context.cpp:2568--2613`). The
  documented response reports the restored token count and bytes, not an
  owner identity (`README.md:1089--1107`).

This establishes **feasibility of testing an authentication-versus-authorization
gap** in the retained source. It does not establish that the historical June
binary had exactly this implementation, nor does it predict a new experimental
result.

### 2.2 Boundary definition

The experiment must define the boundary narrowly:

* Principal A and principal B are two network clients using distinct valid
  bearer keys accepted by the same server.
* B has no access to the slot directory, process memory, filesystem APIs, or
  server administrator privileges.
* A creates a canary-bearing slot state and saves it. B is given the filename
  as an attack input; filename secrecy is not treated as authorization.
* The security question is whether B can restore A's state and cause A's exact
  canary to appear in B's model-visible response.

This is stronger than the retained one-process experiment, but it is still an
implementation-specific serving-interface test. It is not a claim about all
llama.cpp deployments, all local LLM runtimes, or remote multi-tenant systems.

## 3. Smallest scientifically meaningful experiment

### Hypothesis

With slot saving enabled and authentication enabled, a valid client B holding a
different accepted key can restore a state saved by valid client A and obtain
A's exact canary in a subsequent model response, because the server associates
authorization with the HTTP request but not with slot/file ownership.

### Minimal setup

* One freshly built, hash-recorded server binary and one hash-recorded model.
* One server process, loopback or a private test interface, and a dedicated
  slot-save directory readable only by the server account.
* Two distinct valid keys (`A`, `B`) configured before startup.
* One fixed prompt template containing a random UUID canary and one fixed
  continuation prompt that asks for the preceding confidential token.
* External client-side transcript recording: logical principal label, key label
  (never the secret itself in the report), endpoint, slot, filename, status,
  response fields, timestamp, and server process identity.

### Minimal per-trial sequence

1. A submits the canary-bearing prompt to slot 0.
2. A saves slot 0 to a random filename.
3. B, using key B and no local file access, restores that filename into slot 1.
4. B submits a continuation request to slot 1.
5. Record both the restore response and whether B's response contains the exact
   canary. Erase the slot/file after the trial.

The first experiment should use one representative model and ten independent
server-process trials. The trial count is a proposed design parameter, not a
result. If the positive oracle is deterministic, the four-model replication can
follow as a second gate; adding four models before establishing the boundary
would spend effort on breadth without answering the novelty question.

### Controls

| Control | Expected interpretation |
|---|---|
| A saves, A restores with key A | Same-principal functionality baseline |
| A saves, B restores with key B | Decisive cross-principal authorization condition |
| A saves, invalid key restores | Authentication control; must be rejected |
| B restores a nonexistent/random filename | File-existence/error control |
| B is given a filename from a different trial | Prevents accidental state attribution |
| Separate fresh server without A's file | Process/server isolation control |
| Direct filesystem read by B is denied | Confirms the observation is through the API, not filesystem access |
| Authentication disabled, if safely isolated | Positive protocol baseline only; not evidence about authenticated authorization |

The minimal decisive contrast is A-save/B-restore versus invalid-key restore,
with A-save/A-restore as a functionality baseline. A wrong-key *file* is not a
native llama-server concept; it must not be described as a built-in control
unless the experiment adds an external ownership layer.

### Success oracles

Use two tiers and report them separately:

1. **Unauthorized state-use oracle:** B's authenticated restore returns success
   and `n_restored > 0` for a file created by A, while B cannot read the file
   directly.
2. **Confidentiality oracle:** B's subsequent model response contains A's exact
   UUID canary. This is the result that supports a confidentiality claim.

`n_saved == n_restored` alone is insufficient: it measures token-count/state
   transfer, not principal authorization or secret disclosure. A model that
   refuses to repeat the canary may still yield a successful state-use event;
   that case must be reported separately rather than treated as a negative
   authorization result.

### Evidence package required for a positive result

Retain the full source commit, executable SHA-256, model SHA-256, startup
arguments, API-key configuration schema (with key values redacted), client
transcripts, raw JSON responses, server logs, process IDs, slot-save directory
metadata, filesystem-permission checks, and a machine-readable per-trial
manifest. Include an explicit statement that the result is a new experiment,
not a reclassification of the June records.

## 4. Go/no-go criteria

### GO / novelty-positive

Proceed to the four-model replication only if all of the following hold:

* B's valid distinct key is accepted by the same server;
* invalid-key control is rejected;
* B restores A's named state through the API without filesystem access;
* the event repeats across the proposed independent process trials; and
* at least one controlled B response contains A's exact canary, with the
  transcript and process/file evidence linked.

The paper could then claim an implementation-specific cross-principal
saved-state isolation failure, bounded to the tested server configuration. It
would still need comparison with PROMPTPEEK and Cache Me, Catch You rather than
claiming the first multi-tenant cache leak.

### NO-GO / do not make the security claim

Do not claim a cross-principal authorization failure if:

* the server accepts only one global key and cannot represent two principals;
* B's restore succeeds only because B has filesystem or process-memory access;
* `n_restored` is positive but no principal-linked transcript exists;
* the canary appears only in a researcher-side memory scan, not B's response;
* the source/binary/model manifest is incomplete; or
* the result is negative or inconsistent across controls.

In a NO-GO case, retain the existing same-process state-transfer wording and
use the experiment as a boundary characterization, not as a vulnerability.

## 5. Candidate B: why it is not the first gate

Candidate B is feasible only after a provenance-pinned intervention is available.
The retained Remediation 2 source includes zeroization code and synthetic unit
tests, but its README explicitly says that no model-backed inference,
process-memory acquisition, full comparison, or new latency result was run
(`remediation2/README.md:20--24`). A scientifically adequate B study would need:

* one exact binary pair differing only in the zeroization treatment;
* identical model, prompts, allocator, context, threads, and offload settings;
* independent fresh processes randomized to treatment/control;
* memory scans at fixed post-request checkpoints;
* process-restart and clean-process controls; and
* a canary-recovery oracle that distinguishes byte occurrences, unique canaries,
  and model-visible disclosure.

That design could support a causal mitigation statement. It would not, by
itself, answer the strongest novelty objection: whether LLAnalyzer demonstrates
a security boundary that prior work did not already exercise. It should be the
fallback experiment if candidate A is technically impossible or negative.

## 6. Final recommendation

The smallest scientifically meaningful novelty-rescue experiment is:

> **One hash-linked server/model, two distinct valid API keys, one shared
> saved-state directory, a network-only B client, exact-canary continuation,
> invalid-key and fresh-server controls, and a small repeated process matrix.**

Candidate A is the decision gate. Candidate B is a secondary reproducibility and
mitigation study, not the first novelty rescue. Until candidate A produces the
required principal-linked oracle, the manuscript should continue to describe
slot behavior as same-process state transfer and should not use it to claim
cross-principal authorization failure.

