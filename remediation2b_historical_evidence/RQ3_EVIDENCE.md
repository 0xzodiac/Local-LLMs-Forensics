# RQ3 evidence: persistence and network observations

## LM Studio

Historical reports identify `logSensitiveData` enabled in the evaluated configuration and report canary recovery from a plaintext server log, with no canary after disabling that setting and restarting. The original plaintext log is not retained in this project, so the finding is **E4** here: a historical summary supported by referenced probes, not an independently rescanned primary file. It must not be restated as a universal or clean-install default.

The six retained LM Studio telemetry summaries report startup connections but no canary in captured egress. This is a bounded network observation, not proof that encrypted payloads contained no other prompt-derived data or that later versions behave identically.

## Ollama

The workspace retains 205 valid canary-generation telemetry sessions and one incomplete directory. Six summary envelopes plus lower-level packet/trigger/idle artifacts report no canary egress in the captured sessions. The result is **E2** for the retained bounded negative observation, with the caveat that not all sessions have a summary envelope and that unexamined files or versions are outside scope.

## Grade

Persistence claims are mixed: LM Studio log persistence **E4**, Ollama bounded monitored-artifact/network observations **E2**, and any product-wide default or retention claim **E5** if stated without configuration and version bounds.
