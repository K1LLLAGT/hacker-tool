"""
modules/vuln/audit.py — local vulnerability surface checks.

Offline (ports, perms) + online opt-in (headers). Stdlib only.
"""
from datetime import datetime, timezone
import os
from pathlib import Path
import socket
import stat
import urllib.error
import urllib.request

SECURITY_HEADERS = {
    "strict-transport-security": {"desc": "HSTS — enforces HTTPS",           "severity": "high"},
    "content-security-policy":   {"desc": "CSP — restricts resource origins", "severity": "high"},
    "x-content-type-options":    {"desc": "Prevents MIME-type sniffing",      "severity": "medium"},
    "x-frame-options":           {"desc": "Clickjacking protection",          "severity": "medium"},
    "referrer-policy":           {"desc": "Controls Referer leakage",         "severity": "low"},
    "permissions-policy":        {"desc": "Restricts browser feature access", "severity": "low"},
    "x-xss-protection":          {"desc": "Legacy XSS filter",                "severity": "info"},
}
LEAKY_HEADERS = ("server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version")

COMMON_PORTS = {
    21:    ("FTP",      "plaintext auth — use SFTP instead"),
    22:    ("SSH",      "OK if hardened; check key-only auth and fail2ban"),
    23:    ("Telnet",   "unencrypted — disable immediately"),
    25:    ("SMTP",     "open relay risk — verify auth required"),
    53:    ("DNS",      "check for recursive resolver exposure"),
    80:    ("HTTP",     "redirect all traffic to HTTPS"),
    110:   ("POP3",     "plaintext — use IMAPS/POP3S"),
    143:   ("IMAP",     "plaintext — use IMAPS"),
    443:   ("HTTPS",    "expected — verify TLS version"),
    445:   ("SMB",      "close to internet — ransomware target"),
    3306:  ("MySQL",    "should not be exposed externally"),
    3389:  ("RDP",      "high-risk if public — use VPN + MFA"),
    5900:  ("VNC",      "unencrypted — tunnel via SSH"),
    6379:  ("Redis",    "no auth by default — bind to localhost"),
    8080:  ("HTTP-alt", "dev server? ensure not running as root"),
    8443:  ("HTTPS-alt","verify TLS cert validity"),
    27017: ("MongoDB",  "no auth by default — bind to localhost"),
}


def check_headers(url: str, timeout: int = 10) -> dict:
    """Fetch headers from a URL and audit security posture. Online — opt-in."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "hacker-tool/3.0 (audit)"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
            status, final = resp.status, resp.url
    except urllib.error.URLError as e:
        return {"url": url, "ok": False, "error": str(e)}

    missing, present, leaking = [], [], []
    for h, meta in SECURITY_HEADERS.items():
        if h in headers:
            present.append({"header": h, "value": headers[h], **meta})
        else:
            missing.append({"header": h, **meta})
    for h in LEAKY_HEADERS:
        if h in headers:
            leaking.append({"header": h, "value": headers[h]})

    score = len(present)
    total = len(SECURITY_HEADERS)
    grade = "A" if score >= total - 1 else "B" if score >= total - 2 else \
            "C" if score >= total - 3 else "D" if score >= total - 4 else "F"

    return {
        "url": final, "status": status,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "grade": grade, "score": f"{score}/{total}",
        "present": present, "missing": missing, "leaking_info": leaking,
    }


def scan_ports(host: str, ports: list = None, timeout: float = 1.0) -> dict:
    """TCP connect scan — restricted to localhost and RFC1918 ranges."""
    import ipaddress
    PRIVATE = [ipaddress.ip_network(n) for n in
               ("10.0.0.0/8","172.16.0.0/12","192.168.0.0/16","127.0.0.0/8")]
    try:
        resolved = socket.gethostbyname(host)
        if not any(ipaddress.ip_address(resolved) in net for net in PRIVATE):
            raise ValueError(f"{host} ({resolved}) is not private/loopback. "
                             "vuln ports only scans RFC1918 and localhost.")
    except socket.gaierror as e:
        return {"host": host, "ok": False, "error": str(e)}

    target_ports = ports or list(COMMON_PORTS.keys())
    open_ports, closed_ports = [], []

    for port in sorted(target_ports):
        try:
            with socket.create_connection((host, port), timeout=timeout):
                svc, note = COMMON_PORTS.get(port, ("unknown", "no hint available"))
                open_ports.append({"port": port, "service": svc, "note": note})
        except (ConnectionRefusedError, OSError):
            closed_ports.append(port)

    return {"host": host, "resolved": resolved, "scanned": len(target_ports),
            "open_count": len(open_ports), "open": open_ports, "closed": closed_ports}


def check_perms(root: str, max_findings: int = 100) -> dict:
    """Walk a directory tree and flag world-writable, SUID, and SGID files."""
    root_path = Path(root).expanduser().resolve()
    findings, errors, checked = [], [], 0

    for p in root_path.rglob("*"):
        if len(findings) >= max_findings:
            break
        try:
            mode = p.stat().st_mode
            checked += 1
            issues = []
            if mode & stat.S_IWOTH:
                issues.append("world-writable")
            if p.is_file() and mode & stat.S_ISUID:
                issues.append("SUID set")
            if p.is_file() and mode & stat.S_ISGID:
                issues.append("SGID set")
            if issues:
                findings.append({"path": str(p.relative_to(root_path)),
                                 "mode": oct(mode), "issues": issues})
        except (PermissionError, OSError) as e:
            errors.append({"path": str(p), "error": str(e)})

    return {"root": str(root_path), "checked": checked,
            "findings_count": len(findings), "findings": findings, "errors": errors}
