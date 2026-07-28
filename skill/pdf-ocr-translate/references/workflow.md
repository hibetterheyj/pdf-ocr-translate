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
```

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

### 6. Translate Chunks in Parallel

Launch subagents for each chunk. Each agent receives:
- The chunk file path
- Translation policy (preserve LaTeX, math, citations; translate prose + captions)
- Write-back instruction (overwrite the same file)

Reference the [example/kimi_k3_report/](../../example/kimi_k3_report/) — 9 chunks handled by 6 parallel agents.

Translation policy:
- Translate English prose to Chinese
- **Preserve**: All LaTeX commands, math environments, `\cite{}`, `\ref{}`, `\label{}`, `\includegraphics{}`, tables, `\multirow`, `\multicolumn`
- **Keep in English**: Model names, benchmark names, technical identifiers, citation keys, library/framework names, author names
- Translate figure captions: `Figure X: ...` → `图 X: ...`
- Translate table captions and column headers

### 7. Merge, Fix Fonts, and Clean Again

Merge preamble + all translated chunks into `main_cn.tex`. Update the font preamble with macOS-compatible fallbacks (add Songti SC, Heiti SC before SimSun/FangSong). Re-run artifact cleanup:

```bash
python3 scripts/fix_ocr_artifacts.py main_cn.tex -v
```

### 8. Normalize Headings (if needed)

If the OCR output uses numbered headings (e.g., `\section{2.3.4. Title}`):

```bash
python3 scripts/normalize_heading_levels.py --write path/to/parts/*.md
```

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

Expect 20-50 non-fatal errors from OCR artifacts. The `-interaction=nonstopmode` flag skips past them. Check that the page count is reasonable and key elements (images, tables, math) render correctly.

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
