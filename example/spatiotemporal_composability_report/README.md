# A Programming Paradigm for Spatiotemporal Composability — Chinese Translation Example

Complete worked example of the `pdf-ocr-translate` skill workflow on a formal-methods / programming-languages paper (Peking University / DeepSeek-AI).

## Source

- **Original PDF**: `Spatiotemporal_Composability.pdf` (88 pages)
- **OCR LaTeX**: MinerU output, 6570 lines, 91 images
- **Source**: arxiv-style preprint (PKU / DeepSeek-AI)

## Translation Stats

| Metric | Value |
|--------|-------|
| Source lines | 6,570 |
| Chunks | 17 (split at section/subsection boundaries) |
| Parallel agents | 16 (two waves: 10 + 6) |
| U+FFFD replacement chars fixed | ~900 (reconstructed from source PDF) |
| Final PDF pages | 80 |
| Compilation errors | 0 (after cleanup) |
| Font | Songti SC (macOS fallback) |

## File Structure

```
spatiotemporal_composability_report/
├── Spatiotemporal_Composability.pdf       # Original English PDF (88 pages)
├── Spatiotemporal_Composability_CN.pdf    # Translated Chinese PDF (80 pages)
├── ocr_latex/                             # OCR source from MinerU
│   └── MinerU_latex_*.tex                 # Original 6570-line OCR output
├── pdf_pages/                             # Per-page text extracted from source PDF (88 files)
│   └── page_001.txt ... page_088.txt      # Cross-validation reference for translators
└── translate_latex/                       # Translated LaTeX project
    ├── main_cn.tex                        # Merged translated LaTeX (3316 lines)
    ├── normalize_heading_levels.py        # Patched normalizer (trailing-dot prefixes)
    ├── images/                            # Symlink to OCR images (91 files)
    └── parts/                             # 17 translation chunks
        ├── chunk_00_preamble.tex
        ├── chunk_01_frontmatter.tex       # title/authors/abstract/contents
        ├── chunk_02_intro.tex             # Section 1
        ├── chunk_03_preliminaries.tex     # Section 2
        ├── chunk_04_revertible_effects.tex    # Section 3.1
        ├── chunk_05_reactive_coeffects.tex    # Section 3.2
        ├── chunk_06_context_paradigm.tex      # Section 3.3
        ├── chunk_07_components_base.tex       # Section 4.1–4.2
        ├── chunk_08_transitions.tex           # Section 4.3
        ├── chunk_09_metatheory_a.tex          # Section 4.4 intro + 4.4.1
        ├── chunk_10_metatheory_b.tex          # Section 4.4.2–4.4.3
        ├── chunk_11_metatheory_c.tex          # Section 4.4.4–4.4.5
        ├── chunk_12_impl_a.tex                # Section 5.1
        ├── chunk_13_impl_b.tex                # Section 5.2–5.3
        ├── chunk_14_discussion.tex            # Section 6
        ├── chunk_15_related_work.tex          # Section 7
        └── chunk_16_conclusion_refs.tex       # Section 8 + References
```

## Key Findings (this case)

1. **OCR drops repeated letters**: the paper consistently uses "effect/coeffect" (double-f) but MinerU output "efect/coefect" everywhere. Cross-validation against the source PDF caught this systematically — fix in translation, keep `\label{}` keys as-is (they are internal anchors).
2. **U+FFFD replacement chars are the #1 hazard**: ~900 occurrences where MinerU failed to recognize math symbols (ℭ, 𝔇, 𝔓, 𝔈, Γ, π, σ, τ, θ). The source PDF text (pymupdf extraction) preserves these as Unicode math; translators reconstruct proper LaTeX from it. Heaviest density in the metatheory proofs (chunk 11 alone had 305).
3. **Zero-error compilation is achievable**: unlike earlier examples (Kimi K3: 25 non-fatal errors), this case compiled with 0 errors and 0 missing glyphs after (a) cleaning all `�`, (b) converting stray Unicode math in prose (⋄, ≃, ∎, ⊥, ⌀, ▷, ↦, ∘) into math mode with a stateful text/math-mode tracker, (c) fixing CJK fonts for macOS.
4. **Normalizer regexes need trailing-dot support**: OCR headings come as `\subsection{4.1. 组件与纤维}` (dot before space); the stock `normalize_heading_levels.py` patterns (`^(\d+)\s+`) don't match. The patched copy in `translate_latex/` uses `^(\d+)\.?\s+` variants.
5. **Title rule needs line-count tolerance**: the stock normalizer only converts the title `\section` within the first 30 lines; with a ~100-line preamble the title must be converted manually to a `\begin{center}{\LARGE ...}` block.
6. **Hand-built TOC has stale page numbers**: the OCR Contents enumerate carries English-version page numbers; replace with `\tableofcontents` + `\renewcommand{\contentsname}{目录}` placed **in the document body** (polyglossia re-defines `\contentsname` at language activation, so a preamble renewcommand is lost).
7. **`\pandocbounded` figures work as-is**: MinerU wraps images in `\pandocbounded{\includegraphics...}`; the preamble already defines the macro, keep it untouched.

## Notes

- The translated chunk files contain only the translated LaTeX (no intermediate English version is kept).
- Compile with 3 passes: `xelatex -interaction=nonstopmode main_cn.tex` ×3 (TOC + cross-references).
- In-text citation numbers `{[}1{]}` and the 124-entry bibliography are verified to match the source PDF.
