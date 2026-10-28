# Proposed manuscript text for author approval

These passages are proposed only. They have not been inserted into the
authoritative T-IFS manuscript.

## Reproducibility / experimental protocol paragraph

> In addition to the primary evaluation, the authors report a complete rerun of
> the LLAnalyzer framework by collaborator Dr. Mohammed Ikram on a separate
> research server. The reported rerun covered the four evaluation boundaries
> (GGUF integrity, memory residue and sanitisation, persistence/network
> observations, and saved-state/timing behaviour) and reproduced the original
> experimental results. This is a cross-machine collaborative replication
> report; it is distinct from an independently executed third-party
> reproduction. The present artifact record documents the rerun as author
> reported. The experiment-level run manifest, environment manifest, raw
> outputs, and source-to-binary hashes should be provided separately for
> verification.

The final sentence should be changed if the requested existing records are
located and attached to the artifact package. It should then name the verified
records rather than implying that they are currently available in this local
checkout.

## Results qualification paragraph

> The cross-machine rerun provides corroborating evidence that the framework's
> reported observations are not confined to a single research server. Because
> the rerun is reported by a collaborating author and its complete raw record
> is not part of the present local audit package, we do not use it to claim
> independently recomputed per-trial counts, confidence intervals, timing AUCs,
> or exact binary-level equivalence. The numerical values in the tables remain
> attributed to the primary records and are interpreted with the provenance
> limitations described in the artifact documentation.

## Limitations paragraph

> The replication evidence has two levels. Selected primary records were
> independently recomputed from retained local JSON/CSV-derived outputs, while
> the complete cross-machine rerun by Dr. Ikram is currently documented as an
> author-reported match pending inspection of its existing run and provenance
> records. This distinction does not imply that the rerun did not occur; it
> limits only the strength of the artifact-verification claim. We also do not
> treat the secondary review by P. K. Sharma as an independent experimental
> reproduction.

## Artifact/reproducibility statement

> Reproducibility materials should identify, for each experiment, the source
> revision, patch set, build flags, executable hash, model hash, server
> configuration, raw output path, and analysis script. The authors report that
> a collaborator completed a full cross-machine rerun; the corresponding
> existing records should be released or made available to the reviewers, with
> sensitive prompts and credentials redacted in a documented manner, before the
> rerun is described as artifact-verified.

## Wording to avoid

Do not use “independent third-party reproduction,” “bit-for-bit replication,”
“independently verified AUC,” or “all replication artifacts were inspected”
unless the corresponding evidence is actually supplied and audited. Do not
insert exact Ikram counts merely because the author reported that the results
matched.
