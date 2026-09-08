#!/usr/bin/env bash
# 07_build_ld_hook.sh -- build the L2 LD_PRELOAD libc network hook
# (net_hooks.so) used by the LM Studio telemetry runs: intercepts
# getaddrinfo() + connect() inside the isolated namespace and writes a
# trace the harness correlates with the L1 wire capture.
set -u
ROOT="${RESEARCH_ROOT:-$HOME/research}"
HARN="$ROOT/.agents/skills/local-llm-telemetry-audit/scripts"
mkdir -p "$HARN"

cat > "$HARN/net_hooks.c" <<'EOF'
/* net_hooks.c -- LD_PRELOAD layer-L2 network tracer (research harness).
 * getaddrinfo: log every DNS resolution; connect: log every socket target.
 * Trace goes to $NET_HOOK_LOG (default /tmp/net_hooks.log). */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>

static void trace(const char* fmt, ...) {
    va_list ap; va_start(ap, fmt);
    const char* p = getenv("NET_HOOK_LOG");
    FILE* f = fopen(p ? p : "/tmp/net_hooks.log", "a");
    if (f) { vfprintf(f, fmt, ap); fputc('\n', f); fclose(f); }
    va_end(ap);
}

int getaddrinfo(const char* node, const char* service,
                const struct addrinfo* hints, struct addrinfo** res) {
    static int (*real)(const char*, const char*, const struct addrinfo*, struct addrinfo**);
    if (!real) real = dlsym(RTLD_NEXT, "getaddrinfo");
    int rc = real(node, service, hints, res);
    if (node) trace("DNS %s rc=%d", node, rc);
    return rc;
}

int connect(int fd, const struct sockaddr* addr, socklen_t len) {
    static int (*real)(int, const struct sockaddr*, socklen_t);
    if (!real) real = dlsym(RTLD_NEXT, "connect");
    if (addr && addr->sa_family == AF_INET) {
        const struct sockaddr_in* a = (const struct sockaddr_in*)addr;
        char ip[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &a->sin_addr, ip, sizeof ip);
        trace("CONNECT %s:%d", ip, ntohs(a->sin_port));
    }
    return real(fd, addr, len);
}
EOF
sed -i 's/#include <stdio.h>/#include <stdio.h>\n#include <stdarg.h>/' "$HARN/net_hooks.c"

gcc -shared -fPIC -O2 -o "$HARN/net_hooks.so" "$HARN/net_hooks.c" -ldl
echo "[hook] built: $HARN/net_hooks.so"
echo "[hook] usage: LD_PRELOAD=$HARN/net_hooks.so NET_HOOK_LOG=<file> <lms-serve-cmd>"
