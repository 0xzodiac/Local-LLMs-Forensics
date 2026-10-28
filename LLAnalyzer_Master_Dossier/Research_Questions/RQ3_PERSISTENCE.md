# RQ3 dossier: wrapper-managed persistence

## 1. Research question

Do consumer local-LLM wrappers retain prompt material in files or expose it
through external communication after the inference request completes?

## 2. Security hypothesis

A wrapper can extend prompt lifetime independently of the model runtime. A
prompt may be written to server logs, prediction history, temporary files, or
other application artifacts even when inference remains on-device. Conversely,
absence of a canary in a monitored channel does not prove that every storage or
transmission channel is clean.

## 3. LM Studio protocol

The retained LM Studio report evaluates a configuration with
`logSensitiveData: true` in
`~/.lmstudio/.internal/http-server-config.json`. A canary-bearing API request
is submitted, the server log directory is searched, the setting is changed to
`false`, the server is restarted, and a new canary-bearing request is tested.
The report also distinguishes `ttlDays` for internal prediction history from
file-based server logs: setting the former to zero does not retroactively delete
or disable the latter.

The local report records a model/configuration-specific environment, including
LM Studio v0.0.15-2 and a llama.cpp backend, but the historical audit does not
retain a clean-install executable/profile sufficient to support a universal
default claim. The correct manuscript phrase is “in the evaluated LM Studio
configuration with sensitive-data logging enabled,” not “LM Studio always logs
prompts by default.”

## 4. LM Studio measurements

The baseline report records canaries in cleartext server logs when sensitive
logging is enabled. After changing the internal setting to false and restarting,
the new test canary was not found in the searched logs. Existing historical log
files remained on disk; disabling future logging is not retroactive deletion.

The result establishes:

- configuration-dependent prompt persistence;
- an effective on/off differential for the tested setting; and
- the need to separate logging controls from prediction-history TTL.

It does not establish clean-install defaults for all versions, encryption
behavior for every artifact, or absence from unexamined application channels.

## 5. Ollama protocol

The telemetry work covers 205 valid Ollama canary-generation sessions plus one
incomplete directory without a trigger. Six summary envelopes and lower-level
packet/trigger/idle records were retained in the workspace. The reported bounded
observation is that no recoverable canary appeared in captured external egress
or searched monitored artifacts.

Loopback traffic required for local inference is excluded from the external
connection count. This is a negative observation under the monitored version,
files, capture scope, and canary analysis. It is not a proof that all future
versions, encrypted payloads, unobserved files, or every wrapper channel are
clean.

## 6. Variables and controls

- **Independent variables:** wrapper, configuration setting, restart state,
  model/request, and monitored channel.
- **Dependent variables:** exact canary presence in files, logs, captured
  egress, or summary records.
- **Controls:** baseline canary with logging enabled, setting disabled followed
  by restart, recursive artifact search, packet capture, trigger/idle records,
  and local-loopback exclusion.
- **Unit:** individual canary-bearing request/session.

## 7. Evidence classification

LM Studio plaintext persistence is **E4 in the local historical audit** because
the original plaintext server log is absent even though reports and referenced
probes remain. The bounded Ollama observation is **E2** for retained structured
monitoring records. The external expert review and Korean discussion are
secondary review/summary material, not a new wrapper execution.

## 8. Publication-ready interpretation

> Wrapper behavior can dominate prompt confidentiality after inference. In the
> evaluated LM Studio configuration, enabling sensitive-data logging caused
> prompt canaries to appear in wrapper-managed server logs, while disabling the
> setting and restarting prevented the tested canary from appearing in new log
> output. Comparable monitored Ollama sessions yielded no captured canary in
> the examined egress and artifacts. These are configuration- and observation-
> bounded results, not a universal default claim for either product.

