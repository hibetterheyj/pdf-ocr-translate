#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


HEADING_RE = re.compile(
    r'^(?P<indent>\s*)\\(?P<cmd>section|subsection|subsubsection)\{(?P<title>[^}]*)\}(?P<tail>.*)$'
)
NUMBERED_RE = re.compile(
    r'^(?P<prefix>(?:[0-9]+|[A-Z])(?:\.(?:[0-9]+|[A-Z]))*\.?)\s*(?P<rest>\S.*)$'
)


def target_command(prefix: str) -> str:
    parts = prefix.strip(".").split(".")
    depth = len(parts)
    if depth <= 1:
        return "section"
    if depth == 2:
        return "subsection"
    return "subsubsection"


def normalize_title(title: str) -> tuple[str, str] | None:
    m = NUMBERED_RE.match(title.strip())
    if not m:
        return None
    return target_command(m.group("prefix")), m.group("rest").strip()


def rewrite_line(line: str, inline_bold: set[str]) -> str:
    m = HEADING_RE.match(line.rstrip("\n"))
    if not m:
        return line

    title = m.group("title").strip()
    tail = m.group("tail").strip()
    indent = m.group("indent")

    normalized = normalize_title(title)
    if normalized:
        cmd, clean_title = normalized
        tail_part = f"{tail}" if tail else ""
        return f"{indent}\\{cmd}{{{clean_title}}}{tail_part}\n"

    if title in inline_bold:
        label_part = tail if tail else ""
        lines = [f"{indent}\\medskip"]
        if label_part:
            lines.append(f"{indent}\\phantomsection{label_part}")
        lines.append(f"{indent}\\noindent\\textbf{{{title}}}")
        return "\n".join(lines) + "\n"

    return line


def process_file(path: Path, inline_bold: set[str], write: bool) -> bool:
    original = path.read_text()
    rewritten = "".join(rewrite_line(line, inline_bold) for line in original.splitlines(True))
    changed = rewritten != original
    if changed and write:
        path.write_text(rewritten)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize OCR-numbered LaTeX headings.")
    parser.add_argument("files", nargs="+", help="TeX or Markdown files to rewrite")
    parser.add_argument(
        "--inline-bold",
        action="append",
        default=[],
        help="Exact heading title to demote from a section command into an inline bold heading",
    )
    parser.add_argument("--write", action="store_true", help="Write changes back to disk")
    args = parser.parse_args()

    inline_bold = set(args.inline_bold)
    changed_any = False
    for file_name in args.files:
        path = Path(file_name)
        changed = process_file(path, inline_bold, args.write)
        print(f"{path}: {'changed' if changed else 'unchanged'}")
        changed_any = changed_any or changed
    return 0 if changed_any or args.write else 0


if __name__ == "__main__":
    raise SystemExit(main())
