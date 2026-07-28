# DeepSeek V4 Technical Report — Chinese Translation Example

Earlier worked example from the `pdf-ocr-translate` skill workflow.

## Source

- **Original PDF**: `DeepSeek_V4.pdf`
- **OCR LaTeX**: `ocr_latex/DeepSeek_V4_ocr_latex.tex`

## File Structure

```
deepseek_v4_report/
├── DeepSeek_V4.pdf                  # Original English PDF
├── DeepSeek_V4_CN.pdf              # Translated Chinese PDF
├── ocr_latex/                      # OCR source from MinerU
│   ├── DeepSeek_V4_ocr_latex.tex
│   └── images/                     # OCR-extracted images
└── translate_latex/                # Translated LaTeX project
    ├── DeepSeek_V4_ocr_latex.tex   # Merged translated TeX
    ├── DeepSeek_V4_ocr_latex.pdf   # Native XeLaTeX compiled PDF
    ├── DeepSeek_V4_cn_pandoc.pdf   # Pandoc-wrapped PDF
    ├── pandoc_wrapper.md
    ├── parts/                      # Translation chunks
    │   ├── frontmatter_cn.tex
    │   ├── part1_cn.md
    │   ├── part2_cn.md
    │   ├── part3_cn.md
    │   ├── part4_cn.md
    │   ├── conclusion_cn.md
    │   ├── appendix_heads_cn.md
    │   └── appendix_b_captions_cn.tex
    ├── images/                     # OCR images (copied)
    └── images_hi/                  # High-res extracted figures
```
