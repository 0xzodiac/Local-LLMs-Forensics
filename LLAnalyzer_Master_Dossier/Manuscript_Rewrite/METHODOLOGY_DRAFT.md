# Methodology: author-editable draft

## Environment and model corpus

The principal workload uses a dedicated bare-metal Ubuntu workstation recorded in
the supplement: Intel Core i7-9850H at 2.60 GHz, 16 GB RAM, an 8 GB
CUDA-capable GPU, NVIDIA driver 595.84, CUDA 12.0, and ext4. Native Ubuntu is
used for headline memory/isolation and GPU observations; early WSL2 results are
identified separately. The model corpus contains four GGUF Q4_K_M model
families: Gemma, Qwen, Nemotron, and Phi-4.

The retained project records identify model digests in
`Runs/provenance/model_digests.json`, but the model files, original binary hash,
and historical source-to-run manifest are not present. This distinction is
carried into the reproducibility statement.

## Controlled canaries

Each trial generates a fresh UUID, checks its absence from the relevant
pre-experiment source, embeds it in the prompt, and records its origin. Exact
matches are scored in process memory, wrapper artifacts, captured traffic,
protocol responses, reasoning fields, or another client's continuation.

## Experimental conditions

RQ1 uses the 80-case structured battery, 21-file structural corpus, and reported
24-hour campaign exceeding 12 million parser executions. RQ2 uses sequential
tenant memory acquisition, baseline/sanitised conditions, KV-cell inspection,
allocator controls, and a partial-offload host-memory condition. RQ3 compares
the evaluated LM Studio logging setting with bounded Ollama monitoring. RQ4
uses 50 direct saved-slot trials per model, separate continuation scoring, and
the reported cached/uncached timing workload.

## Acquisition and permissions

The headline memory collector is F, not A1. It launches the server as a child,
reads writable maps, and accesses memory through the Linux checks documented in
the supplement. GDB and CUDA-GDB diagnostics are separate and are not used to
claim unprivileged access.

## Statistical analysis

Binary proportions use two-sided 95% Wilson intervals. Memory changes are
relative descriptive reductions from the retained recorded fields. The timing
AUC is reported only as a historical result because its underlying per-request
vectors and script are not retained. Model-specific continuation rates remain
visible rather than being replaced by a single pooled interpretation.

## Replication and artifact status

The author reports that Dr. Mohammed Ikram completed a full rerun on a separate
research server and obtained matching results. This is included as author-
reported collaborative replication. It does not supply exact rerun numbers or
server configuration and is not called artifact-verified or third-party
independent reproduction.

