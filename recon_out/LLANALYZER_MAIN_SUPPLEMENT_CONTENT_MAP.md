# LLAnalyzer main-paper / supplementary content map

The allocation below keeps the main manuscript independently evaluable while
placing procedural and provenance detail in the technical companion.

| Subject | Main manuscript | Supplement | Allocation rationale |
|---|---|---|---|
| Motivation and research gap | Introduction, pp. 1--2 | Relationship to Main Manuscript | The motivation and gap are necessary for independent review; the supplement only states the document relationship. |
| Four confidentiality boundaries | Framework, Sec. II | Sec. S1, boundary/adversary tables S1--S2 | The main paper defines the conceptual model and objectives; the supplement supplies the compact reference tables. |
| Threat model | Sec. II-C | Sec. S1 boundary mapping | The tested actors and untested authorization boundary must be visible in the main paper; the supplement provides the table form. |
| LLAnalyzer workflow | Sec. III, design goals and pipeline | Sec. S1 synthetic workload and acquisition details | The main paper explains why the workflow is scientifically useful; the supplement records instrumentation and evidence-source details. |
| Hardware and runtime provenance | Sec. III-D and Open Science | Sec. S1 hardware/software tables and chronology | The main paper gives the provenance limits that affect interpretation; the supplement preserves the complete configuration record. |
| GGUF integrity observations | RQ1 and integrity table | Sec. S1 model-file corpus | The main paper reports separate retained report families and the `phi3`/`phi4` identity caveat; the supplement describes corpus targets and missing artifacts. |
| Runtime residue | RQ2.1--RQ2.2 and residue table | Sec. S1 memory-acquisition and workload protocol | The main paper states the 11/12 observations and evidence-consistent mechanism account; the supplement defines the collector and scan scope. |
| D4 model-swap residue | RQ2.2 | Sec. S1 D4 workload | The main paper preserves the 200 primary records and pair assignments; the supplement records process identity, canary oracle, and debug-file exclusion. |
| Sanitisation and allocator observations | RQ2.3 and runtime tables | Sec. S1 runtime configurations and Sec. S2 memory/statistical definitions | The main paper keeps the descriptive 11/12 and latency results plus their causal limits; the supplement distinguishes configured capabilities from retained records. |
| GPU-v5 host-memory evidence | RQ2.4 and GPU table | Sec. S1 acquisition permissions and model/runtime details | The main paper gives field meanings and the Nemotron-only scope; the supplement explains why host-memory observations do not establish device-memory recovery. |
| LM Studio and Ollama | RQ3 | Sec. S1 wrapper workload and provenance | The main paper gives the Nemotron logging-toggle result, four-model hook scope, and 206/203/2/1 Ollama accounting; the supplement records capture limitations and version status. |
| Slot equality and continuation | RQ4 | Sec. S1 shared-process slot workload | The main paper must state the oracle, chronology, denominators, and untested credentials; the supplement preserves request sequence and model-specific offload settings. |
| Related work and contribution positioning | Sec. V | Not duplicated | This synthesis is part of the argument reviewers must evaluate in the main paper. |
| Statistical treatment | Controls paragraph and result-specific caveats | Sec. S2 | The main paper states descriptive versus causal interpretation; the supplement provides Wilson, unit-of-analysis, and null-result definitions. |
| Reproducibility and open science | Sec. III and Open Science | Sec. S1--S2 provenance paragraphs | The main paper exposes missing hashes, vectors, and artifact URL status; the supplement lists exact retained/missing evidence classes. |
| Ethics and disclosure status | Main Open Science/Ethical Considerations | Sec. S1 disclosure paragraph | The main paper keeps the concise status statement; the supplement supplies the operational scope and capture boundary. |

No essential control, denominator, model attribution, or limitation was moved
out of the main paper. The supplement extends traceability rather than serving
as a repository for otherwise necessary qualifications.
