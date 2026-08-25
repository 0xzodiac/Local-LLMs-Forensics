# Cybersecurity Filter Patterns

Pre-built tshark filters and analysis patterns for common security
investigations. Each pattern includes the filter, what it detects, and
the false positives to watch for.

## Threat detection

### 1. Cleartext credentials in HTTP
**Filter:** `http.request.method == POST and (http.file_data contains "pass" or http.file_data contains "token" or http.file_data contains "apikey")`
**Catches:** Form submissions, API calls with secrets in body
**False positives:** Login pages, password reset flows
**Action:** Check if the host is internal; flag external cleartext auth

### 2. DNS exfiltration / tunneling
**Filter:** `dns.flags.response == 0 and (dns.qry.name matches "\\.(tk|ml|ga|cf|gq)$" or dns.qry.name matches "^[a-f0-9]{20,}\\." or frame.len > 200)`
**Catches:** Data leaving via long DNS queries to free TLDs
**False positives:** CDN, CDN-frontend to short TTL records
**Action:** Pull full query list, check for hex/base32 in subdomain

### 3. C2 beaconing
**Pattern:** Periodic connections to same IP:port
**Detection (manual):**
```bash
tshark -r file.pcap -Y "tcp" -T fields -e ip.dst -e tcp.dstport -e frame.time_relative \
  | awk '{print $1":"$2}' | sort | uniq -c | sort -rn | head -20
```
Look for flows with high packet count and consistent time deltas.
**Catches:** Cobalt Strike, Sliver, Mythic beacons
**False positives:** Browser keepalives, long-lived TLS connections

### 4. Port scanning
**Filter:** `tcp.flags.syn == 1 and tcp.flags.ack == 0`
**Group by source:** `tshark -r file.pcap -Y "tcp.flags.syn == 1 and tcp.flags.ack == 0" -T fields -e ip.src | sort | uniq -c | sort -rn`
**Catches:** Nmap, masscan, custom port scans
**Threshold:** > 20 SYNs from one source in <60s

### 5. Lateral movement (SMB/RDP)
**SMB writes to admin shares:**
`smb2.cmd == 5 and (smb2.file contains "ADMIN$" or smb2.file contains "C$")`
**RDP brute force:**
`tcp.port == 3389 and tcp.flags.syn == 1 and tcp.flags.ack == 0`
**WinRM:**
`tcp.port == 5985 or tcp.port == 5986`

### 6. TLS to suspicious destinations
**Filter:** `tls.handshake.extensions_server_name and !(tls.handshake.extensions_server_name matches "^(google\\.|cloudflare\\.|microsoft\\.|apple\\.|amazonaws\\.|github\\.|gitlab\\.|atlassian\\.|slack\\.|zoom\\.)")`
**Catches:** TLS connections to non-mainstream domains
**Action:** Cross-reference SNI list against threat intel (VirusTotal, AbuseIPDB)

### 7. Unencrypted protocol usage
**Filter:** `(tcp.port == 21 or tcp.port == 23 or tcp.port == 25 or tcp.port == 80 or tcp.port == 110 or tcp.port == 143 or tcp.port == 161) and !tcp.port == 80`
(Adjust 80 if you expect HTTP.)
**Catches:** Telnet, FTP, SMTP, POP3, IMAP, SNMP — all unencrypted

### 8. ARP spoofing
**Detection:** Multiple IPs claiming same MAC
```bash
tshark -r file.pcap -Y "arp" -T fields -e arp.src.hw_mac -e arp.src.proto_ipv4 \
  | sort | uniq | awk '{print $1}' | sort | uniq -c | sort -rn | head
```
If any MAC has > 3 IPs, investigate.

### 9. ICMP tunneling
**Filter:** `icmp and frame.len > 200`
**Catches:** ptunnel, icmpsh, custom ICMP exfil
**Threshold:** ICMP packets > 200 bytes are unusual

### 10. Web exploitation attempts
**SQLi probes:**
`http.request.uri matches "(union|select|from|where|or 1=1|sleep\\(|benchmark\\(|' or '"` (case-insensitive in matches, so use both)
**XSS probes:**
`http.request.uri matches "(<script|onerror=|onload=|javascript:|alert\\()"`
**Path traversal:**
`http.request.uri contains "..%2f" or http.request.uri contains "../"`

## Reconnaissance

### Top talkers
```bash
tshark -r file.pcap -T fields -e ip.src | sort | uniq -c | sort -rn | head
tshark -r file.pcap -T fields -e ip.dst | sort | uniq -c | sort -rn | head
```

### Protocol hierarchy
```bash
tshark -r file.pcap -q -z io,phs
```

### Conversations (TCP/UDP pairs)
```bash
tshark -r file.pcap -q -z conv,tcp
tshark -r file.pcap -q -z conv,udp
```

### Endpoints
```bash
tshark -r file.pcap -q -z endpoints,ip
tshark -r file.pcap -q -z endpoints,tcp
```

### DNS statistics
```bash
tshark -r file.pcap -q -z dns,tree
tshark -r file.pcap -Y "dns" -T fields -e dns.qry.name | sort | uniq -c | sort -rn | head
```

### HTTP statistics
```bash
tshark -r file.pcap -q -z http,tree
tshark -r file.pcap -q -z http,req,tree
tshark -r file.pcap -q -z http,srv,tree
tshark -r file.pcap -q -z http,status,tree
```

### TLS statistics
```bash
tshark -r file.pcap -q -z tls,tree
# SNI list:
tshark -r file.pcap -Y "tls.handshake.extensions_server_name" -T fields -e tls.handshake.extensions_server_name | sort -u
```

## Operational recipes

### Live capture with BPF filter (kernel-level)
```bash
sudo tshark -i eth0 -f "tcp port 443" -w /tmp/web.pcap -a duration:300
```

### Live capture with display filter (userspace)
```bash
sudo tshark -i eth0 -Y "http.request" -T fields -e http.host -e http.request.uri
```

### Capture on multiple interfaces
```bash
sudo tshark -i eth0 -i wlan0 -w /tmp/multi.pcap
```

### Ring buffer for long captures
```bash
sudo tshark -i eth0 -b filesize:51200 -b files:10 -w /tmp/rolling.pcap
# writes 50MB × 10 files = 500MB max, then overwrites
```

### Capture with name resolution disabled (faster)
```bash
sudo tshark -i eth0 -n -w /tmp/fast.pcap
```

### Extract files from HTTP traffic
```bash
# Method 1: tshark export
tshark -r file.pcap --export-objects "http,/tmp/extracted"
# Method 2: just get URLs
tshark -r file.pcap -Y "http.response and http.content_type contains \"octet\"" \
  -T fields -e http.host -e http.request.uri -e http.response.code
```

## Threat intel integration

After extracting IOCs from a pcap, cross-reference:

```bash
# Domains from DNS queries
tshark -r file.pcap -Y "dns.flags.response == 0" -T fields -e dns.qry.name | sort -u > /tmp/domains.txt
# Check each on VirusTotal: https://www.virustotal.com/gui/domain/<domain>

# External IPs (excluding RFC1918)
tshark -r file.pcap -T fields -e ip.dst | sort -u | grep -vE "^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.|127\.)" > /tmp/ext_ips.txt
# Check each on AbuseIPDB: https://www.abuseipdb.com/check/<ip>
```

## Time-correlated analysis

For incident response, often you need traffic around a specific event time:

```bash
# All traffic in a 60-second window starting at 14:32:00
tshark -r file.pcap -Y "frame.time >= \"2026-01-15 14:32:00\" and frame.time < \"2026-01-15 14:33:00\""

# Or relative to a known time
tshark -r file.pcap -Y "frame.time_relative >= 120 and frame.time_relative < 180"
```
