# Canary / Egress Report

**Canary:** `TELEMETRY_CANARY_1068b0813ab6`

## Verdict: NO EGRESS DETECTED

## Layer-by-layer
- **L1 packet capture:** 56 packets on egress; 0 unique external dest IP(s)
- **L2 DNS:** 0 queries in pcap extract, 0 in live capture
- **L2/L3 LD_PRELOAD hooks:** 0 non-loopback getaddrinfo; 0 external connect() attempts
- **L4 proxy:** 0 total requests (0 external, 0 unique hosts)

## Canary sweep
- in egress pcap: **False**
- in DNS pcap: **False**
- in proxy body: **False**
- in hooks log (host strings only): **False**

## Non-loopback hostnames resolved by the tool
*(empty = the tool resolved nothing outside localhost)*

## Proxy-bypass check
No proxy layer in this run (netns architecture: ground truth is the wire capture itself); external traffic above is authoritative.

## External dest IPs seen on the wire
*(none)*