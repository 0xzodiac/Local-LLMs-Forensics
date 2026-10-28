# Threat model and security semantics

## Security property

The target property is prompt confidentiality across the serving lifecycle. A
prompt is confidential when an entity outside the authorized request flow cannot
recover its plaintext or a functionally equivalent representation through the
boundary under study. The property is not reduced to “the prompt did not cross
the Internet.”

The dossier distinguishes four statements:

1. **Residual existence:** bytes or derived state still contain prompt-related
   information after the request appears complete.
2. **Conditional forensic recoverability:** an authorized collector can recover
   a canary under a documented acquisition path.
3. **Adversarial access:** an attacker with the stated capability can obtain the
   information.
4. **Confidentiality compromise:** the threat model and evidence together show
   that the protected party's confidentiality objective is violated.

Residual existence is not automatically adversarial access.

## Actors and capabilities

### A1: co-resident local adversary

A1 is an unrelated same-UID process without assumed root access,
`CAP_SYS_PTRACE`, global Yama relaxation, target-side `PR_SET_PTRACER`
permission, or a parent/supervisor relationship. Same UID alone is not treated
as arbitrary `/proc/<pid>/mem` access. The paper must state the exact permission
path before using a memory observation as an adversarial result.

### F: authorized forensic collector

F is the research collector used to characterize residual data. The headline
memory harness launches the serving process as a direct child, reads writable
regions listed in `/proc/<pid>/maps`, and reads `/proc/<pid>/mem` subject to
Linux `PTRACE_MODE_ATTACH_FSCREDS` checks. F demonstrates residual existence and
conditional recoverability under the evaluated parent-child/permission path. It
does not prove that A1 can perform the same read.

### A2: authenticated network client

A2 can submit requests to the published serving interface and possesses a valid
credential. It cannot directly read host memory or wrapper files. In B4 it tests
whether a shared service enforces resource-level authorization after
authentication.

### A3: malicious model provider

A3 supplies a crafted or malformed GGUF artifact. A3 does not already control
the host or the inference process. The B1 experiment asks whether model
admission rejects malformed inputs without a relevant parser or sanitizer
failure in the explored state space.

### Wrapper-local file reader

The persistence experiments use a local reader of wrapper-managed artifacts.
This is a configuration-specific local threat model, not a claim that every
wrapper exposes the same files or retention policy.

## Trust boundaries

| Boundary | Trusted component being challenged | Attacker/collector | Property measured |
|---|---|---|---|
| B1 | GGUF parser and model loader | A3 | Malformed artifact is rejected safely within tested states |
| B2 | Runtime allocations, KV cache, slot release, allocator | F; interpreted against A1 only with permission evidence | Prompt representations are not recoverable after release, or residual scope is quantified |
| B3 | Wrapper logging, history, temporary storage, network behavior | Local file reader and telemetry | Prompt is not unintentionally retained or externally emitted under evaluated configuration |
| B4 | Authentication, slot persistence, cache/state ownership | A2 | One client cannot restore or infer another client's state |

## Authentication versus authorization

The saved-slot experiment uses different valid API credentials. This proves that
the requests entered through distinct authentication inputs. It does not prove
that the server recognized distinct security principals, bound slot files to
clients, or promised tenant isolation. The correct security question is whether
the shared resource has an ownership check after authentication.

## Scope limits

- No fully compromised operating system is modeled.
- No claim is made for macOS, Windows-native execution, or all GPU backends.
- The timing scope is the evaluated loopback/LAN condition, not arbitrary WAN.
- Wrapper results are product/version/configuration-specific.
- Negative observations bound only the instrumentation and state space that
  produced them.
- Public-host prevalence observations are not converted into an exploit count.
- Dr. Ikram's rerun is reported collaborative evidence; its server-side threat
  model and configuration are not locally inspected.

