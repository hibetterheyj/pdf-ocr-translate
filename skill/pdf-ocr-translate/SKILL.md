---
name: pdf-ocr-translate
description: Translate OCR-produced LaTeX/Markdown papers into high-quality Chinese PDFs with source-PDF cross-checking, multi-agent chunked translation, heading normalization, high-resolution figure extraction, and reliable XeLaTeX/pandoc packaging. Use when the input comes from MinerU, Nougat, Mathpix, OCR-to-LaTeX pipelines, or other noisy PDF-to-LaTeX conversions and the user wants a polished translated PDF rather than raw OCR output.
---

# PDF OCR Translate

Orchestration layer on top of the local `pdf` skill for translating OCR-generated LaTeX/Markdown papers (from MinerU, Nougat, Mathpix) into polished Chinese PDFs.

## Before You Start: Environment Check

Before any translation work, verify the toolchain is available:

1. **XeLaTeX** — required for CJK compilation. If missing:
   ```bash
   brew install --cask basictex
   eval "$(/usr/libexec/path_helper)"
   ```
2. **LaTeX packages** — BasicTeX is minimal. Common missing packages:
   ```bash
   sudo /Library/TeX/texbin/tlmgr install ctex adjustbox multirow footmisc
   ```
   If compilation fails with "File `X.sty' not found", install the missing package with `sudo tlmgr install X`.

3. **Python with pymupdf** — for PDF text extraction and cross-validation. Use the project's Python env:
   ```bash
   env/data_env/bin/python -c "import fitz; print('pymupdf OK')"
   ```

## Translation Workflow

### 1. Inspect and Initialize

Inspect the OCR project and source PDF, then create a working copy. If the `init_translation_workspace.sh` script encounters recursion issues (target inside source), create the workspace manually:

```bash
mkdir -p <working_dir>/{parts,images}
cp <source_main.tex> <working_dir>/
ln -s <source_images_dir> <working_dir>/images
```

### 2. Clean OCR Artifacts

OCR output contains predictable noise. Run the cleanup script before translation:

```bash
python3 scripts/fix_ocr_artifacts.py <working_dir>/main.tex
```

This fixes: escaped `\$ → $` (math mode), Unicode math chars (`ϕ→$\phi$`, `α→$\alpha$`), invisible control characters, and other common MinerU/Nougat artifacts. Read [references/tooling-and-gotchas.md](references/tooling-and-gotchas.md) for the full list of OCR failure patterns.

### 3. Split into Translation Chunks

For papers longer than ~300 lines, split the document at major section boundaries. Use a Python script to extract the preamble, split the body at `\section{}` boundaries, and write each chunk to `parts/chunk_NN_description.tex`.

Reference the approach demonstrated in [example/kimi_k3_report/](example/kimi_k3_report/) — the Kimi K3 technical report (~4000 lines) was split into 9 chunks by major section, translated by 6 parallel subagents, then merged.

For the splitting, preserve:
- **Preamble** (everything before `\begin{document}`) → `parts/preamble.tex`
- **Body** → split at `\section{}`, `\subsection{}` boundaries into `parts/chunk_01_*.tex`, etc.
- **Postamble** → `\end{document}` in final position

### 4. Translate Chunks in Parallel

Launch subagents for each chunk with these instructions:
- Translate English prose to Chinese (section titles, body text, figure/table captions)
- **Preserve exactly**: all LaTeX commands, math environments (`$...$`, `\[...\]`, `\begin{equation}`), `\cite{}`, `\ref{}`, `\label{}`, `\includegraphics{}`, table environments, `\multirow`, `\multicolumn`
- **Keep in English**: model names, benchmark names, technical identifiers, citation keys, library/framework names
- Translate figure captions: `Figure X: ...` → `图 X: ...`
- Translate table captions: `Table X: ...` → `表 X: ...`
- Write each translated chunk back to its original file

Read [references/translation-policy.md](references/translation-policy.md) for full rules.

### 5. Merge and Fix Fonts

Merge all chunks (preamble + translated body parts) into a single `main_cn.tex`. Then ensure the font preamble uses macOS-compatible fallbacks:

- Add `Songti SC` and `Heiti SC` between `Noto Serif CJK SC` and `SimSun` in the CJK font chain
- macOS system fonts: Songti SC (serif), Heiti SC (sans), PingFang SC (modern) are available without additional installs
- Reference: [assets/font_preamble_snippet.tex](assets/font_preamble_snippet.tex)

### 5.5. Normalize Heading Levels

OCR output flattens all headings to `\subsection{}` with number prefixes merged into the title text. After merge, run the heading normalizer to restore proper hierarchy:

```bash
python3 scripts/normalize_heading_levels.py main_cn.tex --write -v
```

This applies five rules (in order). The number-prefix patterns accept both `1 引言` and `1. 引言` (trailing dot optional — MinerU commonly leaves the dot before the space).

**Rule 0 — Title → centered block.** The first `\section{...}` near the top of the document (no number prefix) is converted to a centered title block:
```latex
% Before:
\section{KIMI K3：开放前沿智能}

% After:
\begin{center}
{\LARGE KIMI K3：开放前沿智能\par}
\end{center}
```
**Caveat**: Rule 0 only fires within the first 30 lines of the file. With a long preamble (~100 lines) the title `\section` is out of range — convert it manually to the centered block (see the spatiotemporal example's frontmatter chunk).

**Rule 1 — Abstract / References → `\section*`.** Unnumbered special sections that should not appear in the table of contents:
- `\subsection{摘要}` / `\subsection{Abstract}` → `\section*{摘要}`
- `\subsection{参考文献}` / `\subsection{References}` → `\section*{参考文献}`

**Rule 2 — Numbered headings → correct level.** Strip the OCR-merged number prefix and promote/demote by depth:
| OCR Input | Correct Output |
|---|---|
| `\subsection{1 引言}` | `\section{引言}` |
| `\subsection{2.1 Hybrid Attention}` | `\subsection{Hybrid Attention}` |
| `\subsection{2.1.1 KDA}` | `\subsubsection{KDA}` |

The depth is determined by the count of dots in the prefix: single digit → section, digit.digit → subsection, digit.digit.digit → subsubsection.

**Rule 3 — Appendix letters → `\section`.** Strip the A-F prefix but preserve the appendix letter in the `\label{}` for ordering:
```latex
% Before:
\subsection{A 贡献者名单}\label{a-contributions}

% After:
\section{贡献者名单}\label{a-contributions}
```

**Rule 4 — Inline bold demotion.** Specific unnumbered headings can be demoted to bold inline text (pass with `--inline-bold "标题文本"`). This is used for section summaries that shouldn't be numbered.

Run the normalizer on both `main_cn.tex` and all `parts/*.tex` for consistency. If the document has a hand-built Contents (enumerate TOC from OCR), replace it with `\tableofcontents` — the OCR copy carries the English-version page numbers and will mislead. Put `\renewcommand{\contentsname}{目录}` **in the document body** right before `\tableofcontents`: `polyglossia` re-defines `\contentsname` at language activation, so a preamble-level renewcommand is silently lost. Reference the DeepSeek V4, Kimi K3, and spatiotemporal composability examples in `example/` for the expected output pattern.

### 6. Cross-Validate Against Source PDF

Use pymupdf to extract text from the source PDF and verify key facts survived translation:

```python
import fitz
doc = fitz.open("source.pdf")
for page in doc:
    text = page.get_text('text')
    # Compare key numbers, technical claims with translated output
```

Focus verification on: numerical values, model sizes, benchmark scores, citation keys. This catches OCR errors that would otherwise go unnoticed. See [references/workflow.md](references/workflow.md) for the full approach.

**Missing-glyph sweep**: after the first clean compile, grep the log for `Missing character`. MinerU frequently leaves raw Unicode math in prose (`⋄`, `≃`, `∎`, `⊥`, `⌀`, `▷`, `↦`, `∘`, `•`, `‣`). Fix with a stateful text/math-mode tracker that wraps each occurrence in `$\diamond$`, `$\simeq$`, `$\bot$`, `$\emptyset$`, `$\triangleright$`, `$\mapsto$`, `$\circ$` etc. — a naive global regex replace corrupts surrounding CJK text.

### 7. Compile

Compile natively with XeLaTeX (required for CJK + ctex):

```bash
xelatex -interaction=nonstopmode main_cn.tex
xelatex -interaction=nonstopmode main_cn.tex  # second pass for cross-refs
xelatex -interaction=nonstopmode main_cn.tex  # third pass for TOC
```

**Troubleshooting compilation errors:**
- `File 'X.sty' not found` → `sudo tlmgr install X`
- `I can't find file 'SimSun'` → Update font fallback chain (add macOS fonts)
- `Missing $ inserted` / `Missing number` → Run `fix_ocr_artifacts.py` again on the merged file; these come from OCR artifacts that survived translation
- `Text line contains an invalid character` → Control characters in OCR output; run cleanup script
- `Missing character: There is no X` → Raw Unicode math left in prose; wrap in math mode (see step 6)
- Non-zero errors with `-halt-on-error` are expected (OCR artifacts); use `-interaction=nonstopmode` to power through. Zero-error compiles are achievable — see the spatiotemporal example

If the user explicitly requires a pandoc-generated artifact, wrap the already-compiled native PDF:
```bash
scripts/compile_pdf.sh path/to/main_cn.tex path/to/output_pandoc.pdf
```

### 8. Verify Output

- Open the compiled PDF and spot-check random sections
- Verify tables rendered correctly (longtables are fragile in OCR output)
- Check that figure captions are translated and images are visible
- Confirm citation keys are intact

## Reference Files

Read only when needed:

- **[references/workflow.md](references/workflow.md)** — Full end-to-end flow with subagent chunking strategy and cross-validation
- **[references/translation-policy.md](references/translation-policy.md)** — What to translate, what to preserve, heading mapping rules
- **[references/tooling-and-gotchas.md](references/tooling-and-gotchas.md)** — Compilation troubleshooting, font pitfalls, OCR failure patterns, figure extraction
- **[references/example-session.md](references/example-session.md)** — Concrete paths and commands from a successful DeepSeek V4 run

## Scripts

- **`scripts/fix_ocr_artifacts.py`** — Clean common OCR artifacts: escaped `\$`, Unicode math chars, control characters
- **`scripts/init_translation_workspace.sh`** — Create working copy with `parts/` and `images_hi/`
- **`scripts/normalize_heading_levels.py`** — Convert OCR-numbered headings to proper LaTeX section commands
- **`scripts/check_latex_translation.py`** — Scan for untranslated prose, bad escapes, OCR placeholders, unnormalized headings
- **`scripts/extract_hd_figures.py`** — Render high-DPI figure pages from source PDF
- **`scripts/build_pandoc_wrapper.py`** — Create minimal pandoc wrapper using `pdfpages`
- **`scripts/compile_pdf.sh`** — Compile native LaTeX, optionally emit pandoc PDF wrapper

## Assets

- **[assets/pandoc_wrapper.template.md](assets/pandoc_wrapper.template.md)** — Minimal pandoc wrapper template
- **[assets/font_preamble_snippet.tex](assets/font_preamble_snippet.tex)** — CJK-safe XeLaTeX font setup with macOS fallbacks
- **[assets/heading_examples.tex](assets/heading_examples.tex)** — Heading normalization and inline-bold demotion examples
- **[assets/deepseek_v4_paper_template/](assets/deepseek_v4_paper_template)** — Copyable modular starter project for OCR-LaTeX translation

## Example

See **[example/kimi_k3_report/](example/kimi_k3_report/)** for a complete worked example: the Kimi K3 technical report (~4000 lines OCR LaTeX) translated to Chinese, compiled to a 65-page PDF. Includes the split chunks, merged `main_cn.tex`, and compiled PDF.

See **[example/spatiotemporal_composability_report/](example/spatiotemporal_composability_report/)** for a formal-methods paper (6570 lines, heavy math): 17 chunks, ~900 OCR `�` symbols reconstructed from the source PDF, zero-error compilation. Demonstrates: repeated-letter OCR drops ("efects"→"effects"), per-page PDF text as cross-validation reference, hand-built TOC replacement, and the missing-glyph sweep.
