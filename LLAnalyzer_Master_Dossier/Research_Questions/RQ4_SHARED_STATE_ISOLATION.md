# RQ4 dossier: shared-state isolation

## 1. Research question

Does a shared local serving interface prevent one authenticated client from
restoring another client's saved state or inferring whether a candidate prompt
prefix was previously processed?

## 2. Security hypothesis

Authentication answers who may enter the interface. It does not necessarily
answer who owns a saved slot, cache entry, or shared resource. If slot save/load
identifiers are not bound to a resource owner, a second authenticated client may
restore another client's state. Shared prefix caching may also create a timing
signal without exposing plaintext.

## 3. Saved-slot protocol

The shared server is configured with slot save/load support and two logical
clients. The victim client submits a fresh UUID-bearing secret and saves slot
state. A second client with a different valid API credential attempts to restore
the state. The protocol-level result is scored before the model-mediated result:

1. create victim session;
2. save victim state;
3. restore from the second authenticated context; and
4. record direct state transfer separately from any generated continuation.

The experiment demonstrates a confidentiality hazard under the evaluated shared
server. It does not prove that the keys correspond to independent tenant
principals or that an upstream maintainer has classified the behavior as a
vulnerability.

## 4. Retained numerical results

The retained slot file and four detailed extraction files support:

| Model | Direct transfer | Model continuation |
|---|---:|---:|
| Gemma | 50/50 | 50/50 |
| Qwen | 50/50 | 50/50 |
| Nemotron | 50/50 | 25/50 |
| Phi-4 | 50/50 | 1/50 |
| **Pooled** | **200/200** | **126/200** |

The pooled continuation proportion is `126/200 = 0.63` with a 95% Wilson
interval approximately `[0.5612263, 0.6938739]`. The direct-transfer Wilson
interval is approximately `[0.9811547, 1.0]`. These are descriptive binomial
intervals; sequential/shared-server dependence and the representation of logical
clients limit an independence interpretation.

The direct transfer and continuation outcomes answer different questions:

- 200/200 asks whether protocol state can be transferred.
- 126/200 asks whether the model subsequently emits the secret under the
  tested decoding and response path.

Failure to generate the secret is not evidence that the saved state was not
transferred. Model stopping behavior and reasoning channels affect continuation.

## 5. Timing protocol

The historical timing workload compares cached and uncached prompt-prefix
requests using time-to-first-token under evaluated loopback/LAN conditions. The
manuscript reports AUC=1.000 for four models. The local audit did not find the
per-request TTFT vectors, request-order manifest, or original AUC script. The
result therefore remains a historical report, not an independently recomputed
timing statistic.

The retained patched/unpatched KV benchmark vectors are a different experiment
and must not be substituted for cached/uncached TTFT data.

## 6. Variables and limitations

- **Independent variables:** client credential, slot identifier, model, saved
  state, cache condition, and request sequence.
- **Dependent variables:** direct restore response, exact state/token match,
  generated secret, and TTFT.
- **Controls:** fresh secrets, 50 trials/model, separate credential inputs,
  direct-transfer scoring, continuation scoring, and timing condition labels.
- **Limitations:** authenticated keys are not proved independent principals;
  server-wide configuration and sequential trials may create dependence;
  no WAN claim is made; source/binary linkage is incomplete.

## 7. Evidence classification

Direct transfer and continuation arithmetic are **E1** from retained per-trial
records and **E2** as recorded observations. Timing AUC is **E4**. Dr. Ikram's
complete rerun is an **AUTHOR-REPORTED MATCH** with no inspected server-side
slot/timing artifacts. No third-party independent reproduction is claimed.

## 8. Publication-ready interpretation

> In the evaluated shared-server configuration, a second authenticated client
> restored saved state in 200/200 trials. The subsequent model-mediated secret
> continuation occurred in 126/200 trials, with strong model dependence. The
> direct transfer result is therefore the primary protocol observation; the
> continuation result is a separate model-output channel. Because the experiment
> used valid credentials in one shared authentication domain, it demonstrates a
> resource-isolation hazard rather than proving that API keys represent distinct
> tenant principals.

