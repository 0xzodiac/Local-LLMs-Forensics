# Architecture explanation for Figure 1

## Upper data path

1. **Client/wrapper entry:** a user or API client supplies a prompt. The
   wrapper may add settings, chat templates, logging, and history.
2. **Serving API:** JSON and authentication are parsed by the server. B4 begins
   here because authentication and resource ownership are separate decisions.
3. **Prompt construction:** templates, request strings, and token buffers create
   multiple prompt-bearing representations. B2 begins here.
4. **Model admission:** GGUF headers, metadata, tensor descriptors, offsets, and
   allocations are validated. B1 is crossed before inference.
5. **Runtime/KV state:** scheduling, tokenization, attention, KV cache, and slot
   state hold derived and sometimes recoverable prompt information.
6. **Response and wrapper handling:** generated output returns through the
   wrapper, where logs, history, temporary files, and external connections may
   extend lifetime. B3 is measured here.

## Four boundary panels

- **B1:** inputs are malformed artifacts; output is loader/sanitizer behavior.
- **B2:** inputs are UUID canaries; output is authorized memory/KV evidence.
- **B3:** inputs are canary-bearing requests and configuration changes; output is
  file/network presence.
- **B4:** inputs are victim state and second-client requests; output is direct
  transfer, continuation, or timing distinguishability.

## Arrows that must be explained

The arrow from wrapper to server is a protocol path, not proof that the wrapper
is trusted. The arrow from prompt construction to runtime is where copies and
tokenized state diverge. The arrow from runtime to persistence is optional but
important: a wrapper can retain plaintext even if the runtime is cleaned. The
arrow from runtime to shared slot/KV state is the B4 resource path; a valid
credential does not establish ownership of the resulting state. The evidence
arrows point to measurements, not to universal security conclusions.

