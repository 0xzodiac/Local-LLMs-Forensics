# RQ4 evidence: slot restoration and timing

## Slot restoration

The four-model slot file contains 200/200 successful protocol-level transfers, 50 per model, with all stored summaries matching row-level recomputation. The four detailed extraction files independently reproduce 200/200 transfer, 126/200 KV continuation, 200/200 memory-channel hits, and 200/200 either-channel hits. Continuation counts are Gemma 50/50, Qwen 50/50, Nemotron 25/50, and Phi 1/50.

This is **E1 for retained per-trial arithmetic** and **E2 for the recorded observations**. It remains conditional on the configured shared server, saved-slot path, valid credentials, and the harness's representation of distinct clients. It does not by itself prove universal deployment exposure or a vendor vulnerability classification.

## Timing

The manuscript and external reviews report AUC = 1.000 for four models, but the retained workspace has no per-request cached/uncached TTFT vectors, request-order manifest, or original AUC script. The available KV patched/unpatched vectors are a different benchmark and cannot be substituted.

The timing claim is therefore **E4**: historical summary only, not independently recomputable. It should remain explicitly bounded to the reported evaluated conditions and should not be presented as independently validated or WAN-general.
