#!/usr/bin/env python3
"""Merge translated chunks into ``main_cn.tex``.

Ordering is by the numeric prefix of each chunk filename.  The preamble chunk is
emitted first, the hand-built OCR Contents is replaced by a real
``\\tableofcontents``, and a heading duplicated across a chunk boundary (MinerU
repeats the section title at the top of the next chunk) collapses to one.

The table-of-contents title is set in the document body: polyglossia
re-activates the language after the preamble and would otherwise reset
``\\contentsname`` to its English default.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

SECTIONISH = re.compile(r"^\\(section|subsection|subsubsection)\*?\{")


def chunk_key(path: Path) -> tuple[int, str]:
    m = re.match(r"(?:chunk_)?(\d+)", path.name)
    return (int(m.group(1)) if m else 999, path.name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("parts_dir")
    ap.add_argument("--output", required=True)
    ap.add_argument("--toc-title", default="目录")
    args = ap.parse_args()

    parts = sorted(Path(args.parts_dir).glob("*.tex"), key=chunk_key)
    if not parts:
        raise SystemExit(f"no chunk files under {args.parts_dir}")

    preamble = next((p for p in parts if "preamble" in p.name), None)
    if preamble is None:
        raise SystemExit("no preamble chunk found")

    body: list[str] = []
    seen_headings: set[str] = set()
    dropped: list[str] = []

    for path in parts:
        text = path.read_text()
        if path == preamble:
            body.append(text)
            continue
        if "contents" in path.name.lower():
            dropped.append(path.name)
            continue
        lines = text.split("\n")
        kept: list[str] = []
        for line in lines:
            if SECTIONISH.match(line):
                key = re.sub(r"\s+", " ", line.strip())
                if key in seen_headings:
                    continue
                seen_headings.add(key)
            kept.append(line)
        body.append("\n".join(kept))

    merged = "\n".join(body)
    marker = "\\begin{document}"
    idx = merged.find(marker)
    if idx < 0:
        raise SystemExit("no \\begin{document} in merged output")
    insert_at = idx + len(marker)
    # The preamble chunk carries the centred title block *after*
    # \begin{document}, so the table of contents must be inserted after that
    # block rather than immediately after \begin{document} — otherwise the
    # contents pages precede the title page.
    after = merged[insert_at:]
    title_end = len(after)
    for m in re.finditer(r"\\(?:section\*?|chapter)\{", after):
        title_end = m.start()
        break
    toc = (
        f"\n\n\\renewcommand{{\\contentsname}}{{{args.toc_title}}}\n"
        "\\tableofcontents\n\\clearpage\n"
    )
    merged = merged[:insert_at] + after[:title_end] + toc + after[title_end:]
    if "\\end{document}" not in merged:
        # The chunk splitter strips trailing page-marker residue and can take the
        # end-of-document line with it; restore it so XeLaTeX terminates cleanly.
        merged = merged.rstrip("\n") + "\n\n\\end{document}\n"
    Path(args.output).write_text(merged)
    print(f"merged {len(parts)} chunks -> {args.output} ({merged.count(chr(10))} lines)")
    if dropped:
        print(f"dropped at merge: {', '.join(dropped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
