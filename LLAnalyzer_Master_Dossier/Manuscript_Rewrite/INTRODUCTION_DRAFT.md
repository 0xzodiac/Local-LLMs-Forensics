# Introduction: author-editable draft

Large language models can now run entirely on personal computers through
consumer serving stacks such as LM Studio, Ollama, and `llama.cpp`. For
privacy-sensitive workloads, the appeal is clear: prompts need not be sent to a
cloud inference provider. Yet “local” describes the location of computation,
not the lifetime, storage, or ownership of the prompt after it enters the
serving stack.

A single request can be parsed by a wrapper, copied into JSON and chat-template
objects, tokenized, retained in allocator-managed memory, associated with KV or
slot state, written to logs, and exposed through a shared interface. Each stage
can make a different confidentiality decision. A model can be admitted safely
while its prompt survives in memory; a memory control can be effective while a
wrapper writes the same request to disk; and an authenticated service can lack
resource-level ownership for saved state.

Existing work provides important but separated evidence about model
memorisation, malformed model files, prompt injection, memory forensics, and
shared KV-cache timing. What is missing is a measurement framework that follows
the prompt across the complete local serving lifecycle and attributes an
observation to the boundary in which it occurs. Without that decomposition, a
negative parser test can be mistaken for a system-wide privacy result, or an
interface observation can be overgeneralized into a claim about runtime memory.

We present LLAnalyzer, which divides the stack into four boundaries. B1 covers
model-artifact integrity and admission. B2 covers the lifetime of prompt-bearing
runtime representations. B3 covers wrapper-managed persistence and monitored
external communication. B4 covers shared serving state, saved-slot ownership,
and cache-derived timing. For each boundary, LLAnalyzer injects a controlled
artifact or UUID canary, records the relevant observation, and states the threat
model required to interpret it.

The evaluation produces an intentionally uneven result. The reported GGUF
campaign observed no relevant failure in its explored state space. Under the
authorized forensic collector used for memory measurement, canaries remained
recoverable from 11 of 12 sequential tenants. The evaluated sanitisation reduced
recorded copy and matching-region metrics, but not tenant-level recovery. In an
LM Studio configuration with sensitive-data logging enabled, canaries appeared
in wrapper-managed logs; bounded Ollama monitoring found no canary in the
examined channels. In a shared `llama-server` configuration, direct saved-state
transfer occurred in 200/200 trials, while model-mediated secret continuation
occurred in 126/200 trials with strong model dependence.

The paper makes four contributions. First, it formulates prompt confidentiality
as a four-boundary systems property. Second, it implements LLAnalyzer as a
measurement and attribution framework. Third, it reports the cross-boundary
observations and their configuration-specific mitigations. Fourth, it provides a
provenance-aware account of local recomputation, secondary review, and the
author-reported complete cross-machine rerun by collaborator Dr. Mohammed
Ikram. The latter is reported as collaborative corroboration, not as an
artifact-inspected third-party reproduction.

The rest of the paper defines the boundaries and threat model, describes the
framework and methodology, evaluates RQ1--RQ4, discusses implications and
limitations, positions the work against related research, and concludes with
the open-science record.

