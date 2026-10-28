# Related work: author-editable draft

## Model artifacts and parser safety

Prior work and vulnerability records document malformed model parsing,
allocation arithmetic, tensor validation, and template-injection risks. The
LLAnalyzer RQ1 contribution is narrower: it evaluates a structured validation
gap and a reported coverage-guided campaign, then preserves the explored-state
negative result without claiming global parser safety.

## Memory forensics and secure memory

Forensic studies show that local applications and processes may retain prompt or
conversation artifacts. Secure-memory work motivates explicit zeroisation,
allocator controls, and `explicit_bzero`-style invariants. LLAnalyzer adds a
serving-runtime perspective: it measures prompt canaries after inference,
separates ordinary heap-string residue from KV tensor state, and reports the
limits of a sanitisation comparison.

## Wrapper persistence

Product-specific logging and local-storage work demonstrates that deployment
wrappers can change the privacy properties of a model runtime. LLAnalyzer's
LM Studio/Ollama comparison shows why “local” cannot be treated as one wrapper-
independent category. The result is configuration-specific and complements,
rather than replaces, product documentation review.

## Shared state and timing

Prior work on KV-cache sharing, prefix reuse, timing leakage, and state
reconstruction motivates RQ4. LLAnalyzer connects two outcomes: direct saved-slot
state transfer and model-mediated continuation. It also retains the historical
timing result while explicitly separating it from the locally recomputed KV
overhead benchmark.

## Prompt injection and memorisation

Prompt-injection work studies how instructions alter model or agent behavior;
memorisation work studies training-data extraction. LLAnalyzer uses controlled
canaries as provenance markers to measure prompt handling after a request enters
the serving stack. It should not be presented as a replacement for either line
of research.

## Positioning sentence

> Unlike studies that isolate a parser, wrapper, memory, or cache primitive,
> LLAnalyzer uses one boundary-oriented measurement design to connect these
> surfaces and to state the threat model needed to interpret each observation.

