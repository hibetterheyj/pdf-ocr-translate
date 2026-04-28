# OCR LaTeX Translation Workflow

Use this workflow when the user has a source PDF plus OCR-generated LaTeX or Markdown and wants a polished translated PDF.

## Inputs

- Source PDF: the authoritative visual and textual reference.
- OCR project: LaTeX, Markdown, or a mixed OCR directory such as MinerU / Nougat / Mathpix output.
- Figure directory: usually extracted low-resolution images from OCR.
- Translation scope: what to translate and what to preserve.

## End-to-End Flow

1. Inspect the OCR project and identify the main `.tex` or `.md` entrypoint.
2. Initialize a separate working copy with:

```bash
scripts/init_translation_workspace.sh <ocr_project_dir> <working_dir>
```

3. Extract clean comparison material from the source PDF:

```bash
pdftotext -layout source.pdf /tmp/source_layout.txt
pdfimages -list source.pdf
```

4. Decide whether the OCR project should stay monolithic or be split into modular parts:
   - Keep it monolithic for short documents.
   - Split it into `parts/` for long papers or when multiple subagents will translate in parallel.

5. If the user explicitly asks for multiple subagents or the paper is long, assign disjoint write targets:
   - `part1_cn.md`: title, intro, architecture
   - `part2_cn.md`: infrastructure
   - `part3_cn.md`: pre-training
   - `part4_cn.md`: post-training
   - one extra worker for conclusion / appendix headings / image extraction notes

6. Ask each worker to:
   - preserve formulas and LaTeX environments,
   - translate prose and necessary captions,
   - write only to its own file,
   - avoid touching the main TeX file.

7. Merge translated parts into the working main TeX file.

8. Normalize heading levels:

```bash
python3 scripts/normalize_heading_levels.py --write \
  --inline-bold "核心评测结果摘要" \
  --inline-bold "注入的指令" \
  --inline-bold "工具调用 Schema" \
  path/to/parts/*.md
```

9. Extract higher-quality figures from the source PDF when OCR images are blurry. Read [tooling-and-gotchas.md](tooling-and-gotchas.md).

10. Run consistency checks:

```bash
python3 scripts/check_latex_translation.py path/to/parts \
  --allow-prefix "Authors are listed alphabetically"
```

11. Compile native LaTeX first. Prefer `latexmk`; fall back to repeated `xelatex`.

12. If the user explicitly requires a pandoc-produced PDF artifact, wrap the native PDF instead of asking pandoc to reinterpret a complex native TeX source:

```bash
scripts/compile_pdf.sh path/to/main.tex path/to/output_pandoc.pdf
```

## Decision Rules

- Use the source PDF as truth when OCR text and LaTeX disagree.
- Prefer direct PDF image extraction over OCR images when the page contains embedded raster screenshots.
- Prefer page rendering plus crop for vector plots or multi-panel figures that OCR exported as tiny fragments.
- Prefer native XeLaTeX compilation over direct pandoc ingestion of OCR-LaTeX.

## Deliverables

- Clean translated working directory.
- Native compiled PDF.
- Optional pandoc-wrapped PDF.
- Image upgrade notes when figures were replaced.
