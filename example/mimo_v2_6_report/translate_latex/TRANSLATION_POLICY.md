# 翻译策略 — MiMo-V2.6 技术报告中译

本文件是各翻译 subagent 的共享约定。**只读一次，不要重复研读。**

## 交付形态

把英文论文译为中文技术报告，产物是 XeLaTeX 源码（不是 Markdown、不是纯文本）。
每个 agent 只负责**一个** chunk 文件，原地覆盖写回。

## 必须翻译

- 正文散文、章节标题、图表标题（`\caption{}` 内的描述文字）。
- 表头单元格文字；表格内成句的描述（如 Table 2 的 "Illustrative case" 两列）。

## 必须原样保留（不得改动）

- 所有 LaTeX 命令与环境：`$...$`、`\[...\]`、`\begin{}...\end{}`、`\tag{}`、
  `\label{}`、`\ref{}`、`\cite{}`、`\includegraphics`、`\multirow`、`\multicolumn`、
  `\multicolumn` 的列数、`L{}`/`C{}` 列宽参数、`\footnotesize`、`\tabcolsep`。
- 数学公式**逐字符**保留（包括 `\ ` 空格风格，不要重排）。
- `\label{}` 的键名即使含 OCR 拼写错误也原样保留（它是 `\ref{}` 的锚点）。
- 参考文献条目整体保留英文。
- 附录 A（Contributions and Acknowledgments）的**作者姓名保留拉丁原名**。

## 保留英文的专有标识

模型名、基准名、脚手架名、库名、工具名、产品名一律保持英文：
MiMo-V2.6 / MiMo-V2.6-Pro / MiMo-V2.6-Flash / MiMo-V2.5-Pro / MiMo-ViT /
MiMo-Audio / Qwen3.5-9B / Claude Opus 5 / GPT-5.6 Sol / Claude Fable 5 /
GRPO / MoE / SWA / GA / MTP / RVQ / GRPO / MXFP4 / SFT / RL / OPD / MOPD /
Muon / Ray / DeepSWE v1.1 / ProgramBench / MiMo Code Bench / CyberGym /
ExploitGym / ExploitBench / SEC Bench Pro / AutomationBench / Toolathlon-Verified /
GDPval-AA 2.1 / Agents' Last Exam / Terminal Bench 4.0 / Terminal Bench 2.1 /
OSWorld-Verified / JobBench / OfficeQA Pro / MiMo Cyber Bench / MiMo Visual Coding /
MiMo General Bench / SWE-bench Verified / SWE-bench Pro / DFlash / MiniBench、
以及 `codex` / `claude code` / `mini-swe-agent` / `mini-harness1..4`。

## 术语表（全篇统一，务必遵守）

| 英文 | 中文 |
|---|---|
| reinforcement learning (RL) | 强化学习（RL） |
| recursive self-improvement (RSI) | 递归自我改进 |
| pre-training / mid-training / post-training | 预训练 / 中期训练 / 后训练 |
| rollout | rollout（保留英文，首次可注「采样展开」） |
| grader / grading | 评分器 / 评分 |
| groupwise agentic grading | 组内智能体评分 |
| groupwise reward synthesis (GRS) | 组内奖励合成（GRS） |
| groupwise advantage redistribution (GAR) | 组内优势重分配（GAR） |
| advantage | 优势 |
| reward hacking | 奖励作弊 |
| harness / agent harness | 脚手架 / 智能体脚手架 |
| agent / agentic | 智能体 / 智能体的 |
| trajectory | 轨迹 |
| policy | 策略 |
| importance sampling | 重要性采样 |
| clip / clipping | 裁剪 |
| entropy | 熵 |
| router (MoE) | 路由器 |
| expert / activated expert | 专家 / 激活专家 |
| on-policy distillation (OPD) | 同策略蒸馏（OPD） |
| distillation | 蒸馏 |
| teacher / student | 教师 / 学生 |
| prefix | 前缀 |
| speculative decoding | 推测解码 |
| multi-token prediction (MTP) | 多 token 预测（MTP） |
| tokenizer / codebook | 分词器 / 码本 |
| sliding window attention (SWA) | 滑动窗口注意力（SWA） |
| global attention (GA) | 全局注意力（GA） |
| hybrid-SWA backbone | 混合 SWA 主干 |
| omni-modal | 全模态 |
| context length | 上下文长度 |
| batch size | 批大小 |
| throughput | 吞吐 |
| data plane / control plane | 数据面 / 控制面 |
| verifier | 校验器 |
| rubric | 评分细则 |
| pass rate | 通过率 |
| held-out | 留出（held-out） |
| unweighted average | 未加权平均 |

## 标题处理（供后续 normalizer 使用）

- 译文保留 OCR 的数字前缀：`\subsection{4.1 Scaling RL Training Computation}`
  → `\subsection{4.1 扩展 RL 训练算力}`。normalizer 之后会剥掉 `4.1`。
- 多行标题**合并成一行**（normalizer 逐行匹配，看不见跨行标题）。
- Abstract / References 标题保持 `\subsection{Abstract}` / `\subsection{References}`
  这个**英文形式不变**（合并脚本靠它定位目录插入点），标题文字不要改。

## 风格

- 中文技术报告语体，句子直白，不用「首先/其次/最后」凑结构，不加主观评价。
- 标点用全角（，。；：（）），但公式、英文短语、代码内保持半角。
- 英文缩写首次出现时给中文全称 + 缩写，如「滑动窗口注意力（SWA）」。
- `Figure X:` / `Table X:` 前缀已由 `\caption` + `\renewcommand` 生成中文编号，
  正文中提到图/表时写「图 3」「表 1」（半角数字，前后不加空格）。

## 边界与禁止

- **不要重新调查已核实的修正**：本目录的 OCR 修复（数学符号、连字、公式、表格宽度）
  已完成并逐条对照过 `pdf_pages/`，不要再打开 PDF 复核。
- **不要改写论文结构**：不删标题、不合并章节、不调整段落顺序。
- **不要"改进"内容**：不补写、不删减、不做事实性改写。
- 若确实遇到语义无法确定的句子，保留原意直译，并在该行末加
  `% CHECK: <一句说明>` 注释，不要停下来反复查证。
