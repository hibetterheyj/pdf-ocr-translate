#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


CHECKS = {
    "numeric_heading_prefix": re.compile(
        r'^\\(?:section|subsection|subsubsection)\{(?:[0-9]+|[A-Z])(?:\.(?:[0-9]+|[A-Z]))*\.?\s+'
    ),
    "ocr_placeholder": re.compile(r"\?\?"),
    "literal_backslash_n": re.compile(r"\\n(?![A-Za-z])"),
    "escaped_dollar": re.compile(r"\\\$"),
    "long_english_prose": re.compile(
        r"[A-Za-z]+(?:[-./][A-Za-z0-9]+)?(?:\s+[A-Za-z]+(?:[-./][A-Za-z0-9]+)?){5,}"
    ),
}


def should_skip(line: str, allow_prefixes: list[str]) -> bool:
    return any(line.startswith(prefix) for prefix in allow_prefixes)


def scan_file(path: Path, allow_prefixes: list[str]) -> list[tuple[int, str, str]]:
    findings: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if should_skip(line, allow_prefixes):
            continue
        for name, pattern in CHECKS.items():
            if name == "long_english_prose" and ("\\" in line or "$" in line):
                continue
            if pattern.search(line):
                findings.append((lineno, name, line[:240]))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan LaTeX translation parts for common OCR/translation issues.")
    parser.add_argument("paths", nargs="+", help="Files or directories to scan")
    parser.add_argument(
        "--allow-prefix",
        action="append",
        default=[],
        help="Line prefix to ignore when matching long English prose or other rules",
    )
    parser.add_argument(
        "--ignore-glob",
        action="append",
        default=[],
        help="Filename glob to ignore, for example 'part1a_*' or '*draft*'",
    )
    args = parser.parse_args()

    all_files: list[Path] = []
    for raw in args.paths:
        path = Path(raw)
        if path.is_dir():
            all_files.extend(sorted(p for p in path.rglob("*") if p.is_file()))
        elif path.is_file():
            all_files.append(path)

    if args.ignore_glob:
        filtered: list[Path] = []
        for path in all_files:
            if any(path.match(pattern) or path.name == pattern for pattern in args.ignore_glob):
                continue
            filtered.append(path)
        all_files = filtered

    findings_total = 0
    for path in all_files:
        findings = scan_file(path, args.allow_prefix)
        if findings:
            print(f"== {path} ==")
            for lineno, name, snippet in findings:
                print(f"{lineno}: [{name}] {snippet}")
            findings_total += len(findings)

    if findings_total:
        print(f"\nFound {findings_total} suspicious lines.")
        return 1

    print("No suspicious lines found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
