#!/usr/bin/env python3
"""Check that every ``longtable`` row has the column count its preamble declares.

OCR damage in MinerU output usually shows up as merged or shifted cells, which
makes one row carry a different number of ``&`` than its neighbours.  LaTeX
reports that as "Extra alignment tab has been changed to \\cr", but catching it
here keeps the compile loop short.

Usage:  check_tables.py --parts parts
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

BEGIN = re.compile(r"\\begin\{longtable\}(?:\[[^\]]*\])?\{@\{\}(.*?)@\{\}\}", re.DOTALL)
END = "\\end{longtable}"


def column_count(spec: str) -> int:
    return len(re.findall(r"[lcrp]", spec))


def strip_shortstack(body: str) -> str:
    """Blank out \\shortstack{...} bodies so their internal \\\\ is not a row break."""
    return re.sub(r"\\shortstack\{[^}]*\}", "X", body)


def check(path: Path) -> tuple[int, list[str]]:
    text = path.read_text()
    problems: list[str] = []
    checked = 0
    for match in BEGIN.finditer(text):
        end = text.find(END, match.end())
        if end < 0:
            problems.append(f"{path.name}: unterminated longtable at offset {match.start()}")
            continue
        cols = column_count(match.group(1))
        body = strip_shortstack(text[match.end():end])
        rows = [r for r in body.split(r"\\") if "&" in r]
        checked += 1
        for row in rows:
            amps = row.count("&")
            # a full row has cols-1 separators; allow \multicolumn rows to differ
            if "\\multicolumn" in row or "\\multirow" in row:
                continue
            if amps != cols - 1:
                snippet = " ".join(row.split())
                problems.append(
                    f"{path.name}: table #{checked} expects {cols} cols "
                    f"({cols - 1} '&') but found {amps}  :: {snippet[:110]}"
                )
    return checked, problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", required=True)
    args = ap.parse_args()
    total = 0
    problems: list[str] = []
    for path in sorted(Path(args.parts).glob("*.tex")):
        n, p = check(path)
        total += n
        problems += p
    print(f"checked {total} longtable(s)")
    for p in problems:
        print("  " + p)
    print(f"{len(problems)} row(s) with unexpected column count")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
