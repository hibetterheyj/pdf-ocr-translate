# Tooling and Gotchas

## Use the Neighboring PDF Skill

This skill should not duplicate generic PDF extraction advice. Reuse the local `pdf` skill for:

- text extraction,
- table extraction,
- OCR fallbacks,
- basic PDF manipulation.

This skill adds the OCR-LaTeX translation workflow on top.

## Compilation Environment

### XeLaTeX Installation

macOS: `brew install --cask basictex` (~140MB download). After install, refresh PATH:
```bash
eval "$(/usr/libexec/path_helper)"
```

### Required LaTeX Packages

BasicTeX is minimal. Install commonly needed packages:
```bash
sudo /Library/TeX/texbin/tlmgr install ctex adjustbox multirow footmisc
```

If compilation fails with `File 'X.sty' not found`:
```bash
kpsewhich X.sty           # check if installed
sudo tlmgr install X       # install missing package
```

Common missing packages for OCR papers: `ctex`, `adjustbox`, `multirow`, `footmisc`, `mhchem`, `ucharclasses`, `stmaryrd`, `bbold`, `setspace`, `parskip`, `calc`.

**Note**: Some packages (`calc`, `longtable`, `tabularx`, `booktabs`) are bundled in the `tools` collection and come with BasicTeX. The `tlmgr` won't find them as standalone packages.

### Check Before Compiling

First check which packages are missing to avoid iterative install loops:
```bash
for pkg in ctex multirow adjustbox footmisc; do
  if kpsewhich ${pkg}.sty > /dev/null 2>&1; then
    echo "OK: $pkg"
  else
    echo "MISSING: $pkg"
  fi
done
```

## Prefer Native LaTeX Compilation

Complex OCR-derived LaTeX often contains:

- custom pandoc macros,
- fragile longtables,
- OCR noise in math,
- custom font logic,
- mixed English/CJK content.

Direct `pandoc input.tex -o out.pdf` **requires a PDF engine** (xelatex/pdflatex/etc.) — pandoc alone only converts formats. The file's first line comment (`% This LaTeX document needs to be compiled with XeLaTeX.`) tells you which engine to use.

Recommended order:

1. Compile native TeX with `latexmk -xelatex` if available.
2. Fall back to repeated `xelatex -interaction=nonstopmode` runs (3 passes: content → cross-refs → TOC).
3. If the user explicitly needs a pandoc-generated artifact, wrap the already compiled native PDF using `pdfpages`.

**Expect errors on first pass.** OCR-derived LaTeX typically has 20-50 compilation errors. Use `-interaction=nonstopmode` (not `-halt-on-error`) to skip past them. Most errors are cosmetic and don't affect readability.

## Font Snippet

If CJK font loading fails, start from [assets/font_preamble_snippet.tex](../assets/font_preamble_snippet.tex).

Key lessons from real runs:

- `\usepackage[fontset=none]{ctex}` is safer than relying on ctex defaults.
- Explicitly set `\setCJKmainfont` and `\setmainfont`.
- **macOS system fonts** (available without install): PingFang SC, Songti SC (宋体), Heiti SC (黑体), Kaiti SC (楷体).
- **Windows fonts NOT on macOS**: SimSun, FangSong. Always include macOS fallbacks before these.
- Use multiple fallbacks, for example:
  - `Source Han Serif CN` (best quality, may need install)
  - `Noto Serif CJK SC` (open-source)
  - `PingFang SC` (macOS system)
  - `Songti SC` (macOS serif, good for body text)
  - `Heiti SC` (macOS sans-serif, good for headings)
  - `SimSun` (Windows only)
  - `FangSong` (Windows only)
  - `Arial Unicode MS` (last resort)

## OCR Artifact Cleanup

MinerU/Nougat/Mathpix output has predictable noise. Run `scripts/fix_ocr_artifacts.py` before translation and again on the merged file before compilation.

### Hand-Built TOC Replacement

OCR papers carry a hand-built Contents (an `enumerate` with dotted leaders and the **English-version page numbers**). Those page numbers are wrong in the translated PDF. Replace with:

```latex
\renewcommand{\contentsname}{目录}
\tableofcontents
```

Placed **in the document body** (before the first `\section`). A preamble-level `\renewcommand{\contentsname}` is silently lost because `polyglossia` re-defines `\contentsname` when the document language activates. Bonus: `\tableofcontents` also keeps TOC titles consistent with the actual headings (the OCR TOC often abbreviates or diverges from heading text).

### Common OCR Failures

- **Repeated-letter drops**: MinerU sometimes drops doubled letters consistently (observed: "effects/coeffects" → "efects/coefects" throughout a 6570-line paper). Cross-check one occurrence against the source PDF text; if systematic, fix globally in translation. `\label{}` keys keep the OCR spelling — they are internal anchors and renaming them would break `\ref{}`.
- **Escaped dollar signs**: `\$ \{ \boldsymbol { z } \} \_ \{ t \} \$` → should be `$\{ \boldsymbol { z } \} _ { t }$`. The `\$` produces a literal `$` in text mode, but the content needs math mode. This is the #1 source of `Missing $ inserted` errors.
- **Unicode math chars**: ϕ (U+03D5), α (U+03B1), β (U+03B2), ∈ (U+2208), × (U+00D7) appearing outside math mode. XeLaTeX can't render these in text fonts.
- **U+FFFD replacement chars (`�`)**: the worst failure mode on math-heavy papers — up to several hundred occurrences where OCR failed on a symbol (observed 900+ in a PL-style paper, ~305 in one proof-heavy chunk alone). The source PDF text (pymupdf) preserves the symbols as Unicode math; reconstruct LaTeX from it during translation. Budget for this in chunk sizing.
- **Control characters**: U+0001 (SOH), U+0016 (SYN) from OCR processing artifacts. Cause "invalid character" errors.
- **section titles encoded as** `\section{2.3.4. ...}` (note: the number prefix may keep its trailing dot — normalizer accepts both)
- **literal `??` placeholders** from failed OCR recognition
- **malformed math delimiters** such as `\$ ... \$` or unbalanced `$`
- **literal escaped newlines** inside prose prompts
- **special symbols replaced** by missing glyphs or invisible control characters
- **source PDF screenshots** exported as tiny low-resolution OCR images

### After Translation: Residual Errors

Some errors survive OCR cleanup + translation. Common post-translation errors:
- `\setcounter{enumi}{...}` without prior `\begin{enumerate}` — from OCR misreading of figure labels
- Unicode characters re-introduced during translation — re-run `fix_ocr_artifacts.py`
- `\mathbb{1}` requiring `bbold` package — replace with `\mathbf{1}` or ensure `bbold` installed

## Figure Extraction Heuristics

Use `pdfimages -list` first (requires poppler: `brew install poppler`).

- If the source PDF has large embedded JPEG/PNG assets on the relevant page, extract them directly with `pdfimages`.
- If the figure is mostly vector charts or OCR split it into many tiny fragments, render the full page at high DPI with `pdftocairo` and crop the panel you need.

Example commands:

```bash
pdfimages -list source.pdf
python3 scripts/extract_hd_figures.py --pdf source.pdf --output-dir images_hi --pdfimages-pages 43,56
python3 scripts/extract_hd_figures.py --pdf source.pdf --output-dir images_hi --render-pages 1 --crop page=1,x=520,y=3900,w=3900,h=2050,name=Figure1_hi.png
```

## Cross-Validation with Source PDF

Use pymupdf (fitz) to extract text from the source PDF for fact verification:

```python
import fitz
doc = fitz.open("source.pdf")
for page in doc:
    text = page.get_text('text')
# Compare key facts against translated output
```

Verify: numerical values (parameter counts, percentages, scores), model names, benchmark results, citation keys. This catches OCR errors that silently corrupt data — e.g., "2.5×" becoming "2.5 倍" is fine, but "104B" becoming "10.4B" is a critical error.

**Practical pattern from the spatiotemporal example**: save per-page text to `pdf_pages/page_NNN.txt` at setup time, and hand each translation subagent its section's page-range files alongside the chunk. This makes the authoritative reference cheap for agents to consult for every `�` reconstruction and every number check.

## Missing-Glyph Sweep (post-compile)

After the first compile that produces a PDF, grep the log:

```bash
grep 'Missing character' compile.log | sort -u
```

This finds raw Unicode math left in prose (not in math mode). Common offenders from MinerU + translation:

| Char | Meaning | Replacement |
|------|---------|-------------|
| `⋄` (U+22C4) | effect composition | `$\diamond$` |
| `≃` (U+2243) | approx-equal / equivalence | `$\simeq$` |
| `∎` (U+220E) | QED | `$\blacksquare$` |
| `∘` (U+2218) | function composition | `$\circ$` |
| `⊥` (U+22A5) | bottom | `$\bot$` |
| `⌀` (U+2300) | empty set | `$\emptyset$` |
| `▷` (U+25B7) | lookup/action operator | `$\triangleright$` |
| `↦` (U+21A6) | maplet | `$\mapsto$` |
| `•` (U+2022) / `‣` (U+2023) | bullets | keep as text bullets (or `\item`) |

**Fix with a stateful text/math-mode tracker**, not a global regex: walk the file tracking `\(...\)`, `\[...\]`, `$...$`, and `\begin{math-env}`; replace each occurrence only when outside math. A naive loop that collects match positions on the original string and then writes into a mutating string corrupts the text (positions go stale once a replacement changes string length — observed replacement of CJK glyphs adjacent to the target char). Either iterate once building a new string, or replace from the end backwards.

## Packaging Strategy

When the user says "use pandoc", clarify whether they mean:

- "compile the final PDF somehow", or
- "the final artifact must be produced by pandoc".

Pandoc alone cannot produce PDF — it delegates to a PDF engine (`--pdf-engine=xelatex`). If the second requirement is strict, use the wrapper approach. That preserves the native XeLaTeX result while still producing a pandoc-authored PDF container.
