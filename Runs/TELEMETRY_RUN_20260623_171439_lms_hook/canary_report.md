# Canary / Egress Report

**Canary:** `TELEMETRY_CANARY_759ae70d6ccf`

## Verdict: EGRESS DETECTED (no canary observed in outbound payload)

## Layer-by-layer
- **L1 packet capture:** 757 packets on egress; 2 unique external dest IP(s)
- **L2 DNS:** 6 queries in pcap extract, 0 in live capture
- **L2/L3 LD_PRELOAD hooks:** 3 non-loopback getaddrinfo; 8 external connect() attempts
- **L4 proxy:** 0 total requests (0 external, 0 unique hosts)

## Canary sweep
- in egress pcap: **False**
- in DNS pcap: **False**
- in proxy body: **False**
- in hooks log (host strings only): **False**

## Non-loopback hostnames resolved by the tool
*(empty = the tool resolved nothing outside localhost)*
- `versions-prod.lmstudio.ai` × 1
- `lmstudio.ai` × 1
- `extensions.lmstudio.ai` × 1

## Proxy-bypass check
No proxy layer in this run (netns architecture: ground truth is the wire capture itself); external traffic above is authoritative.

## External dest IPs seen on the wire
- `104.26.6.153`
- `104.26.7.153`