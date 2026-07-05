"""
fs/archive.py — tar.gz / zip pack, unpack, and list (stdlib tarfile/zipfile).

Format is inferred from the archive extension. Extraction is path-traversal
safe (rejects absolute paths and ``..`` escapes — Zip-Slip / tar-slip guard).

    python modules/fs/archive.py pack out.tar.gz src_dir
    python modules/fs/archive.py pack out.zip file1 file2 dir3
    python modules/fs/archive.py list out.tar.gz
    python modules/fs/archive.py unpack out.tar.gz dest_dir
"""
from __future__ import annotations

import argparse
import os
import sys
import tarfile
import zipfile


def _is_zip(path: str) -> bool:
    return path.lower().endswith(".zip")


def _safe_dest(base: str, name: str) -> str | None:
    """Return the resolved path if *name* stays inside *base*, else None."""
    if os.path.isabs(name) or name.startswith(("/", "\\")):
        return None
    target = os.path.normpath(os.path.join(base, name))
    base_abs = os.path.abspath(base)
    if os.path.abspath(target) == base_abs or \
            os.path.abspath(target).startswith(base_abs + os.sep):
        return target
    return None


def pack(archive: str, sources: list[str]) -> int:
    n = 0
    if _is_zip(archive):
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for src in sources:
                if os.path.isdir(src):
                    for dp, _, fns in os.walk(src):
                        for name in fns:
                            full = os.path.join(dp, name)
                            zf.write(full, os.path.relpath(full, os.path.dirname(src) or "."))
                            n += 1
                            print(f"  + {full}")
                else:
                    zf.write(src, os.path.basename(src))
                    n += 1
                    print(f"  + {src}")
    else:
        with tarfile.open(archive, "w:gz") as tf:
            for src in sources:
                arc = os.path.basename(src.rstrip(os.sep))
                tf.add(src, arcname=arc, recursive=True)
                n += 1
                print(f"  + {src}")
    return n


def list_contents(archive: str) -> list[tuple[str, int]]:
    if _is_zip(archive):
        with zipfile.ZipFile(archive) as zf:
            return [(i.filename, i.file_size) for i in zf.infolist()]
    with tarfile.open(archive, "r:*") as tf:
        return [(m.name, m.size) for m in tf.getmembers() if m.isfile()]


def unpack(archive: str, dest: str) -> int:
    os.makedirs(dest, exist_ok=True)
    n, skipped = 0, []
    if _is_zip(archive):
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                if _safe_dest(dest, info.filename) is None:
                    skipped.append(info.filename)
                    continue
                zf.extract(info, dest)
                if not info.is_dir():
                    n += 1
    else:
        with tarfile.open(archive, "r:*") as tf:
            for member in tf.getmembers():
                if _safe_dest(dest, member.name) is None or member.issym() or member.islnk():
                    skipped.append(member.name)
                    continue
                tf.extract(member, dest)
                if member.isfile():
                    n += 1
    for s in skipped:
        print(f"  ! skipped unsafe path: {s}", file=sys.stderr)
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fs archive", description="Pack/unpack/list archives.")
    sub = ap.add_subparsers(dest="action", required=True)
    p_pack = sub.add_parser("pack", help="create an archive")
    p_pack.add_argument("archive")
    p_pack.add_argument("sources", nargs="+")
    p_list = sub.add_parser("list", help="list archive contents")
    p_list.add_argument("archive")
    p_unpack = sub.add_parser("unpack", help="extract an archive (safely)")
    p_unpack.add_argument("archive")
    p_unpack.add_argument("dest")
    args = ap.parse_args(argv)

    try:
        if args.action == "pack":
            for s in args.sources:
                if not os.path.exists(s):
                    print(f"[archive] source not found: {s}", file=sys.stderr)
                    return 2
            count = pack(args.archive, args.sources)
            print(f"packed {count} item(s) -> {args.archive}")
            return 0
        if args.action == "list":
            rows = list_contents(args.archive)
            for name, size in rows:
                print(f"{size:>12}  {name}")
            print(f"; {len(rows)} file(s)", file=sys.stderr)
            return 0
        if args.action == "unpack":
            count = unpack(args.archive, args.dest)
            print(f"extracted {count} file(s) -> {args.dest}")
            return 0
    except (tarfile.TarError, zipfile.BadZipFile, OSError) as e:
        print(f"[archive] {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
