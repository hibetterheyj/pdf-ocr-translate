\section{预训练}\label{pre-training}

\subsection{数据构建}\label{data-construction}

在 DeepSeek-V3 的预训练数据基础上，我们致力于构建一个更加多样化、质量更高且具有更长有效上下文的训练语料。我们持续改进数据构建流水线。对于网页来源的数据，我们实现了过滤策略，以去除批量自动生成内容和模板化内容，从而降低模型塌缩的风险 (Zhu et al., 2024)。数学和编程语料仍然是我们训练数据的核心组成部分，我们还在中期训练阶段引入智能体式数据，以进一步增强 DeepSeek-V4 系列的代码能力。对于多语言数据，我们为 DeepSeek-V4 构建了更大的语料库，以提升其对不同文化中长尾知识的捕捉能力。对于 DeepSeek-V4，我们特别强调长文档数据整理，优先纳入科学论文、技术报告以及其他体现独特学术价值的材料。综合以上各类数据，我们的预训练语料包含超过 32T 个词元，涵盖数学内容、代码、网页、长文档以及其他高质量类别。

对于预训练数据，我们基本沿用了 DeepSeek-V3 的同类预处理策略。在分词方面，我们在 DeepSeek-V3 分词器的基础上引入了少量用于上下文构造的特殊词元，同时仍将词表大小保持为 128K。我们还继承了 DeepSeek-V3 的 token-splitting (DeepSeek-AI, 2024) 和 Fill-in-Middle (FIM) (DeepSeek-AI, 2024) 策略。受 Ding et al.~(2024) 启发，我们将来自不同来源的文档打包成合适的序列，以尽量减少样本截断。不同于 DeepSeek-V3，我们在预训练期间采用样本级 attention masking。

\subsection{预训练设置}\label{pre-training-setups}

\subsubsection{模型设置}\label{model-setups}

DeepSeek-V4-Flash. 我们将 Transformer 层数设为 43，隐藏维度 \(d\) 设为 4096。前两层使用纯滑动窗口注意力。对于后续层，CSA 和 HCA 交替使用。对于 CSA，我们将压缩率 \(m\) 设为 4，将 indexer 查询头数 \(n _ { h } ^ { I }\) 设为 64，将 indexer 头维度 \(c ^ { I }\) 设为 128，并将为稀疏注意力选取的 KV 条目数（即 attention top-k）设为 512。对于 HCA，我们将压缩率 \(m ^ { \prime }\) 设为 128。对于 CSA 和 HCA，我们都将查询头数 \(n _ { h }\) 设为 64，头维度 \(c\) 设为 512，查询压缩维度 \(d _ { c }\) 设为 1024。输出投影分组数 \(g\) 设为 8，每个中间注意力输出的维度 \(d _ { g }\) 设为 1024。对于滑动窗口注意力的附加分支，窗口大小 \(n _ { \mathrm { W i n } }\) 设为 128。我们在所有 Transformer 块中都采用 MoE 层，但前 3 个 MoE 层使用哈希路由策略。每个 MoE 层由 1 个共享专家和 256 个路由专家构成，其中每个专家的中间隐藏维度为 2048。在这些路由专家中，每个词元会激活 6 个专家。多词元预测深度设为 1。对于 mHC，扩展因子 \(n _ { \mathrm { h c } }\) 设为 4，Sinkhorn-Knopp 迭代次数 \(t _ { \mathrm { m a x } }\) 设为 20。在该配置下，DeepSeek-V4-Flash 总参数量为 284B，其中每个词元激活 13B 参数。

DeepSeek-V4-Pro. 我们将 Transformer 层数设为 61，隐藏维度 \(d\) 设为 7168。前两层使用 HCA。对于后续层，CSA 和 HCA 交替使用。对于 CSA，我们将压缩率 \(m\) 设为 4，将 indexer 查询头数 \(n _ { h } ^ { I }\) 设为 64，将 indexer 头维度 \(c ^ { I }\) 设为 128，并将为稀疏注意力选取的 KV 条目数（即 attention top-k）设为 1024。对于 HCA，我们将压缩率 \(m ^ { \prime }\) 设为 128。对于 CSA 和 HCA，我们都将查询头数 \(n _ { h }\) 设为 128，头维度 \(c\) 设为 512，查询压缩维度 \(d _ { c }\) 设为 1536。输出投影分组数 \(g\) 设为 16，每个中间注意力输出的维度 \(d _ { g }\) 设为 1024。对于滑动窗口注意力的附加分支，窗口大小 \(n _ { \mathrm { W i n } }\) 设为 128。我们在所有 Transformer 块中都采用 MoE 层，但前 3 个 MoE 层使用哈希路由策略。每个 MoE 层由 1 个共享专家和 384 个路由专家构成，其中每个专家的中间隐藏维度为 3072。在这些路由专家中，每个词元会激活 6 个专家。多词元预测深度设为 1。对于 mHC，扩展因子 \(n _ { \mathrm { h c } }\) 设为 4，Sinkhorn-Knopp 迭代次数 \(t _ { \mathrm { m a x } }\) 设为 20。在该配置下，DeepSeek-V4-Pro 总参数量为 1.6T，其中每个词元激活 49B 参数。

\subsubsection{训练设置}\label{training-setups}

DeepSeek-V4-Flash. 我们对大多数参数使用 Muon 优化器 (Jordan et al., 2024; Liu et al., 2025)，但对嵌入模块、预测头模块和所有 RMSNorm 模块的权重使用 AdamW 优化器 (Loshchilov and Hutter, 2017)。对于 AdamW，我们将其超参数设为 \(\beta _ { 1 } = 0 . 9\) 、\(\beta _ { 2 } = 0 . 9 5\) 、\(\varepsilon = 1 0 ^ { - 2 0 }\) ，以及 weight\_decay \(= 0 . 1\) 。对于 Muon，我们将 momentum 设为 0.95，将 weight decay 设为 0.1，并将每个更新矩阵的 RMS 重缩放为 0.18，以复用 AdamW 的学习率。我们在 32T 个词元上训练 DeepSeek-V4-Flash，并且和 DeepSeek-V3 一样，也采用 batch size 调度策略：将 batch size（按词元计）从较小值逐步增加到 75.5M，随后在训练的大部分阶段维持在 75.5M。学习率在前 2000 步线性预热，并在训练的大部分阶段保持在 \(2 . 7 \times 1 0 ^ { - 4 }\)。在训练接近尾声时，我们最终按照 cosine 调度将学习率衰减到 \(2 . 7 \times 1 0 ^ { - 5 }\)。训练从 4K 的序列长度开始，并逐步将训练序列长度扩展到 16K、64K 和 1M。对于稀疏注意力的设置，我们首先在前 1T 个词元上使用稠密注意力对模型进行预热，并在序列长度达到 64K 时引入稀疏注意力，随后在训练的其余阶段持续使用稀疏注意力。在引入 attention sparsity 时，我们先设置一个较短阶段来预热 CSA 中的 lightning indexer，然后在训练的大部分阶段使用稀疏注意力训练模型。对于无辅助损失的负载均衡，我们将 bias update speed 设为 0.001。对于平衡损失，我们将其损失权重设为 0.0001，以避免单个序列内部出现极端不均衡。MTP 损失权重在训练的大部分阶段设为 0.3，并在学习率衰减开始时调整为 0.1。

DeepSeek-V4-Pro. 除了少数超参数取值不同外，DeepSeek-V4-Pro 的训练设置与 DeepSeek-V4-Flash 基本一致。我们对大多数参数使用 Muon 优化器，但对嵌入模块、预测头模块和所有 RMSNorm 模块的权重使用 AdamW 优化器。AdamW 和 Muon 的超参数与 DeepSeek-V4-Flash 相同。我们在 33T 个词元上训练 DeepSeek-V4-Pro，并同样采用 batch size 调度策略，其中最大 batch size 为 94.4M 个词元。学习率调度策略与 DeepSeek-V4-Flash 基本相同，但峰值学习率设为 \(2 . 0 \times 1 0 ^ { - 4 }\)，末尾学习率设为 \(2 . 0 \times 1 0 ^ { - 5 }\)。训练同样从 4K 的序列长度开始，并逐步扩展到 16K、64K 和 1M。与 DeepSeek-V4-Flash 相比，DeepSeek-V4-Pro 的稠密注意力阶段更长，而引入稀疏注意力的策略与 DeepSeek-V4-Flash 相同，遵循两阶段训练方法。对于无辅助损失的负载均衡，我们将 bias update speed 设为 0.001。对于平衡损失，我们将其损失权重设为 0.0001，以避免单个序列内部出现极端不均衡。MTP 损失权重在训练的大部分阶段设为 0.3，并在学习率衰减开始时调整为 0.1。

\subsubsection{缓解训练不稳定性}\label{mitigating-training-instability}

训练万亿参数级的 MoE 模型会带来显著的稳定性挑战，DeepSeek-V4 系列也不例外。我们在训练过程中遇到了明显的不稳定性问题。尽管简单的回滚可以暂时恢复训练状态，但它并不足以作为长期解决方案，因为它无法阻止 loss spike 再次发生。根据经验，我们发现 spike 的出现始终与 MoE 层中的离群值有关，而路由机制本身似乎还会加剧这些离群值的产生。因此，我们尝试从两个维度来解决这一问题：一是打破由路由诱发的恶性循环，二是直接抑制异常值。幸运的是，我们发现了两种在实践中非常有效的技术，能够维持训练稳定性。尽管我们目前仍未完全从理论上理解其底层机制，但我们公开分享这两种方法，以促进社区的进一步探索。

前瞻式路由. 我们发现，将骨干网络和路由网络的同步更新解耦，能够显著提升训练稳定性。因此，在 step \(t\) 时，我们使用当前网络参数 \(\theta _ { t }\) 进行特征计算，但路由索引则使用历史网络参数 \(\theta _ { t - \Delta t }\) 计算并应用。在实践中，为了避免两次加载模型参数的开销，我们会在 step \(t - \Delta t\) 时提前获取 step \(t\) 的数据。我们会“前瞻式地”计算并缓存稍后在 step \(t\) 使用的路由索引，这也是我们将该方法命名为 Anticipatory Routing 的原因。我们还在基础设施层面对其进行了大量优化。首先，考虑到预计算路由索引只需要对数据做一次前向传播，我们精心编排了流水线执行，并对计算与 Expert Parallelism (EP) 通信进行了重叠，从而成功将 Anticipatory Routing 带来的额外实际运行时间开销限制在大约 \(20\%\)。其次，我们引入了一种自动检测机制：仅当出现 loss spike 时，系统才会触发一次短暂回滚并启用 Anticipatory Routing；在该模式运行一段时间后，系统会恢复到标准训练。最终，这种动态应用方式使我们能够以几乎可忽略的额外总体训练开销避免 loss spike，同时不损害模型性能。

SwiGLU 截断. 在以往文献中 (Bello et al., 2017; Riviere et al., 2024)，clamping 已被明确用于约束数值范围，从而增强训练稳定性。在我们的实际训练中，我们通过经验发现，应用 SwiGLU clamping (OpenAI, 2025) 能够有效消除离群值，并在不损失性能的前提下显著帮助稳定训练过程。在 DeepSeek-V4-Flash 和 DeepSeek-V4-Pro 的整个训练过程中，我们将 SwiGLU 线性分量截断在 [-10, 10] 范围内，同时将 gate 分量的上界限制为 10。

\subsection{评测}\label{evaluations}

\subsubsection{评测基准}\label{evaluation-benchmarks}

在基座模型的评测中，我们考虑了四个关键维度的基准：世界知识、语言理解与推理、代码与数学，以及长上下文处理。

世界知识类基准包括 AGIEval (Zhong et al., 2023)、C-Eval (Huang et al., 2023)、CMMLU (Li et al., 2023)、MMLU (Hendrycks et al., 2020)、MMLU-Redux (Gema et al., 2024)、MMLU-Pro (Wang et al., 2024b)、MMMLU (OpenAI, 2024a)、MultiLoKo (Hupkes and Bogoychev, 2025)、Simple-QA verified (Haas et al., 2025)、SuperGPQA (Du et al., 2025)、FACTS Parametric (Cheng et al., 2025)，以及 TriviaQA (Joshi et al., 2017)。

语言理解与推理类基准包括 BigBench Hard (BBH) (Suzgun et al., 2022)、DROP (Dua et al., 2019)、HellaSwag (Zellers et al., 2019)、CLUEWSC (Xu et al., 2020)，以及 WinoGrande (Sakaguchi et al., 2019)。

代码与数学类基准包括 BigCodeBench (Zhuo et al., 2025)、HumanEval (Chen et al., 2021)、GSM8K (Cobbe et al., 2021)、MATH (Hendrycks et al., 2021)、MGSM (Shi et al., 2023)，以及 CMath (Wei et al., 2023)。

长上下文类基准包括 LongBench-V2 (Bai et al., 2025b)。

表 1 \textbar{} DeepSeek-V3.2-Base、DeepSeek-V4-Flash-Base 和 DeepSeek-V4-Pro-Base 的对比。所有模型均在我们的内部框架下评测，并共享相同的评测设置。分差不超过 0.3 的分数被视为处于同一水平。每行最高分以粗体标出，第二高分以下划线标出。

{\def\LTcaptype{none} % 不增加计数器
\begin{longtable}[]{@{}llllll@{}}
\toprule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
& 基准（指标） & \# 示例 & DeepSeek-V3.2 Base & DeepSeek-V4-Flash
Base & DeepSeek-V4-Pro Base \\
& 架构 & - & MoE & MoE & MoE \\
& \# 激活参数量 & - & 37B & 13B & 49B \\
& \# 总参数量 & - & 671B & 284B & 1.6T \\
\multirow{12}{*}{世界知识} & AGIEval (EM) & 0-shot & 80.1 & 82.6 &
83.1 \\
& MMLU (EM) & 5-shot & 87.8 & 88.7 & 90.1 \\
& MMLU-Redux (EM) & 5-shot & 87.5 & 89.4 & 90.8 \\
& MMLU-Pro (EM) & 5-shot & 65.5 & 68.3 & 73.5 \\
& MMMLU (EM) & 5-shot & 87.9 & 88.8 & 90.3 \\
& C-Eval (EM) & 5-shot & 90.4 & 92.1 & 93.1 \\
& CMMLU (EM) & 5-shot & 88.9 & 90.4 & 90.8 \\
& MultiLoKo (EM) & 5-shot & 38.7 & 42.2 & 51.1 \\
& Simple-QA verified (EM) & 25-shot & 28.3 & 30.1 & 55.2 \\
& SuperGPQA (EM) & 5-shot & 45.0 & 46.5 & 53.9 \\
& FACTS Parametric (EM) & 25-shot & 27.1 & 33.9 & 62.6 \\
& TriviaQA (EM) & 5-shot & 83.3 & 82.8 & 85.6 \\
\multirow{5}{*}{语言与推理} & BBH (EM) & 3-shot & 87.6 & 86.9 &
87.5 \\
& DROP (F1) & 1-shot & 88.2 & 88.6 & 88.7 \\
& HellaSwag (EM) & 0-shot & 86.4 & 85.7 & 88.0 \\
& WinoGrande (EM) & 0-shot & 78.9 & 79.5 & 81.5 \\
& CLUEWSC (EM) & 5-shot & 83.5 & 82.2 & 85.2 \\
\multirow{6}{*}{代码与数学} & BigCodeBench (Pass@1) & 3-shot & 63.9
& 56.8 & 59.2 \\
& HumanEval (Pass@1) & 0-shot & 62.8 & 69.5 & 76.8 \\
& GSM8K (EM) & 8-shot & 91.1 & 90.8 & 92.6 \\
& MATH (EM) & 4-shot & 60.5 & 57.4 & 64.5 \\
& MGSM (EM) & 8-shot & 81.3 & 85.7 & 84.4 \\
& CMath (EM) & 3-shot & 92.6 & 93.6 & 90.9 \\
长上下文 & LongBench-V2 (EM) & 1-shot & 40.2 & 44.7 & 51.5 \\
\end{longtable}
}

\subsubsection{评测结果}\label{evaluation-results}

在表 1 中，我们给出了 DeepSeek-V3.2、DeepSeek-V4-Flash 和 DeepSeek-V4-Pro 三个基座模型的详细对比；所有结果都在统一的内部框架下、采用严格一致的设置进行评测。

将 DeepSeek-V4-Flash-Base 与 DeepSeek-V3.2-Base 对比，可以看到一个非常有说服力的效率提升案例。尽管其激活参数量和总参数量都显著更小，DeepSeek-V4-Flash-Base 仍在广泛的基准上超越了 DeepSeek-V3.2-Base。这一优势在世界知识任务和具有挑战性的长上下文场景中尤为明显。这些结果表明，DeepSeek-V4-Flash-Base 在架构改进、数据质量提升和训练优化上的进步，使其即便在更紧凑的参数预算下也能取得更优性能，并在大多数评测中有效超过规模更大的 DeepSeek-V3.2-Base。

此外，DeepSeek-V4-Pro-Base 还展示了进一步且决定性的能力跃升，几乎在所有方面都压过了 DeepSeek-V3.2-Base 和 DeepSeek-V4-Flash-Base。随着几乎所有类别上的提升，DeepSeek-V4-Pro-Base 在最具挑战性的基准上达到了 DeepSeek 基座模型中的新性能高点。在知识密集型评测上，它取得了显著增益，同时也大幅推进了长上下文理解能力。在大多数推理和代码基准上，DeepSeek-V4-Pro-Base 同样超过了前两个模型。这种全方位提升表明，DeepSeek-V4-Pro-Base 是 DeepSeek 系列中最强的基础模型，在知识、推理、代码和长上下文能力等各个维度上都优于其前代模型。
