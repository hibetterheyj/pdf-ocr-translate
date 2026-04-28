# Example Session Template

This reference turns a successful large-paper translation run into a reusable template.

It is modeled after a DeepSeek\_V4-scale technical paper:

- one main OCR-produced LaTeX file,
- a large `images/` directory,
- a source PDF used as the authoritative reference,
- a modular translated working copy under `parts/`,
- upgraded high-resolution figures under `images_hi/`.

Use it as a pattern, not a rigid contract.

## Generic Input Layout

Assume these placeholders:

- `<OCR_PROJECT_DIR>`: OCR output directory from MinerU, Mathpix, Nougat, or a similar tool
- `<WORK_DIR>`: translated working copy
- `<TMP_DIR>`: temporary extraction directory

Typical source structure:

```text
<OCR_PROJECT_DIR>/
├── main_ocr.tex
├── source.pdf
└── images/
    ├── figure_fragment_01.jpg
    ├── figure_fragment_02.jpg
    └── ...
```

For a DeepSeek\_V4-style paper, a concrete naming convention may look like:

```text
<OCR_PROJECT_DIR>/
├── DeepSeek_V4_ocr_latex.tex
├── DeepSeek_V4.pdf
└── images/
```

## Recommended Working Copy Layout

For long technical papers, create a separate translated workspace:

```text
<WORK_DIR>/
├── main.tex
├── native_output.pdf
├── final_pandoc.pdf
├── images/
├── images_hi/
├── parts/
│   ├── frontmatter_cn.tex
│   ├── part1_cn.md
│   ├── part2_cn.md
│   ├── part3_cn.md
│   ├── part4_cn.md
│   ├── conclusion_cn.md
│   ├── appendix_heads_cn.md
│   ├── appendix_b_captions_cn.tex
│   └── figure_extraction_notes.md
└── pandoc_wrapper.md
```

For a DeepSeek\_V4-style paper, this modular split worked well:

- `frontmatter_cn.tex`: title, abstract, TOC, first-page figures
- `part1_cn.md`: introduction and architecture
- `part2_cn.md`: infrastructure
- `part3_cn.md`: pre-training
- `part4_cn.md`: post-training and evaluations
- `conclusion_cn.md`: conclusion
- `appendix_heads_cn.md`: appendix headings and exempt sections
- `appendix_b_captions_cn.tex`: appendix tables/figures where only captions need translation

## Source-PDF Cross-Check Files

Useful derived files:

```text
<TMP_DIR>/source_layout.txt
<WORK_DIR>/parts/figure_extraction_notes.md
<WORK_DIR>/images_hi/
```

Where:

- `source_layout.txt` comes from `pdftotext -layout`
- `figure_extraction_notes.md` records page-to-figure mapping and extraction decisions
- `images_hi/` stores upgraded crops and extracted embedded images

## DeepSeek_V4-Style Figure Upgrade Pattern

For long technical papers with mixed chart figures and screenshot-style figures, this pattern worked well:

- Figure 1: page render + crop from the source PDF
- Figure 13: extract embedded page image directly from the source PDF
- Figure 14: extract embedded page image directly from the source PDF
- Figure 15: extract embedded page image directly from the source PDF

General rule:

- use `pdfimages` for embedded screenshots or slide-like figures,
- use `pdftocairo` + crop for vector plots or OCR-split multi-panel figures.

## Commands Template

### Initialize workspace

```bash
scripts/init_translation_workspace.sh <OCR_PROJECT_DIR> <WORK_DIR>
```

### Extract source text layer

```bash
pdftotext -layout <SOURCE_PDF> <TMP_DIR>/source_layout.txt
pdfimages -list <SOURCE_PDF>
```

### Normalize headings

```bash
python3 scripts/normalize_heading_levels.py --write \
  --inline-bold "核心评测结果摘要" \
  --inline-bold "注入的指令" \
  --inline-bold "工具调用 Schema" \
  <WORK_DIR>/parts/*.md
```

### Scan translated parts

```bash
python3 scripts/check_latex_translation.py <WORK_DIR>/parts \
  --allow-prefix "Authors are listed alphabetically" \
  --allow-prefix "* denote" \
  --ignore-glob part1a_cn.md \
  --ignore-glob part1b_cn.md
```

### Compile native TeX and emit pandoc wrapper PDF

```bash
scripts/compile_pdf.sh <WORK_DIR>/main.tex <WORK_DIR>/final_pandoc.pdf
```

## Suggested Main-File Assembly Pattern

A practical assembly pattern for large translated papers:

```latex
\input{parts/frontmatter_cn.tex}
\input{parts/part1_cn.md}
\input{parts/part2_cn.md}
\input{parts/part3_cn.md}
\input{parts/part4_cn.md}
\input{parts/conclusion_cn.md}

\phantomsection
\section*{References}

\appendix
\input{parts/appendix_heads_cn.md}
\input{parts/appendix_b_captions_cn.tex}
```

This pattern is especially useful when:

- multiple subagents translate disjoint ranges,
- the bibliography must remain untranslated,
- appendix treatment differs from main-body policy.

## What To Reuse From This Template

Reuse these ideas from the DeepSeek\_V4-style session:

- modular `parts/` layout,
- source PDF text-layer cross-checking,
- heading normalization after translation,
- native XeLaTeX first, pandoc wrapper second,
- figure-upgrade notes as a persistent decision log.

Adjust these per project:

- part boundaries,
- which sections are exempt from translation,
- which figures deserve HD replacement,
- whether appendix tables need full translation or caption-only translation.
