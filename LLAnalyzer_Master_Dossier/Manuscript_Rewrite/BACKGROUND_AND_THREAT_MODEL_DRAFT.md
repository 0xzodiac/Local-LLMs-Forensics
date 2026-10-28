# Background and threat model: author-editable draft

## Local execution is not a confidentiality proof

Network locality removes a cloud provider from the immediate request path. It
does not constrain every local component that can copy or retain the prompt.
Prompt confidentiality therefore has at least four dimensions: admission,
runtime lifetime, persistent retention, and shared-state ownership.

## Boundaries

B1 asks whether a malicious model artifact can reach unsafe loading behavior. B2
asks whether prompt plaintext or derived state remains recoverable after
inference. B3 asks whether a wrapper persists prompt data or emits it through
monitored channels. B4 asks whether a shared service separates client state and
whether cache reuse creates an observable signal.

## Actors

We distinguish a co-resident same-UID adversary A1, the authorized forensic
collector F, an authenticated network client A2, and a malicious model provider
A3. A1 has no assumed root, `CAP_SYS_PTRACE`, Yama relaxation, target-side
ptrace permission, or parent relationship. F does have the documented
parent-child/acquisition path. This difference is essential: F's result proves
residual existence and conditional recoverability, not arbitrary same-UID access.

A2 can use the serving protocol but cannot directly read host memory or wrapper
files. The saved-slot experiment tests authorization of shared resources after
authentication. Different API keys are distinct credentials in the experiment;
they are not proof of independently isolated tenant principals.

A3 supplies malformed GGUF artifacts without already controlling the host. The
RQ1 result is limited to the tested corpus and campaign.

## Security semantics

We report residual plaintext existence, conditional forensic recoverability,
adversarial access, and confidentiality compromise as separate claims. A
recovered canary under F is not automatically a claim that A1 can recover it.
Similarly, a direct saved-state transfer is a protocol observation distinct
from whether a model emits the transferred secret.

## Scope

The study does not claim universal behavior across operating systems, wrappers,
GPU backends, versions, WAN deployments, or unobserved storage channels. The
collaborator rerun is a reported full-framework cross-machine replication and
does not fill unknown server-side configuration fields in this manuscript.

