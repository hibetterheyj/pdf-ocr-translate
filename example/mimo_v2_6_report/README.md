# MiMo-V2.6 技术报告中译 — pdf-ocr-translate 完整示例

使用 `pdf-ocr-translate` skill 对 MiMo-V2.6 技术报告（44 页英文原版）执行 OCR LaTeX 中译的完整工作示例。

## 来源

- **原始 PDF**：`MiMo-V2.6-Technical-Report.pdf`（44 页，矢量绘制，正文数学变量用 `XCharterMathMI` 字体）
- **OCR LaTeX**（两个 pass，本示例的交叉验证对象）：
  - `ocr_latex/MiMo_V26_ocr_latex_v1.tex` — MinerU **VLM** 识别版本（2,667 行）
  - `ocr_latex/MiMo_V26_ocr_latex_v2.tex` — MinerU **二阶段**流水线识别版本（2,774 行）
  - `ocr_latex/images/` — 45 张 OCR 切图
- **中文成品**：`MiMo-V2.6-Technical-Report_CN.pdf`（42 页）

## 翻译统计

| 指标 | 值 |
|------|-----|
| 源 tex 行数（二阶段基准） | 2,774 |
| 交叉验证取材 | 正文取二阶段版、**7 张表全部取 VLM 版**、公式 (1) 取 VLM 版 |
| 切分块（chunks） | 14（preamble + 正文 13） |
| 翻译 agent | 13（每块一个，无重发、无超时） |
| 中文字符数 | 22,927 |
| 恢复的丢失数学符号（U+FFFD） | 24 处 |
| 修复的连字丢失（ff/fi/fl） | 97 处 / 33 种词形 |
| 重绘的高清图 | 17 张（400 DPI，源自 PDF 矢量图）+ 1 个页眉 logo |
| 重排宽度的表格 | 5 张（Table 1/2/3/6/7） |
| 从正文段落改回 `\caption` 的表格 | 7 张（含把 Table 4 的图注从表下移到表上） |
| 从散落文本改回 `\footnote` 的脚注 | 2 处 |
| 剔除的页码残行 | 43 行 |
| 最终 PDF 页数 | 42 页 |
| 编译错误 / 缺字形 / 溢出行 | 0 / 0 / 0 |
| 字体 | Songti SC（STSongti-SC） |

## 目录结构

```
mimo_v2_6_report/
├── MiMo-V2.6-Technical-Report.pdf      # 原始英文 PDF（44 页）
├── MiMo-V2.6-Technical-Report_CN.pdf   # 中文翻译 PDF（42 页，0 错误 0 缺字形）
├── ocr_latex/                          # MinerU OCR 原始输出（保留原样，供对照）
│   ├── MiMo_V26_ocr_latex_v1.tex       #   VLM 识别版本
│   ├── MiMo_V26_ocr_latex_v2.tex       #   二阶段识别版本
│   └── images/                         #   45 张 OCR 切图
├── pdf_pages/                          # pymupdf 逐页文本层（44 页）
│   └── page_001.txt ... page_044.txt   #   交叉校验的权威参考
└── translate_latex/                    # 翻译工程
    ├── build_source.sh                 #   ① 从两个 OCR 输出重建 main.tex（译前，会覆盖 parts/）
    ├── assemble.sh                     #   ② 合并 → 归一化 → 编译（译后，一键复现成品）
    ├── main.tex                        #   译前基准（2,724 行）
    ├── main_cn.tex                     #   合并 + 标题规范化后的中文主文件（1,729 行）
    ├── images_hi/                      #   17 张 PDF 高清重绘图 + title_logo.png + manifest.json
    ├── parts/                          #   14 个翻译块 + CHUNK_MAP.json
    ├── TRANSLATION_POLICY.md           #   多 agent 共享翻译策略（含术语表）
    └── *.py                            #   各阶段脚本，见下表
```

## 交叉验证：VLM 版 vs 二阶段版

本示例的主要结论是：**两个 OCR pass 不等价，且不是全面优劣，而是各坏一半。**
归一化空白与数学空格风格后，两份 tex 的行级相似度只有 **87.8%**（149 个差异块）。
逐项对照 `pdf_pages/` 后，裁剪方案定为「正文取二阶段、表格与关键公式取 VLM」。

### VLM 版更好的地方

| 位置 | 二阶段版的问题 | VLM 版 |
|------|---------------|--------|
| **Table 1** 模型配置 | `\multicolumn` 从 22 处掉到 **0** 处——编码器各列本该跨 Flash/Pro 两列的值被压进单列；`# Total Parameters` 与 `# Active Parameters` 两行被并成一行裸数据；`Speculative Decoder` 整组标签丢失；`Spatial Merge Size` 被并进上一行 | 结构完整 |
| **Table 3** 主结果矩阵 | 12 个 `-` 占位符只剩 1 个——**未测的单元格变成空白**，读者无法区分「没测」和「没漏」 | 12 个 `-` 齐全 |
| **Table 7** 多脚手架 | 表头多出一行空白行，`\multirow` 归零 | 表头两行正确 |
| **Table 2** 奖励作弊案例 | 单元格被拆到多行，一行一个词 | 单元格完整 |
| **Table 6** 蒸馏结果 | 列数声明成 6（实为 5），一个数值被推进幽灵列 | 5 列正确 |
| **公式 (1)** RL 目标 | `\bigcup_{d}_{\mathcal{D}_d}` —— **双重下标，是硬编译错误**；且把 rollout 样本 `o_i` 写成了 `\mathcal{D}_i` | 与 PDF 一致 |

### 二阶段版更好的地方

- **正文分词更干净**：以 PDF 文本层为词典统计，二阶段版 28 处词内误插空格，VLM 版 34 处（`fur ther`、`sig nals`、`com ponents`）。
- 数学符号丢失量略少：二阶段 24 个 U+FFFD，VLM 22 个——**但两者丢的是同一批符号**，换版本救不回数学（与 DeepSeek-V4.1-Flash 示例同一结论）。

### 最终取材

`build_hybrid.py` 把二阶段版的正文与 VLM 版的 7 张表（其中 2 张两版相同，实际替换 5 张）拼成 `main.tex`；
公式 (1) 由 `fix_lost_math.py` 按 PDF 用 VLM 的转写替换。两处都有脚本留痕，可重放。

## 数学与文本修复

1. **24 个丢失的数学符号**。正文数学变量用 `XCharterMathMI`（Unicode Mathematical Italic），MinerU 无法映射，一律写 U+FFFD；pymupdf 的 `get_text("text")` **也丢这些字**，所以纯文本比对看起来无解。
   改用 `get_text("dict")` 读 span 级字体信息后全部可读（`recover_math_glyphs.py`）。恢复清单逐条在句子里读过再定，例如：
   `It stacks ‹M› hybrid blocks … with ‹N› consecutive SWA blocks`、`sliding window size ‹W›`、
   `group size ‹G›=16`、`where ‹r› denotes the importance sampling ratio, ‹M› the mask, ‹A› the advantage`。
   **一个符号错照样编译通过、渲染也像模像样**，所以这步不能跳过读句子。

2. **`\hat{R}` 应为 `\bar{R}`**（第 18 页）：PDF span 显示的是 macron（`¯𝑅`），且全文其他地方都用 `\bar{p}`。MinerU 把横线读成了帽子。
   同类还有第 20 页的 `the ethreshold`——那个 `e` 是前一句 `\widetilde{R}` 的波浪号溢出到下一个词，已删。

3. **97 处连字丢失 / 33 种词形**。两份 OCR 都丢 ff/fi/fl 连字里的 `f`：`efective→effective`、`ofline→offline`、`bufer→buffer`、`diferences→differences`，参考文献作者名里也有（`Laufer→Lauffer`、`Sutclife→Sutcliffe`、`Muennighof→Muennighoff`）。
   判定标准是**双向**的：坏拼写不出现在 PDF 文本层、修好的拼写出现。只靠词典两个方向都会错——它会「修」从未坏过的专名（`Guo→gulo`），又会漏掉词典没有的屈折形式（`/usr/share/dict/words` 里没有 `efforts`，`eforts` 因此一度漏网，直到改用 PDF 文本层当词典才捞出来）。

4. **被字母间距拉散的 URL**（第 41 页参考文献）：pymupdf 把这一条 URL 逐字符析出（`h t t p s : / / g i t h u b . c o m / v l l m- p`），MinerU 原样抄了下来。
   用 PDF 自身的 link annotation 取到真值 `https://github.com/vllm-project/humming/releases/tag/v0.1.15` 写回。
   顺带核对了**全部 58 个 PDF link target 都在译文里**，无链接丢失。

5. **`∼`（U+223C）** 在摘要里是纯文本，拉丁现代字体没有这个字形，编译时静默消失（`Missing character`）。已包进 `$2.7\sim$`。

## 图表处理

1. **31 个图注桩 → 17 张图**。MinerU 把多面板图切成一块一个位图（图 1 拆成 6 块 ~400×300 的碎片、图 17 拆成 5 块），且是屏幕分辨率。
   源 PDF 的图是矢量绘制的，`render_figures.py` 按**图注上方的墨迹包围盒**以 400 DPI 重绘，标签锐利、体积反而更小。
   裁剪框是算出来的不是手写的：图注必须紧邻图墨迹（排除「Figure 11 compares …」这类正文交叉引用），横向范围按实测墨迹取而非固定栏宽（图 4 的框比正文栏更宽，固定栏宽会切掉两侧面板）。
   重绘后包成 `figure` + `\caption` + `\label`，由 LaTeX 自己编号；实测输出图号严格 1→17，与原文一致，正文里的「图 9」等引用不会错位。

2. **页眉 logo**。原文标题页顶部是 Xiaomi MiMo 字标 + 图标，MinerU 把它读成了正文里一行多余的 `Xiaomi MIMO`。改为按页眉墨迹裁出位图，放进居中标题块。

3. **图 13 / 图 17 的子图标签**。这两张图的 (a)(b)(c) 面板标签被 MinerU 输出成 `enumerate` 块。重绘图里已经含这些标签，因此整块删除（否则会重复打印两遍）。

4. **5 张宽表重排**。MinerU 一律用 `l` 列，而 `l` 不换行：首次编译时 Table 3 超出正文栏 **1247pt**（正文栏本身才 500pt），Table 7 超 153pt。
   做法是把标签列与模型名列改成固定宽的 `L{}`/`C{}` 列（宽表另把列间距减半到 3pt），整组套 `{\footnotesize …}`。
   **`\footnotesize` 必须包在 `longtable` 外层**——放进对齐导言区（`\endlastfoot` 之后）会触发 `Misplaced \noalign`。
   修完 0 溢出行。注意 `C{}`/`L{}` 里宽度用 `em` 才跟得住字号。

5. **页码残行**。OCR 把每页页脚的页码抄成了独立成行的数字，切分脚本自动剔除 43 行。

## 表格与脚注的收尾（第二轮）

首版编译后修的四处「结构对了但不符合惯例」：

1. **表格图注改回 `\caption`，并统一放到表上方**。MinerU 把图注输出成普通正文段落
   （`表 3 MiMo-V2.6 与上一代模型…`），表体是裸 `longtable`，且包裹层写着
   `\def\LTcaptype{none}` —— 意思是「不编号」。
   后果有二：一是表号写死在文字里、不受 LaTeX 管理；二是**图注的位置随 OCR 阅读顺序漂移**，
   本次 Table 4 的图注落在表**下**方，而 Table 5 的图注紧接其后，两段连在一起读起来像是
   都在给 Table 5 当注。
   `fix_table_captions.py` 把图注搬到 `\begin{longtable}` 正下方、去掉 `\def\LTcaptype{none}`
   让表号由 LaTeX 生成（实测输出 表 1…表 7 与正文引用一一对应），并统一套 `{\footnotesize}`。
   Table 1 跨页时，续页改为右侧「（续表）」标记而不是把整条图注再印一遍
   （`\endfirsthead` / `\endhead` 的标准用法）。

2. **脚注从散落文本改回 `\footnote`**。MinerU 把脚注拆成两截：正文里那个上标数字黏在前一个
   词后面（`CyberGym（Wang et al., 2025）1、`、`…Distill-Qwen-9B,2，`），脚注原文则连着这个
   数字单独成段掉在页面底部（`2https://huggingface.co/XiaomiMiMo/…`）。渲染出来就是正文中间
   一个孤零零的「1」和下方一段莫名其妙的「2https://…」。`fix_footnotes.py` 把两截接回去，
   共 2 处。URL 包进 `\url{}` 靠已加载的 `xurl` 断行。

3. **图注泄漏进正文的模型名**。图 17 是网页截图九宫格，其列表头
   （`Qwen3.5-9B` / `MiMo-V2.6-Distill-Qwen-9B SFT RL`）被 MinerU 当成正文读了出来，而且
   落点离开图整整一节，正好在 `参考文献` 前面，读起来像两个孤立的模型名。
   重绘的 `fig17.png` 里已经带这两行表头，`strip_leaked_figure_labels.py` 删掉正文里的副本
   （只匹配独立成行的整行，不会误伤同名的表格行标签）。

4. **Table 1 没有对齐**。四列合计只有 44em ≈ 367pt，而正文栏宽 498.6pt；`longtable` 默认居中，
   于是表的左缘停在页边距内侧 66pt 处 —— 既不像居中（表头两列各自换行、参差），也不像左对齐
   （与上方图注和正文都对不齐）。列宽改用**原报告第 6 页量出来的列比例**（标签 126pt / 配置
   155pt / Flash 89pt / Pro 79pt，占 449pt 表宽），再按正文栏宽等比放大，表就铺满了。
   两列模型名各占一行后，表头与数据列逐列对齐。

5. **表格图注比表格窄、还居中**。`longtable` 把 `\caption` 排进一个宽度为 `\LTcapwidth` 的盒子，
   而**这个长度默认是 4in（约 289pt），与表格实际宽度无关**。在 480pt 宽的表里，图注就渲染成
   一个窄盒子，还居中摆在表格中间 —— 左缘既不对齐表格，也不对齐正文。原报告的图注是铺满整栏的，
   `\setlength{\LTcapwidth}{\textwidth}` 即可。**`\textwidth` 是 498.6pt 不是 480pt**：
   这个模板用的是 US Letter（612pt）配 `margin=2cm`，别再按 A4 估。

6. **短图注被居中**。长宽都修好后剩下一个不一致：Table 3 的图注只有一行，却居中排在页面中间，
   而 Table 1 的两行图注是左对齐的。这是 `longtable`（以及标准 `caption`）的固有行为 ——
   `\LT@makecaption` 会先量一下 `\wd\@tempboxa`，**能排成一行就 `\hfil…\hfil` 居中，排不下才左对齐**。
   加载 `caption` 宏包并设 `singlelinecheck=false` 即可关掉这个「单行居中」；顺带把标签改成加粗、
   分隔符改成 quad 空格（`表 1␣␣正文`），与原报告一致 —— 这条对图表一视同仁。

## 排版收尾

- **目录插在标题块之后**。合并脚本在 preamble chunk 末尾的摘要标题之前注入 `\tableofcontents`；若按「紧跟 `\begin{document}`」插入，目录页会跑到标题页前面。
- **手搓目录已删**。MinerU 把印刷版目录抄成纯文本列表（`1 Introduction 3\`），页码是英文版的、会误导。它在摘要之后、不在块边界上，切分脚本的 `DROP_AT_MERGE` 机制看不到，因此由 `strip_ocr_contents.py` 在源头删除。
- **`\contentsname` 必须放正文区**（polyglossia 会在语言激活时重置），且与 `\tableofcontents` 同处一行块内。
- **图/表编号需显式中文化**：`\renewcommand{\figurename}{图}`、`\renewcommand{\tablename}{表}`。
- **标题层级归一化**后：`\subsection{4.2.1 代码智能体任务}` → `\subsubsection{…}`，`\subsection{A 贡献与致谢}` → `\section{贡献与致谢}`（字母留在 `\label{}` 里）。
  Abstract / References 两个标题刻意保留英文交给归一化器识别，之后再由 `fix_after_normalize.py` 改成 `\section*{摘要}` / `\section*{参考文献}`。

## 校验结果

```
编译错误          0
缺字形(Missing character) 0
溢出行(Overfull \hbox)    0
版面审计         0 边界溢出 / 2 处重叠 / 0 残留列表标记
```

那 2 处「重叠」是第 19 页公式 (5) 的大括号——`\left\{` 在 PDF 里由多段 CMEX10 字形纵向拼成，包围盒天然互相重叠，属审计工具的已知误报（渲染无问题，见图）。

数值保真另做了两项机械核对：

- **正文全部数字**与 PDF 文本层比对，284 个数字里 9 个不在 PDF 中，逐一查明：5 个是排版参数（`0.26`/`0.66`/`0.34` 列宽、`1.2` 行距、`999999` 颜色值），3 个是中文单位换算（`20 million`→`2000 万`、`77.4B`→`774 亿`、`27.2B`→`272 亿`），1 个是 Django ticket `#29205`（PDF 第 15 页确有）。
- **Table 3 的 88 个数值**全部出现在 PDF 第 26–27 页，无一杜撰。

## 关键发现

1. **两个 OCR pass 抓不同的错，不能只留一个**。VLM 版看得见版面，表格结构完整；二阶段版正文分词更干净，但会把表格拍平、把 `-` 占位符当空值丢掉、并把 RL 目标函数写成双重下标。任何「哪个版本更好」的单选都会丢东西。DeepSeek-V4.1-Flash 那次两版相似度 98.9%、结论是「几乎等价」；**这次只有 87.8%，结论相反**。

2. **`-` 占位符丢失是静默的语义损伤**。Table 3 里 `-` 表示「该模型没跑这个基准」，二阶段版把它删成空单元格，编译不会报任何错，表格看起来也正常——只是读者会把「没测」读成「测了但空白」。这类错误只有比对原表才能发现。

3. **切分脚本与合并脚本的命名约定不一致**（两处都是 skill 自带脚本的真实缺陷，本次发现并已在上游修复）。
   `split_translation_chunks.py` 产出 `chunk_00_preamble.tex` + `NN_<name>.tex`，而
   `merge_translation_chunks.py` 用 `re.match(r'chunk_\d+', f.name)` 过滤——按过滤规则会
   **把所有正文块丢掉，只剩 preamble**；就算放宽过滤，按字典序也会把 `01_body.tex` 排在
   `chunk_00_preamble.tex` 前面。
   合并脚本还有第二处：它在**正文块**里找摘要标题来定位目录插入点，而切分脚本把标题块和
   摘要标题都留在了 preamble 块的末尾，于是永远找不到、目录静默不注入。
   本示例当时自带 `merge_chunks.py` 绕开这两点；上游已修复（`fix: repair chunk merging and
   custom column types in the skill scripts`），示例保留自己的合并脚本只是为了它额外的
   `\clearpage` 与三项自检输出。

4. **`check_tables.py` 读不了自定义列类型**（同样已在上游修复）。它按固定的字母表数列，而
   `L{13em}C{7em}` 这类 `\newcolumntype` 里的 `C` 不在表内，于是把 9 列的表数成 1 列，
   报了 50 条「列数不符」的假警报——**假警报掩盖了它本该抓到的真问题**。
   修复后它只报 1 条：表 7 的子表头行少一格（该行末尾那一格被上方 `\multirow` 覆盖，
   LaTeX 会当空格补上，所以渲染一直是对的，但行本身确实不完整）。
   现在加了 `--fix`，会把这类「末尾缺格」的行补齐；本示例的 `assemble.sh` 已把它接进流程。

5. **并行 agent 全部一次通过**。13 个 agent 各 4–7 次工具调用、无一耗尽上下文。区别在于这次**校验收在切分之前做完**：数学、连字、表格宽度、图片都已修好并写进 `main.tex`，agent 拿到的是一份「已核实、不要重新调查」的清单，没有一个是停下来反复读 PDF 的。（DeepSeek 那次 13 个 agent 挂了 5 个，全是反复读 PDF 做校验的。）

6. **列宽脚本重跑会静默复制整张表**。`fix_table_width.py` 定位表格包裹层时用的是对标记串
   `{\def\LTcaptype{none}` 做全局 `rfind`。第一次运行没问题（所有表的包裹层都长这样），但
   跑完之后它自己会把包裹层改写成 `{\footnotesize\def\LTcaptype{none}` —— 这时再跑第二遍，
   `rfind` 就跳过这些已处理的表，回溯到**前一张还没处理的表**的包裹层，于是把两张表之间的
   整段内容当成一张表的块又输出一次。实测 7 张表变成 9 张、表 5 被套上表 6 的列宽。
   改成从 `\begin{longtable}` 往上找最近的非空行来定位包裹层后就幂等了。
   **这类「脚本本身不幂等」的坑只有重跑才会暴露**，而本项目的设计恰恰要求同一批 pass 既在
   `build_source.sh` 跑、又在 `assemble.sh` 跑。

## 复现要点

```bash
cd translate_latex

# ① 译前：从两个 OCR 输出重建 main.tex（会 rm -rf parts/，译后勿跑）
PY=/path/to/env/data_env/bin/python ./build_source.sh

# ② 翻译：13 个 chunk 并行翻译（本示例由 subagent 完成）
#    parts/01_body.tex ... parts/13_body.tex

# ③ 译后：合并 + 归一化 + 编译，产出 build/final/main_cn.pdf
PY=/path/to/env/data_env/bin/python ./assemble.sh
```

各阶段脚本：

| 脚本 | 作用 |
|------|------|
| `build_hybrid.py` | 二阶段版正文 + VLM 版表格拼成基准 `main.tex` |
| `fix_ocr_artifacts.py` | （skill 脚本）转义 `\$`、文本模式 Unicode 数学、控制字符、数学区内 pandoc 转义 |
| `fix_lost_math.py` | 24 处 U+FFFD、公式 (1)、`\bar{R}`、字母间距 URL、`∼` —— 每条都注明取自 PDF 第几页 |
| `fix_ligatures.py` | 97 处 ff/fi/fl 连字丢失，双向对照 PDF 文本层判定 |
| `fix_table_width.py` | 5 张宽表的 `L{}`/`C{}` 列宽与 `\footnotesize` 包装 |
| `fix_table_captions.py` | 图注段落 → 表上方 `\caption{}`/`\label{tab:N}`，去除不编号开关，续页用「（续表）」 |
| `fix_footnotes.py` | 正文上标数字 + 页底孤立脚注段 → `\footnote{}`（2 处） |
| `strip_leaked_figure_labels.py` | 删除从图 17 泄漏到正文的列表头 |
| `convert_figures.py` | OCR 图注桩 → 17 个 `figure` 环境；删除已烘进重绘图的子图标签 |
| `render_figures.py` | 按图注上方墨迹包围盒 400 DPI 重绘 17 张图 + 页眉 logo，写 `images_hi/manifest.json` |
| `strip_ocr_contents.py` | 删除 MinerU 手搓的英文页码目录 |
| `patch_preamble.py` | 字体链（Songti SC/Heiti SC）、居中标题块、图表中文编号、`xurl`、`L{}`/`C{}` 列类型、`\LTcapwidth`、图注样式（幂等） |
| `split_translation_chunks.py` | （skill 脚本）按标题边界切块，写 `CHUNK_MAP.json` |
| `merge_chunks.py` | 按序号合并 14 块、在标题块后注入目录、补回 `\end{document}` |
| `normalize_heading_levels.py` | （skill 脚本）OCR 数字标题还原层级 |
| `fix_after_normalize.py` | `\section*{Abstract}`→`摘要`、`\section*{References}`→`参考文献` |
| `audit_layout.py` / `check_structure.py` / `check_tables.py` | （skill 脚本）版面体检 / 结构 token 对照基线 / 表列数校验（见「关键发现」第 4 条） |

## 说明

- 本目录仅用于展示 OCR LaTeX 翻译、校验与编译工作流，不改变原报告署名与参考文献归属。
- 参考文献条目按策略保留英文原文；正文中保留英文的仅有模型名、基准名、脚手架名与工具名等专有标识。
- 附录 A（贡献与致谢）的**作者名单保留拉丁原名**，仅修复了 OCR 吃掉的连字拼写损坏。
- 表 2 `Illustrative case` 列里引号内的智能体思考轨迹（`Let me check the pytest changelog …`）刻意保留英文——那是原文引用的模型输出，不是待翻译的叙述文字。
