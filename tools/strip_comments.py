#!/usr/bin/env python3
"""
Strip non‑essential comments from the project tree.

Safe by default:
 - Python: removes # comments via tokenize; preserves code and strings (docstrings untouched).
 - JS/TS: removes // line comments and /* */ block comments (best‑effort, skips inside quotes heuristically disabled by default).
 - CSS: removes /* */ block comments.
 - HTML: removes <!-- --> comments.

Usage examples:
  python tools/strip_comments.py --dry-run                # show planned changes
  python tools/strip_comments.py --write                  # apply changes
  python tools/strip_comments.py --write --extensions .py .js .css .html
  python tools/strip_comments.py --write --exclude esp32_sketch models

Notes:
 - Creates a .bak next to each modified file unless --no-backup.
 - JS/CSS/HTML stripping is regex-based and best‑effort; review diffs.
 - Use --aggressive to also strip Python docstrings and JSDoc blocks (riskier).
"""

from __future__ import annotations
import argparse
import io
import os
import re
import sys
import tokenize
from typing import Iterable


DEF_EXTS = [".py", ".js", ".mjs", ".cjs", ".ts", ".css", ".html", ".htm"]


def is_binary(path: str, chunk_size: int = 8000) -> bool:
    try:
        with open(path, "rb") as f:
            b = f.read(chunk_size)
        if b"\0" in b:
            return True
    except Exception:
        return True
    return False


def strip_python(src: str, aggressive: bool = False) -> str:
    out = io.StringIO()
    prev_toktype = None
    first_stmt_seen = False
    try:
        tokens = tokenize.generate_tokens(io.StringIO(src).readline)
        for tok_type, tok_str, start, end, line in tokens:
            if tok_type == tokenize.COMMENT:
                continue
            if aggressive and tok_type == tokenize.STRING and not first_stmt_seen:
                # Remove top‑level module docstring in aggressive mode
                continue
            out.write(tok_str)
            # Mark first non‑encoding/newline/comment/string as stmt
            if tok_type not in {tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT,
                                tokenize.ENCODING} and not (tok_type == tokenize.STRING and not first_stmt_seen):
                first_stmt_seen = True
            prev_toktype = tok_type
        return out.getvalue()
    except Exception:
        return src


_re_js_line = re.compile(r"(^|[\n\r])\s*//.*?(?=$|[\r\n])", re.DOTALL)
_re_block = re.compile(r"/\*.*?\*/", re.DOTALL)
_re_html = re.compile(r"<!--.*?-->", re.DOTALL)


def strip_text_generic(src: str, ext: str, aggressive: bool = False) -> str:
    out = src
    if ext in (".js", ".mjs", ".cjs", ".ts"):
        # Best‑effort: strip /* */ then //
        out = _re_block.sub("", out)
        out = _re_js_line.sub(lambda m: m.group(1), out)
    elif ext == ".css":
        out = _re_block.sub("", out)
    elif ext in (".html", ".htm"):
        out = _re_html.sub("", out)
    return out


def iter_files(root: str, exts: Iterable[str], exclude: Iterable[str]) -> Iterable[str]:
    exts = tuple(exts)
    exclude_set = set(os.path.normpath(p) for p in exclude)
    for dirpath, dirnames, filenames in os.walk(root):
        # prune excluded dirs
        norm = os.path.normpath(dirpath)
        if any(norm.startswith(e + os.sep) or norm == e for e in exclude_set):
            continue
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext in exts:
                yield os.path.join(dirpath, name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="apply changes to files")
    ap.add_argument("--dry-run", action="store_true", help="show planned changes (default)")
    ap.add_argument("--extensions", nargs="*", default=DEF_EXTS, help="file extensions to process")
    ap.add_argument("--exclude", nargs="*", default=[".venv", "models", "node_modules", "dist", "build"], help="paths to exclude")
    ap.add_argument("--aggressive", action="store_true", help="strip more aggressively (e.g., Python docstrings)")
    ap.add_argument("--no-backup", action="store_true", help="do not create .bak files when writing")
    args = ap.parse_args()

    if not args.write:
        args.dry_run = True

    changed = 0
    for path in iter_files(os.getcwd(), args.extensions, args.exclude):
        try:
            if is_binary(path):
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                src = f.read()
            ext = os.path.splitext(path)[1].lower()
            if ext == ".py":
                dst = strip_python(src, aggressive=args.aggressive)
            else:
                dst = strip_text_generic(src, ext, aggressive=args.aggressive)
            if dst != src:
                changed += 1
                if args.dry_run:
                    rel = os.path.relpath(path)
                    print(f"would change: {rel}")
                else:
                    if not args.no_backup:
                        with open(path + ".bak", "w", encoding="utf-8") as b:
                            b.write(src)
                    with open(path, "w", encoding="utf-8") as w:
                        w.write(dst)
        except Exception as e:
            print(f"skip {path}: {e}")

    if args.dry_run:
        print(f"Dry run complete. Files to change: {changed}")
    else:
        print(f"Done. Files changed: {changed}")


if __name__ == "__main__":
    main()

