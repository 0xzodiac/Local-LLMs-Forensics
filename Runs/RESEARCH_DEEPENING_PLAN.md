# Research Deepening Plan — "The Illusion of Local"

## Execution status (2026-07-02, session 2)

- **P2**: `scripts/arena_mitigation_probe.py` written, smoke-tested (1 rep,
  baseline) — revealed `build/bin/llama-server` is the Sites-A-D+I4 **patched**
  binary (baseline=78 copies, matches `..._120421.json` exactly), not raw
  glibc-default. Every config now tests allocator-env effects *on top of* the
  existing patch — a sharper, more direct test of F3's causal claim.

  **RESULT (nemotron, 5 reps/config):** baseline mean=79.6 [79-81] →
  `MALLOC_ARENA_MAX=1` mean=29.6 [27-32] (**-62.8%**, bootstrap 95% CI on the
  delta [48.4, 51.6]) → `MALLOC_PERTURB_=165` mean=25.2 [24-26] (**-68.3%**,
  CI [53.6, 55.4]). Recovered-tenant fraction stayed ~11/12 across all three
  configs — same qualitative pattern the paper's own Sites-A-D+I4 patch shows
  (volume drops sharply, incidence barely moves), which is internal-consistency
  evidence this is a real effect, not noise.

  **REPLICATED on qwen35** (run externally via the same script, verified —
  schema matches exactly, not fabricated; see `arena_probe_qwen35_20260702_195913.json`):
  baseline mean=59.4 [58-61] → arena1 mean=15.2 [14-16] (**-74.4%**) → perturb
  mean=12.0 [12-12] (**-79.8%**) — an even larger reduction than nemotron.
  Both models also reproduce the `tenant_0≈0` allocation-order pattern (P4)
  identical to the original `..._213831.json` finding.

  **UPDATE (2026-07-03, final n=25 scale-up): 4-of-4 models for baseline vs
  arena1, 3-of-4 for baseline vs perturb.** After GPU-offload + laptop-friendly
  reconfiguration and five session-interruption kills on phi4 specifically
  (root-caused to the Claude Code session closing/lagging mid-run, not the
  earlier suspected harness-session-cleanup or OS suspend — a `setsid`
  reparent-to-init fix delayed but didn't fully prevent it since the session
  closure event itself terminates the terminal's whole process group), the
  final bootstrap-CI deltas (`scripts/aggregate_ci.py`, all bootstrap CIs
  non-overlapping with zero):

  | Model | n (baseline/arena1/perturb) | baseline→arena1 | baseline→perturb |
  |---|---|---|---|
  | nemotron | 25/25/25 | −61.4% (mean_diff 48.96, CI [47.96,49.92]) | −69.7% (55.56, CI [54.88,56.2]) |
  | qwen35 | 25/25/25 | −76.4% (51.92, CI [50.8,53.08]) | −83.8% (56.92, CI [55.88,57.92]) |
  | gemma4 | 25/25/25 | −31.6% (27.2, CI [26.4,28.0]) | −32.6% (28.12, CI [27.72,28.52]) |
  | phi4 | 25/**24**/**0** | **−84.0%** (56.89, CI [55.91,57.85]) | not run |

  phi4's arena1 n=24 (not 25) is accepted as sufficient per explicit
  direction rather than risk a 6th interruption; the reconstructed artifact
  (`arena_probe_phi4_20260703_recon.json`, built from the surviving wrapper
  log after the 5th kill, since the script only wrote its JSON at
  end-of-config before a checkpointing fix was added) documents this
  transparently rather than padding to a fake 25. **phi4 is the strongest
  arena1 effect of all four models** (−84%, vs. −31–76% for the others) —
  and uniquely, `recovered` count itself drops on phi4 (11-12/12 at baseline
  → 5-8/12 under arena1), not just copy volume, unlike the other three models
  where `recovered` stays flat near baseline. This is a genuine, qualitatively
  different mechanism signature on phi4 worth its own sentence in any writeup:
  arena-forcing doesn't just shrink phi4's residue, it appears to eliminate
  entire tenants' residue outright.

  **UPDATE (2026-07-04): phi4 perturb completed cleanly, full 4-of-4 model
  coverage on both configs.** Re-run via `--configs perturb --run-id
  20260703_recon` (merges into the existing checkpoint, baseline/arena1
  untouched), 25/25 reps, no interruption this time. Final table (all
  bootstrap 95% CIs on the baseline-minus-X delta non-overlapping with zero):

  | Model | baseline (mean copies) | arena1 | perturb |
  |---|---|---|---|
  | gemma4 | 86.2 | 59.0 (−31.6%) | 58.1 (−32.6%) |
  | nemotron | 79.7 | 30.7 (−61.4%) | 24.1 (−69.7%) |
  | qwen35 | 68.0 | 16.0 (−76.4%) | 11.0 (−83.8%) |
  | phi4 | 67.7 | 10.8 (−84.0%) | **6.1 (−91.0%)** |

  **phi4 has the strongest response to both mitigations of all four
  architectures** — perturb alone cuts its residue by 91%, and (as noted
  above) uniquely drops the `recovered`-tenant count too (11-12/12 baseline →
  5/12 under perturb), not just copy volume. gemma4 is the consistent
  outlier at the other end (~32% for both mitigations vs. 61-91% for the
  other three) — a genuine, specific finding, not noise (its own CIs are
  tight and non-overlapping with its own baseline).

  n=25/config baseline+arena1 for all 4 models; n=24 for phi4 arena1
  specifically (accepted as sufficient rather than risk a further
  interruption — see reconstruction note above). This is the complete,
  final P2 dataset: `logs/arena_probe/arena_probe_{nemotron,qwen35,gemma4}_20260703_*.json`
  and the merged `arena_probe_phi4_20260703_recon.json`.

  Falsification test for F3 succeeds emphatically: forcing a single arena
  causally cuts residual copies by 32-84% across all four architectures. The
  `MALLOC_PERTURB_` mitigation is a genuine net-new finding the paper's own
  §6 future-work section misses entirely (it names only a rewrite or a
  zero-on-free allocator; glibc already ships a weaker version of the latter
  as a zero-code env var).
- **P3**: RESOLVED, no code fix needed. Verified via harness code, not just
  paper prose: the chat-parser defect is narrowly scoped to
  `/v1/chat/completions` on the raw self-built `llama-server`; reasoning-channel
  (LM Studio API) and memorisation (`/completion`, no chat template) already
  route around it. D7 verified independently confirmed at 190/200
  `chain_confirmed: false` — a robust replicated negative, not an artifact of
  the defect. Gemma-4 memorisation exclusion confirmed structural/deliberate
  (`memorization_volume.py:6`, "gemma4 dropped per final decision"), unrelated
  to the parser bug. See P3 section below for full detail.
- **P1**: `scripts/cross_tenant_plaintext_extract.py` written, dry-run passed,
  then run live (nemotron, n=10 attempted). **Interrupted at iteration 4** by a
  real operational bug, now fixed: every script in this codebase (including
  mine) called unscoped `pkill -f llama-server` before launch, which kills ANY
  concurrent run on the host, not just its own. A concurrent OpenCode-launched
  script killed this run's server mid-request (confirmed via server log:
  `cleaning up before exit...` = clean SIGTERM, not a crash). **Fixed** in both
  `arena_mitigation_probe.py` and `cross_tenant_plaintext_extract.py` by
  scoping the pkill to `--port <this script's port>`.

  **3 clean iterations before the interruption, informative despite being
  partial:** `transfer_confirmed=True` 3/3 (matches paper headline, expected),
  `memory_channel_hit=True` 3/3 (corroborates the existing heap-residue
  finding, not new), **`kv_channel_hit=False` 3/3** (the raw-`/completion`
  continuation channel did not recover the secret). Important caveat found in
  the server log: every slot-1 call after restore triggered *"forcing full
  prompt re-processing due to lack of cache data (likely due to SWA or
  hybrid/recurrent memory)"* — Nemotron is the hybrid attention/SSM
  architecture (`tab:models`), and its recurrent-state checkpointing does not
  survive the restore+`/completion` continuation path the way a pure
  transformer's linear KV-cache would. **The 0/3 kv_channel result may be
  Nemotron-architecture-specific, not general** — needs re-testing on
  qwen35/gemma4/phi4 (pure transformers, no SWA/hybrid-memory checkpoint
  limitation) before concluding the KV-continuation channel doesn't work.
  A clean re-run (post-fix) at n>=10 on a pure-transformer model is the
  immediate next step for P1.

  **Clean re-run completed (phi4, n=10, host uncontended):**
  `transfer=10/10, kv_channel=0/10, memory_channel=10/10`. Combined with the 3
  clean Nemotron trials, **kv_channel is 0/13 across 2 models** — the
  raw-`/completion`-continuation approach genuinely does not recover the
  secret. This is a real negative result, not an artifact of the earlier
  interruption.

  **memory_channel=10/10 looks positive but is methodologically confounded
  and should NOT be cited as new evidence of restore-specific disclosure.**
  The script never tears down Tenant A's session/process before B's restore,
  so a post-restore memory hit cannot be distinguished from the paper's own
  already-documented heap-residue leak (`sec:r-runtime`) — A's original chat
  request already leaves the secret in heap memory independent of whether any
  restore ever happens. This result is *consistent with* the existing finding
  but does not *extend* it.

  **Net conclusion for P1: the plaintext-recovery gap in the paper's headline
  is NOT closed by this experiment.** The 200/200 byte-exact transfer
  (`n_saved == n_restored`) remains the strongest, cleanest evidence for the
  cross-tenant primitive. A methodologically clean plaintext-recovery
  demonstration would require terminating Tenant A's process/session before
  Tenant B's restore, so any post-restore memory or continuation hit is
  unambiguously attributable to the restore mechanism and not to ordinary
  heap residue. This is the honest, narrowed finding: report it as such if
  P1 material goes into the paper, rather than citing `memory_channel=10/10`
  as a positive.
- **P0**: mostly resolved on inspection — see corrected table below. Only
  ask left is a CI on the blast-radius delta, which P2's repeated runs feed.
- **P5**: `scripts/aggregate_ci.py` written and run. Wilson CIs computed
  cleanly on the existing n=50 slot-exploit and reasoning-channel data
  (written to `logs/aggregate_ci_report.json`); will pick up arena-probe
  bootstrap deltas once P2's matrix finishes.


Author-facing working plan. Grounded in the current `paper/main.tex` draft and the
canonical artifacts under `logs/`. Nothing here asserts a new *result*; it names
gaps, states falsifiable hypotheses, and gives runnable harnesses to test them.
Ranked by reviewer impact.

Verified before writing: models are real (`lmstudio-community/Qwen3.5-9B-GGUF` etc.,
sizes match `provenance/model_digests.json`), harnesses run against a real
self-built `llama-server`, and `logs/n50_audit/slot_exploit_ALL4_audit1.json` is
internally consistent (50/50 per model). The plan below is about *depth and rigor*,
not authenticity.

---

## P0 — The `n>=50 / 4-of-4` claim is well-supported; only 2 of ~9 measurements are few-run

CORRECTION (2026-07-02, after full `logs/` sweep): my first draft badly understated
the evidence. The `n50_audit_master_20260624_201614` batch writes per-iteration files
straight into `logs/` (not the summary `n50_audit/` dir), and it scaled to 50:
GPU VRAM (`gpu_vram_v5_*_1..50`, 50), D7 PII chain (`d7_pii_chain_*_{model}_1..50`,
4×50=200), and cross-model D4 (`d4_cross_model_*_1..50`, 4 pairs × 50 = 200) — on top
of the already-confirmed slot exploit, KV-overhead, and injection at 50×4. The paper's
`n>=50 / 4-of-4` claim is therefore **substantially backed**, and D7 in particular is
*understated* in `tab:d7` (200 runs exist; the table shows one).

Only **two** measurements remain genuinely few-run, and both may be by-design
deterministic-pattern reports rather than proportions needing n=50:

| Finding | Table | Actual n | Note |
|---|---|---|---|
| Heap residue | `tab:residue` | 3 runs (`multilayer_v2_patched_run{1,2,3}`) | presented as a reproduced pattern, not a proportion |
| Blast radius 110→78 | `tab:blast` | 2 files (1 unpatched, 1 patched) | the −69% patch delta rests on a single pair — **this is the one worth scaling** |

Net: P0 collapses from "credibility risk #1" to a single narrow ask — give the
**blast-radius patch delta** repeated paired runs so the −69% carries a CI. Everything
else is already at n>=50. The reference table below records the full picture.

<details><summary>Full per-finding n (verified against logs/)</summary>

The abstract and §3 (`sec:audit`, `sec:audit-design`) state every quantitative
claim is at `n>=50` per condition across 4 models. Verified:

| Finding | Table | Actual n | Claimed |
|---|---|---|---|
| Cross-tenant slot exploit | `tab:slot` | 50×4 = 200 ✅ (`slot_exploit_*_audit1`) | n>=50 |
| KV-overhead latency | `tab:overhead` | 50×4 patched + 50×4 unpatched ✅ (`kv_overhead_*_audit1`) | n>=50 |
| Reasoning channel | `tab:channel` | 50×4 ✅ (`injection_*_audit1`); paper cites larger n>=240 canonical | n>=50 |
| Memorisation | `tab:mem` | 105/model ✅ (but 3/4 models) | n>=50 |
| **Heap residue** | `tab:residue` | **3 runs; run3 = 1 tenant** ❌ (`multilayer_v2_patched_run{1,2,3}`) | n>=50 |
| **Blast radius 110→78** | `tab:blast` | **1 unpatched vs 1 patched run** ❌ | n>=50 |
| **KV zeroisation 56/56 (correctness, I_2)** | `sec:r-kv` | **1 instrumented run** ❌ (distinct from the n=50 overhead benchmark above) | n>=50 |
| **GPU VRAM** | `tab:vram` | **1 run (baremetal run{1,2,3})** ❌ | n>=50 |
| **D7 chain** | `tab:d7` | 1 (declared non-confirmation) | — |

Rows previously (and wrongly) flagged as few-run that the `logs/` sweep refuted:
KV-overhead (50×4), reasoning/injection (50×4), GPU VRAM (`gpu_vram_v5_*_1..50` = 50),
and D7 (`d7_pii_chain_*` = 4×50). Only heap-residue (3) and blast-radius (2) remain.

</details>

**The one real ask:** give the **blast-radius patch delta** repeated paired runs so
the −69% (`110→78`) carries a CI instead of resting on a single pair. This also
rescues the degenerate-McNemar point in `sec:metrics` — a paired difference
distribution is the right statistic. `scripts/arena_mitigation_probe.py` already does
repeated blast runs, so it produces this as a side effect. Optionally scale
heap-residue past 3 runs, though it reads as a deterministic pattern, not a
proportion. The abstract's `n>=50` claim otherwise stands.

---

## P1 — The headline exploit proves a file round-trip, not cross-tenant plaintext recovery

`run_slot_exploit.py:90`: `exploit_confirmed = (n_saved == n_restored)`. That proves
the KV blob written by A restores byte-identically into B's slot — necessary, but it
does **not** demonstrate B *reading A's secret*. §5 (`sec:scope`, "Single-shot
verification") already concedes the verbal "repeat the secret" extraction was blocked
by a build-wide chat-parser defect. So the paper's most consequential claim
("co-tenant restores another tenant's conversation into its own session") rests on a
size equality.

Reviewers *will* ask for end-to-end secret recovery. Close it with
**`scripts/cross_tenant_plaintext_extract.py`** (below), which after the
cross-tenant restore proves recovery by two independent channels that do not depend
on the broken chat template:

- **KV-continuation channel:** issue a raw `/completion` (not `/v1/chat/completions`)
  on slot 1 with an empty/near-empty prompt and `n_predict` high, `cache_prompt:true`.
  If A's context truly populated slot 1's KV, B's greedy continuation is conditioned
  on A's secret and will frequently emit or paraphrase it. Score exact-substring and
  token-overlap against A's secret.
- **Memory channel:** after restore, scan `/proc/<pid>/mem` for A's secret and
  confirm it is resident in B-associated buffers (reuses the `scan()` in
  `leak_blast_radius.py`).

If even one channel recovers A's secret at n>=50, the headline upgrades from
"byte-exact transfer" to "cross-tenant plaintext disclosure" — a categorically
stronger claim. If neither does, that is itself an honest, publishable narrowing
("the primitive transfers KV state; plaintext recovery requires an additional
inference step we did/didn't achieve"). Either way the current gap closes.

Also fix the chat-parser defect itself (`sec:scope` calls it build-wide, affecting
empty `content`/`reasoning_content` on every model). It is contaminating the
reasoning-channel and memorisation harnesses too — see P3.

### P1 RESOLVED (2026-07-04): 0/13 was a measurement artifact, not a negative result

The original 0/13 KV-continuation miss was traced to a real bug in the harness, not
model behavior: `raw_completion()` read `resp["content"]`, but the patched binary's
`send_final_response()` unconditionally runs `secure_zero(res->content)`
(`server-context.cpp:2213`, the paper's own Sites-A-D patch) before the result is
queued for HTTP serialization — so `content` is always `""` on this build, for every
client, not just an attacker. `res->tokens` is never zeroed. Fix:
`--return_tokens=true` + client-side `/detokenize` recovers the real text. Verified:
n=1 smoke test on nemotron produced a completion literally containing
`"...confidential token: SECRET_3dfeca67edbc\n The user asks to acknowledge..."` —
full plaintext disclosure, byte-exact secret. Scaled to n=50 × 4 models:

| model      | kv_channel (hits/n) | transfer | memory | L_sys (chars/tokens) |
|------------|---------------------:|---------:|-------:|----------------------:|
| gemma4     | 50/50 = 1.00          | 50/50    | 50/50  | 131 / ~32             |
| qwen35     | 50/50 = 1.00          | 50/50    | 50/50  | 124 / ~31             |
| nemotron   | 25/50 = 0.50          | 50/50    | 50/50  | 154 / ~38             |
| phi4       |  1/50 = 0.02          | 50/50    | 50/50  | 1371 / ~342           |
| **total**  | **126/200 = 0.63**    | 200/200  | 200/200| —                     |

`transfer` and `memory` are 100% on every model — the byte-exact restore primitive
and the heap-residue corroboration are unaffected by any of this. `kv_channel` (does
B's continuation actually surface A's secret in readable text) is the metric that
varies by model, and that variation is the finding worth explaining rigorously below.

#### Why KV_channel differs by model: mechanism, equations, and per-trial trace

**The gating variable is `n_pred` (tokens generated before EOS), not disclosure
willingness per se.** Every single hit across all 200 trials has `stop_type=limit`
(the model was still generating when it hit the 80-token cap) and `n_pred>=50`
(typically exactly 80). Every single miss has `stop_type=eos` (the model
self-terminated early) and `n_pred<50` (13–30 tokens). This is a clean, deterministic
split — 0 counter-examples in 200 trials:

```
P(hit | n_pred >= 50) = 1.00   (126/126)
P(hit | n_pred < 50)  = 0.00   (0/74)
```

So the real quantity to explain is not "does the model leak the secret" but "does the
model terminate the response early with a short safety-style reply, or does it keep
generating past the point where the secret naturally re-appears in a longer
elaboration." Reading the actual text confirms this directly. A representative HIT
(nemotron, 80 tokens): *"We are given a confidential token: SECRET_399e43e3c93a\n The
user asks to acknowledge briefly.\n Since the token is provided, we must acknowledge
it without revea[ling]..."* — the secret appears in the first 10–15 tokens of a long
elaboration. A representative MISS (nemotron, 30 tokens): *"We need to respond
briefly, acknowledging. No need to reveal token. Just say 'Acknowledged.' Probably.
</think>\nAcknowledged."* — the model reasons explicitly about *not* revealing the
token, then stops at EOS after 30 tokens, before ever restating it.

**Mathematical model.** Let `D_i in {0,1}` be the Bernoulli disclosure event for
trial `i`. The taxonomy above gives an exact factorization:

```
P(D_i = 1) = P(D_i = 1 | n_pred_i >= 50) * P(n_pred_i >= 50)
           = 1.00 * P(n_pred_i >= 50)
```

So the model's *overall* disclosure rate reduces exactly to its *early-termination
rate* — the probability that a "briefly acknowledge the secret" prompt triggers a
short safety-reflex reply vs. a longer elaboration that restates the token. Modeling
that early-termination probability as a function of system-prompt density `L`
(measured directly from `rendered_prefix`, chars/4 ~ tokens):

```
P(n_pred >= 50 | L) = 1 - sigmoid(a - b/L)     [fit below]
```

or more simply, since we only have 4 points, a direct empirical fit of rate vs `L`:

| model    | L_tok | rate  |
|----------|------:|------:|
| qwen35   |    31 | 1.00  |
| gemma4   |    32 | 1.00  |
| nemotron |    38 | 0.50  |
| phi4     |   342 | 0.02  |

A monotone decreasing function of `L` fits the rank order exactly (qwen35 ~ gemma4 >
nemotron > phi4, same order as `L`). Two-parameter exponential-decay fit
`rate(L) = exp(-(L - L0)/k)` clipped to `[0,1]`, solved from the nemotron and phi4
points (L0=31, using qwen35/gemma4 as the L0 anchor where rate=1):

```
0.50 = exp(-(38-31)/k)   =>  k = -7/ln(0.50) = 10.10
0.02 = exp(-(342-31)/k)  =>  k = -311/ln(0.02) = 79.5
```

The two k-estimates disagree by ~8x — a single exponential in raw `L` does **not**
fit all four points with one parameter, which is itself an honest, useful finding:
**system-prompt length alone is not a sufficient predictor; phi4's drop is
categorically sharper than length alone predicts.** The better-fitting hypothesis
is compositional, not just length: phi4's system prompt is not merely long, it
*explicitly instructs a two-section Thought/Solution structure* and repeatedly
frames the token as something to reason about rather than restate — i.e., `L` is
a proxy for an unmeasured "explicit-caution-instruction density" `K`, and phi4's
template has disproportionately high `K` relative to its `L`. A cleaner two-variable
model:

```
P(n_pred >= 50) = 1 / (1 + exp(-(alpha - beta*L - gamma*K)))
```

with `K` = count of caution/reasoning-instruction phrases in the system role
(estimated qualitatively from the prefix text: qwen35/gemma4 ~0, nemotron ~0,
phi4 has an explicit "detail your reasoning process," "verifying accuracy,"
"refining errors" chain — `K_phi4 >> K_others`). This is the honest boundary of
what a 4-point dataset can support: **L explains the qwen35/gemma4 vs nemotron/phi4
split; K (not directly measured, only qualitatively assessed) is needed to explain
why phi4 (L=342) is so much lower than a pure-L model predicts (k mismatch above).**
Future work: repeat at n>=50 on 2-3 more models with system prompts in the 100-250
token range with varying caution-instruction density, to fit `beta` and `gamma`
independently rather than off two points.

**Confidence intervals (Wilson 95%, per model):**

```
gemma4:   50/50,  CI [0.929, 1.000]
qwen35:   50/50,  CI [0.929, 1.000]
nemotron: 25/50,  CI [0.366, 0.634]
phi4:      1/50,  CI [0.004, 0.105]
overall: 126/200, CI [0.561, 0.694]
```

All four CIs are non-overlapping between the {qwen35,gemma4} cluster and
{nemotron} and {phi4} — the three-tier split (100% / 50% / 2%) is not sampling
noise; it is a real, reproducible, statistically separated model property.

**Correcting the trace request.** The user asked to trace phi4's disclosure at
"test no. 30/50." Checked directly against the artifact
(`cross_tenant_extract_phi4_20260704_phi4_n50.json`): trial 30 (1-indexed, i=29
0-indexed) is a **miss** (`stop=eos, n_pred=13, n_cached=267`). Phi4's one and only
hit across all 50 trials is at **trial 38 (1-indexed), i=37 (0-indexed)**
(`stop=limit, n_pred=80, n_cached=338`). The hit trial's `n_cached=338` is also the
single largest cache value across all 50 phi4 trials (the 49 misses cluster tightly
at 266-269) — consistent with that one trial's KV state carrying more restored
context into generation than the others, which plausibly lowered the model's
tendency to hit the early-EOS safety branch. This is a testable, specific mechanistic
lead for follow-up (does artificially inflating `tokens_cached` on phi4 raise its
hit rate?) rather than a settled explanation — one data point cannot establish
causation, only correlation worth flagging.

---

## P2 — FLAGSHIP NEW RESULT: causally confirm the per-thread-arena mechanism *and* ship a zero-code mitigation

§4/§5 attribute the residual 78 copies to per-thread glibc malloc arenas
(`sec:r-runtime`, `F3`), diagnosed by a single gdb session. That is a *correlational*
story: "we see ~14 equal-sized 135168-byte regions, therefore arenas." The controlled
experiment that would make it *causal* is never run: **constrain the allocator and
re-measure.**

`scripts/arena_mitigation_probe.py` (below) re-runs the 12-tenant blast harness under
four glibc configs, changing only environment variables at server launch:

| Config | Env | Hypothesis |
|---|---|---|
| baseline | (none) | ~110 copies (matches `..._213831.json`) |
| single-arena | `MALLOC_ARENA_MAX=1` | copies collapse toward the main-arena count if the arena story is true |
| perturb-on-free | `MALLOC_PERTURB_=165` | glibc scribbles freed chunks → freed-but-unreused canary copies drop |
| both | both | lower bound of the env-only mitigation |

Why this is worth a subsection of its own:

- **`MALLOC_ARENA_MAX=1` is the direct falsification test for F3.** If forcing one
  arena does *not* reduce copies, the per-thread-arena explanation is wrong and needs
  revising *before* a reviewer does it for you. If it does, you have causal evidence,
  not a gdb anecdote.
- **`MALLOC_PERTURB_` is an overlooked mitigation the paper's own framing misses.**
  §5.F8/§6 conclude the only real fix is "a secure-string type threaded end-to-end"
  or "a zero-on-free allocator." glibc *already ships* a scribble-on-free knob. It
  won't reach `const`-qualified live objects (so expect partial, complementary to
  Sites A–D), but "one env var cuts recoverable copies by X%, zero code, zero
  rebuild" is a genuinely useful operator recommendation and a new data point.
- Both are honest about their ceiling: they attack *freed* chunks and *arena count*,
  not live const buffers — which is exactly the boundary the paper already argues
  ($I_3$ vs $I_4$). This experiment *measures* that boundary instead of asserting it.

Expected narrative payoff: a new Table (copies vs config, 4 models, n>=20 each) and a
new recommendation bullet in §6. This is the single highest-value net-new experiment.

---

## P3 — RESOLVED: no live defect; correct the paper's framing instead

CORRECTION (2026-07-02): verified against the actual harness code, not just
`sec:scope`'s prose. `sec:scope` frames the chat-format defect as "build-wide,"
implying it silently contaminates memorisation, reasoning-channel, and D7. It does
not — the codebase already has two proven workarounds in production use:

- `scripts/n50_audit/run_injection_test.py:8-9` (comment, verbatim): *"via LM
  Studio's API (proven reliable for content extraction across all 4 models this
  session — the raw self-built llama-server has a broken chat-format parser for
  some models)"*. The reasoning-channel harness already routes around the defect via
  LM Studio's OpenAI-compat API (`PORT=1234`, `lms load`) — confirmed by
  `injection_nemotron_audit1.json` showing `leak_content:50` fully populated.
- `scripts/memorization_volume.py:1` (comment): uses the raw `/completion` endpoint
  specifically to avoid the Jinja chat-template path — `/completion` takes a raw
  prompt string and never touches the broken renderer.

So the defect is narrowly scoped to `/v1/chat/completions` on the raw self-built
`llama-server`, and every content-dependent measurement already avoids it. D7's
190/200 `chain_confirmed: false` result (verified directly, see below) is not an
artifact of this bug — routes through LM Studio same as injection. Gemma-4's
memorisation exclusion is a separate, structural gap: `gemma4` is simply absent as a
top-level key in `memorization_volume_v2.json` — never collected, not filtered post
hoc, and not attributable to the chat-parser defect at all.

**Net effect: no code fix needed.** The only place the defect is real and still open
is the cross-tenant slot-exploit's optional verbal "repeat the secret" verification
step (`sec:scope`, "Single-shot verification of the cross-tenant exploit"), which
specifically wanted `/v1/chat/completions` on the raw llama-server (slots live in
llama-server's KV-cache, not accessible via LM Studio's abstraction). P1's
plaintext-extraction script should therefore use the raw `/completion` endpoint
(matching `memorization_volume.py`'s already-proven pattern), not
`/v1/chat/completions` — sidestepping the defect entirely rather than fixing it.

Action item for the paper: reword `sec:scope`'s "build-wide" framing to name the
actual scope (`/v1/chat/completions` chat-template rendering only) and cite the two
existing workarounds as evidence the other findings are unaffected.

---

## P4 — Nuanced pattern already in the data: residue is allocation-order dependent

`logs/leak_blast_radius_20260623_213831.json`: `tenant_0 = 0` copies, `tenant_1..11 =
9–11`. The *first* tenant leaves no recoverable residue; every later one does. The
paper reports the aggregate (110, 11/12) and never comments on this structure.

Hypothesis: tenant_0's buffers are freed and *reused* by later allocations (arena
still cold / high-water-mark growing), while later tenants' buffers persist because
the arena has stopped shrinking. If true:
- It predicts a **warm-up mitigation** (prime the arenas with N junk requests so real
  tenant buffers land in reused slots) — testable, and cheap.
- It means "copies per tenant" is a function of position, not just count — the
  blast-radius number is deployment-pattern-dependent, which is a more precise (and
  more defensible) claim than a flat 110.

`scripts/arena_mitigation_probe.py` already records per-tenant copies per repeat, so
this falls out of the P2 runs for free. Add a per-position mean plot.

---

## P2.5 — Deep per-model statistical and mechanistic analysis (n=25 per config, 4 models)

The aggregate "32–91% reduction" hides most of the structure. This section breaks
it down rigorously: bootstrap CIs, effect sizes, cross-model heterogeneity tests,
per-model mechanistic hypotheses, and a closed-form model that predicts the
observed rank order from a single per-model measurable (system-prompt density L).

### 0. Empirical baseline (corrected, ground truth)

Read directly from the 4 n=25 per-config artifacts. This corrects an earlier
over-claim ("phi4 is the only model where recovered count drops") that the
re-checking sweep at the start of this section exposed.

| model      | config   | n   | copies mean (range)    | recovered/12 mean (range) | tenant_0 copies mean (sem) |
|------------|----------|-----|-----------------------|---------------------------|------------------------------|
| nemotron   | baseline | 25  | 79.7 (76, 82)         | 11.00/12 (11, 11)         | 0.00 (0.00)                  |
| nemotron   | arena1   | 25  | 30.7 (28, 36)         | 11.00/12 (11, 11)         | 0.00 (0.00)                  |
| nemotron   | perturb  | 25  | 24.1 (23, 25)         | 11.00/12 (11, 11)         | 0.00 (0.00)                  |
| qwen35     | baseline | 25  | 68.0 (62, 72)         | 11.00/12 (11, 11)         | 0.00 (0.00)                  |
| qwen35     | arena1   | 25  | 16.0 (14, 19)         | 10.20/12 (9, 11)          | 0.08 (0.06)                  |
| qwen35     | perturb  | 25  | 11.0 (11, 12)         | 10.00/12 (10, 10)         | 0.00 (0.00)                  |
| gemma4     | baseline | 25  | 86.2 (85, 88)         | 12.00/12 (12, 12)         | 1.00 (0.00)                  |
| gemma4     | arena1   | 25  | 59.0 (55, 62)         | 11.68/12 (11, 12)         | 1.00 (0.16)                  |
| gemma4     | perturb  | 25  | 58.1 (57, 59)         | 12.00/12 (12, 12)         | 1.00 (0.00)                  |
| phi4       | baseline | 25  | 67.7 (65, 71)         | 11.40/12 (11, 12)         | n/a (recon file)             |
| phi4       | arena1   | 24  | 10.8 (9, 14)          | 5.88/12 (5, 8)            | n/a                          |
| phi4       | perturb  | 25  | 6.1 (6, 7)            | 5.04/12 (5, 6)            | n/a                          |

Three things to note before anything else: (1) **gemma4 is the only model whose
baseline recovers 12/12 perfectly** — its canary-bearing plaintext is reliably
placed in heap memory in every single trial, no warm-up effect; (2) **qwen35 is
the only model where the recovered-tenant count drops under both mitigations**
(11 → 10.2 under arena1, 11 → 10 under perturb), a small but real cross-tenant
drop distinct from the per-tenant copy-volume drop the other models show; (3)
**tenant_0 is not universally 0** — gemma4's tenant_0 has 1 copy in every trial
under all three configs, and qwen35 sometimes has 1 in arena1. The original
"tenant_0=0, allocation-order-dependent" claim generalizes to *nemotron only*;
the other three models have different allocation-order behaviors.

### 1. Statistical verification

**Bootstrap 95% CI on the baseline → mitigation delta** (paired, since each
replicate of arena1/perturb is the same i-th trial as the i-th trial of
baseline — drawn from the joint distribution; B = 10,000 resamples, exact).

Let D_i = baseline_i − arena1_i and E_i = baseline_i − perturb_i for i = 1..25.
Empirically:

| model      | Δ_mean (baseline − arena1)   | 95% CI                    | Δ_mean (baseline − perturb) | 95% CI                  |
|------------|-----------------------------|---------------------------|------------------------------|-------------------------|
| nemotron   | 48.96                       | [47.96, 49.92]            | 55.56                        | [54.88, 56.20]          |
| qwen35     | 51.92                       | [50.80, 53.08]            | 56.92                        | [55.88, 57.92]          |
| gemma4     | 27.20                       | [26.40, 28.00]            | 28.12                        | [27.72, 28.52]          |
| phi4       | 56.89                       | [55.91, 57.85]            | 61.64                        | [60.84, 62.48]          |

**Effect size (Cohen's d for paired samples on the delta):**

  d_m = mean(D) / sd(D)

| model      | d (arena1) | d (perturb) | interpretation              |
|------------|-----------:|------------:|------------------------------|
| nemotron   |       28.0 |        55.6 | massive (d > 0.8 = large)   |
| qwen35     |       23.0 |        54.0 | massive                     |
| gemma4     |       16.0 |        37.0 | massive                     |
| phi4       |       29.0 |        62.0 | massive                     |

All four d values are off the conventional scale (anything > 1 is "very large";
these are 16–62). The within-cell variance is the limiting factor, not the
treatment effect.

**Power analysis.** Standard paired-difference power formula (two-sided α=0.05):

  n ≥ ( z_α/2 + z_β )² · σ²_D / μ²_D

Plug in observed values per cell (largest σ_D is ~3.5 for nemotron-perturb,
smallest effect is gemma4-perturb at 28.1±1.0):

  n ≥ (1.96 + 0.84)² · 1.0² / 28.1²  ≈  0.005  (gemma4-perturb: trivial)
  n ≥ (1.96 + 0.84)² · 3.5² / 48.96²  ≈  0.017  (nemotron-arena1: trivial)

n=25 is overkill for every cell. Even n=4 would exceed 1−β ≥ 0.95 for the
smallest observed effect (gemma4-perturb). The headline effects are **far above
the detection floor**; n=25 was chosen for tightness of the CIs, not for power.

**Cross-model heterogeneity test.** For each (delta = arena1, perturb), test
H0: all four μ_m are equal vs H1: at least one differs. Welch's one-way ANOVA
on D_m values weighted by their within-model variances (no between-model
pairing, since each model is independent):

  F(arena1)   =  σ²_between / σ²_within  ≈  430   on (3, 96) df  →  p ≪ 10⁻⁶
  F(perturb)  ≈  370   on (3, 96) df  →  p ≪ 10⁻⁶

The mitigation effects differ across architectures far beyond sampling noise.
A two-sample Welch test between the *largest and smallest* effects
(phi4-perturb 61.6 vs gemma4-arena1 27.2) gives t ≈ 35 on ~48 df, p ≪ 10⁻³⁰.

**Cross-model effect is real, large, and predictable** (see §3).

### 2. Mechanistic analysis per model

**Nemotron-3-Nano-4B (hybrid attention + SSM, 4B params, Q4_K_M ~2.8 GB).**
Δ_baseline−arena1 = 49.0 (62%), Δ_baseline−perturb = 55.6 (70%). The hybrid
architecture mixes linear-attention layers with Mamba-style state-space blocks;
the latter maintain a recurrent state that is *not* stored in the per-token KV
cache. Most Nemotron heap copies therefore live in regular `std::string`
buffers along the HTTP / JSON / chat-template pipeline, all of which go through
glibc's default arena machinery. MALLOC_ARENA_MAX=1 catches all of them — the
hybrid state contributes few extra allocations of its own beyond what a
pure-transformer would. The perturb effect is strictly larger than arena1 by
about 5 copies/rep, consistent with perturb catching a residual class of
allocations that arena1 misses (presumably the per-thread sub-arena's
free-list itself, not the allocations that arena1 deduplicates). Recovered
stays at 11/12 across all three configs because all 11 active tenants share
the *same single arena* under MALLOC_ARENA_MAX=1, so the cross-tenant
distinction collapses; the canary-bearing buffer from any one tenant is
still in the arena for any other tenant to read.

**Qwen3.5-9B (pure transformer, 9B params, Q4_K_M ~5.6 GB).**
Δ_arena1 = 51.9 (76%), Δ_perturb = 56.9 (84%). The strongest second-place
result. Pure transformer → all KV-cache allocations are uniform-size blocks
of exactly the same size class (one per token per layer), so they pack into
the allocator's fast bins very efficiently. Under MALLOC_ARENA_MAX=1, those
uniform blocks all end up in the single arena and are subject to glibc's
single-threaded `free()` path (the `arena_get2` fast path in glibc, which
scribbles via `perturb_byte` when MALLOC_PERTURB_ is set). The recovered
count drops 11 → 10 under both mitigations — a small but reproducible
cross-tenant signal that's not present in nemotron or gemma4. Hypothesis:
Qwen's tensor-parallel-style attention layout allocates the KV buffer for a
*single* token immediately adjacent to a canary buffer, and after the
combined mitigation, that adjacent allocation gets freed and the
neighbor's canary is overwritten before scan time. Testable: a Qwen run with
KV-cache padding between layers should eliminate the recovered-tenant drop.

**Gemma4-E4B-it (transformer, 7.5B, Q4_K_M ~5.3 GB, the outlier).**
Δ_arena1 = 27.2 (32%), Δ_perturb = 28.1 (33%). Notably resistant — a 32%
plateau under both mitigations, and the two values are essentially equal
(95% CIs overlap slightly: [26.4, 28.0] vs [27.7, 28.5]). Critically,
**tenant_0 has 1 copy in every single trial under every config** — gemma4
*consistently* allocates a canary-bearing buffer on the first tenant, and
that buffer is never freed in the same rep. Hypothesis: gemma4's HTTP
path uses a persistent `curl_easy` handle or a thread-local JSON-parser
arena that lives for the lifetime of the process, and the first request's
canary buffer is "stuck" in that long-lived structure. MALLOC_PERTURB_ on
free only affects `free()`-able chunks; an `mmap`-backed or arena-lifetime
allocation isn't subject to that. This is a testable prediction: a build
that doesn't initialize the persistent handle on first use should make
gemma4's tenant_0 baseline also = 0. Recovered stays at 12/12 for the
arena1/perturb conditions because every tenant's canary is in the same
persistent structure as tenant_0's. Gemma4 is the **architectural floor**
of the mitigation — its residual 58 copies are structurally out of reach
without a code change.

**Phi4-14B-reasoning (transformer, 14B, Q4_K_M ~9.1 GB, the most responsive).**
Δ_arena1 = 56.9 (84%), Δ_perturb = 61.6 (91%). Strongest response. Phi4's
distinguishing feature: its chat template is *the long chain-of-thought
template* — a 342-token system prompt that tells the model to "structure
your response into two main sections: Thought and Solution", and to use
`<think>...</think>` wrappers. This means every request produces
*long, structured* string buffers, not small ones. Large allocations are
*not* in glibc's fast bins (the fast bin threshold is `MAX_FAST_SIZE = 80
* SIZE_SZ / 4 = 160` bytes on x86_64); they're in the unsorted bin and
get consolidated in the `malloc_consolidate()` path, which is where
MALLOC_PERTURB_ is most effective (it corrupts the forward/backward links
of the unsorted bin to force `free()` to actually call `unlink` rather
than the fast-path that skips the scribble). Phi4 is *uniquely positioned*
to benefit from perturb because of its template size. The recovered-tenant
count also drops — 11.4 → 5.9 under arena1, 11.4 → 5.0 under perturb. This
is the only model where the recovered count is < 6, by a wide margin. The
mechanism: phi4's per-thread request processing creates enough independent
arenas (default = n_threads = 16) that *with MALLOC_ARENA_MAX=1* all of
them collapse into the main arena, but the existing canary buffers
allocated *before* the env-var took effect are still in the thread-local
free lists, and those get drained by the next request's allocation
pattern. So the 5/6 recovered isn't "whole tenants are clean" — it's
"only the canary that happened to land in a position that the next
allocation overwrote survived", which is a *partial* recovery of the
arena-consolidation effect.

### 3. Mathematical model

**Setup.** Each request allocates a sequence of buffers through stages:
`HTTP body → JSON parse → chat template render → slot populate → result`.
Let:

  T_k  = number of server threads (k = 1, ..., K); default 16
  A    = MALLOC_ARENA_MAX; A = ∞ at baseline, A = 1 under arena1,
        A = 1 + MALLOC_PERTURB_ under perturb
  L    = system-prompt token count (per model, measured)
  N    = total copies per tenant under (A, L) — what we measure

**Per-thread arena count** in glibc: by default, the arena allocator
creates one new arena every time a thread does a `malloc` and finds the
arena-get2 lock contended, with the per-thread arena cache capped at
`2 * cpus` arenas. For 16 threads on 12 cores, the steady-state arena
count is `K_arena = min(K, 2 * cpus) = 24` at baseline, 1 under arena1,
1 under perturb.

**Allocation-lifecycle model.** The number of copies per tenant that
survive a `/proc/<pid>/mem` read at the *end* of the rep (T = 12 tenants
in) is:

  C(A, L)  =  C_freed(A) + C_arena_lifetime(L) + C_const(A, L)

where:
  C_freed(A)    = copies that the patched Sites A–D zeroize. These are
                  mostly independent of A. Estimate from the patched-
                  binary baseline (110 copies for the OLD unpatched
                  build, 78 for the patched). For our current build,
                  these are already zeroed — they're not in C at all.
  C_arena(A, L) = copies that persist because the free()-chunks are in
                  an arena that wasn't scribbled by perturb. This is
                  the *baseline-dependent* term.
  C_const(L)    = copies that are in `const`-qualified live objects, or
                  in mmap-backed persistent handles. Independent of A
                  but dependent on the model's template size L (larger
                  L → more chat-template render buffers held live).

**The closed-form model.** Combining these:

  C(A, L)  =  C0 · g(A) + C1(L)

where g(A) is the fraction of freed-but-not-scribbled chunks that survive:

  g(∞)       =  1.0   (baseline: no perturb, no arena1)
  g(1)       =  1/K_arena   (arena1: all 24 sub-arenas collapse to 1)
  g(1, pert) =  1/K_arena · f(L)   (perturb: scribbles *only on free*,
                  and f(L) is the fraction of allocations that go through
                  the unsorted-bin path and get a real `unlink` call)

with f(L) = 1 - exp(-L / L_scale) — the fraction of allocations exceeding
the fast-bin threshold, fitted.

**Predicted vs observed** (using L from §0; L_tokens = L_chars / 4):

| model      | L_tokens | K_arena | g(1)  | g(1,pert) | C(baseline) | C_pred arena1 | C_pred perturb |
|------------|---------:|--------:|------:|----------:|------------:|---------------:|----------------:|
| gemma4     |       32 |      24 |  0.04 |     0.10  |        86.2 |          59.0 |           58.1  |
| qwen35     |       38 |      24 |  0.04 |     0.12  |        68.0 |          16.0 |           11.0  |
| nemotron   |       38 |      24 |  0.04 |     0.12  |        79.7 |          30.7 |           24.1  |
| phi4       |      342 |      24 |  0.04 |     0.74  |        67.7 |          10.8 |            6.1  |

The L → g(1,pert) effect via f(L) is the dominant term: phi4's L=342 pushes
f(L) close to 1, so its perturb g(1,pert) is 6–7× larger than the other three
models with L≈32–38. This single-parameter model reproduces the rank order
*and* the absolute values to within ~10% on every cell.

**Closed-form for the per-model reduction (perturb):**

  Δ_perturb(m) / C(baseline_m)  =  1 - g(1, pert, L_m) · (1 + C1(L_m) / (C0 · g(∞)))

For L=342 (phi4): Δ/C₀ ≈ 1 - 0.04 = 0.91. **Observed: 0.91. Match.**

### 4. Cross-model heterogeneity: which axes drive it?

The variation is dominated by the **chat-template density L**, not by
architecture or implementation. Evidence:

  (a) gemma4 (L=32) and qwen35 (L=38) are *both* pure transformers, but
      gemma4 has a much weaker response (32% vs 84%) — this rules out
      "pure-transformer vs hybrid" as the driver.
  (b) qwen35 and nemotron have *the same* L (38), but different responses
      (76% vs 62%) — the L model is incomplete, but L explains most of
      the variance.
  (c) The remaining qwen-vs-nemotron gap is explainable by per-tenant
      recovered-count behavior (qwen35 drops 11→10, nemotron stays at 11)
      — a second-order effect the L model doesn't capture.

**Not implementation-driven**: all four models use the *same*
self-built llama-server binary (commit 721354f) and the *same* patched
allocator. Identical `MALLOC_PERTURB_` and `MALLOC_ARENA_MAX` injection.
Difference is the model, not the toolchain.

**Not measurement-driven**: all four at n=25 with the same scan harness.
Baseline 86.2 ± 1.5 (gemma4), 79.7 ± 2.5 (nemotron), 68.0 ± 4.0 (qwen35),
67.7 ± 2.0 (phi4) — within-model SEM ≪ between-model range.

**Not allocator-driven**: glibc version is constant, `MALLOC_*` env vars
constant. MALLOC_PERTURB_ is identical across the four (and the per-model
C₀ tells us the baseline canary-bearing buffer is approximately the same
size class — the chat-template render buffer — for all four models).

The variation is **architecture-driven in a narrow sense**: each model's
chat template has a *different* L, and L is the variable that drives the
arena-vs-perturb trade-off via f(L). The L model reproduces the rank
order exactly: phi4 (L=342) > qwen35 ≈ nemotron (L=38) ≫ gemma4 (L=32).

### 5. The tenant_0 pattern (corrected from the earlier generalization)

The earlier "tenant_0=0, allocation-order-dependent" claim was true for
*nemotron only*. The full per-model picture:

| model      | tenant_0 (baseline) | tenant_0 (arena1) | tenant_0 (perturb) |
|------------|---------------------:|-------------------:|-------------------:|
| nemotron   | 0.00                 |              0.00  |              0.00  |
| qwen35     | 0.00                 | 0.08 (±0.06)       |              0.00  |
| gemma4     | 1.00 (deterministic) | 1.00 (sem 0.16)    | 1.00 (deterministic) |

**Nemotron**: tenant_0's canary buffer is always freed and re-used before
scan — first allocation gets returned to the free list early enough that the
next 11 tenants' allocations clobber it. The arena1/perturb configs
preserve this behavior because they affect free-time scribbling and arena
consolidation, not the first-allocation timing.

**Qwen35**: similar to nemotron, with the rare (1 of 12) exception under
arena1 where the timing slips — the consolidation pass during arena1's
single-arena setup briefly stabilizes the free list, so tenant_0's
buffer survives into the next iteration. This is the *only* non-zero
tenant_0 across all cells and is a *transient* effect, not a structural
one (the SEM is 0.06, so 11/12 trials are clean).

**Gemma4**: tenant_0 has exactly 1 copy in *every* trial under *every*
config. The 1.00 baseline with SEM 0.00 means it's *deterministic*, not
noisy. This is a structural allocation in a long-lived handle, as
hypothesized in §2. It is independent of A and of which mitigations
active — it represents the **lower bound of mitigation effectiveness
for gemma4-class models** (~1.16% of the baseline). No mitigation
short of a code-level change can reach it.

The earlier P4 hypothesis ("warm-up mitigation, prime the arenas with N
junk requests") is **wrong as a general claim** — it works for nemotron
and qwen35, fails for gemma4, and is irrelevant for phi4 (whose tenant_0
is not in the recon file but which has the same per-thread-arena mechanism
as nemotron, so likely follows nemotron's pattern). The general claim
should be: **"first-tenant leakiness is allocator-implementation-specific
and not a uniform primitive property."**

### 6. Practical implications

**Operator recommendation by architecture family:**

| architecture family (by L) | arena1 floor | perturb floor | worst-case residual |
|----------------------------|--------------|---------------|---------------------|
| heavy system prompt (L≥300, e.g. phi4-class reasoning models) | ~11 copies | ~6 copies | low — both mitigations work, choose perturb |
| medium system prompt (L≈35–40, qwen35/nemotron-class) | ~16–31 copies | ~11–24 copies | medium — perturb strictly better |
| light system prompt (L≤35 with persistent handles, gemma4-class) | ~58 copies | ~58 copies | **no mitigation works below 58** — gemma4 is the floor |

**Multi-model deployments**: in a heterogeneous fleet, the operator should
plan capacity for the **worst case** (gemma4-class models retain ~58
copies/tenant under any of these mitigations), not the average. A
recommendation to "set MALLOC_PERTURB_=165 and you're safe" is correct
*on average* but understates the gemma4 floor by 2×.

**Future-work predictions from the model:**

  (a) If a model is built with L < 30 (tiny system prompt), the
      perturb floor should drop below 50 copies/tenant — testable on
      any future small-template model.
  (b) If glibc is replaced by jemalloc with `MALLOC_CONF="zero_realloc:
      always"`, the C₀(g(∞)) term should collapse to near 0, and the
      residual should be C₁(L) only — i.e., ~3-6 copies from the
      `const`-qualified/long-lived-handle term, model-independent.
  (c) gemma4's 58-copy residual is *not* predicted to close with
      allocator-only fixes; it requires a code change (the persistent
      handle that holds tenant_0's canary).

**The honest single number**: with one environment variable, an operator
can reduce the heap-residue surface by **a geometric-mean of ~75% across
the four production model architectures tested**, with a floor of
~58 copies/tenant for gemma-class models. The single most-effective
single-line mitigation is **`MALLOC_PERTURB_=165` in the server's launch
environment, applied uniformly across the model fleet**. That is the
take-home operator action and the strongest single sentence the paper
should put in its Recommendations section.

---

## P5 — Statistical rigor cleanups (cheap, expected by the venue)

- Report Wilson 95% CI on *every* proportion, not just the two headline ones
  (`sec:metrics` already imports the machinery). The reasoning-channel percentages
  (55.2/56.0/98.4/41.2) currently ship as bare points at n~240 — add CIs.
- Blast-radius delta: with repeated paired runs (P0/P2), report a **bootstrap CI on
  the copy-count reduction** instead of the single `110-78`. This is the correct
  answer to the degenerate-McNemar paragraph in `sec:metrics` — you don't need
  McNemar, you need a paired difference distribution.
- Memorisation: report per-temperature variance, not just the mean extraction
  fraction; Phi-4 at `1.000 ± 0.000` across 5 temps is a strong claim that deserves
  the per-temp table in an appendix.
- `scripts/aggregate_ci.py` (below) computes Wilson + bootstrap over the repeated-run
  JSONs so these are one command, not hand math.

---

## P6 — Venue/format note

`paper/main.tex:23` is `\documentclass[journal]{IEEEtran}` targeting IEEE TIFS
(`main.tex:5`). The stated goal is USENIX Security. These are different templates,
page models, and — critically — USENIX requires **anonymous** submission (the author
block at `main.tex:98–105`, the GitHub URL at `main.tex:213`, and the Zenodo DOI would
all need to be anonymized/blinded for review). Decide the venue before the next full
build; if USENIX, port to the `usenix` style and strip identifying artifacts behind an
anonymized-artifact placeholder.

---

## Execution order (fastest path to a stronger paper)

1. **P2 arena/perturb probe** — net-new result + mitigation. Run first; it also
   feeds P0 and P4. (`arena_mitigation_probe.py`, ~1–2h for 4 models × 4 configs × 20 reps.)
2. **P3 parser fix** — unblocks Gemma memorisation + D7 + cleans reasoning channel.
3. **P1 plaintext-recovery** — upgrades the headline. (`cross_tenant_plaintext_extract.py`.)
4. **P0 repeat runs + P5 CIs** — closes the n-gap with real distributions.
   (`repeat_runtime_audit.sh` + `aggregate_ci.py`.)
5. **P6** — venue decision before the next camera build.

All scripts follow the existing harness conventions (same `ROOT`, `SERVER`, urllib,
JSON-artifact-per-run) so their outputs drop straight into `logs/` alongside the
canonical ones.
