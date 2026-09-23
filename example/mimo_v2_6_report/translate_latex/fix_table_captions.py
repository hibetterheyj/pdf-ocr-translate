#!/usr/bin/env python3
"""Move the tables' prose captions into real `\\caption`s, above the table.

MinerU emits each table as a bare `longtable` — unnumbered, because the wrapper
sets `\\def\\LTcaptype{none}` — with the caption as an unmarked body paragraph.
The paragraph's position follows OCR reading order, not convention, so it lands
after the table about as often as before it, and consecutive tables' captions
can bunch together so they read as both belonging to the later table.  On the
MiMo-V2.6 run, Tables 4 and 5 arrived that way.

Per table this pass:

  * finds the caption paragraph ("表 N ..." / "Table N ...") on either side of
    the block and consumes it;
  * drops `\\def\\LTcaptype{none}` so the caption increments the `table`
    counter, and inserts `\\caption{...}\\label{tab:N}\\` directly under
    `\\begin{longtable}` — longtable prints a top caption there, which is where
    a table caption belongs;
  * unifies the font size wrapper to `{\\footnotesize ... }`;
  * replaces longtable's repeated caption on continuation pages with a
    right-aligned `（续表）` marker, via `\\endfirsthead` / `\\endhead`.

Numbering then matches the prose references as long as the tables appear in
order.  `\\renewcommand{\\tablename}{表}` supplies the label; the companion
preamble patch sets `\\LTcapwidth` to the text width, because longtable's 4in
default renders the caption as a narrow centred box inside a wider table.

Run on the source before splitting (translators then see `\\caption{}` and
translate inside it) — it is idempotent, so it also works on an already
translated file.  Usage:  fix_table_captions.py main.tex
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

BLOCK_OPEN = re.compile(r"^\s*\{?\s*(\\footnotesize)?\s*(\\setlength\{\\tabcolsep\}\{[^}]*\})?\s*"
                        r"\\def\\LTcaptype\{none\}.*$")
BEGIN = re.compile(r"^\\begin\{longtable\}")
END = r"\end{longtable}"
CAPTION = re.compile(r"^\s*(?:表|Table)\s*(\d+)\s+(.*)$")
SPEC = re.compile(r"\{@\{\}(.*?)@\{\}\}")
COLUMN_TOKEN = re.compile(r"[lcr](?!\{)|[LC]\{[^}]*\}")
SEARCH_WINDOW = 14


def n_columns(longtable_line: str) -> int:
    m = SPEC.search(longtable_line)
    return len(COLUMN_TOKEN.findall(m.group(1))) if m else 1


def continued_marker(text: str) -> str:
    """Continuation label in the document's language."""
    return "（续表）" if re.search(r"[一-鿿]", text) else "(continued)"


def paragraph_at(lines: list[str], i: int) -> tuple[int, int] | None:
    """Span of the blank-line-delimited paragraph containing line i."""
    if not lines[i].strip():
        return None
    s = i
    while s > 0 and lines[s - 1].strip():
        s -= 1
    e = i
    while e + 1 < len(lines) and lines[e + 1].strip():
        e += 1
    return s, e + 1


def find_caption(lines: list[str], start: int, end: int, used: set[int]):
    """Nearest unused '表 N' paragraph just before or just after [start, end)."""
    for i in range(start - 1, max(-1, start - SEARCH_WINDOW - 1), -1):
        if not lines[i].strip():
            continue
        span = paragraph_at(lines, i)
        if span and span[0] not in used:
            m = CAPTION.match(lines[span[0]])
            if m:
                return m.group(1), span, " ".join(l.strip() for l in lines[span[0]:span[1]])
    for i in range(end, min(len(lines), end + SEARCH_WINDOW)):
        if not lines[i].strip():
            continue
        span = paragraph_at(lines, i)
        if span and span[0] not in used:
            m = CAPTION.match(lines[span[0]])
            if m:
                return m.group(1), span, " ".join(l.strip() for l in lines[span[0]:span[1]])
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tex", nargs="?", default="main.tex")
    args = ap.parse_args()
    path = Path(args.tex)
    lines = path.read_text(encoding="utf-8").split("\n")

    # Locate the wrapper span of every table: the nearest `{...` line above the
    # `\begin{longtable}`, through the closing brace after `\end{longtable}`.
    # Anchoring on the longtable rather than on the `\def\LTcaptype{none}`
    # marker matters because fix_table_width.py runs first and rewrites that
    # opener, dropping the marker.
    spans = []
    for i, line in enumerate(lines):
        if not line.startswith("\\begin{longtable}"):
            continue
        j = i - 1
        while j >= 0 and not lines[j].strip():
            j -= 1
        start = j if j >= 0 and lines[j].lstrip().startswith("{") else i
        close = next((k for k in range(i, len(lines)) if lines[k].strip() == END), None)
        if close is None:
            continue
        spans.append((start, close + 2))   # include the trailing "}"

    used: set[int] = set()
    drop: set[int] = set()
    edits: list[tuple[int, str, str]] = []   # (line index, old, new)
    done = []

    for start, end in spans:
        if any("\\caption{" in lines[j] for j in range(start, end)):
            continue                     # already captioned (idempotent re-run)
        found = find_caption(lines, start, end, used)
        if not found:
            print(f"  WARNING: no caption found for the table at line {start + 1}")
            continue
        num, span, text = found
        used.add(span[0])
        drop.update(range(*span))
        done.append(num)

        # unify the wrapper opener: keep the size/column-sep settings, drop the
        # `\def\LTcaptype{none}` that suppressed numbering
        opener = lines[start]
        keep = "".join(m.group(0) for m in re.finditer(
            r"\\footnotesize|\\setlength\{\\tabcolsep\}\{[^}]*\}", opener))
        if "\\footnotesize" not in keep:
            keep = "\\footnotesize" + keep
        edits.append((start, opener, "{" + keep))

        # caption goes directly under \begin{longtable}
        body = re.sub(r"^(?:表|Table)\s*\d+\s+", "", text).strip()
        edits.append((start + 1, lines[start + 1],
                      lines[start + 1] + f"\n\\caption{{{body}}}\\label{{tab:{num}}}\\\\"))

        # A longtable that breaks repeats everything before `\endhead` on the
        # next page — caption included, so the table would be labelled "表 N"
        # twice.  Close the first head after the caption and give later pages a
        # plain continuation marker instead.
        head = next((k for k in range(start, end) if lines[k].strip() == "\\endhead"), None)
        if head is not None:
            n = n_columns(lines[start + 1])
            edits.append((head, lines[head],
                          f"\\endfirsthead\n"
                          f"\\multicolumn{{{n}}}{{r}}{{{continued_marker(text)}}}\\\\\n"
                          f"\\toprule\\noalign{{}}\n"
                          f"\\endhead"))

    out: list[str] = []
    for i, line in enumerate(lines):
        if i in drop:
            continue
        repl = next((new for idx, old, new in edits if idx == i), None)
        out.append(repl if repl is not None else line)

    path.write_text("\n".join(out), encoding="utf-8")
    print(f"tables captioned: {', '.join(done) if done else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
