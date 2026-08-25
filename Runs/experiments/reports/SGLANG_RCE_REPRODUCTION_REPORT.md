# SGLANG RCE REPRODUCTION REPORT — CVE-2026-5760

**Status:** NOT REPRODUCED (patched)  
**Date:** 2026-06-22  
**Investigator:** Automated agent under `LATEST_INTEL_2026-06-22.md §1`

---

## 1. Verdict

**NOT REPRODUCED** — the installed SGLang version (0.5.13.post1) already contains the fix. The vulnerable code path was examined and confirmed patched. The attack mechanism was demonstrated against a standalone vulnerable Jinja2 environment to prove the vulnerability class, but the actual SGLang deployment is not exploitable via this vector.

---

## 2. CVE Information (Primary-Source Verified)

| Field | Value |
|-------|-------|
| **CVE ID** | CVE-2026-5760 |
| **CVSS** | 9.8 (Critical) — CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H |
| **CWE** | CWE-94 (Code Injection) |
| **Source** | CERT/CC (VU#915947), NVD |
| **Affected versions** | SGLang up to (excluding) 0.5.11 |
| **Fixed in** | PR #23660 (merged 2026-04-29), commit `a26af7b` |
| **Fixed version** | SGLang ≥ 0.5.11 |
| **PoC** | https://github.com/Stuub/SGLang-0.5.9-RCE |
| **References** | [NVD](https://nvd.nist.gov/vuln/detail/CVE-2026-5760), [CERT/CC](https://www.kb.cert.org/vuls/id/915947), [PR #23660](https://github.com/sgl-project/sglang/pull/23660) |

---

## 3. Vulnerable Component

**File:** `python/sglang/srt/entrypoints/openai/serving_rerank.py`  
**Function:** `_get_jinja_env()`  
**Vulnerable code (< 0.5.11):**
```python
def _get_jinja_env():
    ...
    return jinja2.Environment(
        loader=jinja2.BaseLoader(),
        autoescape=False,
        undefined=jinja2.Undefined,
    )
```
**Patched code (≥ 0.5.11):**
```python
def _get_jinja_env():
    ...
    from jinja2.sandbox import ImmutableSandboxedEnvironment
    return ImmutableSandboxedEnvironment(
        loader=jinja2.BaseLoader(),
        autoescape=False,
        undefined=jinja2.Undefined,
    )
```

---

## 4. Attack Surface

| Element | Detail |
|---------|--------|
| **Endpoint** | `/v1/rerank` |
| **GGUF field** | `tokenizer.chat_template` (STRING metadata) |
| **Trigger phrase** | `The answer can only be "yes" or "no"` |
| **Trigger path** | `_is_qwen3_reranker_template()` → `_render_jinja_chat_template()` |
| **SSTI payload** | `{{ lipsum.__globals__["os"].popen("cmd").read() }}` |
| **Delivery** | Malicious GGUF model → SGLang model load → `/v1/rerank` request |

---

## 5. Installed Version Check

| Property | Value |
|----------|-------|
| SGLang installed | 0.5.13.post1 |
| Affected range | < 0.5.11 |
| Status | **PATCHED** (0.5.13.post1 ≥ 0.5.11) |
| Venv location | `/home/elaref/research/.venv_sglang` |

---

## 6. Fix Verification

### 6.1 Source inspection (line 121 of installed `serving_rerank.py`)
```
return ImmutableSandboxedEnvironment(
    loader=jinja2.BaseLoader(),
    autoescape=False,
    undefined=jinja2.Undefined,
)
```

### 6.2 Patched environment blocks SSTI
```
Template: 'The answer can only be "yes" or "no".\n{{ lipsum.__globals__["os"].popen("echo SGLANG_RCE_CONFIRMED").read() }}'
RESULT:   SecurityError: access to attribute '__globals__' of 'function' object is unsafe.
>>> FIX EFFECTIVE
```

### 6.3 Vulnerable `jinja2.Environment()` confirms attack class
```
Same template with jinja2.Environment():
RENDERED: uid=1000(elaref) gid=1000(elaref) groups=1000(elaref),4(adm),...
>>> ATTACK CLASS CONFIRMED
```

---

## 7. GGUF Model Examined

| Property | Value |
|----------|-------|
| Model file | `/home/elaref/.lmstudio/models/lmstudio-community/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf` |
| `tokenizer.chat_template` | **Present** — 7756 chars, Qwen3 complex template with `image_count`, `video_count`, macros, `raise_exception` |
| Attack relevance | This model's chat_template would be rendered by the vulnerable code path if SGLang were unpatched |

---

## 8. Conclusion

CVE-2026-5760 is a **real, critical (CVSS 9.8)** vulnerability in SGLang < 0.5.11 caused by unsandboxed `jinja2.Environment()` in the `/v1/rerank` endpoint's `_get_jinja_env()` function. The installed version (0.5.13.post1) **is patched** via `ImmutableSandboxedEnvironment`, which blocks the documented SSTI exploitation vector (`lipsum.__globals__["os"].popen()`).

The attack was independently confirmed against a standalone vulnerable environment — the `id` command executed successfully — but **SGLang 0.5.13.post1 itself is not exploitable** via this CVE.

### Recommendation

If the paper intends to cite CVE-2026-5760 as evidence of the "file-format-is-the-attack-surface" thesis:
- The GGUF field (`tokenizer.chat_template`) and the delivery model (poisoned model → runtime compromise) **directly support** the thesis.
- The fix (sandboxed Jinja2 environment) is trivial in diff size (1 file, 3 insertions, 2 deletions) — worth noting as a low-effort mitigation that any runtime should adopt.
- SGLang is **no longer vulnerable** as of 0.5.11. If testing against SGLang is desired for Track A/G, an intentionally vulnerable version (≤ 0.5.10) would need to be installed from source at a specific pre-fix commit.
