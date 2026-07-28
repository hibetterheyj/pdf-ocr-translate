# Figure Extraction Notes

## 1. Figure 1-15 大致页码

以下按 PDF 中 `Figure N | ...` caption 所在页统计，页码为 PDF 1-based 页码。

| Figure | PDF 页 |
| --- | --- |
| Figure 1 | p.1 |
| Figure 2 | p.6 |
| Figure 3 | p.9 |
| Figure 4 | p.11 |
| Figure 5 | p.15 |
| Figure 6 | p.23 |
| Figure 7 | p.32 |
| Figure 8 | p.40 |
| Figure 9 | p.40 |
| Figure 10 | p.41 |
| Figure 11 | p.43 |
| Figure 12 | p.43 |
| Figure 13 | p.43 |
| Figure 14 | p.56 |
| Figure 15 | p.56 |

## 2. 哪些最适合“整页渲染后裁切”

最适合直接从 PDF 整页渲染后裁切的，是 **Figure 1-6、8-12**。

- 这些 figure 在 `pdfimages -list` 里基本没有对应的大嵌入位图，说明它们主要是 LaTeX/矢量线条/文字组合，直接整页高 DPI 渲染更容易得到清晰结果。
- OCR LaTeX 当前导出的若干图分辨率偏低，重裁切收益明显：
  - Figure 1 当前被拆成 `750x528`、`422x328`、`419x331`
  - Figure 5 当前主图约 `1214x166`
  - Figure 8 当前主图约 `572x142`
  - Figure 11 / 12 当前主图约 `597x350`、`600x353`

不太建议走“整页渲染后裁切”，更适合直接抽 PDF 内嵌图像的，是 **Figure 7、13、14、15**。

- p.32 有 2 张内嵌 JPEG：`3418x2276`、`1923x980`，对应 Figure 7 的两部分。
- p.43 有 1 张内嵌 JPEG：`5708x3220`，更像 Figure 13 的原始大图。
- p.56 有 2 张内嵌 JPEG：`3433x1600`、`4584x1600`，更像 Figure 14 / 15 的原始大图。

## 3. 可执行命令建议

本机已确认有 `pdftocairo`、`pdfimages`、`sips`，**没有** `magick`。下面用 `pdftocairo + sips` 或 `pdfimages`。

```bash
PDF="/Users/heyujie/Documents/code/DeepSeek_V4_ocr_latex/DeepSeek_V4.pdf"
OUT="/tmp/dsv4_fig_extract"
mkdir -p "$OUT"
```

### 方案 A：Figure 1

这张图当前在 OCR 源里被拆成 3 张小图，最值得重做。

```bash
pdftocairo -png -r 600 -f 1 -l 1 "$PDF" "$OUT/p1"
sips -c 2050 3900 --cropOffset 3900 520 "$OUT/p1-01.png" --out "$OUT/Figure1_hi.png"
```

### 方案 B：Figure 10

这页顶部是纯图表区，裁切比较稳。

```bash
pdftocairo -png -r 600 -f 41 -l 41 "$PDF" "$OUT/p41"
sips -c 1600 3800 --cropOffset 600 620 "$OUT/p41-41.png" --out "$OUT/Figure10_hi.png"
```

### 方案 C：Figure 13-15 直接抽内嵌图

这几张更适合直接从 PDF 抽原始 JPEG，不必先整页渲染。

```bash
pdfimages -f 43 -l 43 -j "$PDF" "$OUT/p43"
pdfimages -f 56 -l 56 -j "$PDF" "$OUT/p56"
```

经验上可按下面对应关系先看：

- `p43-000.jpg`：大概率对应 Figure 13
- `p56-000.jpg`：大概率对应 Figure 14
- `p56-001.jpg`：大概率对应 Figure 15

如果下一步只想优先替 2-3 张，我会先做：

1. Figure 1
2. Figure 10
3. Figure 13 或 Figure 15（优先直接 `pdfimages`）
