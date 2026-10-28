# System design: author-editable draft

## Framework architecture

LLAnalyzer treats a local deployment as a chain of components rather than a
single trusted box. A request enters through a consumer wrapper or HTTP client,
passes through request parsing and prompt construction, reaches tokenization and
the inference runtime, and interacts with model artifacts, allocator-managed
buffers, KV cache, and slot state. The response then returns through wrapper
handling, logging, history, and the shared serving interface.

The framework's key design decision is to place an evidence point at each
confidentiality boundary. A malformed artifact is judged at model admission. A
memory canary is judged after inference and logical release. A persistence
canary is judged in files or monitored egress. A saved-slot canary is judged at
the protocol and model-output layers separately.

## Evidence pipeline

Each experiment follows five steps:

1. Define the boundary objective and threat actor.
2. Inject a known artifact or fresh UUID canary.
3. Execute the smallest boundary-specific workload.
4. Acquire the channel-specific evidence.
5. Classify the result as observed, not observed, or not determinable under the
   documented instrumentation.

## B1 design

Structured GGUF mutations target semantic validation paths; coverage-guided
inputs explore parser states. Loader status and sanitizer output are recorded.
The result is a bounded parser observation, not a global safety certificate.

## B2 design

The memory harness launches the target as a child and scans writable mappings
through `/proc`. UUID matches provide exact attribution to the originating
request. KV-cache instrumentation is separate from literal text scanning because
KV cells hold floating-point state after tokenization. The baseline/sanitised
aggregate and direct KV-cell mechanism test are reported as different evidence
classes.

## B3 design

Wrapper inspection searches application-managed logs/files before and after a
configuration change and restart. Network monitoring records external attempts
and excludes expected loopback inference traffic. The design reports product,
version, setting, and observed channels rather than generalizing from one
wrapper to all local applications.

## B4 design

The saved-slot harness creates a victim state and asks another authenticated
client to restore it. It scores direct state transfer before scoring a generated
secret. The timing workload uses TTFT to test whether shared prefix reuse is
distinguishable. The latter remains a historical report without locally retained
vectors.

