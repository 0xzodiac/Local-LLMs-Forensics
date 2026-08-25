# tshark Cheatsheet

A focused reference for tshark 4.x. For exhaustive docs, see `man tshark`
or https://www.wireshark.org/docs/man-pages/tshark.html.

## Interface and capture

```bash
tshark -D                    # list interfaces
tshark -i eth0               # capture on eth0
tshark -i any                # capture on all interfaces
tshark -i eth0 -c 100        # stop after 100 packets
tshark -i eth0 -a duration:30   # stop after 30 seconds
tshark -i eth0 -b filesize:10240 -b files:5   # ring buffer, 10MB × 5 files
tshark -i eth0 -w out.pcap   # write to file
tshark -i eth0 -f "port 443" # capture filter (BPF, applied at kernel)
```

## Reading pcaps

```bash
tshark -r file.pcap                    # read and display
tshark -r file.pcap -c 10              # first 10 packets
tshark -r file.pcap -Y "tcp.port==443" # display filter (Wireshark syntax)
tshark -r file.pcap -V                 # verbose (full dissection)
tshark -r file.pcap -T fields -e ip.src -e ip.dst   # extract fields
tshark -r file.pcap -T json            # JSON output
tshark -r file.pcap -T ek              # Elasticsearch format
```

## Display filter syntax (Wireshark)

### Comparison
```
ip.addr == 192.168.1.1
ip.addr != 10.0.0.1
tcp.port > 1024
tcp.len >= 100
```

### Logical
```
http and ip.src == 192.168.1.1
http or dns
not tcp
!(tcp.port == 443 or tcp.port == 80)
```

### Contains / matches
```
http.request.uri contains "admin"
http.host matches "google\\.com$"
tcp.flags.syn == 1 and tcp.flags.ack == 0
```

### Layer references
```
ip.src, ip.dst, ip.proto
tcp.srcport, tcp.dstport, tcp.flags
udp.srcport, udp.dstport
http.request.method, http.host, http.request.uri
dns.qry.name, dns.a
tls.handshake.extensions_server_name
smb2.cmd, smb2.file
```

### Slicing
```
tcp[0:4] == 47:43:50:01   # raw bytes (rarely needed; use field names)
```

## Capture filter (BPF) syntax

Different from display filters! Used at capture time, runs in kernel.

```
host 192.168.1.1
net 10.0.0.0/8
port 443
portrange 80-443
src host 10.0.0.1 and dst port 22
tcp
udp
icmp
not broadcast and not multicast
```

## Output options

```bash
-T fields -e field1 -e field2        # columnar output
-T json                              # one JSON object per packet
-T jsonraw                           # JSON with raw bytes
-T ek                                # Elastic Common Schema
-T psml                              # Packet Summary Markup Language
-T pdml                              # Packet Details Markup Language
-E header=y -E separator=, -E quote=d   # CSV
```

## Useful flags

```
-l   # line-buffered stdout (use with `| tee`)
-q   # quiet (less protocol info, faster)
-S   # absolute sequence numbers
-t   # time format: r=rel, a=abs, ad=abs+date
-e   # capture duration
-n   # disable name resolution (don't resolve IPs/ports)
-N   # name resolution flags: m=mac, n=network, t=transport
```

## Decryption

```bash
tshark -o tls.keys_list:"192.168.1.1,443,http,/path/to/key.log" -r file.pcap
# or via env: SSLKEYLOGFILE=/path/to/key.log tshark ...
```

## Examples (one-liners)

```bash
# Top 10 talkers by packet count
tshark -r file.pcap -T fields -e ip.src -e ip.dst | sort | uniq -c | sort -rn | head

# All DNS queries
tshark -r file.pcap -Y "dns.flags.response == 0" -T fields -e dns.qry.name

# HTTP requests with response codes
tshark -r file.pcap -Y "http.request" -T fields -e http.request.method -e http.host -e http.request.uri
tshark -r file.pcap -Y "http.response" -T fields -e http.response.code -e http.content_type

# TLS SNI extraction
tshark -r file.pcap -Y "tls.handshake.extensions_server_name" -T fields -e tls.handshake.extensions_server_name

# Failed TCP connections (SYN without SYN-ACK)
tshark -r file.pcap -Y "tcp.flags.syn == 1 and tcp.flags.ack == 0 and not tcp.analysis"

# Detect ARP spoofing (multiple IPs claiming same MAC)
tshark -r file.pcap -Y "arp" -T fields -e arp.src.hw_mac -e arp.src.proto_ipv4 | sort | uniq -c | sort -rn

# Beacon-like periodic connections
tshark -r file.pcap -Y "tcp" -T fields -e ip.dst -e frame.time_relative | sort -k1,1 -k2,2n
```
