# MAI-Thinking-1 技术报告中译 — pdf-ocr-translate 完整示例

使用 `pdf-ocr-translate` skill 对微软 MAI-Thinking-1 技术报告（109 页英文原版）执行 OCR LaTeX 中译的完整工作示例。

## 来源

- **原始 PDF**：`MAI-Thinking-1.pdf`（109 页，微软 AI 团队技术报告）
- **OCR LaTeX**：MinerU 输出，7495 行，67 张图（35 张完整大图 + 32 张碎片图）
- **本示例位置**：`example/mai_thinking_1_report/`（工作副本在 `archive/MAI-Thinking-1_translate/`）

## 翻译统计

| 指标 | 值 |
|------|-----|
| 源 tex 行数 | 7,495 |
| 翻译块（chunks） | 27 个（preamble + frontmatter + 正文 13 + 参考文献 3 + 附录 10；Contents 块合并时丢弃） |
| 并行 agent | 27（两波：14 + 13） |
| 修复的连字丢失错词（fi/ff 类） | ~170 处 |
| 修复的 URL/arXiv 断行 | ~35 处 |
| 交叉验证页码参考 | 109 页逐页文本（pdf_pages/） |
| 最终 PDF 页数 | 120 页 |
| 编译错误 | 0（三次 XeLaTeX 均无错误、无缺字形） |
| 字体 | Songti SC（macOS 回退链，见 preamble） |

## 目录结构

```
MAI-Thinking-1_translate/
├── MAI-Thinking-1.pdf                  # 原始英文 PDF（109 页）
├── MAI-Thinking-1_CN.pdf               # 中文翻译 PDF（120 页）
├── ocr_latex/                          # MinerU OCR 原始输出（保留原样）
│   ├── MinerU_latex_MAI-Thinking-1.tex
│   └── images/                         # 67 张 OCR 图片
├── pdf_pages/                          # pymupdf 逐页提取的源 PDF 文本（109 个文件）
│   └── page_001.txt ... page_109.txt   # 翻译交叉验证权威参考
└── translate_latex/                    # 翻译后的 LaTeX 工程
    ├── main_cn.tex                     # 合并 + 标题规范化后的主文件（4065 行）
    ├── images -> ../ocr_latex/images   # 图片软链
    ├── parts/                          # 27 个翻译块（保留翻译痕迹）
    │   ├── chunk_00_preamble.tex       #   preamble + 标题居中块 + 字体回退链
    │   ├── chunk_01_frontmatter.tex    #   摘要 + 引言
    │   ├── chunk_02_contents.tex       #   手写目录（合并时被 \tableofcontents 替换）
    │   ├── chunk_03...14               #   正文第 2-7 章
    │   ├── chunk_15...17               #   参考文献三段（保留英文，修复 OCR）
    │   └── chunk_18...27               #   附录 A-L
    ├── split_chunks.py                 # 切分脚本（页码行剔除 + 按标题边界切分）
    ├── merge_chunks.py                 # 合并脚本（TOC 注入 + 重复段去重）
    └── TRANSLATION_POLICY.md           # 多 agent 共享翻译策略（含本文档 OCR 缺陷清单）
```

## 本案例的关键发现

1. **fi/ff 连字系统性丢失**：MinerU 全书把 `eficiency/efficient`、`diferent/different`、`ofer/offer`、`efort/effort` 等约 170 处连字吃掉。翻译 agent 对照 PDF 逐处修复；连参考文献作者名（`Jefrey→Jeffrey`、`Hofmann→Hoffmann`、`Muennighof→Muennighoff`）也被波及。
2. **OCR 丢失 Section 6 主标题**：`6 Cluster Environment` 在 OCR 中变成纯文本段落，不在标题命令里。交叉验证发现后补回 `\subsection{6 集群环境}`。
3. **页码残行**：OCR 每页末尾残留独立页码行（109 个，与 PDF 页一一对应），切分脚本用"空行包围的独立整数且构成 1..109 递增链"判定并剔除。
4. **表格数据行被打乱**：Table 12 第二块数据行被 OCR 打乱（单元格翻倍合并），agent 按 PDF 页逐格重写；Table 17 的 em dash 被误识为中文"一"，按 PDF 修正为 `---`。
5. **数学转写垃圾**：MinerU 把数学写成 `\textgreater0`、`x\^{}2`、`\textsuperscript{...}` 括号错位、`=\textgreater{}$` 等。合并后经三轮编译迭代修复，最终 0 错误 0 缺字形。
6. **手写 Contents 带英文页码**：OCR 的 Contents 是英文版页码的纯文本，替换为 `\tableofcontents` + `\renewcommand{\contentsname}{目录}`（放在正文区，polyglossia 会重置 contentsname）。
7. **JSON/代码块**：附录 E 的 JSON schema 用 pandoc 转义（`\{`、`{[}`）展示，编译正常；正文里的 `\n` 字面量需替换为 `\textbackslash{}n`（注意别误伤 preamble 宏名）。
8. **图片碎片**：67 张图中 32 张是公式条/表格行小图，35 张完整大图（800px+）直接用；`\pandocbounded` 宏保留可用，无需替换高清图。

## 复现要点

1. 切分：按标题边界 27 块，每块附该页范围的 `pdf_pages/` 参考文本。
2. 翻译：两波 27 个并行 agent，共享 `TRANSLATION_POLICY.md`（含连字丢失、脚注误置、页码残行等本文档特有缺陷清单）。
3. 合并：丢弃手写目录，注入 `\tableofcontents`；去重附录 I 重复段；修复 Table 2 表头 pandoc 转义。
4. 标题规范化：stock `normalize_heading_levels.py` 处理后，手动补齐 G-L 附录提升（脚本附录规则只覆盖 A-F）和 J.1.x 降级。
5. 编译：`xelatex -interaction=nonstopmode main_cn.tex` ×3，0 错误 0 缺字形，120 页。

## 说明

- 本目录仅为展示 OCR LaTeX 翻译、校验和编译工作流，不改变原论文署名与参考文献归属。
- 参考文献条目按策略保留英文原文（仅修复 OCR 错误），章节标题"参考文献"译中文。
