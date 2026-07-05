<!-- hacker-tool:generated -->
# modules/net/dns.py

## Overview

net/dns.py — pure-stdlib DNS client.

Forward (A, AAAA, MX, TXT, NS, CNAME) and reverse (PTR) lookups built on raw
UDP wire-format queries. No dnspython, no external binaries. stdlib only.

    python modules/net/dns.py example.com                 # A record
    python modules/net/dns.py example.com --type MX
    python modules/net/dns.py example.com --type ANY_COMMON
    python modules/net/dns.py 1.1.1.1 --reverse
    python modules/net/dns.py example.com --server 8.8.8.8

## Key functions

### `_encode_name(name: str) -> bytes`
No description available.

### `_read_name(msg: bytes, off: int) -> tuple[str, int]`
Decode a (possibly compressed) name; return (name, next_offset).

### `_build_query(qname: str, qtype: int) -> tuple[bytes, int]`
No description available.

### `_parse_rdata(rtype: int, msg: bytes, off: int, rdlen: int) -> str`
No description available.

### `query(qname: str, qtype: str, server: str, timeout: float) -> list[dict]`
Return a list of {name,type,ttl,data} answer records.

### `_reverse_name(ip: str) -> str`
No description available.

### `main(argv: list[str] | None) -> int`
No description available.

## Usage

```python
from modules.net import dns

result = dns.query(...)
print(result)
```
