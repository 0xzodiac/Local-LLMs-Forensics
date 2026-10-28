# Existing-record evidence request for the Ikram rerun

This request is intentionally limited to records that already exist. It does
**not** request a third experimental campaign, new model downloads, new LLM
inference, GPU work, or a new timing study.

## Minimum sufficient packet

Please provide the existing read-only directory, archive, or artifact links for
Dr. Ikram's completed rerun, together with a checksum if one exists. The
minimum packet is:

1. **Run index:** a short mapping from each LLAnalyzer experiment to its output
   path, run ID, date, and status. If a component was not included, mark it
   explicitly.
2. **Environment manifest:** host hardware, OS/kernel, compiler/runtime,
   server/library versions, and relevant startup flags.
3. **Source/build manifest:** source commit or archive identity, patch list and
   hashes, build command/flags, executable SHA-256, and model filename/hash.
4. **Raw output index:** paths and hashes for JSON/CSV/log/pcap/sanitizer files,
   plus the analysis scripts or notebooks that generated reported tables.
5. **Comparison note:** the existing author/collaborator note that says how the
   rerun was judged to reproduce the original results, including whether
   “match” means exact numeric equality, qualitative agreement, or agreement
   within a tolerance.

## Experiment-specific records

Only supply the records that already exist:

| Area | Existing records needed to verify the reported rerun |
|---|---|
| RQ1 GGUF | Corpus manifest, per-case exit/status table, sanitizer/coverage logs, long-campaign run log, executable and source identity |
| RQ2 memory | Memory-acquisition metadata, raw region/match records or retained summary outputs, baseline/sanitised run IDs, patch/build identity, and model hash |
| RQ2 KV/prompt mitigation | Probe vectors, latency vectors, prompt-zeroisation run records, patch and binary hashes, and analysis output |
| RQ3 LM Studio | Product/version/configuration manifest, plaintext server-log or canary report, restart/setting-change record, and network-capture summary if used |
| RQ3 Ollama | Version/configuration manifest, session index, packet/trigger/idle records, and canary-analysis output |
| RQ4 saved slots | Slot-save/load configuration, client/API identity description, per-trial JSON, server logs, model hashes, and analysis output |
| RQ4 timing | Paired cached/uncached per-request TTFT vectors, order/load manifest, exact AUC script, and rendered/derived result |

## Preferred transfer format

A read-only tar/zip or mounted directory is sufficient. Please preserve the
original relative paths and do not regenerate or edit files before transfer.
If sensitive prompts, credentials, or host identifiers are present, redact or
replace them in a documented copy while retaining hashes for the unredacted
records where policy permits.

## What this request will establish

With the minimum packet, the status can move from `AUTHOR-REPORTED MATCH` to
`VERIFIED MATCH` for the rows whose source-to-analysis chain is complete. A
partial packet can still verify individual RQ1--RQ4 experiments. Missing records
will remain explicitly marked `NOT DETERMINABLE`; they will not be inferred from
the general statement that the complete framework was rerun.

