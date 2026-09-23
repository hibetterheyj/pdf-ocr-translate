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
        check_tables.py --parts parts --fix   # also pad short rows in place
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

BEGIN = re.compile(r"\\begin\{longtable\}(?:\[[^\]]*\])?\{@\{\}(.*?)@\{\}\}", re.DOTALL)
END = "\\end{longtable}"


def column_count(spec: str) -> int:
    """Count declared columns.

    Handles the plain types plus every wrapped form the pipeline introduces —
    ``p{3em}``, the custom ``L{15em}`` / ``C{7em}`` ragged-right and centred
    columns a sizing pass defines, ``>{\\RaggedRight\\arraybackslash}p{3em}``,
    and ``*{3}{c}``.

    Any *brace-argument* descriptor counts as one column, whatever letter names
    it: matching a fixed list of letters is what let ``C{7em}`` slip through
    uncounted and produced a screenful of bogus "declares 1 columns" rows.
    """
    spec = re.sub(r"[<>]\{[^{}]*\}", "", spec)                # array's >{...}/<{...}
    spec = re.sub(r"\*\s*\{[^{}]*\}\s*\{([^{}]*)\}", r"\1", spec)   # *{n}{col} -> col
    spec = re.sub(r"[A-Za-z]\{[^{}]*\}", "X", spec)           # any brace-arg type
    return len(re.findall(r"[lcrX]", spec))


def blank_cell_internals(body: str) -> str:
    """Remove cell-internal row breaks so they are not read as table rows."""
    body = re.sub(r"\\shortstack\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", "X", body)
    body = re.sub(r"\\multirow\{[^{}]*\}\{[^{}]*\}\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}",
                  r"\1", body)
    return body


def pad_short_rows(body: str, cols: int) -> tuple[str, int]:
    """Append the missing trailing ``&`` to rows that fall short of ``cols``.

    A row with fewer cells than the preamble declares is usually just a row
    whose *trailing* cells are empty — a header row under a ``\\multirow`` (the
    multirow covers the cell, but the row still has to supply a placeholder),
    or a data row with no value in the last column.  LaTeX renders those
    correctly by leaving the cells blank, so the damage is invisible; but it is
    also indistinguishable from a cell that OCR genuinely dropped, which is why
    the checker flags it and this pass only ever *appends*, never moves or
    removes.  Rows that are too *long* are left alone — that is a merged cell
    and needs the PDF.
    """
    pieces, prev, fixed = [], 0, 0
    for m in re.finditer(r"\\\\(?!\s*\[)", body):
        row = body[prev:m.start()]
        pieces.append(row)
        missing = cols - 1 - row.count("&")
        if ("&" in row and missing > 0
                and "\\multicolumn" not in row and "\\multirow" not in row):
            pieces.append("& " * missing)
            fixed += 1
        pieces.append(m.group(0))
        prev = m.end()
    pieces.append(body[prev:])
    return "".join(pieces), fixed


def check(path: Path, fix: bool = False) -> tuple[int, list[str], int]:
    text = path.read_text()
    problems: list[str] = []
    checked = 0
    padded = 0
    out: list[str] = []
    pos = 0
    for match in BEGIN.finditer(text):
        end = text.find(END, match.end())
        if end < 0:
            problems.append(f"{path.name}: unterminated longtable at offset {match.start()}")
            continue
        cols = column_count(match.group(1))
        body = text[match.end():end]
        checked += 1

        if fix:
            new_body, n = pad_short_rows(body, cols)
            if n:
                out.append(text[pos:match.end()])
                out.append(new_body)
                pos = end
                padded += n
                body = new_body

        for row in (r for r in blank_cell_internals(body).split(r"\\") if "&" in r):
            if "\\multicolumn" in row or "\\multirow" in row:
                continue
            amps = row.count("&")
            if amps != cols - 1:
                snippet = " ".join(row.split())[:110]
                problems.append(
                    f"{path.name}: table #{checked} declares {cols} columns "
                    f"({cols - 1} '&') but this row has {amps}  :: {snippet}"
                )

    if fix and padded:
        out.append(text[pos:])
        path.write_text("".join(out))
    return checked, problems, padded


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", required=True)
    ap.add_argument("--fix", action="store_true",
                    help="append the missing trailing '&' to short rows, in place")
    args = ap.parse_args()
    total = 0
    padded = 0
    problems: list[str] = []
    for path in sorted(Path(args.parts).glob("*.tex")):
        n, p, f = check(path, fix=args.fix)
        total += n
        padded += f
        problems += p
    print(f"checked {total} longtable(s)")
    if args.fix:
        print(f"padded {padded} short row(s)")
    for p in problems:
        print("  " + p)
    print(f"{len(problems)} row(s) with an unexpected column count")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
