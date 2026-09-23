#!/usr/bin/env python3
"""Merge the translated chunks into `main_cn.tex`.

Three things the bundled merger does not do for this project:

  * **Chunk ordering.** `split_translation_chunks.py` names its output
    `chunk_00_preamble.tex` plus `NN_<name>.tex`, so a plain lexical sort puts
    `01_body.tex` first and `chunk_00_preamble.tex` last.  (The bundled merger
    filters on `chunk_\\d+` instead, which drops every body chunk — worth fixing
    there, but this pipeline should not depend on it.)  Chunks are sorted by
    their leading number here.
  * **Table of contents placement.** The TOC goes after the centred title block
    and before the Abstract, not straight after `\\begin{document}` — otherwise
    it lands in front of the title page.  `\\renewcommand{\\contentsname}{目录}`
    travels with it, because polyglossia re-activates the language and resets
    the name, so a preamble-level setting is silently lost.
  * **`\\end{document}`.** The splitter slices the body out of the original file,
    so the closing command is re-added here.

Usage:  merge_chunks.py --parts parts --output main_cn.tex
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

TOC_BLOCK = (
    "\\renewcommand{\\contentsname}{目录}\n"
    "\\tableofcontents\n"
    "\\clearpage\n"
)

# The splitter keeps `\subsection{Abstract}` as the preamble chunk's last line.
ABSTRACT = re.compile(r"\\subsection\{(?:Abstract|摘要)\}\s*\\label\{[^}]*\}")


def order_key(path: Path) -> int:
    m = re.match(r"(?:chunk_)?(\d+)", path.name)
    return int(m.group(1)) if m else 10**6


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", default="parts")
    ap.add_argument("--output", default="main_cn.tex")
    args = ap.parse_args()

    parts = Path(args.parts)
    files = sorted((p for p in parts.glob("*.tex")), key=order_key)
    if not files:
        raise SystemExit(f"no chunks in {parts}")

    chunks = [f.read_text(encoding="utf-8").strip("\n") for f in files]
    head, body = chunks[0], chunks[1:]

    # Inject the TOC where the Abstract heading sits, i.e. right after the title
    # block that closes the preamble chunk.
    if ABSTRACT.search(head):
        head = ABSTRACT.sub(lambda m: TOC_BLOCK + "\n" + m.group(0), head, count=1)
        toc_where = "preamble chunk, before Abstract"
    else:
        raise SystemExit("Abstract heading not found in the preamble chunk — "
                         "cannot place the table of contents safely")

    text = "\n\n".join([head] + body) + "\n\n\\end{document}\n"
    Path(args.output).write_text(text, encoding="utf-8")

    print(f"merged {len(files)} chunks -> {args.output} "
          f"({len(text.splitlines())} lines); TOC in {toc_where}")
    for pat, want in [("\\begin{document}", 1), ("\\end{document}", 1),
                      ("\\tableofcontents", 1), ("\\contentsname", 1)]:
        got = text.count(pat)
        print(f"  {pat!r}: {got} (want {want})"
              + ("" if got == want else "   <<< CHECK"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
