# pdf-ocr-translate

一个面向论文与技术文档场景的 OCR LaTeX 翻译工程。核心目标是把 MinerU 等 OCR 工具产出的
LaTeX 工程，结合原始 PDF 做交叉校验与结构化修复，经多 agent 并行翻译后，整理为可直接
XeLaTeX 编译的高质量中文 PDF。

目录下同时提供**可复用的 skill**（`skill/pdf-ocr-translate/`）与**五个完整示例**（`example/`），
示例保留从 OCR 原始输出到最终中文 PDF 的全部中间产物，可用于对照、复现与回归。

## 目录结构

```text
pdf-ocr-translate/
├── skill/pdf-ocr-translate/
│   ├── SKILL.md                    # 工作流（8 步）
│   ├── scripts/                    # 14 个脚本：切分 / 清理 / 恢复 / 校验 / 编译
│   ├── references/                 # 6 份参考：编排、失败模式、工具坑、翻译策略等
│   └── assets/                     # 导言区补丁、字体链、标题层级示例、starter template
├── example/
│   ├── kimi_k3_report/             # Kimi K3 技术报告
│   ├── deepseek_v4_report/         # DeepSeek V4 技术报告
│   ├── spatiotemporal_composability_report/
│   ├── mai_thinking_1_report/      # 微软 MAI-Thinking-1（最大规模：7495 行 / 109 页）
│   └── deepseek_v4_1_flash_report/ # DeepSeek-V4.1-Flash（脚本最全，推荐先读）
│       ├── <原名>.pdf
│       ├── <原名>_CN.pdf           # 中文成品
│       ├── README.md               #   本例统计与经验教训
│       ├── ocr_latex/              #   OCR 原始输出（保留原样）
│       ├── pdf_pages/              #   pymupdf 逐页文本层（交叉校验的权威参考）
│       └── translate_latex/        #   翻译工程
│           ├── main_cn.tex         #     合并 + 标题规范化后的主文件
│           ├── parts/              #     分块译文 + CHUNK_MAP.json
│           ├── images_hi/          #     从源 PDF 高 DPI 重绘的图
│           ├── TRANSLATION_POLICY.md
│           ├── assemble.sh         #     合并 → 归一化 → 编译，一键复现成品
│           ├── build_parts.sh      #     从 main.tex 重建 parts/（翻译后勿用）
│           └── *.py                #     本例流水线脚本（其通用版本见 skill/scripts/）
├── README.md
└── .gitignore
```

每个示例目录自带 README，记录该案例的翻译统计、关键发现与复现要点。

## 工作流概览

1. **环境检查** — XeLaTeX + CJK 字体 + 带 pymupdf 的 Python 环境
2. **初始化工作区** — 建 `parts/`、`images_hi/`，抽取 PDF 逐页文本层
3. **清洗 OCR 噪声** — 转义符、Unicode 数学字符、控制字符、数学转写垃圾
4. **恢复丢失的数学字形** — MinerU 无法映射数学字体时会把变量写成 U+FFFD；改读 PDF 的
   span 级字体名即可取回，并逐条给出上下文供人工核对
5. **切分翻译块** — 按标题边界切分，剔除页码残行，产出 `CHUNK_MAP.json`
6. **多 subagent 并行翻译** — 每块一个 agent，共享翻译策略，对照 PDF 交叉校验
7. **合并与标题规范化** — 丢弃手写目录、注入 `\tableofcontents`、恢复标题层级、
   修附录与参考文献结构
8. **表格适配与版面审计** — 让过宽表格落入页边、校正表头列对齐，编译后检查溢出与重叠

## skill 内含

**脚本（`skill/pdf-ocr-translate/scripts/`）**

- 基础：`split_translation_chunks.py`、`merge_translation_chunks.py`、
  `normalize_heading_levels.py`、`fix_ocr_artifacts.py`、`extract_hd_figures.py`、
  `compile_pdf.sh`、`check_latex_translation.py`、`build_pandoc_wrapper.py`、
  `init_translation_workspace.sh`
- 诊断与恢复（在 DeepSeek-V4.1-Flash 一例中沉淀）：
  - `recover_math_glyphs.py` — 用 PDF 的 span 级字体信息找回被 OCR 丢弃的数学符号，
    输出符号所在句子供人工核对
  - `audit_layout.py` — 编译后体检：页边溢出、文本重叠、残留 `(a)`/`(b)` 列表标记
  - `check_tables.py` — 校验每张 longtable 每行的列数与导言声明一致
  - `check_structure.py` — 对比翻译前后的 `\label`/`\caption`/`\tag` 计数，证明无结构损失
  - `verify_corrections.py` — 核实 subagent 声称的更正是否真在源 PDF 上

**参考（`skill/pdf-ocr-translate/references/`）**

- `orchestration.md` — 并行 subagent 的编排经验：如何给有界 brief、为什么校验型 agent 会
  耗尽上下文、以及卡住后怎么处理
- `ocr-failure-patterns.md` — MinerU 系统性损坏目录（连字丢失、数学字形丢失、表格错位、
  URL 被打断、`\n` 陷阱等）与对应修法
- `workflow.md`、`translation-policy.md`、`tooling-and-gotchas.md`、`example-session.md`

**素材（`skill/pdf-ocr-translate/assets/`）**

- `preamble_patches_cn.tex` — 对位置敏感的导言区补丁（CJK 字体、`xurl`、可换行表格列、
  居中标题、图/表中文编号、`\contentsname`），并说明每条为何放在那个位置
- `font_preamble_snippet.tex`、`heading_examples.tex`、`pandoc_wrapper.template.md`
- `deepseek_v4_paper_template/` — 模块化起步模板

## 适用场景

- OCR 识别后的论文 LaTeX/Markdown 存在大量脏数据
- OCR 输出中变量被写成 U+FFFD 占位符，公式无法阅读
- 表格超出页边、表头与数据列对不齐
- 图表被切成低清碎片，需要从源 PDF 重绘
- 需要保留公式、表格与整体 LaTeX 可编译性，并使用多个 subagent 并行翻译长文档
- 需要最终输出高质量中文 PDF

## 示例来源与致谢

本目录中的示例基于公开论文与技术报告整理：

- DeepSeek_V4 / DeepSeek-V4.1-Flash：感谢 DeepSeek-AI
  （`https://huggingface.co/deepseek-ai/`）
- Kimi K3：感谢 Moonshot AI
- MAI-Thinking-1：微软 AI 团队技术报告（本仓 `archive/` 内原始副本）
- Spatiotemporal Composability：形式化方法论文示例

各示例仅用于展示 OCR LaTeX 翻译、校验与编译工作流，不改变原论文署名与参考文献归属。

## 提交约定

本仓库遵循 Conventional Commits：`<type>: <subject>`，type 取
`feat` / `fix` / `docs` / `chore` 等。编译中间产物（`build/`、`*.aux`、`*.log`、`*.toc`）
与 `__pycache__/` 已由 `.gitignore` 排除，示例只需提交源工程与最终 PDF。
