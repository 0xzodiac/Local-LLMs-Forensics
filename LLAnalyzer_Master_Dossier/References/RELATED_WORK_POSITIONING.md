# Related-work positioning

## The paper's gap

The bibliography contains separate lines of work on model memorisation, parser
vulnerabilities, wrapper forensics, secure memory, prompt injection, and
shared-cache timing. LLAnalyzer's gap is methodological: it connects the
confidentiality decisions made by these layers in one local serving stack and
uses boundary-specific observations to prevent category errors.

## Comparison axes

| Axis | Prior line | LLAnalyzer position |
|---|---|---|
| Object of protection | Training data, model weights, or one prompt channel | User prompt across the entire serving lifecycle |
| Unit of analysis | One primitive or product | Four explicit confidentiality boundaries |
| Evidence | Attack/recovery or code analysis | Controlled canaries, malformed artifacts, memory/file/network/protocol evidence |
| Threat semantics | Often product- or primitive-specific | Separates F, A1, A2, A3 and states permission requirements |
| Negative results | Frequently omitted | Preserves RQ1 and Ollama null observations with scope |
| Mitigation | Component-specific | Compares runtime sanitisation, wrapper configuration, and resource authorization |
| Reproducibility | Varies by source | Separates raw recomputation, historical summaries, collaborative rerun, and secondary review |

## Novelty sentence for related work

> The contribution is not a claim that any individual parser, wrapper, or cache
> primitive is unprecedented. It is a lifecycle measurement and evidence model
> showing how a local deployment can satisfy network locality while failing
> other confidentiality boundaries.

