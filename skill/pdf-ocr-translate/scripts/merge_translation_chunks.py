#!/usr/bin/env python3
"""Merge translated chunk files into a single main_cn.tex.

Learned from the MAI-Thinking-1 run:
- drop hand-built Contents chunks (stale English page numbers) and inject
  \\tableofcontents with \\renewcommand{\\contentsname}{目录} in the BODY
  (polyglossia re-defines \\contentsname at language activation, so a
  preamble-level renewcommand is silently lost)
- detect duplicated tail blocks (splitters can leave a shared heading at
  both ends of adjacent chunks) and keep only the first occurrence
- strip chunks flagged DROP_AT_MERGE in CHUNK_MAP.json

Usage:
  python3 merge_translation_chunks.py <parts_dir> --output main_cn.tex \
      [--toc-title 目录] [--dedupe-headings]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TOC_BLOCK = (
    "\\renewcommand{\\contentsname}{目录}\n"
    "\\tableofcontents\n"
)


def load_chunks(parts_dir: Path) -> list[tuple[str, str]]:
    """Return [(filename, text)] in chunk order, dropping DROP_AT_MERGE chunks."""
    chunks = []
    cmap = {}
    map_file = parts_dir / 'CHUNK_MAP.json'
    if map_file.exists():
        cmap = {c['chunk']: c for c in json.loads(map_file.read_text(encoding='utf-8'))}

    files = sorted(
        f for f in parts_dir.glob('*.tex')
        if re.match(r'chunk_\d+', f.name) or f.name == 'preamble.tex'
    )
    for f in files:
        if f.name in cmap and cmap[f.name].get('note') == 'DROP_AT_MERGE':
            print(f'  skip (DROP_AT_MERGE): {f.name}')
            continue
        chunks.append((f.name, f.read_text(encoding='utf-8').strip('\n')))
    return chunks


def dedupe_shared_headings(chunks: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """If a chunk's leading heading block repeats the previous chunk's tail,
    drop the duplicate from the later chunk.

    Splitters cut at heading lines; a multi-line heading or a section-intro
    paragraph can end up in both neighbours. Keep the first occurrence.
    """
    out = []
    for name, text in chunks:
        if out:
            prev = out[-1][1]
            # find the first heading line in this chunk
            lines = text.split('\n')
            head_idx = next((i for i, l in enumerate(lines)
                             if re.match(r'\s*\\(sub)*section\{', l)), None)
            if head_idx is not None:
                head_line = lines[head_idx]
                if head_line in prev:
                    # drop lines up to and including the duplicated heading
                    lines = lines[head_idx + 1:]
                    text = '\n'.join(lines).strip('\n')
                    print(f'  dedupe: dropped shared heading in {name}')
        out.append((name, text))
    return out


def merge(parts_dir: Path, output: Path, toc_title: str, dedupe: bool) -> None:
    chunks = load_chunks(parts_dir)
    if not chunks:
        raise SystemExit('no chunks found')

    # preamble is the first chunk (chunk_00_preamble.tex)
    preamble = chunks[0][1]
    body_chunks = chunks[1:]

    if dedupe:
        body_chunks = dedupe_shared_headings(body_chunks)

    # inject TOC after the title/authors — before the Abstract heading.
    # Find the abstract (or first \section*/\subsection) in chunk 01.
    toc_injected = False
    for i, (name, text) in enumerate(body_chunks):
        m = re.search(
            r'\\subsection\{(摘要|Abstract)\}\s*\\label\{[^}]*\}', text)
        if m:
            body_chunks[i] = (name, text.replace(
                m.group(0), TOC_BLOCK + '\n' + m.group(0), 1))
            toc_injected = True
            print(f'  TOC injected before Abstract in {name}')
            break
    if not toc_injected:
        print('  WARNING: no Abstract heading found; TOC not injected.'
              ' Insert manually before the first body heading.')

    body = '\n\n'.join(t for _, t in body_chunks)
    main = preamble + '\n\n' + body + '\n\n\\end{document}\n'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(main, encoding='utf-8')
    print(f'merged {len(chunks)} chunks -> {output} ({len(main.splitlines())} lines)')

    # sanity checks
    for pat, want in [
        ('\\begin{document}', 1),
        ('\\end{document}', 1),
        ('\\tableofcontents', 1),
    ]:
        got = main.count(pat)
        status = 'OK' if got == want else '<<< CHECK'
        print(f'  {pat!r}: {got} (want {want}) {status}')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('parts_dir', help='Directory with chunk_NN_*.tex files')
    ap.add_argument('--output', required=True, help='Output main_cn.tex path')
    ap.add_argument('--toc-title', default='目录', help='Contents heading text')
    ap.add_argument('--dedupe-headings', action='store_true',
                    help='Drop shared headings duplicated across adjacent chunks')
    args = ap.parse_args()

    merge(Path(args.parts_dir), Path(args.output), args.toc_title, args.dedupe_headings)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
