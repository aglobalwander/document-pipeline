#!/usr/bin/env python3
"""
find_large_files.py  –  list files larger than a chosen threshold.

Usage
-----
python find_large_files.py 50M             # show everything ≥ 50 MB
python find_large_files.py 500K --top 20   # show 20 largest ≥ 500 KB
python find_large_files.py 1G --skip-dir venv .git

The script ignores symbolic links and (by default) the .git directory.
"""

from __future__ import annotations
import argparse, os, sys
from pathlib import Path
from humanize import naturalsize      # pip install humanize

# ──────────────────────────────────────────────────────────────────────────────
def parse_size(txt: str) -> int:
    """Convert '10M', '512K', '2G' to bytes."""
    units = {"K": 1 << 10, "M": 1 << 20, "G": 1 << 30}
    txt = txt.strip().upper()
    if txt[-1] in units:
        return int(float(txt[:-1]) * units[txt[-1]])
    return int(txt)  # assume raw bytes

def walk_repo(root: Path, skip_dirs: set[Path]) -> list[tuple[int, Path]]:
    big: list[tuple[int, Path]] = []
    for p in root.rglob("*"):
        if p.is_symlink():
            continue
        if any(part in skip_dirs for part in p.parts):
            continue
        if p.is_file():
            try:
                big.append((p.stat().st_size, p))
            except OSError:
                pass
    return big

# ──────────────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Find large files in a repo")
    ap.add_argument("threshold", help="size threshold, e.g. 50M, 500K, 1G")
    ap.add_argument("--top", type=int, default=None,
                    help="show only N largest files")
    ap.add_argument("--skip-dir", nargs="*", default=[".git", ".venv", "venv"],
                    help="directory names to ignore")
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parent.parent
    threshold = parse_size(args.threshold)
    skip = set(args.skip_dir)

    files = [
        (sz, p.relative_to(root))
        for sz, p in walk_repo(root, skip)
        if sz >= threshold
    ]
    files.sort(reverse=True)

    header = f"{'Size':>12} | Path"
    print(header)
    print("-" * len(header))
    for sz, path in (files[: args.top] if args.top else files):
        print(f"{naturalsize(sz, binary=True):>12} | {path}")

    total = sum(sz for sz, _ in files)
    print("\nMatched files:", len(files))
    print("Total size   :", naturalsize(total, binary=True))

if __name__ == "__main__":
    main()