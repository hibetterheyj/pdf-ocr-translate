#!/usr/bin/env python3
"""Check that every ``longtable`` row carries the column count its preamble declares.

OCR damage in MinerU output shows up as merged or shifted cells, leaving a row
with the wrong number of ``&``.  LaTeX reports that as "Extra alignment tab has
been changed to \\cr" — but only at compile time, one row at a time.  Catching
it here keeps the compile loop short and points straight at the bad row.

Two details that matter:

  * ``\\shortstack{a\\\\b}`` and ``\\multirow{2}{*}{a\\\\b}`` contain a row break
    inside a cell.  Splitting naively on ``\\\\`` would read that as a new row,
    so cell-internal commands are blanked first.
  * rows using ``\\multicolumn``/``\\multirow`` legitimately differ from the
    declared count, so they are skipped rather than flagged.

Usage:  check_tables.py --parts parts
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

BEGIN = re.compile(r"\\begin\{longtable\}(?:\[[^\]]*\])?\{@\{\}(.*?)@\{\}\}", re.DOTALL)
END = "\\end{longtable}"


def column_count(spec: str) -> int:
    """Count declared columns.

    Handles the plain types and the wrapped forms a sizing pass introduces —
    ``p{3em}``, ``L{15em}`` (a custom ragged-right p-column), and
    ``>{\\RaggedRight\\arraybackslash}p{3em}``.
    """
    spec = re.sub(r">\{[^}]*\}", "", spec)          # drop array's >{...} insertions
    return (len(re.findall(r"[lcr]", spec))
            + len(re.findall(r"[pLmXb]\{[^{}]*\}", spec)))


def blank_cell_internals(body: str) -> str:
    """Remove cell-internal row breaks so they are not read as table rows."""
    body = re.sub(r"\\shortstack\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", "X", body)
    body = re.sub(r"\\multirow\{[^{}]*\}\{[^{}]*\}\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}",
                  r"\1", body)
    return body


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
        body = blank_cell_internals(text[match.end():end])
        checked += 1
        for row in (r for r in body.split(r"\\") if "&" in r):
            if "\\multicolumn" in row or "\\multirow" in row:
                continue
            amps = row.count("&")
            if amps != cols - 1:
                snippet = " ".join(row.split())[:110]
                problems.append(
                    f"{path.name}: table #{checked} declares {cols} columns "
                    f"({cols - 1} '&') but this row has {amps}  :: {snippet}"
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
    print(f"{len(problems)} row(s) with an unexpected column count")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
