#!/usr/bin/env python3
"""
clean.py — Remove all .pyc files and __pycache__ directories.
No external dependencies required.
"""

import os
import shutil
import argparse


RESET  = "\033[0m"
BOLD   = "\033[1m"
RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"


def colored(text, *codes):
    return "".join(codes) + text + RESET


def clean(root, dry_run=False):
    root = os.path.abspath(root)
    removed_files = []
    removed_dirs  = []

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        # Handle __pycache__ dirs — prune so os.walk won't descend into them
        for d in [d for d in dirnames if d == "__pycache__"]:
            full = os.path.join(dirpath, d)
            removed_dirs.append(full)
            if not dry_run:
                shutil.rmtree(full)
            dirnames.remove(d)

        # Handle stray .pyc files outside __pycache__
        for f in filenames:
            if f.endswith(".pyc"):
                full = os.path.join(dirpath, f)
                removed_files.append(full)
                if not dry_run:
                    os.remove(full)

    prefix = "[dry-run] " if dry_run else ""

    if not removed_dirs and not removed_files:
        print(colored("Nothing to clean — project is already tidy.", GREEN, BOLD))
        return

    if removed_dirs:
        print(colored(f"\n{prefix}__pycache__ directories removed:", YELLOW, BOLD))
        for d in removed_dirs:
            print(f"  {colored('✗', RED)} {os.path.relpath(d, root)}")

    if removed_files:
        print(colored(f"\n{prefix}.pyc files removed:", YELLOW, BOLD))
        for f in removed_files:
            print(f"  {colored('✗', RED)} {os.path.relpath(f, root)}")

    total  = len(removed_dirs) + len(removed_files)
    action = "Would remove" if dry_run else "Removed"
    print(colored(
        f"\n{prefix}✔ {action} {total} item(s) "
        f"({len(removed_dirs)} dir(s), {len(removed_files)} file(s)).",
        GREEN, BOLD
    ))


def main():
    parser = argparse.ArgumentParser(
        prog="clean",
        description="Remove all .pyc files and __pycache__ directories."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be removed without deleting anything."
    )
    parser.add_argument(
        "--path",
        default=".",
        metavar="DIR",
        help="Root directory to search from (default: current directory)."
    )
    args = parser.parse_args()
    clean(args.path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
