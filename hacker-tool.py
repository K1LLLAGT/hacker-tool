#!/usr/bin/env python3
"""
hacker-tool — single-entrypoint offline-first audit/automation CLI.

Usage:
    hacker-tool fs manifest --root <path> [--exclude a,b,c] [--no-hash]
    hacker-tool fs diff <old_manifest.json> <new_manifest.json>
    hacker-tool net scan --range 192.168.1.0/24 [--nmap]
    hacker-tool web check <url>
    hacker-tool web links <url> [--all-domains]
    hacker-tool project snapshot <project_dir> [--name NAME]
    hacker-tool sync push <workspace_name>
    hacker-tool sync pull <workspace_name>
    hacker-tool sync status <workspace_name>
    hacker-tool report <input.json> [--title TITLE] [--fmt md|html]
    hacker-tool clean [--dry-run] [--path DIR]
    hacker-tool crypto hash  [--file F | --text T] [--algo sha256]
    hacker-tool crypto encode [--file F | --text T] [--url-safe]
    hacker-tool crypto decode --text T [--url-safe]
    hacker-tool crypto entropy --file F
    hacker-tool crypto compare --hash-a A --hash-b B
    hacker-tool device info
    hacker-tool device storage
    hacker-tool device battery
    hacker-tool device net
    hacker-tool device cpu
    hacker-tool vuln headers <url>
    hacker-tool vuln ports --host H [--ports 22,80,443]
    hacker-tool vuln perms --root <path>
    hacker-tool proc list [--filter NAME]
    hacker-tool proc top [--n 10] [--sort rss_kb]
    hacker-tool proc find <name>
    hacker-tool proc kill <pid> [--sig TERM]
    hacker-tool proc mem

Design principles:
    - Offline-first: fs/net(ping/local nmap)/project/report/crypto/device/proc
      all work with zero network access.
    - Online features are explicit subcommands (web, vuln headers) — never
      silently triggered.
    - net scan and vuln ports are restricted to RFC1918 / loopback ranges.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from core.config import load_config
from core.logging_setup import setup_logging


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hacker-tool", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="command", required=True)

    # ── fs ────────────────────────────────────────────────────────────────
    fs = sub.add_parser("fs", help="filesystem manifest / integrity / diff")
    fs_sub = fs.add_subparsers(dest="fs_command", required=True)

    fs_manifest = fs_sub.add_parser("manifest", help="build a manifest of a directory")
    fs_manifest.add_argument("--root", required=True)
    fs_manifest.add_argument("--exclude", default="",
                             help="comma-separated dir/file names to skip")
    fs_manifest.add_argument("--no-hash", action="store_true",
                             help="skip hashing (faster, less thorough)")
    fs_manifest.add_argument("--out", default=None,
                             help="output dir (default: <local_root>/reports)")

    fs_diff = fs_sub.add_parser("diff", help="diff two manifest JSON files")
    fs_diff.add_argument("old")
    fs_diff.add_argument("new")

    # ── net ───────────────────────────────────────────────────────────────
    net = sub.add_parser("net", help="local LAN inventory (RFC1918 only)")
    net_sub = net.add_subparsers(dest="net_command", required=True)
    net_scan = net_sub.add_parser("scan", help="host discovery on your own LAN")
    net_scan.add_argument("--range", required=True,
                          help="CIDR, must be private (10/8, 172.16/12, 192.168/16)")
    net_scan.add_argument("--nmap", action="store_true",
                          help="use nmap -sn instead of raw ping sweep")

    # ── web ───────────────────────────────────────────────────────────────
    web = sub.add_parser("web", help="HTTP checks for sites you operate (online, opt-in)")
    web_sub = web.add_subparsers(dest="web_command", required=True)
    web_check = web_sub.add_parser("check", help="check a single URL")
    web_check.add_argument("url")
    web_links = web_sub.add_parser("links", help="check all links found on a page")
    web_links.add_argument("url")
    web_links.add_argument("--all-domains", action="store_true",
                           help="also check off-domain links")

    # ── project ───────────────────────────────────────────────────────────
    project = sub.add_parser("project", help="project snapshot / packaging")
    project_sub = project.add_subparsers(dest="project_command", required=True)
    proj_snap = project_sub.add_parser("snapshot", help="tar.gz snapshot of a project dir")
    proj_snap.add_argument("project_dir")
    proj_snap.add_argument("--name", default=None)
    proj_snap.add_argument("--out", default=None)

    # ── sync ──────────────────────────────────────────────────────────────
    sync = sub.add_parser("sync", help="local <-> remote (SMB or path) workspace sync")
    sync_sub = sync.add_subparsers(dest="sync_command", required=True)
    for name in ("push", "pull", "status"):
        sp = sync_sub.add_parser(name)
        sp.add_argument("workspace")

    # ── report ────────────────────────────────────────────────────────────
    report = sub.add_parser("report", help="render a JSON result as a Markdown/HTML report")
    report.add_argument("input_json")
    report.add_argument("--title", default="hacker-tool report")
    report.add_argument("--fmt", choices=["md", "html"], default="md")
    report.add_argument("--out", default=None)

    # ── clean ─────────────────────────────────────────────────────────────
    clean = sub.add_parser("clean",
                           help="remove .pyc files and __pycache__ dirs from the project tree")
    clean.add_argument("--dry-run", action="store_true",
                       help="preview what would be removed without deleting anything")
    clean.add_argument("--path", default=".", metavar="DIR",
                       help="root directory to clean (default: current directory)")

    # ── crypto ────────────────────────────────────────────────────────────
    crypto = sub.add_parser("crypto",
                            help="offline cryptographic utilities — hash, encode, entropy")
    crypto_sub = crypto.add_subparsers(dest="crypto_command", required=True)

    c_hash = crypto_sub.add_parser("hash", help="hash a file or text string")
    c_hash.add_argument("--file", default=None, metavar="PATH", help="file to hash")
    c_hash.add_argument("--text", default=None, metavar="TEXT", help="text string to hash")
    c_hash.add_argument("--algo", default="sha256",
                        choices=["sha256", "sha1", "md5", "sha512", "sha224", "sha384"],
                        help="hash algorithm (default: sha256)")

    c_enc = crypto_sub.add_parser("encode", help="base64-encode a file or text")
    c_enc.add_argument("--file", default=None, metavar="PATH")
    c_enc.add_argument("--text", default=None, metavar="TEXT")
    c_enc.add_argument("--url-safe", action="store_true", help="use URL-safe alphabet")

    c_dec = crypto_sub.add_parser("decode", help="base64-decode a string")
    c_dec.add_argument("--text", required=True, metavar="B64")
    c_dec.add_argument("--url-safe", action="store_true")

    c_ent = crypto_sub.add_parser("entropy", help="Shannon entropy of a file")
    c_ent.add_argument("--file", required=True, metavar="PATH")

    c_cmp = crypto_sub.add_parser("compare", help="constant-time comparison of two digests")
    c_cmp.add_argument("--hash-a", required=True, metavar="HEX")
    c_cmp.add_argument("--hash-b", required=True, metavar="HEX")

    # ── device ────────────────────────────────────────────────────────────
    device = sub.add_parser("device", help="Android/Termux device introspection (offline)")
    device_sub = device.add_subparsers(dest="device_command", required=True)
    device_sub.add_parser("info",    help="device identity (manufacturer, model, Android ver)")
    device_sub.add_parser("storage", help="disk usage: internal + Termux home")
    device_sub.add_parser("battery", help="battery status, temperature, voltage")
    device_sub.add_parser("net",     help="network interfaces with IPs and state")
    device_sub.add_parser("cpu",     help="CPU model, core count, current frequency")

    # ── vuln ──────────────────────────────────────────────────────────────
    vuln = sub.add_parser("vuln", help="vulnerability surface checks")
    vuln_sub = vuln.add_subparsers(dest="vuln_command", required=True)

    v_hdr = vuln_sub.add_parser("headers",
                                help="HTTP security header audit (online, opt-in)")
    v_hdr.add_argument("url", help="URL to audit (https:// added if missing)")
    v_hdr.add_argument("--timeout", type=int, default=10)

    v_ports = vuln_sub.add_parser("ports",
                                  help="TCP port scan with service hints (LAN/localhost only)")
    v_ports.add_argument("--host", required=True)
    v_ports.add_argument("--ports", default=None,
                         help="comma-separated port list (default: well-known set)")
    v_ports.add_argument("--timeout", type=float, default=1.0)

    v_perms = vuln_sub.add_parser("perms",
                                  help="filesystem permission audit (world-write, SUID, SGID)")
    v_perms.add_argument("--root", required=True, metavar="PATH")
    v_perms.add_argument("--max", type=int, default=100, dest="max_findings",
                         help="max findings to return (default: 100)")

    # ── proc ──────────────────────────────────────────────────────────────
    proc = sub.add_parser("proc", help="process inspection and memory summary (offline)")
    proc_sub = proc.add_subparsers(dest="proc_command", required=True)

    p_list = proc_sub.add_parser("list", help="list all visible processes")
    p_list.add_argument("--filter", default=None, metavar="NAME",
                        help="only show procs whose name/cmdline contains NAME")

    p_top = proc_sub.add_parser("top", help="top N processes by resource usage")
    p_top.add_argument("--n", type=int, default=10, help="number of results (default: 10)")
    p_top.add_argument("--sort", default="rss_kb",
                       choices=["rss_kb", "cpu_ticks", "pid"],
                       help="sort key (default: rss_kb)")

    p_find = proc_sub.add_parser("find", help="find processes by name substring")
    p_find.add_argument("name")

    p_kill = proc_sub.add_parser("kill", help="send a signal to a process by PID")
    p_kill.add_argument("pid", type=int)
    p_kill.add_argument("--sig", default="TERM",
                        choices=["TERM", "KILL", "HUP", "INT"],
                        help="signal to send (default: TERM)")

    proc_sub.add_parser("mem", help="memory summary from /proc/meminfo")

    return p


def main():
    args = build_parser().parse_args()
    cfg = load_config()
    logger = setup_logging(cfg)

    try:
        # ── fs ────────────────────────────────────────────────────────────
        if args.command == "fs":
            from modules.fs import manifest as fs_manifest_mod

            if args.fs_command == "manifest":
                exclude = [e.strip() for e in args.exclude.split(",") if e.strip()]
                m = fs_manifest_mod.build_manifest(args.root, exclude,
                                                   hash_files=not args.no_hash)
                out_dir = Path(args.out) if args.out else Path(cfg["local_root"]) / "reports"
                out_path = fs_manifest_mod.save_manifest(m, out_dir)
                logger.info(f"Manifest written: {out_path} ({m['file_count']} files)")

            elif args.fs_command == "diff":
                old = json.loads(Path(args.old).read_text())
                new = json.loads(Path(args.new).read_text())
                d = fs_manifest_mod.diff_manifests(old, new)
                print(json.dumps(d, indent=2))

        # ── net ───────────────────────────────────────────────────────────
        elif args.command == "net":
            from modules.net import scan as net_scan_mod

            if args.net_command == "scan":
                if args.nmap:
                    out = net_scan_mod.nmap_scan(args.range)
                    print(out)
                else:
                    alive = net_scan_mod.ping_sweep(args.range)
                    print(json.dumps({"range": args.range, "alive": alive}, indent=2))

        # ── web ───────────────────────────────────────────────────────────
        elif args.command == "web":
            from modules.web import checks as web_checks_mod

            if args.web_command == "check":
                result = web_checks_mod.check_url(args.url)
                print(json.dumps(result, indent=2))
            elif args.web_command == "links":
                result = web_checks_mod.check_links_on_page(
                    args.url, same_domain_only=not args.all_domains
                )
                print(json.dumps(result, indent=2))

        # ── project ───────────────────────────────────────────────────────
        elif args.command == "project":
            from modules.project import snapshot as proj_snap_mod

            if args.project_command == "snapshot":
                out_dir = Path(args.out) if args.out else Path(cfg["local_root"]) / "reports"
                out_path = proj_snap_mod.snapshot(args.project_dir, out_dir, name=args.name)
                logger.info(f"Snapshot written: {out_path}")

        # ── sync ──────────────────────────────────────────────────────────
        elif args.command == "sync":
            from modules.sync import commands as sync_mod

            if args.sync_command == "push":
                sync_mod.cmd_push(cfg, logger, args.workspace)
            elif args.sync_command == "pull":
                sync_mod.cmd_pull(cfg, logger, args.workspace)
            elif args.sync_command == "status":
                result = sync_mod.cmd_status(cfg, logger, args.workspace)
                print(json.dumps(result, indent=2))

        # ── report ────────────────────────────────────────────────────────
        elif args.command == "report":
            from modules.report import generate as report_mod

            data = json.loads(Path(args.input_json).read_text())
            out_dir = Path(args.out) if args.out else Path(cfg["local_root"]) / "reports"
            out_path = report_mod.write_report(args.title, data, out_dir, fmt=args.fmt)
            logger.info(f"Report written: {out_path}")

        # ── clean ─────────────────────────────────────────────────────────
        elif args.command == "clean":
            import clean as clean_mod
            clean_mod.run(args, logger)

        # ── crypto ────────────────────────────────────────────────────────
        elif args.command == "crypto":
            from modules.crypto import ops as crypto_mod

            if args.crypto_command == "hash":
                result = crypto_mod.hash_data(file=args.file, text=args.text, algo=args.algo)
                print(json.dumps(result, indent=2))

            elif args.crypto_command == "encode":
                result = crypto_mod.encode_b64(file=args.file, text=args.text,
                                               url_safe=args.url_safe)
                print(json.dumps(result, indent=2))

            elif args.crypto_command == "decode":
                result = crypto_mod.decode_b64(text=args.text, url_safe=args.url_safe)
                print(json.dumps(result, indent=2))

            elif args.crypto_command == "entropy":
                result = crypto_mod.shannon_entropy(file=args.file)
                print(json.dumps(result, indent=2))

            elif args.crypto_command == "compare":
                result = crypto_mod.compare_hashes(args.hash_a, args.hash_b)
                print(json.dumps(result, indent=2))

        # ── device ────────────────────────────────────────────────────────
        elif args.command == "device":
            from modules.device import info as device_mod

            dispatch = {
                "info":    device_mod.device_info,
                "storage": device_mod.storage_info,
                "battery": device_mod.battery_info,
                "net":     device_mod.network_interfaces,
                "cpu":     device_mod.cpu_info,
            }
            result = dispatch[args.device_command]()
            print(json.dumps(result, indent=2))
            logger.info(f"device {args.device_command}: OK")

        # ── vuln ──────────────────────────────────────────────────────────
        elif args.command == "vuln":
            from modules.vuln import audit as vuln_mod

            if args.vuln_command == "headers":
                result = vuln_mod.check_headers(args.url, timeout=args.timeout)
                print(json.dumps(result, indent=2))
                logger.info(f"vuln headers: {args.url} — grade {result.get('grade','?')}")

            elif args.vuln_command == "ports":
                ports = None
                if args.ports:
                    ports = [int(p.strip()) for p in args.ports.split(",") if p.strip()]
                result = vuln_mod.scan_ports(args.host, ports=ports, timeout=args.timeout)
                print(json.dumps(result, indent=2))
                logger.info(f"vuln ports: {args.host} — {result.get('open_count', 0)} open")

            elif args.vuln_command == "perms":
                result = vuln_mod.check_perms(args.root, max_findings=args.max_findings)
                print(json.dumps(result, indent=2))
                logger.info(f"vuln perms: {args.root} — "
                            f"{result.get('findings_count', 0)} findings")

        # ── proc ──────────────────────────────────────────────────────────
        elif args.command == "proc":
            from modules.proc import monitor as proc_mod

            if args.proc_command == "list":
                result = proc_mod.list_procs(filter_name=args.filter)
                print(json.dumps(result, indent=2))

            elif args.proc_command == "top":
                result = proc_mod.top_procs(n=args.n, sort_by=args.sort)
                print(json.dumps(result, indent=2))

            elif args.proc_command == "find":
                result = proc_mod.find_proc(args.name)
                print(json.dumps(result, indent=2))

            elif args.proc_command == "kill":
                result = proc_mod.kill_proc(pid=args.pid, sig=args.sig)
                print(json.dumps(result, indent=2))
                logger.info(f"proc kill: pid={args.pid} sig={args.sig} "
                            f"sent={result.get('sent')}")

            elif args.proc_command == "mem":
                result = proc_mod.mem_summary()
                print(json.dumps(result, indent=2))

    except Exception as e:
        logger.error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
