# DeepSeek-V4.1-Flash 技术报告中译 — pdf-ocr-translate 完整示例

使用 `pdf-ocr-translate` skill 对 DeepSeek-V4.1-Flash 技术报告（51 页英文原版）执行 OCR LaTeX 中译的完整工作示例。

## 来源

- **原始 PDF**：`DeepSeek-V4.1-Flash.pdf`（51 页）
- **OCR LaTeX**：
  - `ocr_latex/DeepSeek_V41_ocr_latex_v2.tex` — MinerU OCR 二阶段识别版本（本次采用的基准）
  - `ocr_latex/DeepSeek_V41_ocr_latex_v1.tex` — MinerU VLM 识别版本（保留对照）
  - `ocr_latex/images/` — 41 张 OCR 切图
- **中文成品**：`DeepSeek-V4.1-Flash_CN.pdf`（49 页）

## 翻译统计

| 指标 | 值 |
|------|-----|
| 源 tex 行数 | 3,313（v2） |
| 切分块（chunks） | 15（preamble + 正文 14） |
| 翻译 agent | 12（其中 3 个需重发一次；另 2 个 chunk 由主流程直接翻译） |
| 中文字符数 | 26,177 |
| 恢复的丢失数学符号（U+FFFD） | 80 处 |
| 修复的跨行标题 | 26 处 |
| 替换的高清图 | 12 张（400 DPI，源自 PDF 矢量图） |
| 剔除的页码残行 | 48 行 |
| 最终 PDF 页数 | 49 页 |
| 编译错误 / 缺字形 | 0 / 0 |
| 字体 | Songti SC（STSongti-SC） |

## 目录结构

```
deepseek_v4_1_flash_report/
├── DeepSeek-V4.1-Flash.pdf            # 原始英文 PDF（51 页）
├── DeepSeek-V4.1-Flash_CN.pdf         # 中文翻译 PDF（49 页，0 错误 0 缺字形）
├── ocr_latex/                         # MinerU OCR 原始输出（保留原样，供对照）
│   ├── DeepSeek_V41_ocr_latex_v1.tex  #   VLM 识别版本
│   ├── DeepSeek_V41_ocr_latex_v2.tex  #   二阶段识别版本（基准）
│   └── images/                        #   41 张 OCR 切图
├── pdf_pages/                         # pymupdf 逐页文本层（51 页）
│   └── page_001.txt ... page_051.txt  #   翻译交叉校验的权威参考
└── translate_latex/                   # 翻译工程
    ├── main_cn.tex                    #   合并 + 标题规范化后的主文件（2,153 行）
    ├── main.tex                       #   OCR 基准（已打字体/标题补丁，供重建）
    ├── images -> ../ocr_latex/images  #   OCR 图片软链
    ├── images_hi/                     #   12 张 PDF 高清重绘图 + manifest.json
    ├── parts/                         #   15 个翻译块 + CHUNK_MAP.json
    ├── TRANSLATION_POLICY.md          #   多 agent 共享翻译策略（含术语表）
    ├── assemble.sh                    #   合并 → 归一化 → 编译（一键复现成品）
    ├── build_parts.sh                 #   从 main.tex 重建 parts/（翻译后勿用）
    └── *.py                           #   各阶段脚本，见下表
```

## 排版收尾（第二轮）

首版编译后修掉三处版面问题：

1. **摘要页残留 `(a)` `(b)`**。图 1 的两个子图标签被 MinerU 输出成两个**空的
   `enumerate` 环境**（每块只有 `\item`、无内容）。图片被包装成 `figure` 后，这两个
   空列表仍留在正文里，LaTeX 便打印出 `(a)` 和 `(b)`。`fix_headings.py` 增加一条规则
   删除空列表环境，结构计数相应减少 2 个 `\begin`/`\end`——这是预期变化。

2. **表 1/3/4/5 过宽**。MinerU 一律用 `l` 列，而 `l` 列不换行，长基准名（
   `Terminal-Bench v2.1 (Pass@1)`）和排成一行的小标题把表格顶出页边。
   `fix_table_width.py` 做两件事：把首个标签列改为固定宽度的 `L{}` 列（
   `>{\RaggedRight\arraybackslash}p{}`，允许连字符断行），并用 `{\footnotesize ...}`
   包住整张表。**注意 `\footnotesize` 必须放在 `longtable` 外层**——放进对齐导言区
   （`\endlastfoot` 之后）会触发 `Misplaced \noalign`。修完表格右缘从
   599pt 收到 555~563pt（正文栏右界 555pt）。

3. **表 3 表头结构错误**。OCR 把首列分组名压成了 `\multicolumn{7}` 且漏掉一个单元格，
   导致表头首行 7 格、次行 7 格，与表体 8 格不一致。已还原为「首列分组 + 7 个模型列」，
   并把次行的 `Max` 行补足首列空单元格。

## 排版收尾（第三轮：表格对齐与 URL）

第二轮只解决了"表格出界"，这一轮解决"表内对不齐"：

1. **表 1 首列文字重叠**。首列固定为 `5em` 包住中文分组名（世界知识/语言与推理/代码与数学），
   但三个模型名所在的列仍是 `l` 列不换行，`DeepSeek-V4.1-Flash Base` 直接顶到页外 573pt。
   已把这几个模型列也改为可换行的 `L{}` 列。表 1、表 3 现在右缘正好落在 555pt。
   表 2/4/5 仍在 562~563pt（超出不足 8pt≈2.8mm），因为 9 列的表在正文宽度下已无可压缩空间。

2. **表 3 表头与数据列不对齐**（用户报的主要问题）。原表头是一个 `\multicolumn{7}` 的
   连续文本 `Opus-5 GPT-5.6 Sol K3 GLM-5.3 DS-V4-Pro DS-V4-Flash|DS-V4.1-Flash`，
   文字按自然间距流排，与下方数据列**毫无关系**（数据列起点 225/262/304/333/376/414/470）。
   已改为每列一个 `\shortstack` 单元格，模型名各自落在自己的列上；实测表头与数据的列起点
   逐一吻合。**注意模型顺序须按原报告**：Opus-5、GPT-5.6 Sol、K3、GLM-5.3、DS-V4-Pro、
   DS-V4-Flash、DS-V4.1-Flash。

3. **参考文献 URL 被 OCR 插入空格**。三处：`https://doi. org/…`、`…arXiv.2405.04 434`、
   `deepseek-a i/deepseek-harness`。空格会同时破坏链接和版面——补齐后 URL 变成一个
   180pt 的不可断行 token，反而把该行顶到 613pt。因此同时引入 `xurl` 宏包（允许 URL
   任意位置断行）。只补空格不加 `xurl` 会更糟。

## 术语对齐（DeepSeek 官方中文口径）

译文初稿把 "reasoning effort" 直译为「推理努力」。对照 DeepSeek 官方中文文档后改为官方的
**「思考强度」**：

- `https://api-docs.deepseek.com/zh-cn/guides/thinking_mode/` — 章节名即
  「思考模式开关与**思考强度控制**」，表内行标为「思考强度控制」。
- `https://api-docs.deepseek.com/zh-cn/news/news260910/` — V4.1-Flash 发布说明。

据此统一（共 49 处）：

| 初稿 | 定稿（官方口径） |
|---|---|
| 推理努力 / 推理强度 | 思考强度 |
| 努力档位 / 努力层级 | 强度档位 |
| 努力值 | 强度值 |
| effort 设置 | 思考强度（effort）控制 |

同时修掉一类机器翻译腔：「智能体化工作负载」→「智能体工作负载」；
并把混用的半角标点统一为全角（86 处，源文是英文故原文用 ASCII 逗号，
各 agent 译文的标点风格不一致）。

`refine_terminology.py` 固化这套替换；`TRANSLATION_POLICY.md` 的术语表已注明官方来源。

## 关键发现

1. **两个 OCR 版本几乎等价**。v1 与 v2 规范化后相似度 98.9%，差异集中在数学公式的空格风格（v1 为 `X _ {l}`，v2 为 `X _ { l }`）与页码残行处理。**关键点：两个版本丢失的是同一批符号**——换版本救不回数学。

2. **MinerU 系统性丢弃数学斜体字形（80 处）**。PDF 正文用 `XCharterMathMI` 字体排数学变量（Unicode Mathematical Italic），MinerU 无法映射，一律写成 U+FFFD。而且 **pymupdf 的 `get_text("text")` 也丢这些字**，所以纯文本层比对无法恢复。
   解法：改用 `get_text("dict")` 读取 **span 级字体信息**，692 个数学斜体字形全部可读。据此把 80 处逐一还原为 `$C$`/`$Z$`（KV 条目）、`$m$`（压缩率）、`$n$`/`$d$`（mHC 维度）、`$b$`/`$x$`/`$j$`/`$\lambda$`/`$\tau$`（推理努力调度）等，全部有 PDF 依据，非猜测。

3. **PDF 文本层无法直接做子串检索**。pymupdf 对数学 span 会在每个字形间插空格（`f u s e d - R o P E`）。跨版本/跨页比对必须先折叠空白与连字符，否则会得到大量假阴性——本工程中途曾因此误判三处"未找到"。

4. **chunk 切分边界与印刷页码不是一 一对应**。`pdf_pages/page_NNN.txt` 对应**印刷页 N**（`page_001.txt` 是标题页，无页码），但 chunk 的范围按切分点给，跨页的图注常与图分属不同 chunk。

5. **表格是 OCR 损坏最集中的地方**。修正清单（均经 PDF 逐格核对）：
   - **表 1**：架构/参数行与多模态行的 shots 列丢失 `-` 占位，导致单元格错位。
   - **表 3**：`一`（U+4E00）被 OCR 当作连字符读入，实为 `-`；`Agntic ExploitGym` 应为 `ExploitGym`；`Reasong GPQA Diamond` 需拆成 `Reasoning` 分组行 + `GPQA Diamond`。原文的分组行（`Reasoning`/`Agentic`）与粗体/下划线（最好/次好）在文本层中不可见，依图注规则与数值重建。
   - **表 4**：表头三个脚手架名被合并成一个 `\multirow` 单元格；DeepSeek Harness 的 Minimal/Standard/PTC 三个子表头被并成一格。

6. **翻译阶段又抓出一批 OCR 语义错误**（说明"译 + 校"双轨确实必要）：
   - 附录 C 中 "controls the rate of penalty decay" 的参数，我最初的恢复表误判为 `λ`，agent 对照 PDF 改为 `τ`——PDF 的定义是 `τ = λΔb`，衰减率是 `τ`。**已同步修正恢复脚本**。
   - `Δb` 在正文丢失上划线（公式 (10) 中有）。
   - `\mathcal{B}`（努力档位集合）被写成普通 `B`。
   - 公式 (8) 前的句子以冒号结尾，非分号。
   - 表 2 努力值表头应为数学斜体 `$b$`。

7. **12 张图全部从 PDF 重绘，不用 OCR 切图**。原 PDF 只有 3 页含内嵌位图，其余图表均为矢量绘制（page 11 有 515 个绘图操作、page 28 有 461 个）。以 400 DPI 按图注上方的墨迹包围盒裁剪，得到清晰矢量渲染。OCR 的 15 个图片引用中，3 个是同页重复/碎片，已删；MinerU 还把 Figure 10 的图注拆散并丢失编号前缀，已按 PDF 补回。

8. **图/表编号需要显式中文化**。ctex 不会自动把 `\caption` 的前缀改成中文，需 `\renewcommand{\figurename}{图}`、`\renewcommand{\tablename}{表}`。这两个命令可放导言区，但 `\contentsname` 必须放在正文区（polyglossia 会在语言激活时重置）。

9. **目录必须插在标题块之后**。preamble chunk 含 `\begin{document}`，而居中标题块在其后；若按"紧跟 `\begin{document}`"插入 `\tableofcontents`，目录页会跑到标题页前面。合并脚本已改为在第一个 `\section` 之前插入。

10. **并行 agent 的失败模式**。13 个并发 agent 里有 5 个在给出结果前耗尽上下文（都是花大量轮次反复读 PDF 做校验的那几个）。给它们"范围收窄 + 结论已给定、不要重新调查"的指令后，同样的 chunk 5 轮内即可完成。教训：**校验与翻译分离**——校验收在单独的、有明确产出物的一轮里做，翻译 agent 只负责译，附带已核实的修正清单。

## 复现要点

```bash
cd translate_latex
PY=/path/to/env/data_env/bin/python ./assemble.sh      # 合并 + 归一化 + 编译，产出 build/final/main_cn.pdf
```

`build_parts.sh` 用于**翻译开始前**从 `main.tex` 重建 `parts/`；它会拒绝在 `parts/` 已含中文时运行（除非 `FORCE=1`），以免覆盖译文。

各阶段脚本：

| 脚本 | 作用 |
|------|------|
| `patch_preamble.py` | 字体链（Songti SC/Heiti SC）、居中标题块、图/表中文编号（幂等） |
| `render_figures.py` | 按墨迹包围盒从 PDF 400 DPI 重绘 12 张图，写 `images_hi/manifest.json` |
| `convert_figures.py` | 把 OCR 图片桩 + 纯文本图注转成 `figure` 环境 + `\caption` |
| `fix_headings.py` | 合并跨行标题、把误提升为标题的正文还原为散文 |
| `fix_lost_math.py` | 按 PDF 恢复 80 处 U+FFFD 与文本模式 Unicode 数学符号 |
| `fix_figure_order.py` | 按论文顺序重排 chunk 11 的 Figure 9/10 |
| `merge_chunks.py` | 合并、去重标题、在标题块后注入目录 |
| `fix_after_normalize.py` | 附录 A/B/C 提升为 `\section`、`B.x` 降级为 `\subsection`、参考文献标题中文化 |
| `refine_terminology.py` | 按 DeepSeek 官方中文口径对齐术语（思考强度等，49 处） |
| `fix_table_width.py` | 把宽表首列改为可换行的 `L{}` 列并套 `\footnotesize`，使表格落入页边 |
| `audit_layout.py` | 对编译后的 PDF 做版面体检：文本重叠、右边界溢出、残留空列表标记 |
| `check_structure.py` | 对照基线校验 `\label`/`\caption`/`\tag`/`longtable` 等结构 token 未被改动 |
| `check_tables.py` | 校验每张 longtable 每行的 `&` 数与导言声明一致 |
| `verify_corrections.py` | 校核"某更正是否真在所指 PDF 页上"（折叠空白后检索） |

## 说明

- 本目录仅用于展示 OCR LaTeX 翻译、校验与编译工作流，不改变原报告署名与参考文献归属。
- 参考文献条目按策略保留英文原文；正文中保留英文的仅有模型名、基准名、脚手架名与工具名等专有标识。
- 作者名单（附录 A）保留拉丁原名，仅修复 OCR 吃掉的连字（fi/ff）等拼写损坏。
