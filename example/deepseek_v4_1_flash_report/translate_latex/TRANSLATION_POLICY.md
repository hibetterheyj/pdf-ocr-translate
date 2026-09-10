# 翻译策略 — DeepSeek-V4.1-Flash 技术报告

所有翻译 subagent 必须遵循本文件。目标：产出可直接 XeLaTeX 编译的高质量中文 LaTeX，
公式、引用、图表编号全部保持原样。

## 一、翻译什么

| 内容 | 处理 |
|---|---|
| 正文散文 | 译成中文 |
| 章节标题（section/subsection/subsubsection） | 译成中文 |
| 图注 / 表注（`\caption{...}` 与 `Table N \textbar{} ...` 段落） | 译成中文，`Figure X`→`图 X`、`Table X`→`表 X` |
| 算法伪代码的说明注释 | 译成中文 |
| 表头、表内文字单元格 | 译成中文（数字、单位、模型名保持原样） |
| 参考文献条目 | **保留英文原文**，仅修 OCR 错误；`\section*{参考文献}` 标题译成中文 |
| 作者名单（附录 A） | 人名保留原文，职务/机构名译成中文 |

## 二、必须原样保留

- **所有 LaTeX 命令与环境**：`\begin{...}`/`\end{...}`、`\label{}`、`\ref{}`、
  `\cite{}`、`\includegraphics{images_hi/figNN}`、`longtable`、`\multirow`、`\multicolumn`、
  `\toprule`/`\midrule`/`\bottomrule`、`\tag{N}`。
- **所有数学**：`$...$`、`\(...\)`、`\[...\]`、`equation`/`align` 环境，逐字符照抄。
- **`\label{}` 的 key**：即使有 OCR 拼写问题也不要改，它们是 `\ref{}` 的锚点。
- **技术标识符**：模型名（DeepSeek-V4.1-Flash、DeepSeek-V4-Flash、DeepSeek-V4-Pro）、
  基准名（DeepSWE v1.1、Terminal-Bench v2.1、FrontierSWE v2、ProgramBench、AIME 2026、
  MathArena Apex 2025、GPQA Diamond、HLE、IMO-AnswerBench、LiveCodeBench、SimpleQA-Verified、
  MMLU-Pro、C-Eval、BBH、BBEH、DROP、BigCodeBench、HumanEval、GSM8K、LongBench-V2、
  MMMU-Pro、CVBench、DocVQA）、模块与机制名（CED、CSA2、mHC、Mega-mHC、Engram、DSpark、
  SWA、MoE、DeepSeekMoE、KV cache、Top-K、FP4、FP8、BF16、Sinkhorn、Muon、AdamW）、
  工具与框架名（Claude Code、Codex、OpenCode、Pi、mini-SWE、DeepSeek Harness/DSH、
  Kubernetes、AppArmor、eBPF、SGLang、vLLM）、版本号与数字。
- **URL、邮箱、commit hash**（如 `https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash`、
  `research@deepseek.com`、`04d809ceab9d`）。

## 三、标题处理

保持 OCR 的数字前缀，标题文字译成中文。后续 `normalize_heading_levels.py` 会统一层级：

- `\subsection{1. Introduction}` → `\subsection{1. 引言}`（脚本会剥掉 `1.` 并提升为 `\section`）
- `\subsection{2.1. Overview}` → `\subsection{2.1. 概览}`
- `\subsection{2.1.1. Multimodal Architecture}` → `\subsection{2.1.1. 多模态架构}`
- 附录：`\subsection{A. Author List}` → `\subsection{A. 作者名单}`
- **不要**自己改 `\section`/`\subsection` 的层级，也不要加/删 `\label{}`。

## 四、术语对照（统一用词）

| 英文 | 中文 |
|---|---|
| KV cache | KV 缓存 |
| persistent KV cache | 持久化 KV 缓存 |
| prefill / decode | 预填充 / 解码 |
| context length | 上下文长度 |
| causal encoder / decoder | 因果编码器 / 解码器 |
| sparse attention | 稀疏注意力 |
| sliding window attention (SWA) | 滑动窗口注意力（SWA） |
| compression ratio | 压缩率 |
| indexer | 索引器 |
| candidate pool | 候选池 |
| residual stream | 残差流 |
| activation memory traffic | 激活内存访问量 |
| speculative decoding | 推测解码 |
| drafter | 草稿模型 |
| rollout | rollout（保留英文） |
| scaffold | 脚手架 |
| effort level / tier | 思考强度档位 / 档位 |
| thinking mode | 思考模式 |
| cache hit / miss | 缓存命中 / 未命中 |
| agent / agentic | 智能体 / 智能体（agentic） |
| trajectory | 轨迹 |
| reasoning effort | **思考强度**（DeepSeek 官方中文口径；首现可注 effort） |
| post-training | 后训练 |
| pre-training | 预训练 |
| SFT / RL / OPD | 保留英文缩写，首现给出中文全称 |
| distillation | 蒸馏 |
| on-policy distillation | 同策略蒸馏 |
| benchmark | 基准（benchmark） |
| throughput | 吞吐 |
| latency | 延迟 |
| long-horizon | 长程 |
| near-duplicate / dedup | 近重复 / 去重 |

> 术语以 DeepSeek 官方中文文档为准：
> `https://api-docs.deepseek.com/zh-cn/guides/thinking_mode/`（思考模式开关与**思考强度控制**）、
> `https://api-docs.deepseek.com/zh-cn/news/news260910/`（V4.1-Flash 发布说明）。
> 原文 "reasoning effort" 对应官方的「思考强度」，不要译成「推理努力」。

## 五、文体要求

- 直译为主，忠实原意；不要增删内容，不要加译者按语。
- 中文行文简洁，避免 AI 味（不要"值得注意的是""总而言之"这类填充）。
- 保留原文的段落划分与换行结构，不要重排段落。
- 数字、百分比、单位、公式编号一律不动。

## 六、交叉校验（本任务的核心要求）

每个 chunk 都对应源 PDF 的若干页，页文本在 `../pdf_pages/page_NNN.txt`。
**印刷页码 N 就是 `page_NNN.txt`**（`page_001.txt` 是无页码的标题页）。
注意 PDF 文件的物理页索引比印刷页码大 1（标题页占首位），换算到 pymupdf 时别数错。

**强制要求**：翻译前先对照 PDF 页文本核查以下内容，发现不符**以 PDF 为准**修正：

1. **数字与分数**：参数规模、token 数、基准分数、倍数（如 `4-fold`、`437-fold`、`1/8`）。
2. **表格单元格**：OCR 常把相邻单元格串行或错位；逐格与 PDF 对照重写。
3. **模型/基准名拼写**。
4. **公式**：对照 PDF 检查上下标、变量名是否被 OCR 弄错。
5. **连字丢失**：MinerU 会吃掉 fi/ff 连字（`eficiency→efficiency`、`diferent→different`、
   `ofer→offer`、`coefcient→coefficient`、`Trainingfor→Training for`）。逐处修正。
6. **`\textbar{}` 图注**里的 `Figure N` / `Table N` 编号必须与 PDF 一致。

如果发现 OCR 与 PDF 有出入，**在回执中列出你修正的每一处**，格式：
`chunk 文件名 | 行号 | OCR 原文 → 修正后 | PDF 依据页`。

## 七、交付

1. **原地修改**你的 chunk 文件（`parts/<chunk>.tex`）。
2. 回执给我：chunk 名、翻译的章节范围、你做的 PDF 交叉校验修正清单、任何无法确定的疑点。
3. 不要动 `parts/` 之外的任何文件。
