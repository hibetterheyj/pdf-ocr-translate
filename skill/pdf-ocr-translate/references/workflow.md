# OCR LaTeX Translation Workflow

Use this workflow when the user has a source PDF plus OCR-generated LaTeX or Markdown and wants a polished translated PDF.

## Inputs

- Source PDF: the authoritative visual and textual reference.
- OCR project: LaTeX, Markdown, or a mixed OCR directory such as MinerU / Nougat / Mathpix output.
- Figure directory: usually extracted low-resolution images from OCR.
- Translation scope: what to translate and what to preserve.

## End-to-End Flow

### 1. Environment Check

Verify XeLaTeX is installed, required LaTeX packages are available, and Python has pymupdf. See [tooling-and-gotchas.md](tooling-and-gotchas.md) for the checklist.

### 2. Inspect and Initialize

Inspect the OCR project and identify the main `.tex` or `.md` entrypoint. Initialize a separate working copy:

```bash
scripts/init_translation_workspace.sh <ocr_project_dir> <working_dir>
```

If the script reports a recursion error (output under source), create manually:
```bash
mkdir -p <working_dir>/{parts,images}
cp <source_main.tex> <working_dir>/
ln -s <absolute_path_to_source_images> <working_dir>/images
```

### 3. Clean OCR Artifacts

Before any translation work, clean common OCR noise:

```bash
python3 scripts/fix_ocr_artifacts.py <working_dir>/main.tex -v
```

This handles escaped `\$`, Unicode math chars, and control characters. Re-run after merging chunks too.

### 4. Extract Comparison Material from Source PDF

Using pymupdf (preferred, available in project Python env) or pdftotext:

```python
import fitz
doc = fitz.open("source.pdf")
for i, page in enumerate(doc):
    text = page.get_text('text')
    # Save per-page text for later cross-validation
    Path(f"pdf_pages/page_{i+1:03d}.txt").write_text(text)
```

Save one file per page (e.g. `pdf_pages/page_001.txt`). Subagents then receive the page-range files for their section as the authoritative reference — essential for reconstructing `�` (U+FFFD) symbols and verifying numbers. Map each LaTeX section to PDF pages once at split time (the OCR Contents gives printed page numbers; TOC pages 1-3 match PDF page indices 1-3 in this case, but verify per document).

If poppler is available:
```bash
pdftotext -layout source.pdf /tmp/source_layout.txt
```

### 5. Split into Translation Chunks

For papers longer than ~300 lines, split the document at major section boundaries:

```python
# Find \begin{document} / \end{document}
# Extract preamble (before \begin{document}) → parts/preamble.tex
# Split body at \section{} boundaries into parts/chunk_NN_description.tex
# Each chunk should be 150-700 lines for manageable translation
```

Splitting strategy (from Kimi K3 example):
- Chunk 1: Abstract + Introduction
- Chunk 2: Architecture / Methods (heaviest math, largest chunk)
- Chunk 3-4: Pre-training + Post-training
- Chunk 5: Infrastructure / Systems
- Chunk 6: Evaluations (many tables, translate headers + captions)
- Chunk 7: Case Studies + Conclusion
- Chunk 8: References (keep English, translate section title only)
- Chunk 9: Appendices (keep math proofs, translate prose)

For a long formal-methods paper, split at **subsection** boundaries too (see the spatiotemporal example): 17 chunks from 8 sections, with the two biggest sections (S3 ~1578 lines, S4 ~2160 lines) each split into 3-5 chunks. Budget chunk size by `�` density, not just line count — a 500-line proof chunk with 300 `�` symbols takes longer than an 800-line prose chunk with none. Keep the preamble + `\begin{document}` in chunk 00/01 so each body chunk starts at a heading.

### 6. Translate Chunks in Parallel

Launch subagents for each chunk. Each agent receives:
- The chunk file path
- Translation policy (preserve LaTeX, math, citations; translate prose + captions)
- Write-back instruction (overwrite the same file)

Reference the [example/kimi_k3_report/](../../example/kimi_k3_report/) — 9 chunks handled by 6 parallel agents; and [example/spatiotemporal_composability_report/](../../example/spatiotemporal_composability_report/) — 17 chunks handled by 16 agents in two waves of 8.

Translation policy:
- Translate English prose to Chinese
- **Preserve**: All LaTeX commands, math environments, `\cite{}`, `\ref{}`, `\label{}`, `\includegraphics{}`, tables, `\multirow`, `\multicolumn`
- **Keep in English**: Model names, benchmark names, technical identifiers, citation keys, library/framework names, author names
- Translate figure captions: `Figure X: ...` → `图 X: ...`
- Translate table captions and column headers
- Translate heading titles but **keep the OCR numeric prefix** in the heading (`\subsection{4.1. Components}` → `\subsection{4.1. 组件}`) — the normalizer strips it later; collapse multi-line heading titles onto one line
- Each agent gets the section's `pdf_pages/*.txt` files and must: fix systematic OCR spelling (e.g. "efects"→"effects"), replace every `�` from the PDF text, verify definition/theorem numbers and equation tags

### 7. Merge, Fix Fonts, and Clean Again

Merge preamble + all translated chunks into `main_cn.tex`. Update the font preamble with macOS-compatible fallbacks (add Songti SC, Heiti SC before SimSun/FangSong). Re-run artifact cleanup:

```bash
python3 scripts/fix_ocr_artifacts.py main_cn.tex -v
```

### 8. Normalize Headings (if needed)

If the OCR output uses numbered headings (e.g., `\section{2.3.4. Title}` or `\subsection{4.1. 组件}`):

```bash
python3 scripts/normalize_heading_levels.py --write main_cn.tex
```

The patterns accept both `1 引言` and `1. 引言` (trailing dot). Also: replace any hand-built Contents enumerate with `\tableofcontents` (+ `\renewcommand{\contentsname}{目录}` in the body), and convert the document title `\section` to a centered block manually when the preamble pushes it past the script's 30-line title window.

Most MinerU output already uses proper `\section{}` / `\subsection{}` commands, so this step is often skipped.

### 9. Cross-Validate Against Source PDF

Extract key sections from the source PDF and compare with the translated LaTeX:

```python
# Extract abstract, introduction, key findings from PDF
# Compare numerical values, technical claims, citation keys
# Flag any discrepancies for review
```

Focus on: parameter counts, percentages, benchmark scores, comparison claims. This catches OCR errors that silently corrupt data.

### 10. Compile

```bash
# Three passes for cross-references and TOC
xelatex -interaction=nonstopmode main_cn.tex
xelatex -interaction=nonstopmode main_cn.tex
xelatex -interaction=nonstopmode main_cn.tex
```

Earlier OCR papers expect 20-50 non-fatal errors from OCR artifacts; the `-interaction=nonstopmode` flag skips past them. With a full `�`-reconstruction pass + missing-glyph sweep (below), zero-error compiles are achievable. Check that the page count is reasonable and key elements (images, tables, math) render correctly.

**Missing-glyph sweep**: `grep 'Missing character' main_cn.log | sort -u` finds raw Unicode math left in prose (⋄, ≃, ∎, ⊥, ⌀, ▷, ↦, ∘). Wrap each in math mode with a stateful tracker — never a global replace on a mutating string.

### 11. Optional: Pandoc Wrapper

If the user explicitly requires a pandoc-produced PDF artifact:

```bash
scripts/compile_pdf.sh path/to/main_cn.tex path/to/output_pandoc.pdf
```

This compiles native LaTeX first, then wraps the result with `pdfpages` via pandoc.

## Decision Rules

- Use the source PDF as truth when OCR text and LaTeX disagree.
- Prefer pymupdf (fitz) over pdftotext for cross-validation — it handles multi-column layouts better and is available in the project's Python env.
- Prefer direct PDF image extraction over OCR images when the page contains embedded raster screenshots.
- Prefer page rendering plus crop for vector plots or multi-panel figures that OCR exported as tiny fragments.
- Prefer native XeLaTeX compilation over direct pandoc ingestion of OCR-LaTeX.
- For large papers (2000+ lines), split into chunks and translate in parallel. For short papers (<300 lines), translate inline without splitting.
- Feed each translator the section's per-page PDF text (`pdf_pages/page_NNN.txt`); every `�` reconstruction and number check reads from it.
- Fix missing-glyph Unicode in prose with a stateful math-mode tracker; never mutate a string while iterating over positions collected from it.
- Use `scripts/split_translation_chunks.py` for splitting (handles page markers, chunk budgeting, References slicing, page-range mapping) and `scripts/merge_translation_chunks.py` for merging (drops hand-built Contents, injects `\tableofcontents`, dedupes shared headings).
- Never globally replace `\n` literals in the merged file — the preamble's macro names (`\newcommand`...) share the prefix. Restrict the fix to body chunks or restore commands afterwards (`\textbackslash{}n` + letter → `\n` + letter).
- Expect MinerU's fi/ff ligature loss to hit reference author names too; translators must check names, not just prose.
- After 0 compile errors, run the `Missing character` sweep from the log — the residual list is exactly the Unicode math left in prose.

## Deliverables

- Clean translated working directory (`main_cn.tex`)
- Native compiled PDF (`main_cn.pdf`, typically 30-70 pages)
- Optional pandoc-wrapped PDF
- Translation chunks in `parts/` for traceability

## Example

See [example/kimi_k3_report/](../../example/kimi_k3_report/) for a complete worked example:
- Source: Kimi K3 technical report (~4000 lines MinerU OCR LaTeX)
- 9 chunks translated by 6 parallel subagents
- Final output: 65-page Chinese PDF
- Includes: split chunks, merged `main_cn.tex`, compiled PDF

See [example/spatiotemporal_composability_report/](../../example/spatiotemporal_composability_report/) for the math-heavy formal-methods case:
- Source: 6570-line PL paper, 88 PDF pages, 91 images
- 17 chunks, 16 parallel subagents in two waves; per-page `pdf_pages/` cross-validation reference
- ~900 `�` symbols reconstructed from the source PDF; systematic "efects"→"effects" fix
- Final output: 80-page Chinese PDF, 0 compilation errors
- Includes: chunks, `main_cn.tex`, patched normalizer, compiled PDF, README with lessons

See [example/mai_thinking_1_report/](../../example/mai_thinking_1_report/) for the largest case:
- Source: 7495-line technical report, 109 PDF pages, 67 images
- 35 chunks translated by 27 parallel subagents (two waves); per-chunk PDF page bundles
- ~170 fi/ff ligature losses fixed (including reference author names), a scrambled Table 12 rebuilt cell-by-cell, a missing Section-6 heading restored, a lost excerpt paragraph reconstructed from the PDF
- The `\n`-literal trap: a global replace turned a clean file into 173 errors; the `\textbackslash{}n`+letter restore pattern recovered it
- Final output: 120-page Chinese PDF, 0 errors, 0 missing glyphs
- Includes: chunks, split/merge scripts, shared translation policy with document-specific defect list, README with lessons
