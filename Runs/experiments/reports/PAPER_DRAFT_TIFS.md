# The Local-LLM Privacy Boundary: A Three-Layer Forensic Measurement

**Target:** IEEE TIFS · **Status:** restructured draft (D9). Source-verified numbers;
see `RECONCILED_NUMBERS.md`, `STRENGTH_WEAKNESS_MAP.md`, `CITATION_AUDIT.md`.
The Abstract and §1–§2 live in `PAPER_DRAFT.md` (rewritten 2026-06-23). This file
holds the restructured body §3–§11.

---

## 3. File-Format Layer — GGUF Validation-Gap Taxonomy (Negative Result)

The first assumption a user makes about a local LLM is that the model *file* is
safe to load. We test this directly by constructing a battery of novel GGUF
attack variants and measuring whether the parser can be driven into memory
corruption.

### 3.1 Threat model for this layer
An attacker who can supply a `.gguf` file to a victim (supply-chain: a trojaned
model on a sharing hub, a malicious Modelfile, an attached model). The question:
can a malformed file corrupt the loader's memory and achieve code execution,
denial of service beyond a clean crash, or unauthorized data disclosure?

### 3.2 Method
We built 80+ novel GGUF variants manipulating metadata and hyperparameter fields
*after* the parser has committed to an allocation strategy, across 4 model
architectures (gemma4, qwen35, nemotron_h, phi3). Variant classes included
`rope_drift`, `overflow_counts`, `linear_values`, `negative_blocks`, `zero_values`,
`mixed_extreme`, and tensor-info manipulation (`ndims`, `dim[]`, `type`, `offset`).
Tested against raw llama.cpp commit `721354f`.

### 3.3 Result: the file-format layer is sound against our variant class
**Every one of the 80+ variants was rejected cleanly** — via `GGUF_ASSERT` or
explicit `exit(1)` with a diagnostic. **Zero SIGSEGV. Zero heap corruption.** The
parser's validation path is robust against metadata/validation-layer tampering.

### 3.4 Honest contextualization — why this is a *narrow* clean bill
This negative result must not be over-read. Our variants targeted the
**post-allocation validation path**. A parallel and already-publicly-known class
of CVEs targets the **allocation-arithmetic path** instead — integer overflow in
size calculations leading to undersized `malloc` + oversized `fread`. We did not
exercise this path (our tensor counts fit in `uint64`; we never supplied dims
whose product exceeds `UINT64_MAX`). The 12 known allocation-path CVEs in the
same parser (2 critical, CVSS 9.1, e.g. CVE-2024-25664..68, CVE-2025-53630,
CVE-2026-27940, CVE-2026-33298, CVE-2026-7482 "Bleeding Llama") establish that
the file format is **not** unconditionally safe — only that our variant class
fails to break it.

### 3.5 Contribution of this layer
(1) A reproducible validation-gap taxonomy (the 80+ variants, with the per-class
exit codes) that future work can re-run as a regression battery. (2) The honest
negative result that redirects the paper's attention: if the file format is sound
against our attacks, where *does* local-LLM privacy fail? Answer: the runtime
layer (§4) and the interface layer (§5).

---

## 4. Runtime Layer — Unprivileged Data-at-Rest Leakage (Headline)

This is the layer where local-LLM privacy materially fails. We show that a
released slot's tenant plaintext persists in the serving process's RAM, readable
by any **same-UID parent process** — unprivileged — and we close it with a
zeroization patch whose correctness we prove.

### 4.1 Two distinct residual surfaces (do not conflate)
The runtime layer exposes two disjoint data-at-rest surfaces, with different
privilege levels:

| Surface | Content | Privilege to observe | Patched by |
|---|---|---|---|
| **Heap-string** (§4.2) | formatted-prompt JSON string (~135 KB/slot) | **unprivileged** (same-UID parent, `ptrace_scope=1`) | `prompt_zeroize.patch` (this section) |
| **KV-cache tensor** (§7) | K/V float vectors | privileged (`CAP_SYS_PTRACE`/root) | `kv_cache_zeroize.patch` (§7) |

The heap-string surface is the practically exploitable one and the one our
headline numbers measure; the KV-tensor surface is defense-in-depth.

### 4.2 Mechanism — the heap-string leak
A chat request's plaintext is rendered by `common_chat_templates_apply()` into a
`std::string`, copied into `task->params.sampling.generation_prompt`, and (in
`send_final_response`) re-detokenized into `res->prompt`. On slot release,
`server_slot::reset()` reassigns the slot-owned strings via `= ""` — which sets
length to 0 but leaves the old bytes in the SSO/heap allocation. The `task`
object is freed (not zeroed) on `task.reset()`. The result is that the previous
tenant's cleartext persists in writable RAM until overwritten by churn. Because
slots are persistent objects reused across requests, every released slot retains
the previous tenant's plaintext.

The read primitive: a process that is the *parent* of the server (or shares its
UID under `ptrace_scope=1`) opens `/proc/<server_pid>/mem` and scans the writable
regions for the plaintext. No root, no `CAP_SYS_PTRACE`, no kernel access.

### 4.3 Empirical measurement
Per-tenant canary tracking (`scripts/multilayer_v2.py`): each of 4 sequential
tenants sends a distinct UUID canary; after each send we scan `/proc/<pid>/mem`
for *every prior* canary independently (the v2 fix to a v1 methodology bug).

| Tenant | peak copies | after 3 more requests | after 10s idle |
|---|---|---|---|
| T1 | 14 | **13** | **13** |
| T2 | 14 | **13** | **13** |
| T3 | 14 | **13** | **13** |
| T4 | 14 | (final) | — |

(Source: `logs/multilayer_v2_v2smoke_1782188364.json`, reproducible.) Each copy's
64-byte context dump shows the JSON-serialized chat prompt verbatim, e.g.
`ser", "content": "Summarize this note. Canary (do not include): T1_c74787ca...`.
Per-slot footprint ~135 KB in a distinct `[anon]` mmap region.

**Multi-tenant blast radius** (`scripts/leak_blast_radius.py`): a *single*
`/proc/<pid>/mem` read after 12 sequential tenants recovers secrets from 11/12
(~10.8 MB printable cleartext) on the patched binary — confirming the leak
persists post-patch (`logs/leak_blast_radius_20260623_213831.json`).

### 4.4 Defense — `prompt_zeroize.patch` (invariant I₃) — measured, partial

We add `explicit_bzero` over the slot-owned plaintext members in
`server_slot::reset()` (Site A) and over the result object's plaintext members
in `send_final_response()` before `queue_results.send()` (Site B). This was
designed to establish invariant **I₃** (slot-released-implies-zeroed for the
live heap strings); full mechanism and proof are in
`PROMPT_ZEROIZE_PATCH_REPORT.md`.

**Measured result (D2): no effect.** Three independent runs gave T1 final
counts of 13, 13, 14 — statistically indistinguishable from the unpatched
baseline of 13. Sites A/B do not touch the dominant leak location.

**Root cause.** All hits in a run land in a single ~132 KB (`135168`-byte)
`[anon]` mmap region — above glibc's `M_MMAP_THRESHOLD`, so it is allocated and
freed via `mmap`/`munmap`, not the regular heap. This region is populated
*upstream* of the slot/task objects Sites A/B target: in the HTTP layer
(`server_http_context::post()` in `server-http.cpp`), which holds the raw
request body in a local `std::string` copy and in `server_http_req::body`
before the request ever reaches a slot.

An experimental **Site C** fix — `explicit_bzero` on both HTTP-layer body
copies — was added and measured: T1 13→12, T2-T4 13→11, confirming the
plaintext is copied at multiple independent points in the pipeline (HTTP body
→ `json::parse()` tree → chat-template render buffer → slot/task strings).

A follow-up **Site D** fix targeted the dominant remaining copy: the rendered
chat-prompt buffer (`chat_params.prompt`, ~135KB, returned by
`common_chat_templates_apply()` inside `oaicompat_chat_params_parse()`,
`server-common.cpp`), zeroed before the local goes out of scope. Result for
the first tenant: **13 → 0 — a complete fix.** But tenants 2-4 each jump to 12
hits immediately and the count **never decays**, including through a 10s idle
period — qualitatively different from the freed-and-reused residue pattern
Sites A-D address. `server_prompt_cache` (`server-context.cpp`'s
`slot.prompt_save()`/`prompt_load()`, gated by `cache_prompt`) was hypothesized
as the carrier given the trigger condition matches exactly (T1 has no prior
cache entry; T2+ each populate one), but reading its storage format
(`server-task.h`) **rules this out**: it holds only token IDs and serialized
KV-state binary blobs, no plaintext string field. Further candidates were
checked and also ruled out: `to_json_non_oaicompat()`'s `{"prompt", prompt}`
field reads the same member Site B already zeros; both
`server_tokens::detokenize()` call sites feed that same member;
`common_prompt_checkpoint` (the cache's checkpoint type) holds only binary
`vector<uint8_t>` fields. **Net finding:** the freed-heap-string leak class is
fixed for the single-tenant case; a second, larger, currently unpatched leak
persists for every multi-request session, with a known trigger condition
(second-and-later request under `cache_prompt`).

**Root-caused via live debugging (not just an open problem):** a `gdb`
session attached to the actual leaking process during reproduction (rather
than further static source reading) found the structural cause.
`info proc mappings` showed the leak's containing region is one of ~14
structurally identical 135168-byte regions, each preceded and followed by a
~64MB no-access gap — the standard signature of a per-thread glibc malloc
sub-heap (arena), not a single named buffer matching the rendered-prompt
size (that size match was coincidental: it is glibc's default sub-heap
granularity). `free()` does not zero memory in glibc, and request
processing legitimately spans multiple threads (HTTP handling, JSON
parsing, chat-template rendering, slot processing), each with an
independent allocator arena. Closing every *known* per-object copy
(Sites A-D) cannot guarantee closing a copy made on a *different thread*
via a code path not yet instrumented — the strongest remaining candidate
being the `json::parse(req.body)` tree itself (≥20 call sites across the
server), which `nlohmann::json` stores as a tree of heap nodes rather than
one contiguous buffer, so no single `explicit_bzero` call can clear it.

**Revised conclusion:** this leak class is **structurally resistant to
per-object zeroization patches**, not a missing call site waiting to be
found. Complete remediation likely requires either a zero-on-every-free
allocator with no per-allocation-size exemption, or a secure-string type
threaded end-to-end through the request pipeline. An attempt at the former
(a global `operator delete` override zeroing every free ≥4KB, added in a
parallel work session) gave a partial, timing-dependent reduction
(13→9-11, inconsistent across repeated runs) — consistent with, not
contradicting, the structural diagnosis: a coarse, threshold-gated
allocator-level fix cannot fully substitute for either patching every copy
site or eliminating the threshold exemption entirely.

### 4.5 Overhead
N=20 short-completion requests, same protocol as the KV-patch benchmark.
`explicit_bzero` calls are pure memory-bandwidth work (sub-microsecond per
~135 KB buffer) and were not separately benchmarked given §4.4's negative
result makes the overhead question secondary to the unresolved leak itself.

### 4.6 The remote vector — cross-tenant session hijacking via `/slots` restore

§4.1-4.4 establish a real but **locally-scoped** threat model: every leak
above requires the attacker to already hold same-UID process access
(`/proc/<pid>/mem`). This subsection reports a finding with no such
requirement.

`llama-server`'s `/slots/:id_slot` endpoint (save and restore a slot's
KV-cache to/from a file) is gated only by `--slot-save-path` being set
(`server-context.cpp:4606`) — independent of `--slots`/`endpoint_slots`,
which gates the separate metrics-dump endpoint. An operator enabling the
ordinary "resume a conversation after a disconnect" feature gets this
exposed with no further configuration. `handle_slots_save()` /
`handle_slots_restore()` (`server-context.cpp:5211-5280`) accept a
client-supplied filename, validated only against path-traversal characters
(`fs_validate_filename()`) — **there is no check that the requesting client
owns the slot ID or the filename it names.** `--api-key`, the only
authentication llama-server offers, does not close this gap: it is a single
perimeter membership check (`server-http.cpp:192`) with no concept of which
key created which slot or file.

**Exploit, reproduced on three independent setups** (nemotron-3-nano-4b/CPU,
Phi-4-reasoning-plus/CPU, Qwen3.5-9B/GPU after rebuilding with
`-DGGML_CUDA=ON` to remove decode speed as a variable): Tenant A sends a
message containing a synthetic secret, pinned to slot 0
(`POST /v1/chat/completions {"id_slot":0,...}`), then saves it
(`POST /slots/0?action=save {"filename":"x.bin"}`). Tenant B — a different,
unrelated client, with no special privilege and no knowledge beyond the
filename — restores it into their own slot
(`POST /slots/1?action=restore {"filename":"x.bin"}`). In all three runs,
the server's own response proves the copy completed exactly:
`n_restored` matched `n_saved` token-for-token (e.g. 68/68, 302/302,
74/74). Tenant B's slot now holds a byte-for-byte copy of Tenant A's
KV-cache and conversation history, obtained entirely over the network API.

A literal "repeat the secret back" verbal extraction was attempted but not
completed — blocked by an unrelated, build-wide chat-format-parser defect
in this research build (empty `content`/`reasoning_content` on every
model and prompt tested, including trivial ones unconnected to slot
restore at all). This does not weaken the finding: the exploit's
load-bearing claim is the cross-tenant *data copy*, proven at the protocol
level independent of whether any one model's response happens to verbalize
it afterward.

**Statistical-power confirmation (n=200, 100%):** a follow-up automated
audit re-ran this exploit 50 times per model across all 4 models
(scripted: model loaded once, then 50 independent save/restore cycles each).
**200/200 trials confirmed** — zero failures, zero ambiguous cases. This is
not a probabilistic leak rate to report a confidence interval for: the
exploit is deterministic on every architecture tested.

**Classification:** CWE-862 (Missing Authorization) compounding CWE-200
(Information Exposure). **This is the only finding in this paper that
requires no local host access** — every other result in §3-§4 and §7
needs same-UID process access or, for the KV-tensor surface, elevated
privilege. It is also the most direct violation of tenant isolation in the
most common real-world deployment shape for this software: a single
backend instance serving multiple customers behind one or a few shared API
keys, with per-customer authentication (if any) terminated upstream at a
gateway that forwards every request to the same llama-server with the same
backend credentials.

---

## 5. Interface Layer — Wrapper Forensics

Even if the runtime were perfectly zeroized, the wrapper sitting above it can
defeat the privacy guarantee by logging the plaintext to disk before it ever
reaches the engine. We introduce **wrapper forensics** as the discipline of
auditing this surface.

### 5.1 Finding — LM Studio `logSensitiveData: true` default
LM Studio's headless daemon writes every API interaction (prompts, responses,
reasoning traces) to cleartext disk logs at `~/.lmstudio/server-logs/`. The
governing setting, `logSensitiveData`, defaults to **`true`** and lives in a
hidden JSON file (`~/.lmstudio/.internal/http-server-config.json`), not in the
user-visible `settings.json`; changing it requires a server restart. There is no
documented GUI control. [GUI audit pending; the headless daemon was measured
directly.]

### 5.2 On/off differential (reproduced)
- Baseline: send canary `MITIGATION_BASELINE_1781972288` via the OpenAI-compat
  API → `grep` finds it verbatim in the day's server log, full body, 10/10 sent.
- Flip `logSensitiveData: false` + restart → canary `MITIGATION_AFTER_CHANGE_*`
  **NOT FOUND** (grep exit 1). Toggle is real, default-on, and mitigable.
- `apiPredictionHistoryEviction.ttlDays` governs a *different* artifact (the
  prediction-history cache), **not** the server logs. The server logs have **no
  observed retention limit** — they persist until manual deletion or file
  rotation. (An earlier "30-day retention" phrasing was incorrect; the reality is
  stricter — indefinite persistence.)

### 5.3 Volume
~6.3 MB/day of logs, ~2,312 content fields, ~777 full response bodies in casual
use. (`MITIGATION_TEST_REPORT.md`.)

### 5.4 Ollama control (disk axis)
A recursive `grep` (user + sudo) across `~/.ollama/`, `/tmp`, `/var/log`,
`/var/snap/ollama`, `journalctl`, and `/proc/<pid>/fd` after sending canaries to
both `/api/generate` and `/api/chat` finds **zero matches**. Ollama does not log
API payloads. The cleartext-logging behavior is **wrapper-specific to LM
Studio**, not universal to local-LLM tools. [Cross-tool *network* control pending
D5.]

---

## 6. Network Layer — The Red Herring (Negative Result)

The most commonly-asked privacy question about a "free" local tool is: *does it
phone home?* We answer it rigorously so it can be set aside.

### 6.1 Method — netns isolation (the methodological contribution)
Co-resident host traffic (IDE, browser, cloud sync) makes host-wide packet
capture unreliable — a measurement that cannot attribute traffic to the tool
produces false positives. We isolate the tool inside a dedicated network
namespace (`lmns`) whose sole egress is a veth pair (`lmns-br`), with host-side
NAT. Capturing on `lmns-br` therefore sees **exactly** the tool's traffic; no
other host process can appear on it. Two independent ground-truth layers: L1
`tcpdump` on `lmns-br` (wire-level, unspoofable) + L2 `LD_PRELOAD` hook on
`getaddrinfo`/`connect` (libc-level).

### 6.2 Result — LM Studio is network-clean
Across 5 runs spanning 4 models (nemotron-3-nano-4b ×2, gemma-4-e4b-it,
phi-4-reasoning-plus, qwen3.5-9b) and ~23 cumulative minutes of idle holding:
- Identical fingerprint every run: 2 external dest IPs (`104.26.6.153`,
  `104.26.7.153`, Cloudflare), 3 resolved hosts (`lmstudio.ai`,
  `versions-prod.lmstudio.ai`, `extensions.lmstudio.ai`), 8 `connect()` attempts.
- All external packets timestamped within the **first ~8 seconds** of daemon
  startup (the update/extension check); **zero** external connections during any
  idle-hold window.
- The injected canary (in a prompt-injection-style chat probe) **never left the
  host** — not in the pcap, not in DNS, not in the hook log. Prompt content is
  not transmitted over the network.

### 6.3 What this proves and does not prove
It disproves the "No Free Lunch" phone-home hypothesis for LM Studio (this
version, default config). It does **not** prove the tool is private — §4 and §5
show the plaintext sits in process RAM and on disk regardless. Network
cleanliness is the *necessary* check that redirects attention to data-at-rest;
it is not *sufficient* for privacy.

**Cross-tool control (D5):** the same netns-isolation harness, re-run against
Ollama across the same 4 models, found **zero external connections of any
kind** (not just zero canary egress) in all 4 runs — stronger than LM
Studio's result, which showed zero canary egress but nonzero cold-start
telemetry calls. This generalizes the "prompt content does not leave the
process" claim across two architecturally different runtimes (an
Electron+Node daemon vs. a single Go binary), not just across models within
one tool. Idle-hold window was shorter for Ollama (3 min vs. LM Studio's
4–9 min) — a real asymmetry, not parity; see
`TELEMETRY_FINDINGS_OLLAMA.md` for full method, results, and limitations.

---

## 7. KV-Cache Tensor Layer — Defense-in-Depth (I₂)

§4 showed the practically-exploitable surface is the unprivileged heap-string
leak. This section covers a second, privileged-only residual surface in the
same runtime: the KV-cache float tensor. We patch it too — not because it is
the headline, but because a complete data-at-rest story requires closing both.

### 7.1 Prior art: three distinct KV-cache privacy problems
The KV-cache is a privacy surface along three **distinct axes**, which must
not be conflated:

1. **Timing side-channel in shared prefix caches.** An adversary sharing a
   multi-tenant inference server infers other tenants' inputs from cache
   hit/miss *latency* on a shared prefix cache. SafeKV [Chu et al., arXiv
   2508.08438] and PrefixWall (formerly CacheSolidarity) [arXiv 2603.10726]
   address this class. The K/V bytes are never read; only the timing of
   serving them leaks.
2. **Semantic inversion of cached tensors.** An adversary *with weight/cache
   access* reconstructs sensitive inputs directly from the K/V values
   themselves. "Shadow in the Cache" [Luo et al., arXiv 2508.09442, NDSS 2026]
   demonstrates Inversion, Collision, and Injection attacks on cached tensors
   and proposes KV-Cloak as a defense.
3. **Data-at-rest residual on slot release (this work).** The K/V bytes
   persist in process memory after the logical session ends — a *temporal*
   exposure from missing zeroization in `seq_rm()`. The adversary reads stale
   buffer bytes from `/proc/<pid>/mem`; the values are not inverted, they are
   simply not erased.

Our contribution is the **third axis**, complementary to the first two.
Neither prior line of work addresses the temporal/residual exposure axis 3
targets.

### 7.2 Mechanism
`llama_kv_cache::seq_rm()` (`src/llama-kv-cache.cpp`) clears a slot's context
by updating each matching cell's owner bitmap and, when no owner remains,
marking it free. It does **not** touch the K/V bytes in the backend buffer.
The floating-point K/V vectors for every prompt/response token remain
physically present in `ggml_backend_buffer_t` (RAM or VRAM) until a future
request happens to overwrite the same cell.

### 7.3 Empirical measurement
Canary-grep against `/proc/<pid>/mem` before/after release:

| Configuration | Pre-release copies | Post-release copies |
|---|---|---|
| Unpatched, raw llama.cpp, `--cache-ram 0` | 11 | 10 |
| Unpatched, LM Studio, full slot cycle | 11–42 (model-dependent) | 10 |

`llama_kv_cache::clear(bool data)` *can* zero bytes, but only for the entire
buffer on explicit request — the server never calls it on slot release.

### 7.4 The patch
`patches/kv_cache_zeroize.patch` (89 lines, `src/llama-kv-cache.{h,cpp}`):
hooks `seq_rm()`'s per-cell loop so that when `cells.seq_rm(i, seq_id)`
reports the cell now has no owners, `zero_cell_data(s, i)` overwrites that
cell's K and V bytes in every layer via `ggml_backend_tensor_set()` —
backend-portable across CPU and GPU buffers. Direct-mechanism verification:
56/56 zeroed cells held real non-zero data immediately before the zero write,
0/56 afterward (`KV_CACHE_PATCH_REPORT.md` §3.1).

---

## 8. Combined Formal Analysis — I₂ ∧ I₃

We formalize correctness for both patches together. We adopt the
invariant-style framing common to the KV-cache-privacy line of work (SafeKV
[Chu et al. 2025], PrefixWall [2603.10726]), though those address a *timing
side-channel in shared prefix caches* — a distinct vulnerability class from
the *data-at-rest residual on slot release* our patches target. Our
formalization is independent in both threat model and in the invariant it
strengthens.

### 8.1 I₂ — KV-tensor ownership-implies-zero
Let $\text{owners}(s,i)$ denote the sequence ids owning cell $(s,i)$, and
$\text{bytes}(s,i,l,\tau)$ the backend-buffer byte $\tau$ of layer $l$ at that
cell.

$$\forall s, i.\ \text{owners}(s,i) = \emptyset \implies \forall l,\tau.\ \text{bytes}(s,i,l,\tau) = 0 \tag{$I_2$}$$

**Proof.** `seq_rm()` calls `zero_cell_data(s,i)` only when
`cells.seq_rm(i,seq_id)` reports the owner set now empty — so no other
sequence still references the cell when it is zeroed. The offset
`zero_cell_data` writes matches exactly the offset `get_k()`/`get_v()` reads
(row-size-indexed, handling the transposed-V case), so the bytes zeroed are
exactly the bytes attention compute would read. `ggml_backend_tensor_set()`
writes are atomic-on-return. Hence after `seq_rm()` returns, every newly-owner-
less cell is fully zeroed; cells still owned are untouched. ∎ (Empirically:
56/56 cells confirmed, §7.4.)

**Residual model (pre-patch).** The unpatched leak window
$\mathbb{E}[T_\text{unpatched}] = \Theta(n_\text{ctx}/\lambda)$ — for LM
Studio's default $n_\text{ctx}=4096$ at interactive request rates,
$\approx 1.1$ hours mean exposure, unbounded in the worst case (a quiescent
server leaves data in place indefinitely).

**Overhead.** $W = O(|R| \cdot n_\text{layers} \cdot \bar{r})$ over released
cells $R$ — pure memory-bandwidth work. Empirically (N=20, CPU-only): 9.71s
patched vs. 9.84s unpatched mean latency — patched is nominally *faster*,
within noise, both dwarfed by ~8s/req token-generation time
(`KV_CACHE_PATCH_REPORT.md` §4).

### 8.2 I₃ — heap-string released-implies-zero
For the surface §4 actually measures: let $\text{PlaintextMembers}(s)$ be the
slot's live plaintext members (Site A: `generated_text`, `stopping_word`,
`debug_generated_text`; Site B, on the result object: `prompt`, `content`,
`generation_params.sampling.generation_prompt`, …).

$$\forall \text{slot } s,\ \forall m \in \text{PlaintextMembers}(s).\ \text{released}(s) \implies \text{bytes}(m) = 0 \tag{$I_3$}$$

**Proof sketch.** `release()` is the sole `PROCESSING → IDLE` transition and
unconditionally calls `reset()`, which runs `explicit_bzero` (Site A) *before*
any string reassignment. `send_final_response()` is the sole constructor of
the authoritative result plaintext and runs `explicit_bzero` on `res->*`
(Site B) immediately before `queue_results.send()`. So no released slot and no
queued result carries live plaintext, *as objects in this proof's scope*. ∎

**Empirical status: I₃ is proved for Sites A/B in isolation but does NOT
predict the measured system behavior.** D2 (§4.4) shows the headline leak
count is unaffected by Sites A/B (13→13/14). The proof is locally valid —
Sites A/B's own members genuinely are zeroed — but the dominant leak lives in
a region the proof's scope (`PlaintextMembers(s)` for slot/result objects)
never included: the HTTP-layer request-body copies (§4.4, Site C), and likely
further copies in `json::parse()` output and the chat-template render buffer
that remain entirely unpatched and unproved. **I₃ as stated is true but
incomplete** — it covers a real but minor fraction of the actual plaintext
lifecycle. A complete invariant would need to range over every copy site from
HTTP body to slot, which Sites A/B/C only partially enumerate.

**Honest caveat (orthogonal to the above).** `task` is `std::unique_ptr<const
server_task>` — immutable by design, so its plaintext members are *freed but
not zeroed* on `task.reset()`, regardless of Sites A/B/C.

### 8.3 I₄ — allocator-level zero-on-free
Targeted zeroization (I₃) cannot reach the immutable `const task` (§8.2 caveat).
We therefore add a process-wide override of `operator delete`
(`tools/server/secure-allocator.cpp`, ~130 lines) that `explicit_bzero`s every
freed chunk ≥ a 4 KB threshold before returning it to glibc — catching the
immutable task's strings at the deallocation boundary, where `[expr.delete]`
strips the `const` qualifier and the `void*` becomes writable. This establishes:

$$\forall p.\ \text{freed}(p) \wedge \text{size}(p) \geq \theta \implies \text{bytes}(p) = 0 \tag{$I_4$}$$

(`nm` confirms our six `operator delete` symbols win the link over libc as `T`
text, so the override is live, not inert.)

### 8.4 Together — a measured partial mitigation, not a complete closure
Neither object-level (I₃) nor allocator-level (I₄) alone drives the unprivileged
heap-string count to zero. Together, the measured effect across 3 runs is:

| Surface | Observability | Patch | Invariant | Measured effect on 13/tenant baseline |
|---|---|---|---|---|
| KV-cache float tensor | privileged | `kv_cache_zeroize.patch` | I₂ | not re-measured this round; no overhead (prior) |
| live slot/result members | unprivileged | Sites A/B | I₃ | **none** (13→13) — blocked by `const task` |
| freed heap (incl. immutable task) | unprivileged, transient | secure allocator | I₄ | **partial** (13→9–11; some tenants →0) |
| `json::parse()` tree, chat-template render | unprivileged | unpatched | — | residual carrier (multi-lifetime) |

The allocator provably fires (the impossible-without-it state — some tenants at
exactly 0 — occurs) and reduces volume: 12-tenant blast-radius copies 110→78
(−29%), cleartext 10834 KB→3352 KB (−69%). But a clean 0 across all tenants is
**not achieved**, and the 0-vs-9-11 inconsistency across runs is the signature of
a **race**: plaintext propagates through a deep, multi-lifetime pipeline (HTTP
body → `json::parse` tree → chat-template render → `task` → `result` → heap), so
at any scan instant some buffers are still live on another thread and not yet
eligible for zeroing.

**This is the paper's architectural finding:** in a C++ server where sensitive
data is held transitively in `const`-qualified, allocator-managed objects and
propagates through a multi-stage pipeline, *neither* object-level zeroization
nor allocator-level zero-on-free alone is sufficient for data-at-rest hygiene.
Object-level is blocked by `const`; allocator-level is defeated by multi-lifetime
propagation. Complete closure requires defense-in-depth across the full plaintext
lifecycle, and we report both patches as necessary-but-partial, with the complete
closure as an open hardening problem — not a single advertised "fix." A vendor
claim of "we zeroize on release" should be verified against a multi-tenant
`/proc/mem` probe, not taken on trust.

---

## 9. Related Work

**Training-data memorization.** Cooper et al. [arXiv 2505.12546] establish
that LLMs memorize and can regurgitate training data verbatim — a *training-
time* privacy failure. Our work is orthogonal: the leak surfaces in §4 and §7
expose *inference-time* tenant data that was never part of training, via
runtime memory hygiene rather than model behavior.

**"Local is private" framing.** "Local Is Not a Sufficient Privacy Boundary"
[arXiv 2606.10173] argues, at the threat-model level, that on-device
deployment alone is not a privacy guarantee. This paper supplies the concrete
forensic mechanism: §4 and §7 are exactly the data-at-rest failures that make
that argument true for llama.cpp-family runtimes, and §5/§6 show *which* of
the commonly-assumed local-deployment guarantees (no logging, no network
exfiltration) actually hold and which do not.

**KV-cache privacy.** As detailed in §7.1: SafeKV [Chu et al., 2508.08438]
and PrefixWall (formerly CacheSolidarity) [2603.10726] address timing side-
channels on *shared* prefix caches; "Shadow in the Cache" [Luo et al.,
2508.09442, NDSS 2026] addresses semantic inversion of cached tensors with an
adversary who has cache access. Both are complementary, NDSS/peer-reviewed-
adjacent confirmations that the KV-cache is a recognized privacy surface; our
axis (temporal residual from missing zeroization) is distinct from both and,
to our knowledge, previously undocumented for llama.cpp's `seq_rm()` path.

**Reasoning-trace exposure.** A separate line of work (Green et al., EMNLP
2025; ACL ARR 2026; Das et al. 2603.05618; "From Leaky Thoughts to Private
Reasoning" 2602.24210 [author surname flagged for final verification]; Zhang
et al. 2603.07267; Wu et al., NDSS 2025; Kwon et al. 2602.20595) documents
that a model's hidden reasoning channel can leak more than its visible
output. We do not claim this as a contribution of this paper — our reasoning-
channel measurement (Qwen, 56.0% leak rate, corrected from an earlier
mis-tabulated 78.3%) is a secondary, confirmatory data point, not a headline
finding.

**GGUF/runtime CVEs.** CVE-2026-7482 ("Bleeding Llama," Ollama GGUF
out-of-bounds read, CVSS 9.1) and the Databricks GGUF heap-overflow family
(CVE-2024-25664–68) establish that the *allocation-arithmetic* path in GGUF
parsers is a real, exploitable surface — distinct from the *post-allocation
validation* path our 80+ variants tested clean against (§3.4). CVE-2026-5760
is Jinja2 server-side template injection in chat-template rendering — a GGUF
*file* is the delivery vector, but the vulnerable code path is the template
renderer, not the GGUF parser; it must not be characterized as a "GGUF-parser
RCE."

---

## 10. Limitations and Ethics

### 10.1 Limitations
- **Two wrappers tested in depth** (LM Studio, Ollama as control). GPT4All,
  text-generation-webui, Jan not directly tested (Jan dropped from scope per
  an explicit narrowing decision mid-project).
- **D2 (empirical I₃ verification) is measured: one real fix, one open and
  partially-misattributed problem.** The formally-proved I₃ (Sites A/B)
  produces no reduction in the headline leak (13→13/14, three runs).
  Follow-up experimental fixes (Site C: HTTP body; Site D: chat-template
  render buffer in `server-common.cpp`, not part of the original patch or
  proof) close the freed-heap-string leak completely for the first tenant
  (13→0) but expose a second, larger leak mechanism producing a persistent
  (non-decaying) 12-copy count for every tenant after the first.
  `server_prompt_cache` was hypothesized as the carrier (its trigger
  condition matches exactly) but reading its storage format
  (`server-task.h`) **disproves this** — it holds only token IDs and
  serialized binary KV-state, no plaintext. Subsequent checks of
  `to_json()`'s prompt field, the `detokenize()` call sites, and the cache's
  checkpoint type (`common_prompt_checkpoint`) likewise found no unzeroed
  plaintext field — every static-code-reading hypothesis is exhausted.
  Locating the remaining leak requires a live debugger session (not
  attempted this round). We report the freed-heap-string class as **fixed**
  for the case tested, and the second leak as **open, with a known and
  reproducible trigger condition but an unidentified storage location**. See
  §4.4 and §8.2-8.3 for full detail.
- **GPU/VRAM path:** the chat-prompt buffer is `mmap`'d host memory the
  driver also pins for GPU DMA, so the same unprivileged `/proc/<pid>/mem`
  read recovers prompt text on a CUDA-offloaded server (9 copies after 1
  request, 16/16 across 2 additional tenants) — the kernel boundary protects
  model weights and the KV-tensor surface from same-UID attackers, but not
  the heap-string surface, on either backend.
- **KV-patch's transposed-V path** verified end-to-end but not independently
  unit-tested beyond that; the contiguous-V (flash-attention) path not
  separately verified.
- **Single hardware configuration** (4 GB GPU, 15 GB RAM) bounds model
  selection and the number of cross-config reruns feasible.
- **Network result is config/version-specific**: LM Studio's network-clean
  result (§6) holds for the tested version and default configuration; it is
  not a claim about all versions or all configurations.

### 10.2 Responsible disclosure
Two findings warrant coordinated disclosure before or concurrent with
submission: (1) LM Studio's `logSensitiveData: true` default (§5.1), notified
to the vendor with the on/off differential and a recommended opt-in default;
(2) the KV-cache and heap-string zeroization patches, submitted upstream to
llama.cpp as a PR (not a private report) so the fix is auditable and
mergeable rather than just disclosed. Drafts for both are in
`DISCLOSURE_PLAN.md`; sending is pending a decision on sender identity.

### 10.3 Ethics
All measurements were performed against local, self-hosted instances on
hardware we own; no third-party service, account, or user data was accessed.
Canary strings are synthetic UUIDs, not real user data. No exploit was
weaponized or distributed; the GGUF variant battery (§3) produced a negative
result and is released only as a regression-test taxonomy.

---

## 11. Conclusion

Local LLMs are commonly sold on a "no free lunch" implication — free because
the provider can't see your data — without distinguishing claims that are
network claims from claims that are memory-hygiene claims. We measured both,
honestly, across four layers:

- **File-format (§3):** sound against our 80+-variant battery — a genuine
  negative result, not a vulnerability.
- **Runtime (§4, headline):** an **unprivileged**, same-UID-readable
  heap-string leak persists tenant plaintext across slot release; we prove
  and (pending D2) measure a zeroization fix.
- **KV-cache tensor (§7, defense-in-depth):** a privileged-only residual on
  the same release path; proven, benchmarked, formally verified fix with
  unmeasurable overhead.
- **Interface (§5):** the wrapper, not the engine, is the weakest link for
  LM Studio specifically — `logSensitiveData: true` by default, no observed
  retention limit. Ollama, the control case, logs nothing.
- **Network (§6):** the phone-home hypothesis is false for LM Studio (this
  version); network cleanliness is necessary to check and *not* sufficient
  for privacy — it just redirects attention to where the real exposure is.

The contribution is not "local LLMs leak data to their providers" — they do
not, on the network evidence. It is that **data-at-rest hygiene in the
runtime and the wrapper**, not network exfiltration, is where the local-LLM
privacy boundary actually breaks, and that this is fixable with small,
provably-correct, low-overhead patches that upstream has not yet adopted.

---

## References

1. CVE-2025-49847 — llama.cpp vocabulary buffer overflow (CVSS 9.1)
2. CVE-2026-7482 — "Bleeding Llama," Ollama GGUF OOB read (CVSS 9.1)
3. CVE-2026-27940 — llama.cpp integer overflow bypass of CVE-2025-53630 fix (CVSS 7.8)
4. CVE-2026-33298 — `ggml_nbytes` integer overflow → heap overflow
5. CVE-2024-25664–68 — Databricks: 5 GGUF heap overflows
6. CVE-2026-5760 — Jinja2 SSTI via malicious GGUF `chat_template` field (CVSS 9.8); GGUF is the delivery vector, not the vulnerable parser path
7. Green et al., "Leaky Thoughts: Large Reasoning Models Are Not Private Thinkers," EMNLP 2025
8. "Hidden Thoughts Are Not Secret: Reasoning Trace Exposure in LLMs," ACL ARR 2026
9. Das et al., "Safer Reasoning Traces," arXiv 2603.05618, 2026
10. Batra et al., "From Leaky Thoughts to Private Reasoning: Controlling What LRMs Say to Themselves," arXiv 2602.24210, 2026. ⚠ author surname not independently re-verified
11. Zhang et al., "Trace Inversion," arXiv 2603.07267, 2026
12. Wu et al., "PROMPTPEEK," NDSS 2025
13. Kwon et al., "OptiLeak," arXiv 2602.20595, 2026
14. Chu et al., "Selective KV-Cache Sharing to Mitigate Timing Side-Channels in LLM Inference" (SafeKV), arXiv 2508.08438, 2025
15. "PrefixWall" (formerly "CacheSolidarity"), arXiv 2603.10726, 2026
16. Luo, Shao, Zhang, Zhou, Hu, Zhao, Liu, Qin, "Shadow in the Cache: Unveiling and Mitigating Privacy Risks of KV-cache in LLM Inference," arXiv 2508.09442, NDSS 2026
17. Cooper et al., arXiv 2505.12546, 2025 — training-data memorization
18. "Local Is Not a Sufficient Privacy Boundary," arXiv 2606.10173, 2026
19. OWASP LLM Top 10 (2025)
20. Carlini et al., "Extracting Training Data from Large Language Models," USENIX 2021
21. `DEEP_LEAK_REPORT.md` (this work) — KV-cache RAM residual + multi-tenant recovery
22. `KV_CACHE_PATCH_REPORT.md` (this work) — I₂ patch mechanism, verification, benchmark
23. `PROMPT_ZEROIZE_PATCH_REPORT.md` (this work) — I₃ patch mechanism, verification (pending D2), benchmark
24. `TELEMETRY_FINDINGS_4MODELS.md` (this work) — netns-isolated 4-model network sweep
25. `RECONCILED_NUMBERS.md` (this work) — cross-report claim reconciliation
26. `CITATION_AUDIT.md` (this work) — primary-source verification log</new_string>

