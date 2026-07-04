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

Design principles:
    - Offline-first: fs/net(ping/local nmap)/project/report all work with
      zero network access.
    - Online features are explicit subcommands (web) — never silently
      triggered.
    - net scan is restricted to RFC1918 private ranges (your own LAN) —
      see modules/net/scan.py.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.config import load_config
from core.logging_setup import setup_logging


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hacker-tool", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="command", required=True)

    # fs
    fs = sub.add_parser("fs", help="filesystem manifest / integrity / diff")
    fs_sub = fs.add_subparsers(dest="fs_command", required=True)

    fs_manifest = fs_sub.add_parser("manifest", help="build a manifest of a directory")
    fs_manifest.add_argument("--root", required=True)
    fs_manifest.add_argument("--exclude", default="", help="comma-separated dir/file names to skip")
    fs_manifest.add_argument("--no-hash", action="store_true", help="skip hashing (faster, less thorough)")
    fs_manifest.add_argument("--out", default=None, help="output dir (default: <local_root>/reports)")

    fs_diff = fs_sub.add_parser("diff", help="diff two manifest JSON files")
    fs_diff.add_argument("old")
    fs_diff.add_argument("new")

    # net
    net = sub.add_parser("net", help="local LAN inventory (RFC1918 only)")
    net_sub = net.add_subparsers(dest="net_command", required=True)
    net_scan = net_sub.add_parser("scan", help="host discovery on your own LAN")
    net_scan.add_argument("--range", required=True, help="CIDR, must be private (10/8, 172.16/12, 192.168/16)")
    net_scan.add_argument("--nmap", action="store_true", help="use nmap -sn instead of raw ping sweep")

    # web
    web = sub.add_parser("web", help="HTTP checks for sites you operate (online, opt-in)")
    web_sub = web.add_subparsers(dest="web_command", required=True)
    web_check = web_sub.add_parser("check", help="check a single URL")
    web_check.add_argument("url")
    web_links = web_sub.add_parser("links", help="check all links found on a page")
    web_links.add_argument("url")
    web_links.add_argument("--all-domains", action="store_true", help="also check off-domain links")

    # project
    project = sub.add_parser("project", help="project snapshot / packaging")
    project_sub = project.add_subparsers(dest="project_command", required=True)
    proj_snap = project_sub.add_parser("snapshot", help="tar.gz snapshot of a project dir")
    proj_snap.add_argument("project_dir")
    proj_snap.add_argument("--name", default=None)
    proj_snap.add_argument("--out", default=None)

    # sync
    sync = sub.add_parser("sync", help="local <-> remote (SMB or path) workspace sync")
    sync_sub = sync.add_subparsers(dest="sync_command", required=True)
    for name in ("push", "pull", "status"):
        sp = sync_sub.add_parser(name)
        sp.add_argument("workspace")

    # report
    report = sub.add_parser("report", help="render a JSON result as a Markdown/HTML report")
    report.add_argument("input_json")
    report.add_argument("--title", default="hacker-tool report")
    report.add_argument("--fmt", choices=["md", "html"], default="md")
    report.add_argument("--out", default=None)

    return p


def main():
    args = build_parser().parse_args()
    cfg = load_config()
    logger = setup_logging(cfg)

    try:
        if args.command == "fs":
            from modules.fs import manifest as fs_manifest_mod

            if args.fs_command == "manifest":
                exclude = [e.strip() for e in args.exclude.split(",") if e.strip()]
                m = fs_manifest_mod.build_manifest(args.root, exclude, hash_files=not args.no_hash)
                out_dir = Path(args.out) if args.out else Path(cfg["local_root"]) / "reports"
                out_path = fs_manifest_mod.save_manifest(m, out_dir)
                logger.info(f"Manifest written: {out_path} ({m['file_count']} files)")

            elif args.fs_command == "diff":
                old = json.loads(Path(args.old).read_text())
                new = json.loads(Path(args.new).read_text())
                d = fs_manifest_mod.diff_manifests(old, new)
                print(json.dumps(d, indent=2))

        elif args.command == "net":
            from modules.net import scan as net_scan_mod

            if args.net_command == "scan":
                if args.nmap:
                    out = net_scan_mod.nmap_scan(args.range)
                    print(out)
                else:
                    alive = net_scan_mod.ping_sweep(args.range)
                    print(json.dumps({"range": args.range, "alive": alive}, indent=2))

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

        elif args.command == "project":
            from modules.project import snapshot as proj_snap_mod

            if args.project_command == "snapshot":
                out_dir = Path(args.out) if args.out else Path(cfg["local_root"]) / "reports"
                out_path = proj_snap_mod.snapshot(args.project_dir, out_dir, name=args.name)
                logger.info(f"Snapshot written: {out_path}")

        elif args.command == "sync":
            from modules.sync import commands as sync_mod

            if args.sync_command == "push":
                sync_mod.cmd_push(cfg, logger, args.workspace)
            elif args.sync_command == "pull":
                sync_mod.cmd_pull(cfg, logger, args.workspace)
            elif args.sync_command == "status":
                result = sync_mod.cmd_status(cfg, logger, args.workspace)
                print(json.dumps(result, indent=2))

        elif args.command == "report":
            from modules.report import generate as report_mod

            data = json.loads(Path(args.input_json).read_text())
            out_dir = Path(args.out) if args.out else Path(cfg["local_root"]) / "reports"
            out_path = report_mod.write_report(args.title, data, out_dir, fmt=args.fmt)
            logger.info(f"Report written: {out_path}")

    except Exception as e:
        logger.error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
