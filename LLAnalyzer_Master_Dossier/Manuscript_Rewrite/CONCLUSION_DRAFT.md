# Conclusion: author-editable draft

Local inference changes where computation occurs, but it does not by itself
define how prompt data are admitted, copied, retained, persisted, or shared.
LLAnalyzer makes those decisions explicit through four confidentiality
boundaries.

Across the evaluated systems, the boundaries behaved differently. We observed
no relevant parser failure in the reported explored state space, but found
post-inference prompt residue under authorized forensic acquisition,
configuration-dependent wrapper persistence, and shared-server saved-state
transfer with model-dependent continuation. The evaluated sanitisation reduced
recorded residue metrics without changing tenant-level recovery. These results
support lifecycle-wide controls rather than a single “local” privacy label.

The authors also report a complete rerun by collaborator Dr. Mohammed Ikram on a
separate research server with matching results across the framework. We record
this as collaborative cross-machine replication. Selected local arithmetic was
independently recomputed from retained records, while the Ikram server-side
artifacts and the original timing vectors were not inspected in the present
workspace. This distinction preserves both the replication history and the
limits of the artifact record.

The practical implication is simple: local-LLM confidentiality requires controls
over the entire serving lifecycle, including model admission, prompt-bearing
memory, wrapper storage, and resource-level state isolation.

