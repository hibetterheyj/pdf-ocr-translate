#!/usr/bin/env python3
"""Split OCR LaTeX into translation chunks at heading boundaries.

Learned from the MAI-Thinking-1 run (7495 lines, 27 chunks):
- page-marker footer lines (standalone ints flanked by blank lines) are removed
- long sections (>~700 lines) are sub-split at the nearest sub-heading
- a chunk map (file -> source PDF page range) is written as JSON for
  cross-validation (translators receive the page-range text files)
- multi-line headings stay intact; the normalizer/translators collapse them later

Usage:
  python3 split_chunks.py <main.tex> --output-dir parts/ \
      [--max-lines 700] [--pdf-pages-dir pdf_pages/] [--refs-chunk-lines 500]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HEADING = re.compile(r'\\(sub)*section\s*\{')

# headings that should be excluded from chunk-body translation
# (hand-built Contents carries stale English page numbers; replace with \\tableofcontents at merge)
DEFAULT_DROP_MARKERS = ('contents',)


def is_page_marker(lines: list[str], i: int) -> bool:
    """Standalone 1-3 digit line flanked by blank lines (page footer residue)."""
    if not (0 < i < len(lines) - 1):
        return False
    s = lines[i].strip()
    return bool(re.fullmatch(r'\d{1,3}', s)) and lines[i - 1].strip() == '' and lines[i + 1].strip() == ''


def remove_page_markers(lines: list[str]) -> tuple[list[str], list[tuple[int, int]]]:
    """Blank out page-marker lines; return (cleaned, [(line_idx, page_num), ...])."""
    out = list(lines)
    markers = [(i, int(lines[i].strip())) for i in range(len(lines)) if is_page_marker(lines, i)]
    for i, _ in markers:
        out[i] = ''
    return out, markers


def find_heading(lines: list[str], start: int, end: int, prefix: str) -> int | None:
    """Find a heading line matching `\\...section{<prefix>` in [start, end)."""
    for i in range(start, end):
        if re.search(r'\\subsection\{' + re.escape(prefix), lines[i]):
            return i
    return None


def heading_at(lines: list[str], i: int) -> bool:
    return bool(HEADING.search(lines[i]))


def compute_cuts(lines: list[str], body_start: int, body_end: int,
                 max_lines: int, min_lines: int = 150,
                 refs_chunk_lines: int = 500) -> list[int]:
    """Cut points at heading boundaries.

    - adjacent small sections are merged until they reach ~min_lines
    - oversized sections are sub-split at the nearest sub-heading
    - heading-free text (e.g. a plain References list) is sliced at paragraph
      boundaries (blank lines) into refs_chunk_lines-sized pieces
    """
    headings = [body_start] + [i for i in range(body_start + 1, body_end)
                               if heading_at(lines, i)]
    # merge small sections greedily (prefer absorbing the following section)
    cuts = [headings[0]]
    for h in headings[1:]:
        prev = cuts[-1]
        size = h - prev
        # look ahead: if current segment is small and next heading exists,
        # skip this cut (absorb into previous segment)
        nxt = headings[headings.index(h) + 1] if headings.index(h) + 1 < len(headings) else body_end
        if size < min_lines and (nxt - prev) <= max_lines:
            continue
        cuts.append(h)
    # sub-split oversized segments
    final = []
    for s, e in zip(cuts, cuts[1:] + [body_end]):
        if e - s <= max_lines:
            final.append(s)
            continue
        # no heading beyond the segment's own first line (e.g. a plain
        # References list): slice at blank-line paragraph boundaries
        inner_headings = [i for i in range(s + 1, e) if heading_at(lines, i)]
        if not inner_headings:
            for i in range(s + refs_chunk_lines, e, refs_chunk_lines):
                while i < e and lines[i].strip() != '':
                    i += 1
                if i < e:
                    final.append(s)
                    s = i + 1
            final.append(s)
            continue
        # find nearest heading after midpoint
        mid = s + (e - s) // 2
        k = mid
        while k < e and not heading_at(lines, k):
            k += 1
        if k < e and k > s:
            final.append(s)
            # recurse on the rest
            rest = compute_cuts(lines, k, e, max_lines, min_lines, refs_chunk_lines)
            final.extend(rest)
        else:
            final.append(s)
    return final


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('main_tex', help='OCR LaTeX main file')
    ap.add_argument('--output-dir', required=True, help='Directory for chunk files')
    ap.add_argument('--max-lines', type=int, default=700)
    ap.add_argument('--pdf-pages-dir', help='Directory of page_NNN.txt files (for chunk page mapping)')
    ap.add_argument('--refs-chunk-lines', type=int, default=500,
                    help='Chunk size for a plain-text References list')
    ap.add_argument('--drop-markers', nargs='*', default=list(DEFAULT_DROP_MARKERS),
                    help='Heading substrings whose chunk is dropped at merge time')
    args = ap.parse_args()

    src = Path(args.main_tex)
    lines = src.read_text(encoding='utf-8').split('\n')

    lines, markers = remove_page_markers(lines)
    print(f'removed {len(markers)} page-marker lines')

    # document boundaries
    doc_start = lines.index('\\begin{document}') if '\\begin{document}' in lines else 0
    doc_end = lines.index('\\end{document}') if '\\end{document}' in lines else len(lines)

    # first heading after \begin{document} starts the title block; everything
    # before it (incl. stray decorations) belongs to the preamble chunk
    first_head = doc_start
    while first_head < doc_end and not heading_at(lines, first_head):
        first_head += 1

    # multi-line title headings: extend past the heading line until the
    # closing brace + \label; keep the whole title block in the preamble chunk
    body_start = first_head + 1
    while body_start < doc_end and '}' + chr(92) + 'label' not in lines[body_start - 1]:
        body_start += 1

    cuts = compute_cuts(lines, body_start, doc_end, args.max_lines)

    chunks = []
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # chunk 00: preamble + \begin{document} + title heading
    chunk_map = []
    names = []

    def chunk_name(idx: int, start: int) -> str:
        for i in range(start, min(start + 3, len(lines))):
            m = re.search(r'\\(?:sub)*section\{([^}]*)\}', lines[i])
            if m:
                t = re.sub(r'[^\w一-鿿-]', '_', m.group(1).strip().lower())[:28]
                return f'{idx:02d}_{t}'
        return f'{idx:02d}_body'

    # preamble chunk
    pre = lines[:body_start]
    (out_dir / 'chunk_00_preamble.tex').write_text('\n'.join(pre).strip('\n') + '\n', encoding='utf-8')
    chunk_map.append({'chunk': 'chunk_00_preamble.tex', 'lines': len(pre), 'pages': '-'})
    names.append('chunk_00_preamble.tex')

    idx = 1
    for s, e in zip(cuts, cuts[1:] + [doc_end]):
        name = chunk_name(idx, s) + '.tex'
        seg = lines[s:e]
        # drop-marker chunks: keep file for reference but flag for merge skip
        drop = any(m in lines[s].lower() for m in args.drop_markers)
        (out_dir / name).write_text('\n'.join(seg).strip('\n') + '\n', encoding='utf-8')
        chunk_map.append({'chunk': name, 'lines': len(seg), 'pages': '-',
                          'note': 'DROP_AT_MERGE' if drop else ''})
        names.append(name)
        idx += 1

    # page ranges: map page markers inside each chunk's original line span
    if args.pdf_pages_dir:
        page_of = {i: n for i, n in markers}
        spans = [(0, body_start)] + [(s, e) for s, e in zip(cuts, cuts[1:] + [doc_end])]
        for entry, (s, e) in zip(chunk_map, spans):
            pages = sorted({page_of[i] for i in range(s, e) if i in page_of})
            if pages:
                entry['pages'] = f'{pages[0]}-{pages[-1]}'

    (out_dir / 'CHUNK_MAP.json').write_text(
        json.dumps(chunk_map, indent=2, ensure_ascii=False), encoding='utf-8')

    for e in chunk_map:
        print(f"  {e['chunk']:32s} lines {e['lines']:5d} pages {e['pages']:>8s} {e.get('note', '')}")
    print(f'wrote {len(chunk_map)} chunks to {out_dir}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
