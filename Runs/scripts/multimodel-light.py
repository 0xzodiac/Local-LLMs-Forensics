#!/usr/bin/env python3
"""Lightweight multi-model GGUF attack tester.

CPU-respectful: uses --check-tensors (no inference), 3s cooldown between tests.
Tests gemma4, nemotron, qwen35 (skips phi4 8.5GB).
"""

from __future__ import annotations

import csv
import os
import signal
import struct
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SERVER = REPO / "llama-monitor/build/llama.cpp/bin/llama-server"
OUT_DIR = REPO / "logs" / "multimodel"
RESULTS_CSV = OUT_DIR / "multimodel_results.csv"

MODELS = {
    "nemotron": "/mnt/c/Users/w.i/.lmstudio/models/lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf",
    "gemma4": "/mnt/c/Users/w.i/.lmstudio/models/lmstudio-community/gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf",
    "qwen35": "/mnt/c/Users/w.i/.lmstudio/models/lmstudio-community/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf",
    "phi4": "/mnt/c/Users/w.i/.lmstudio/models/lmstudio-community/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf",
}


def read_arch(path: str) -> str:
    with open(path, "rb") as f:
        raw = f.read(10 * 1024 * 1024)
    kp = raw.find(b"general.architecture")
    if kp < 0:
        return "unknown"
    pos = kp + 21 + 4
    slen = struct.unpack_from("<Q", raw, pos)[0]
    return raw[pos + 8:pos + 8 + slen].decode("utf-8", errors="replace")


def patch_u32(raw: bytearray, key: bytes, val: int) -> bool:
    kp = raw.find(key)
    if kp < 0:
        return False
    struct.pack_into("<I", raw, kp + len(key) + 4, val)
    return True


def patch_str(raw: bytearray, key: bytes, new_val: bytes) -> bool:
    kp = raw.find(key)
    if kp < 0:
        return False
    pos = kp + len(key) + 4
    old_len = struct.unpack_from("<Q", raw, pos)[0]
    pos += 8
    raw[pos:pos + old_len] = new_val + b"\x00" * (old_len - len(new_val))
    return True


# ---- Attack generators ----

def gen_rope_drift(raw, arch):
    patch_u32(raw, f"{arch}.rope.dimension_count".encode(), 0x7FFFFFFF)
    patch_u32(raw, f"{arch}.context_length".encode(), 0xFFFFFFFF)
    return "rope_drift"


def gen_block_mismatch(raw, arch):
    patch_u32(raw, f"{arch}.block_count".encode(), 1)
    return "block_mismatch"


def gen_embed_crush(raw, arch):
    patch_u32(raw, f"{arch}.embedding_length".encode(), 1)
    patch_u32(raw, f"{arch}.attention.head_count".encode(), 0xFFFFFFFF)
    return "embed_crush"


def gen_token_boundary(raw, arch):
    for tok, val in [("bos_token_id", 0xFFFFFFFF), ("eos_token_id", 0xFFFFFFFE),
                     ("padding_token_id", 0x80000000), ("unknown_token_id", 0x7FFFFFFF)]:
        patch_u32(raw, f"tokenizer.ggml.{tok}".encode(), val)
    return "token_boundary"


def gen_quant_swap(raw, arch):
    swaps = {0: 8, 8: 2, 2: 0}
    for tn in [b"output.weight", b"output_norm.weight", b"token_embd.weight"]:
        kp = raw.find(tn)
        if kp < 0:
            continue
        pos = kp + len(tn)
        nd = struct.unpack_from("<I", raw, pos)[0]
        pos += 4 + nd * 8
        qt = struct.unpack_from("<I", raw, pos)[0]
        struct.pack_into("<I", raw, pos, swaps.get(qt, 8))
    return "quant_swap"


def gen_tensor_offset(raw, arch):
    for tn in [b"output.weight", b"token_embd.weight"]:
        kp = raw.find(tn)
        if kp < 0:
            continue
        pos = kp + len(tn)
        nd = struct.unpack_from("<I", raw, pos)[0]
        pos += 4 + nd * 8 + 4
        old = struct.unpack_from("<Q", raw, pos)[0]
        struct.pack_into("<Q", raw, pos, (old + 0x40000000) & 0xFFFFFFFFFFFFFFFF)
    return "tensor_offset"


def gen_arch_spoof(raw, arch):
    spoofs = {"gemma4": "llama", "nemotron_h": "llama", "phi3": "gemma2", "qwen35": "llama"}
    new = spoofs.get(arch, "llama")
    patch_str(raw, b"general.architecture", new.encode())
    return f"arch_{new}"


def gen_vocab_corrupt(raw, arch):
    kp = raw.find(b"tokenizer.ggml.tokens")
    if kp < 0:
        return "vocab_corrupt(0)"
    pos = kp + 22 + 4 + 4 + 8
    n = 0
    for _ in range(10):
        ol = struct.unpack_from("<Q", raw, pos)[0]
        if ol > 100000 or ol == 0:
            break
        struct.pack_into("<Q", raw, pos, 0x7FFFFFFFFFFFFFFF)
        n += 1
        pos += 8 + ol
    return f"vocab_corrupt({n})"


ATTACKS = [
    gen_rope_drift, gen_block_mismatch, gen_embed_crush, gen_token_boundary,
    gen_quant_swap, gen_tensor_offset, gen_arch_spoof, gen_vocab_corrupt,
]


def check_load(model_path: Path, timeout: int = 20) -> dict:
    """Test with --check-tensors (fast, no inference)."""
    cmd = [str(SERVER), "--check-tensors", "-m", str(model_path),
           "--port", "19999", "--host", "127.0.0.1"]
    try:
        t0 = time.time()
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        elapsed = time.time() - t0
        rc = proc.returncode
        sig = rc - 256 if rc > 128 else rc
        signame = signal.Signals(-sig).name if sig < 0 else f"exit({rc})"
        stderr_tail = proc.stderr[-500:] if proc.stderr else ""
        return {"rc": rc, "signal": signame, "crashed": sig < 0,
                "elapsed": round(elapsed, 1), "stderr_tail": stderr_tail}
    except subprocess.TimeoutExpired:
        return {"rc": -1, "signal": "TIMEOUT", "crashed": False,
                "elapsed": timeout, "stderr_tail": "timeout"}
    except Exception as e:
        return {"rc": -999, "signal": "ERROR", "crashed": False,
                "elapsed": 0, "stderr_tail": str(e)[:200]}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=["nemotron", "gemma4", "qwen35"])
    parser.add_argument("--include-phi4", action="store_true")
    parser.add_argument("--attacks", nargs="+", default=["all"])
    args = parser.parse_args()

    models_to_test = args.models[:]
    if args.include_phi4:
        models_to_test.append("phi4")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    for model_name in models_to_test:
        model_path = MODELS[model_name]
        arch = read_arch(model_path)
        print(f"\n{'='*50}", file=sys.stderr)
        print(f"  {model_name} arch={arch}", file=sys.stderr)
        print(f"{'='*50}", file=sys.stderr)

        for attack_fn in ATTACKS:
            # Read only first 50MB (metadata is in first few MB)
            with open(model_path, "rb") as f:
                head = bytearray(f.read(50 * 1024 * 1024))

            try:
                attack_name = attack_fn(head, arch)
            except Exception as e:
                print(f"  [{attack_name}] gen error: {e}", file=sys.stderr)
                continue

            variant = OUT_DIR / f"{model_name}_{attack_name}.gguf"
            variant.write_bytes(bytes(head))

            # Also need tensor data - copy full file then patch
            # Actually for --check-tensors we need the full file
            # Let's use a symlink + patch approach
            # No - just test the 50MB truncated version
            # --check-tensors will fail on truncated but we can see the error
            
            # Better: test with truncated file to see if metadata is rejected
            # vs the full file test
            
            # Actually let's just copy and patch the full file
            # but only for the small nemotron (2.7GB)
            if model_name == "nemotron":
                # Full file copy + patch
                full_raw = bytearray(Path(model_path).read_bytes())
                attack_fn(full_raw, arch)
                variant.write_bytes(bytes(full_raw))
                del full_raw
            
            result = check_load(variant)
            result["model"] = model_name
            result["arch"] = arch
            result["attack"] = attack_name
            result["variant_size"] = variant.stat().st_size
            results.append(result)

            status = "CRASH" if result["crashed"] else f"rc={result['rc']}"
            print(f"  [{attack_name:20s}] {status} {result['elapsed']}s", file=sys.stderr)
            
            # Extract key error
            st = result["stderr_tail"]
            for line in st.split("\n"):
                if "error" in line.lower() or "assert" in line.lower() or "SIGABRT" in line:
                    print(f"    -> {line.strip()[:120]}", file=sys.stderr)
                    break

            # Cleanup
            try:
                variant.unlink()
            except Exception:
                pass

            time.sleep(2)  # CPU cooldown

    # Write CSV
    if results:
        fields = ["model", "arch", "attack", "variant_size", "rc", "signal",
                  "crashed", "elapsed", "stderr_tail"]
        for r in results:
            for k in fields:
                r.setdefault(k, "")
        with RESULTS_CSV.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(results)
        print(f"\nResults: {RESULTS_CSV}", file=sys.stderr)

    # Summary
    crashes = [r for r in results if r["crashed"]]
    ok = [r for r in results if r["rc"] == 0]
    print(f"\nTotal={len(results)} OK={len(ok)} Crashes={len(crashes)}", file=sys.stderr)
    for r in crashes:
        print(f"  CRASH: {r['model']}/{r['attack']} sig={r['signal']}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
