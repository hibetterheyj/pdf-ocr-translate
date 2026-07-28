#!/usr/bin/env python3
"""Normalize OCR-numbered LaTeX headings into proper hierarchy.

Fixes applied (in order):
  1. Title detection: \\section{...} at top of body → centered title block
  2. Abstract/References: \\subsection{摘要/参考文献/Abstract/References}
     → \\section*{摘要/参考文献}
  3. Numbered headings: strip OCR-merged numbers, set correct level:
        "1 Title"    → \\section{Title}
        "2.1 Title"  → \\subsection{Title}
        "2.1.1 Title"→ \\subsubsection{Title}
  4. Appendix letters: strip A-F prefix, promote to \\section, keep in label
  5. Inline bold demotion: demote unnumbered headings to bold paragraphs

Usage:
  python3 normalize_heading_levels.py main_cn.tex --write
  python3 normalize_heading_levels.py main_cn.tex --dry-run
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


# ---- Pattern matching ----

# Line-level: matches a heading command with optional label
HEADING_LINE = re.compile(
    r'^(?P<indent>\s*)'
    r'\\(?P<cmd>section|subsection|subsubsection)\*?'
    r'\{(?P<title>[^}]*)\}'
    r'(?P<tail>\s*\\label\{[^}]*\})?'
    r'(?P<rest>.*)$'
)

# Numbered prefix patterns
NUMBER_1  = re.compile(r'^(\d+)\s+(.+)')            # "1 Introduction"
NUMBER_2  = re.compile(r'^(\d+\.\d+)\s+(.+)')        # "2.1 Hybrid Attention"
NUMBER_3  = re.compile(r'^(\d+\.\d+\.\d+)\s+(.+)')   # "2.1.1 KDA"
APPENDIX  = re.compile(r'^([A-F])\s+(.+)')            # "A Contributors"

# Special section titles to promote to unnumbered \\section*
SPECIAL_SECTIONS = {
    'abstract', '摘要',
    'references', '参考文献',
}


# ---- Heading rewriters ----

class HeadingNormalizer:
    """Stateful normalizer that tracks position in document."""

    def __init__(self, inline_bold: set[str]):
        self.inline_bold = inline_bold
        self.line_count = 0           # lines processed
        self.title_handled = False    # only convert first \section→title

    def rewrite_line(self, line: str) -> str:
        self.line_count += 1
        m = HEADING_LINE.match(line.rstrip('\n'))
        if not m:
            return line

        cmd = m.group('cmd')
        title = m.group('title').strip()
        tail = (m.group('tail') or '').strip()
        indent = m.group('indent')

        # Rule 0: title detection — first \section{near top} → centered block
        if not self.title_handled and cmd == 'section' and self.line_count < 30:
            # Check if this looks like a paper title (no number prefix, longer text)
            if not re.match(r'^\d', title) and not re.match(r'^[A-F]\s', title):
                self.title_handled = True
                return self._make_title_block(title, tail, indent)

        # Rule 1: special sections → \section* (unnumbered)
        title_lower = title.lower().rstrip('.')
        if title_lower in SPECIAL_SECTIONS:
            label_part = f" {tail}" if tail else ""
            return f"{indent}\\section*{{{title}}}{label_part}\n"

        # Rule 2: appendix letter → \section with letter stripped
        m_app = APPENDIX.match(title)
        if m_app and cmd in ('subsection', 'subsubsection'):
            clean = m_app.group(2)
            label_part = f" {tail}" if tail else ""
            return f"{indent}\\section{{{clean}}}{label_part}\n"

        # Rule 3: numbered headings → promote/demote by depth
        for matcher in (NUMBER_3, NUMBER_2, NUMBER_1):
            m_num = matcher.match(title)
            if m_num:
                depth = m_num.group(1).count('.')  # 0=single, 1=doubledot, 2=triple
                target_cmd = ['section', 'subsection', 'subsubsection'][depth]
                clean_title = m_num.group(2)
                label_part = f" {tail}" if tail else ""
                if target_cmd != cmd:
                    return f"{indent}\\{target_cmd}{{{clean_title}}}{label_part}\n"
                else:
                    return f"{indent}\\{cmd}{{{clean_title}}}{label_part}\n"

        # Rule 4: inline bold demotion for unnumbered headings
        if title in self.inline_bold:
            lines = [f"{indent}\\medskip"]
            if tail:
                lines.append(f"{indent}\\phantomsection{{{tail}}}")
            lines.append(f"{indent}\\noindent\\textbf{{{title}}}")
            return "\n".join(lines) + "\n"

        return line

    @staticmethod
    def _make_title_block(title: str, tail: str, indent: str) -> str:
        """Convert a title section into a centered title block."""
        label = f"\n{indent}\\label{{{tail.split('{')[1].rstrip('}')}}}" if tail else ""
        return (
            f"{indent}\\begin{{center}}\n"
            f"{indent}{{\\LARGE {title}\\par}}\n"
            f"{indent}\\end{{center}}{label}\n"
        )


def process_file(path: Path, inline_bold: set[str], write: bool, verbose: bool) -> bool:
    original = path.read_text()
    normalizer = HeadingNormalizer(inline_bold)
    lines = original.splitlines(True)
    rewritten_lines = []
    changes = []

    for i, line in enumerate(lines):
        new_line = normalizer.rewrite_line(line)
        if new_line != line:
            old_cmd = ''
            m = HEADING_LINE.match(line.rstrip('\n'))
            if m:
                old_cmd = m.group('cmd')
            new_cmd = ''
            m2 = HEADING_LINE.match(new_line.rstrip('\n'))
            if m2:
                new_cmd = m2.group('cmd')
            elif 'begin{center}' in new_line:
                new_cmd = 'title-block'
            elif 'section*' in new_line:
                new_cmd = 'section*'
            if old_cmd or new_cmd:
                changes.append((i + 1, old_cmd, new_cmd, line.strip()[:60]))
        rewritten_lines.append(new_line)

    rewritten = ''.join(rewritten_lines)
    changed = rewritten != original

    if verbose and changes:
        print(f"\n{path.name}: {len(changes)} heading change(s)")
        for ln, old, new, preview in changes:
            arrow = '→'
            print(f"  L{ln}: \\{old} {arrow} \\{new}  [{preview}]")

    if changed and write:
        path.write_text(rewritten)

    return changed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize OCR-numbered LaTeX headings into proper hierarchy."
    )
    parser.add_argument("files", nargs="+", help="TeX or Markdown files to process")
    parser.add_argument(
        "--inline-bold",
        action="append",
        default=[],
        help="Exact heading title to demote into a bold paragraph",
    )
    parser.add_argument("--write", action="store_true", help="Write changes to disk")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show per-heading changes")
    args = parser.parse_args()

    inline_bold = set(args.inline_bold)
    changed_any = False

    for file_name in args.files:
        path = Path(file_name)
        if not path.exists():
            print(f"Warning: file not found: {file_name}", file=__import__('sys').stderr)
            continue
        changed = process_file(path, inline_bold, args.write, args.verbose or args.dry_run)
        if changed:
            status = "would change" if args.dry_run else "changed"
        else:
            status = "unchanged"
        print(f"  {path.name}: {status}")
        changed_any = changed_any or changed

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
