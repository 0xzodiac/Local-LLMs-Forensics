#!/usr/bin/env bash
# 05_build_llamacpp_patched.sh -- build llama.cpp's llama-server with the
# security patches the paper evaluates (secure allocator + prompt zeroize +
# KV-cache zeroize). The original live build tree at ~/research/llama-cpp-build
# is NOT in the repo (gitignored), so rebuild it from scratch:
#   1) clone llama.cpp at a recent master-era commit (patches are written
#      against 2026-era sources; see note below if a hunk fails)
#   2) apply patches/prompt_zeroize.patch + kv_cache_zeroize.patch
#   3) add the secure-allocator override (runtime-switchable via SECURE_ALLOC=1/0)
#   4) cmake build -> build/bin/llama-server
set -u
ROOT="${RESEARCH_ROOT:-$HOME/research}"
BUILD="$ROOT/llama-cpp-build"
PATCHES="$ROOT/patches"
LLAMACPP_REF="${LLAMACPP_REF:-master}"

command -v cmake >/dev/null || { echo "need cmake (02_install_prereqs.sh)"; exit 1; }
mkdir -p "$BUILD"
[ -d "$BUILD/src" ] || git clone --depth 1 -b "$LLAMACPP_REF" https://github.com/ggml-org/llama.cpp "$BUILD/src"

cd "$BUILD/src"
echo "[build] applying patches (a rejected hunk = upstream code drifted; pin an older LLAMACPP_REF and retry)"
for p in prompt_zeroize kv_cache_zeroize; do
  if git apply --check "$PATCHES/$p.patch" 2>/dev/null; then
    git apply "$PATCHES/$p.patch" && echo "[build] applied $p.patch"
  else
    echo "[build] NOTE: $p.patch does not apply cleanly to $LLAMACPP_REF -- inspect and adapt manually (see RUN_FROM_SCRATCH.md 'Patches')"
  fi
done

# secure allocator: runtime-switchable global operator delete that bzeros
# every freed chunk >= 4 KB (SECURE_ALLOC=1 patched / =0 unpatched in
# run_kv_overhead.py). Not shipped as a .patch in the repo; recreate it:
if [ ! -f src/secure-allocator.cpp ]; then
cat > src/secure-allocator.cpp <<'EOF'
// security: zero-on-free allocator override (research patch, see
// SECURE_ALLOCATOR_TEST / secure-allocator.cpp in the paper's D2 measurements)
#include <cstdlib>
#include <cstring>
extern "C" void explicit_bzero(void*, size_t);
static bool sec_alloc_enabled() { const char* e = getenv("SECURE_ALLOC"); return e && e[0]=='1'; }
void operator delete(void* p) noexcept {
    if (p && sec_alloc_enabled()) {
        size_t sz = malloc_usable_size(p);
        if (sz >= 4096) explicit_bzero(p, sz);
    }
    free(p);
}
void operator delete(void* p, size_t) noexcept { operator delete(p); }
void operator delete[](void* p) noexcept { operator delete(p); }
void operator delete[](void* p, size_t) noexcept { operator delete(p); }
EOF
sed -n '1,5p' src/secure-allocator.cpp
fi

cmake -B build -S . -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=ON > /tmp/cmake_conf.log 2>&1 || { tail -20 /tmp/cmake_conf.log; exit 1; }
cmake --build build --config Release -j"$(nproc)" > /tmp/cmake_build.log 2>&1 || { tail -30 /tmp/cmake_build.log; exit 1; }
echo "[build] done -> $BUILD/src/build/bin/llama-server"
"$BUILD/src/build/bin/llama-server" --version 2>&1 | head -2
echo "[build] NOTE: scripts expect the binary at $ROOT/llama-cpp-build/build/bin/llama-server;"
echo "        this clone builds to $BUILD/src/build/bin -- 01_layout.sh symlinks the tree, so"
echo "        either rerun with the repo at that path or: ln -sfn $BUILD/src/build $BUILD/build"
