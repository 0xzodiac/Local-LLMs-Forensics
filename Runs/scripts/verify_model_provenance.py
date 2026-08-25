#!/usr/bin/env python3
"""Verify tensor count + arch string of the 3 final local models against RESEARCH_DOCUMENTATION.md baseline."""
import sys
from gguf import GGUFReader

BASELINE = {
    "qwen35": {"tensors": 427, "path": "/home/elaref/.lmstudio/models/lmstudio-community/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf"},
    "nemotron": {"tensors": 263, "path": "/home/elaref/.lmstudio/models/lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf"},
    "phi4": {"tensors": 243, "path": "/home/elaref/.lmstudio/models/lmstudio-community/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf"},
}

def main():
    ok = True
    for name, info in BASELINE.items():
        r = GGUFReader(info["path"])
        n_tensors = len(r.tensors)
        arch_field = r.fields.get("general.architecture")
        arch = arch_field.parts[arch_field.data[0]].tobytes().decode("utf-8", "ignore") if arch_field else "?"
        match = n_tensors == info["tensors"]
        ok &= match
        print(f"{name}: tensors={n_tensors} (expected {info['tensors']}) arch={arch} -> {'OK' if match else 'MISMATCH'}")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
