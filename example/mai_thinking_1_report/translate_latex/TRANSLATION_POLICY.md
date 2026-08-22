# MAI-Thinking-1 翻译策略（所有翻译 agent 必读）

本文件是各翻译 agent 的共享策略。任务：将 `chunk_XX_*.tex`（英文 OCR LaTeX）翻译为中文，**原地覆盖写回同一文件**。

## 输入材料

1. **待译文件**：`archive/MAI-Thinking-1_translate/parts/chunk_XX_*.tex`（你的块）
2. **PDF 参考文本**（权威真相，用于交叉验证）：
   - 整本逐页文本：`archive/MAI-Thinking-1_translate/pdf_pages/page_NNN.txt`（001-109）
   - 本块对应页范围见 `CHUNK_MAP.json`，相应页已复制到 `bundle_XX/` 子目录
3. OCR 输出有噪音，**任何可疑处以 PDF 页文本为准**。

## 翻译规则（核心）

1. 英文正文 → 中文；章节/小节标题 → 中文（保留数字前缀：`\subsection{2.1 Model Architecture}` → `\subsection{2.1 模型架构}`；无前缀的 `Abstract` → `摘要`，`References` → `参考文献`，`Contents` → `目录`）。
2. **绝对保留原文**：所有 LaTeX 命令、环境、数学公式（`$...$`、`$$...$$`、`\[...\]`、`\begin{...}`）、表格环境（longtable/multirow/multicolumn/行内容）、`\includegraphics{...}`（含文件名）、`\label{}` 键（即使含拼写错误也不改）、`\href{}`/URL。
3. **保留英文**：模型名（MAI-Thinking-1、MAI-Base-1 等）、基准名（AIME、SWE-Bench、LiveCodeBench 等）、技术标识符、库/框架名、文件名、作者名、引用条目（References 只译标题"参考文献"）。
4. 图表题注：`Figure X.` → `图 X.`；表格表头文字译成中文，**表内数据值不改**。
5. 多行标题合并为一行：`\subsection{2.4 Pre‐training\nData}` → `\subsection{2.4 预训练数据}`。
6. 附录标题：`\subsection{B Pre‐training Data Pipeline Details}` → `\subsection{B 预训练数据管线细节}`。
7. 代码块/伪代码/JSON/命令行：结构保留，注释译中文。

## 本文档特有的 OCR 已知缺陷（必须修复）

1. **fi/ff 连字丢失**（全书系统性）：`eficiency→efficiency`、`efort→effort`、`diferent→different`、`afected→affected`、`ofer→offer`、`coefect→coeffect`、`ofset→offset`、`first-class` 里的 `irst` 等。对照 PDF 页文本逐处修复。
2. **其他 OCR 错词**：如 `evalulation→evaluation`、`dificulty→difficulty`。对照 PDF。
3. **脚注误置为正文**：正文中孤立的 `1Correspondence should be sent to mai-technical-report@microsoft.com. Please cite as shown in Appendix A.` 应转为 LaTeX 脚注：`\footnote{Correspondence should be sent to mai-technical-report@microsoft.com. 引用格式见附录 A。}`（放在出现处所在段落末尾）。
4. **已被剔除的行**：切分脚本已移除页码残行（每页底部独立数字），不应出现新的纯数字行。
5. **已修复项**：`\subsection{6 Cluster Environment}` 已补回；`\$` 已还原为 `$`。
6. `ofLiveCodeBench`（缺空格）→ `of LiveCodeBench`。
7. 表格单元内 `\` 换行符、`&` 分隔符保持原样不动。

## 工作步骤

1. 读 `bundle_XX/` 里本块的 PDF 页文本，了解内容与正确拼写。
2. 读待译块文件。
3. 按上述规则翻译并修复 OCR 错误；**数字、百分数、指标、模型参数以 PDF 页文本为准**（如 52.8%、97.0%、35B active / 1T total、8K GB200、30T tokens）。
4. **原地覆盖写回同一文件**（UTF-8）。
5. 最终回复报告（供主会话汇总）：行数变化、修复的连字/错词数量、发现的重大 OCR 缺陷或无法确定处、是否对照了 PDF 页。

## 常见 LaTeX 转中文注意

- `Pre‐training` 的 `‐`（U+2010）译 `预训练`；`Co‐optimizing` → `协同优化`；`Side‐by‐Side` → `并排对比`。
- `%` 在 LaTeX 是注释符：正文里的百分号若在行尾或单独出现需检查；原文数字后的 `\%` 保持 `\%`。
- 长表格（longtable）行内容里含 `\` 表示换行，保留。
- 不确定的英文句意以 PDF 页文本为准，PDF 页文本是最终裁决。
