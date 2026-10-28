# LLAnalyzer system architecture

## Conceptual data path

The architecture follows this path:

```text
user/client -> wrapper or HTTP client -> serving API -> request parser
    -> prompt/chat-template construction -> tokenizer -> runtime scheduler
    -> model artifact/tensor access + KV/slot state -> generated response
    -> wrapper response handling, logs, history, and shared state
```

The arrows are data-flow arrows, not trust statements. A prompt can be copied
at each transition. LLAnalyzer places an observation point at the boundary where
the confidentiality decision is made.

## B1: model-artifact integrity

B1 begins before the prompt reaches inference. A supplied GGUF file is admitted
through header, metadata, tensor, offset, and allocation validation. The
structured corpus mutates dimensions, names, metadata lengths, architecture
fields, offsets, RoPE parameters, and related consistency fields. The
coverage-guided campaign explores parser states with sanitizer instrumentation.

The evidence point is the loader outcome: clean rejection, handled parse error,
process termination, successful malformed load, crash, or sanitizer failure.
The retained negative result means no relevant failure was observed in the
explored corpus and campaign. It does not certify every parser path.

## B2: runtime memory lifetime

B2 begins when the request is parsed and prompt-bearing representations are
created. Relevant representations include JSON request objects, formatted chat
templates, token buffers, `std::string` objects, response buffers, slot state,
and KV-cache tensors. The memory collector acquires writable regions through the
documented authorized path after inference and after logical release.

Two surfaces must remain separate:

- literal canary text in ordinary heap/request/response buffers; and
- floating-point KV-cache data that does not contain the literal ASCII canary.

The KV zeroisation patch targets the latter. A literal string scan is not a
valid test of KV tensor erasure.

## B3: wrapper-managed persistence

B3 begins when the wrapper receives the request and continues after the serving
process returns. LM Studio and Ollama may differ in logging, history, temporary
files, and network behavior. The measurement points are configuration files,
rotated server logs, application directories, packet captures, and canary
searches. The evaluated LM Studio result concerns sensitive-data logging as
configured; the Ollama result concerns the monitored sessions and channels.

## B4: shared serving-state isolation

B4 begins at the shared API and its authentication middleware. A victim client
creates a secret-bearing session, saves slot state, and a second authenticated
client attempts a restore. Direct state transfer is scored separately from
whether the model subsequently emits the victim secret. A timing probe is a
third, weaker outcome: it asks whether shared prefix reuse is externally
distinguishable without recovering plaintext.

## Figure 1 explanation

The current source is
`LLAnalyzer-revised-10point/figures/fig_llanalyzer_arch.tex`; the compiled
artifact is `fig_llanalyzer_arch.pdf`. The manuscript caption describes the
request path above the four boundaries. Reuse the figure without redesigning it.
During rewriting, explain the arrows in this order: request entry, prompt
construction, model loading, runtime/KV state, response/wrapper handling, and
shared state. Explicitly label the F acquisition point and the A2 protocol
observation point so readers do not mistake them for the same threat.

## Measurement-point table

| Point | Observable | Boundary | Interpretation |
|---|---|---|---|
| P1 | GGUF load status, sanitizer output | B1 | Parser/loader behavior |
| P2 | Writable-memory canary matches and region metadata | B2 | Residual existence under F |
| P3 | KV cell bytes before zeroisation | B2 | Mechanism-level tensor evidence |
| P4 | Wrapper files/logs | B3 | Persistent artifact retention |
| P5 | Packet/trigger/idle telemetry | B3 | Bounded egress observation |
| P6 | Slot restore response and per-trial secret | B4 | Protocol transfer and model continuation |
| P7 | Cached/uncached TTFT | B4 | Historical timing distinguishability |

