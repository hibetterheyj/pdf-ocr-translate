#!/usr/bin/env python3
"""Clean common OCR artifacts from MinerU/Nougat/Mathpix LaTeX output.

Fixes applied:
  1. Escaped dollar signs in math contexts: \\$...\\$ → $...$
  2. Unicode math characters → LaTeX commands (ϕ→$\\phi$, α→$\\alpha$, etc.)
  3. Invisible control characters (U+0000-U+001F except tab/newline/return)
  4. Malformed LaTeX from OCR word-break artifacts

Usage:
  python3 fix_ocr_artifacts.py main.tex           # fix in place
  python3 fix_ocr_artifacts.py input.tex -o out.tex  # write to new file
"""

import argparse
import re
import sys
from pathlib import Path


# Unicode characters commonly produced by OCR that should be LaTeX math commands
UNICODE_TO_LATEX = {
    'ϕ': r'$\phi$',       # ϕ
    'α': r'$\alpha$',     # α
    'β': r'$\beta$',      # β
    'γ': r'$\gamma$',     # γ
    'δ': r'$\delta$',     # δ
    'ε': r'$\epsilon$',   # ε
    'θ': r'$\theta$',     # θ
    'λ': r'$\lambda$',    # λ
    'μ': r'$\mu$',        # μ
    'σ': r'$\sigma$',     # σ
    'τ': r'$\tau$',       # τ
    'Δ': r'$\Delta$',     # Δ
    'Γ': r'$\Gamma$',     # Γ
    'Σ': r'$\Sigma$',     # Σ
    'Ω': r'$\Omega$',     # Ω
    '∈': r'$\in$',        # ∈
    '∉': r'$\notin$',     # ∉
    '≤': r'$\leq$',       # ≤
    '≥': r'$\geq$',       # ≥
    '≈': r'$\approx$',    # ≈
    '×': r'$\times$',     # ×
    '·': r'$\cdot$',      # ·
    '→': r'$\to$',        # →
    '←': r'$\leftarrow$', # ←
    '⊂': r'$\subset$',    # ⊂
    '⊃': r'$\supset$',    # ⊃
    'ℓ': r'$\ell$',       # ℓ
    '∞': r'$\infty$',     # ∞
    '∅': r'$\emptyset$',  # ∅
    '∀': r'$\forall$',    # ∀
    '∃': r'$\exists$',    # ∃
    '∪': r'$\cup$',       # ∪
    '∩': r'$\cap$',       # ∩
    '⊆': r'$\subseteq$',  # ⊆
    '⊇': r'$\supseteq$',  # ⊇
    '∝': r'$\propto$',    # ∝
    '∑': r'$\sum$',       # ∑
    '∏': r'$\prod$',      # ∏
    '∫': r'$\int$',       # ∫
}


def remove_control_chars(text: str) -> tuple[str, int]:
    """Remove control characters (U+0000-U+001F except tab, newline, CR).

    Returns (cleaned_text, count_removed).
    """
    count = 0
    result = []
    for ch in text:
        cp = ord(ch)
        if cp < 0x20 and cp not in (0x09, 0x0a, 0x0d):
            count += 1
            continue
        result.append(ch)
    return ''.join(result), count


def fix_escaped_dollar_math(text: str) -> tuple[str, int]:
    r"""Fix OCR artifacts where $ in math mode was escaped as \$.

    The OCR often outputs \\$...\\$ instead of $...$ for inline math.
    This breaks LaTeX because \\$ produces a literal $, and then
    underscores/carets that require math mode cause errors.

    Approach: replace \\$ with $ when the context suggests math content
    (presence of _, ^, \\mathbf, \\boldsymbol, \\pmb, \\mathbb, \\text).

    Returns (fixed_text, count_fixed).
    """
    count = 0
    # Find \$ ... \$ pairs where content looks like math
    # Pattern: \$ followed by math-looking content, ending with \$
    # Math indicators: _, ^{, \mathbf, \boldsymbol, \pmb, \mathbb, {, }
    pattern = re.compile(
        r'\\\$\s*'                    # escaped dollar open
        r'('                         # capture math content
        r'(?=[^$]*?[_^{}\\]|'        # must contain math indicator
        r'[^$]*?\\mathbf|'
        r'[^$]*?\\boldsymbol|'
        r'[^$]*?\\pmb|'
        r'[^$]*?\\mathbb|'
        r'[^$]*?\\operatorname|'
        r'[^$]*?\\mathrm|'
        r'[^$]*?\\text|'
        r'[^$]*?\\alpha|'
        r'[^$]*?\\beta|'
        r'[^$]*?\\gamma)'
        r'[^$]*?'                    # rest of math content
        r')\\?\\?\$'                 # closing escaped dollar
    )

    def replacer(m):
        nonlocal count
        content = m.group(1)
        count += 1
        return f'${content}$'

    result = pattern.sub(replacer, text)
    return result, count


def fix_unicode_math(text: str) -> tuple[str, int]:
    """Replace Unicode math characters with LaTeX commands.

    Only replaces characters NOT already inside $...$ or \\[...\\] math environments.
    """
    count = 0
    result = []
    in_math = 0  # 0 = text, 1 = inline math $, 2 = display math \[
    i = 0
    while i < len(text):
        ch = text[i]
        # Track math mode
        if ch == '\\' and i + 1 < len(text) and text[i + 1] == '[':
            in_math = 2
            result.append('\\[')
            i += 2
            continue
        if ch == '\\' and i + 1 < len(text) and text[i + 1] == ']':
            in_math = 0
            result.append('\\]')
            i += 2
            continue
        if ch == '$':
            if in_math == 0:
                in_math = 1
            elif in_math == 1:
                in_math = 0
            result.append(ch)
            i += 1
            continue

        if in_math == 0 and ch in UNICODE_TO_LATEX:
            result.append(UNICODE_TO_LATEX[ch])
            count += 1
        else:
            result.append(ch)
        i += 1

    return ''.join(result), count


def fix_ocr_text_breaks(text: str) -> str:
    """Fix OCR-produced line-break artifacts in mid-sentence.

    MinerU sometimes inserts literal newlines mid-paragraph.
    This is handled conservatively — only join lines that don't
    start with LaTeX commands or blank lines.
    """
    # For now this is a no-op; the original OCR output is preserved.
    # Future: detect and merge mid-sentence line splits inside paragraphs.
    return text


def fix_artifacts(text: str, verbose: bool = False) -> str:
    """Apply all OCR artifact fixes. Returns cleaned text."""
    total_fixes = 0

    # 1. Remove control characters
    text, n = remove_control_chars(text)
    if verbose and n:
        print(f"  Removed {n} control characters")
    total_fixes += n

    # 2. Fix escaped dollar signs
    text, n = fix_escaped_dollar_math(text)
    if verbose and n:
        print(f"  Fixed {n} escaped dollar sign pairs")
    total_fixes += n

    # 3. Replace Unicode math characters
    text, n = fix_unicode_math(text)
    if verbose and n:
        print(f"  Replaced {n} Unicode math characters")
    total_fixes += n

    # 4. Fix OCR text breaks
    text = fix_ocr_text_breaks(text)

    if verbose and total_fixes:
        print(f"  Total fixes applied: {total_fixes}")
    elif verbose:
        print("  No fixes needed")

    return text


def main():
    parser = argparse.ArgumentParser(
        description="Clean OCR artifacts from LaTeX files"
    )
    parser.add_argument('input', help='Input .tex file')
    parser.add_argument('-o', '--output', help='Output file (default: overwrite input)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show fix summary')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
        original = f.read()

    cleaned = fix_artifacts(original, verbose=args.verbose)

    output_path = args.output if args.output else args.input
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(cleaned)

    if args.verbose or args.output:
        print(f"Output: {output_path}")


if __name__ == '__main__':
    main()
