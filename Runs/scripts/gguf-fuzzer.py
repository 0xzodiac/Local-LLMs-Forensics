#!/usr/bin/env python3
"""GGUF binary fuzzer — test llama-server parsing of malformed GGUF files."""

from __future__ import annotations

import argparse
import os
import random
import struct
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

GGUF_PY = Path(__file__).resolve().parents[1] / "llama-monitor" / "build" / "llama.cpp-src" / "gguf-py"
sys.path.insert(0, str(GGUF_PY))

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_ROOT / "logs"
FUZZ_LOG = LOG_DIR / "gguf_fuzz_results.csv"
LLAMA_SERVER_BIN = REPO_ROOT / "llama-monitor" / "build" / "llama.cpp" / "bin" / "llama-server"
GGUF_MODEL = "/mnt/c/Users/w.i/.lmstudio/models/lmstudio-community/gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf"

FUZZ_CASES = []


def register(description: str, generator):
    FUZZ_CASES.append((description, generator))


# --- Fuzz case generators ---
def fuzz_truncated_header(out: Path):
    """Write only first 4 bytes of GGUF magic."""
    with open(out, "wb") as f:
        f.write(b"GGUF")


def fuzz_bad_magic(out: Path):
    """Write invalid magic bytes."""
    with open(out, "wb") as f:
        f.write(b"EVIL")


def fuzz_version_overflow(out: Path):
    """GGUF magic + uint32 max version."""
    with open(out, "wb") as f:
        f.write(struct.pack("<4sII", b"GGUF", 0xFFFF_FFFF, 0))


def fuzz_tensor_count_overflow(out: Path):
    """GGUF magic + v3 + insane tensor count."""
    with open(out, "wb") as f:
        f.write(struct.pack("<4sII", b"GGUF", 3, 0xFFFF_FFFF))


def fuzz_kv_count_overflow(out: Path):
    """GGUF magic + v3 + 1 tensor + insane KV count."""
    with open(out, "wb") as f:
        f.write(struct.pack("<4sII", b"GGUF", 3, 1))
        f.write(struct.pack("<I", 0xFFFF_FFFF))  # kv count


def fuzz_negative_tensor_count(out: Path):
    """GGUF magic + v3 + signed int max tensor count."""
    with open(out, "wb") as f:
        f.write(struct.pack("<4sII", b"GGUF", 3, 0x7FFF_FFFF))


def fuzz_negative_kv_count(out: Path):
    """GGUF magic + v3 + 0 tensors + negative KV count."""
    with open(out, "wb") as f:
        f.write(struct.pack("<4sII", b"GGUF", 3, 0))
        f.write(struct.pack("<i", -1))  # negative kv count as signed


def fuzz_invalid_key_type(out: Path):
    """GGUF magic + v3 + 1 KV pair with insane type."""
    with open(out, "wb") as f:
        f.write(struct.pack("<4sII", b"GGUF", 3, 0))
        f.write(struct.pack("<I", 1))  # kv count
        f.write(struct.pack("<I", 0xFF))  # invalid key type
        key = b"test"
        f.write(struct.pack("<I", len(key)))
        f.write(key)


def fuzz_zero_tensor_dimensions(out: Path):
    """Copy valid GGUF then corrupt one tensor dimension to 0."""
    with open(GGUF_MODEL, "rb") as src:
        data = bytearray(src.read(4096))
    if len(data) > 100:
        pos = random.randint(100, len(data) - 8)
        data[pos:pos+4] = struct.pack("<I", 0)  # zero dim
    with open(out, "wb") as f:
        f.write(data)


def fuzz_gigantic_tensor_dim(out: Path):
    """Copy valid GGUF then corrupt one dim to huge value."""
    with open(GGUF_MODEL, "rb") as src:
        data = bytearray(src.read(4096))
    if len(data) > 100:
        pos = random.randint(100, len(data) - 8)
        data[pos:pos+4] = struct.pack("<I", 0xFFFF_FFFF)
    with open(out, "wb") as f:
        f.write(data)


def fuzz_nan_metadata_value(out: Path):
    """GGUF with NaN float KV pair."""
    with open(out, "wb") as f:
        f.write(struct.pack("<4sII", b"GGUF", 3, 0))
        f.write(struct.pack("<I", 1))
        f.write(struct.pack("<I", 8))  # float32 type
        key = b"test.float"
        f.write(struct.pack("<I", len(key)))
        f.write(key)
        f.write(struct.pack("<f", float("nan")))


def fuzz_inf_metadata_value(out: Path):
    fname = out
    with open(fname, "wb") as f:
        f.write(struct.pack("<4sII", b"GGUF", 3, 0))
        f.write(struct.pack("<I", 1))
        f.write(struct.pack("<I", 8))
        key = b"test.inf"
        f.write(struct.pack("<I", len(key)))
        f.write(key)
        f.write(struct.pack("<f", float("inf")))


def fuzz_jumbo_string_key(out: Path):
    with open(out, "wb") as f:
        f.write(struct.pack("<4sII", b"GGUF", 3, 0))
        f.write(struct.pack("<I", 1))
        f.write(struct.pack("<I", 4))  # string type
        f.write(struct.pack("<Q", 0xFFFF_FFFF))  # huge string length
        f.write(b"AAAA")


def fuzz_array_with_jumbo_length(out: Path):
    with open(out, "wb") as f:
        f.write(struct.pack("<4sII", b"GGUF", 3, 0))
        f.write(struct.pack("<I", 1))
        f.write(struct.pack("<I", 6))  # array type
        key = b"test.arr"
        f.write(struct.pack("<I", len(key)))
        f.write(key)
        f.write(struct.pack("<I", 0xFFFF_FFFF))  # array length
        f.write(struct.pack("<I", 8))  # element type float32
        f.write(struct.pack("<f", 1.0))


def fuzz_version_9999(out: Path):
    with open(out, "wb") as f:
        f.write(struct.pack("<4sII", b"GGUF", 9999, 0))


def fuzz_repeated_meta_key(out: Path):
    with open(out, "wb") as f:
        f.write(struct.pack("<4sII", b"GGUF", 3, 0))
        f.write(struct.pack("<I", 2))
        for _ in range(2):
            f.write(struct.pack("<I", 4))  # string type
            key = b"general.architecture"
            f.write(struct.pack("<I", len(key)))
            f.write(key)
            f.write(struct.pack("<I", len(key)))
            f.write(key)


def fuzz_oversized_tensor_name(out: Path):
    with open(GGUF_MODEL, "rb") as src:
        data = bytearray(src.read(8192))
    if len(data) > 200:
        pos = data.find(b"blk.")
        if pos > 0 and pos + 200 < len(data):
            for j in range(pos, min(pos + 200, len(data))):
                data[j] = 0x41  # fill with 'A's
    with open(out, "wb") as f:
        f.write(data)


def fuzz_truncated_tensor_data(out: Path):
    """Write valid header but no tensor data."""
    with open(GGUF_MODEL, "rb") as src:
        data = src.read()
    header_end = data.find(b"\x00" * 100)  # rough
    if header_end < 0:
        header_end = min(len(data), 65536)
    with open(out, "wb") as f:
        f.write(data[:header_end])


def fuzz_double_gguf_magic(out: Path):
    data = b"GGUF" + b"\x03\x00\x00\x00" + b"\x00\x00\x00\x00" + b"GGUF"
    with open(out, "wb") as f:
        f.write(data)


def fuzz_all_zeros(out: Path):
    with open(out, "wb") as f:
        f.write(b"\x00" * 4096)


def fuzz_all_ffs(out: Path):
    with open(out, "wb") as f:
        f.write(b"\xFF" * 4096)


# Register all fuzz cases
register("truncated_header (4 bytes only)", fuzz_truncated_header)
register("bad_magic (EVIL)", fuzz_bad_magic)
register("version_overflow (uint32_max)", fuzz_version_overflow)
register("tensor_count_overflow (uint32_max)", fuzz_tensor_count_overflow)
register("kv_count_overflow (uint32_max)", fuzz_kv_count_overflow)
register("negative_tensor_count (int32_max)", fuzz_negative_tensor_count)
register("negative_kv_count (-1)", fuzz_negative_kv_count)
register("invalid_key_type (0xFF)", fuzz_invalid_key_type)
register("zero_tensor_dimension", fuzz_zero_tensor_dimensions)
register("gigantic_tensor_dim (0xFFFFFFFF)", fuzz_gigantic_tensor_dim)
register("nan_metadata_value", fuzz_nan_metadata_value)
register("inf_metadata_value", fuzz_inf_metadata_value)
register("jumbo_string_key", fuzz_jumbo_string_key)
register("array_with_jumbo_length", fuzz_array_with_jumbo_length)
register("version_9999", fuzz_version_9999)
register("duplicate_meta_key", fuzz_repeated_meta_key)
register("oversized_tensor_name", fuzz_oversized_tensor_name)
register("truncated_tensor_data", fuzz_truncated_tensor_data)
register("double_gguf_magic", fuzz_double_gguf_magic)
register("all_zeros", fuzz_all_zeros)
register("all_0xFF", fuzz_all_ffs)


def test_gguf_dump(fpath: Path, timeout: float = 15) -> dict:
    """Try to parse with gguf-py's dump utility."""
    result = {"parser": "gguf-py", "exit_code": -1, "stdout": "", "stderr": "", "crashed": False}
    try:
        sys.path.insert(0, str(GGUF_PY / "gguf" / "scripts"))
        from gguf.scripts import gguf_dump
    except Exception:
        proc = subprocess.run(
            [sys.executable, "-m", "gguf.scripts.gguf_dump", str(fpath)],
            capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "PYTHONPATH": str(GGUF_PY)},
        )
        result["exit_code"] = proc.returncode
        result["stdout"] = proc.stdout[:500]
        result["stderr"] = proc.stderr[:500]
        result["crashed"] = proc.returncode < 0 or "segfault" in proc.stderr.lower() or "crash" in proc.stderr.lower()
    return result


def test_llama_server_load(fpath: Path, timeout: float = 30) -> dict:
    """Try to load with llama-server --check-tensors."""
    result = {"parser": "llama-server", "exit_code": -1, "stdout": "", "stderr": "", "crashed": False}
    try:
        proc = subprocess.run(
            [str(LLAMA_SERVER_BIN), "--check-tensors", "-m", str(fpath)],
            capture_output=True, text=True, timeout=timeout,
        )
        result["exit_code"] = proc.returncode
        result["stdout"] = proc.stdout[:500]
        result["stderr"] = proc.stderr[:500]
        rc = proc.returncode
        sig = rc - 256 if rc > 128 else rc
        result["crashed"] = sig < 0 or "segfault" in proc.stderr.lower() or "SIGSEGV" in proc.stderr
    except subprocess.TimeoutExpired:
        result["exit_code"] = -1
        result["stderr"] = "TIMEOUT"
        result["crashed"] = False
    except FileNotFoundError:
        result["exit_code"] = -2
        result["stderr"] = "llama-server binary not found"
        result["crashed"] = False
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=LOG_DIR / "gguf_fuzz")
    parser.add_argument("--results-csv", type=Path, default=FUZZ_LOG)
    parser.add_argument("--skip-llama-server", action="store_true", help="Skip llama-server binary tests")
    parser.add_argument("--llama-server-bin", type=Path, default=LLAMA_SERVER_BIN)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = args.results_csv
    fieldnames = ["case_id", "description", "gguf_py_exit", "gguf_py_crashed", "gguf_py_stderr",
                  "llama_server_exit", "llama_server_crashed", "llama_server_stderr", "notes"]

    results = []
    case_id = 0

    for desc, generator in FUZZ_CASES:
        case_id += 1
        case_name = f"fuzz_{case_id:03d}_{desc.replace(' ', '_')[:40]}"
        fpath = args.output_dir / f"{case_name}.gguf"
        try:
            generator(fpath)
        except Exception as e:
            print(f"[fuzz]  {case_name}: generator failed: {e}", file=sys.stderr)
            continue

        file_size = fpath.stat().st_size
        notes = f"size={file_size}"

        gguf_result = test_gguf_dump(fpath)

        if args.skip_llama_server:
            llama_result = {"parser": "llama-server", "exit_code": -3, "stderr": "SKIPPED", "crashed": False}
        else:
            llama_result = test_llama_server_load(fpath)

        status = "OK"
        if gguf_result["crashed"] or llama_result["crashed"]:
            status = "CRASH"
        elif gguf_result["exit_code"] != 0 or llama_result["exit_code"] not in (0, -2, -3):
            status = "ERROR"

        crash_flag = " CRASH" if gguf_result["crashed"] or llama_result["crashed"] else ""
        print(f"[fuzz]  {case_name:55s} gguf_exit={gguf_result['exit_code']:4d} "
              f"server_exit={llama_result['exit_code']:4d}{crash_flag} size={file_size}", file=sys.stderr)

        row = {
            "case_id": case_id,
            "description": desc,
            "gguf_py_exit": gguf_result["exit_code"],
            "gguf_py_crashed": gguf_result["crashed"],
            "gguf_py_stderr": gguf_result["stderr"][:200],
            "llama_server_exit": llama_result["exit_code"],
            "llama_server_crashed": llama_result["crashed"],
            "llama_server_stderr": llama_result["stderr"][:200],
            "notes": notes,
        }
        results.append(row)

    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(results)

    crashed = sum(1 for r in results if r["gguf_py_crashed"] or r["llama_server_crashed"])
    errors = sum(1 for r in results if r["gguf_py_exit"] != 0 and r["llama_server_exit"] not in (0, -2, -3))
    ok = sum(1 for r in results if r["llama_server_exit"] == 0 or (
        r["llama_server_exit"] == -3 and r["gguf_py_exit"] in (-1, 0)))

    print(f"\n[fuzz]  Total={len(results)} OK={ok} Errors={errors} Crashes={crashed}", file=sys.stderr)
    print(f"[fuzz]  Results: {csv_path}", file=sys.stderr)

    if crashed:
        print(f"[fuzz]  WARNING: {crashed} crash(es) detected!", file=sys.stderr)

    return 0 if crashed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
