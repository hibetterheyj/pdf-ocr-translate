\section{引言}\label{introduction}

推理模型（DeepSeek-AI, 2025; OpenAI, 2024c）的出现，重新确立了测试时扩展这一新范式，并为大语言模型（LLM）带来了显著的性能提升。然而，这一扩展范式从根本上受限于原始注意力机制（Vaswani et al., 2017）的二次计算复杂度，这为超长上下文与推理过程带来了难以承受的瓶颈。与此同时，长时程场景与任务 --- 从复杂的智能体工作流到大规模跨文档分析 --- 的出现，也使得对超长上下文的高效支持成为未来进展的关键。尽管近期的开源工作（Bai et al., 2025a; DeepSeek-AI, 2024; MiniMax, 2025; Qwen, 2025）推动了通用能力的发展，但在处理超长序列时，这一核心架构低效性仍然是主要障碍，既限制了测试时扩展的进一步收益，也阻碍了对长时程场景与任务的进一步探索。

为了突破超长上下文中的效率瓶颈，我们提出了 DeepSeek-V4 系列，其中包括 DeepSeek-V4-Pro 的预览版（1.6T 参数，49B 激活）以及 DeepSeek-V4-Flash 的预览版（284B 参数，13B 激活）。借助架构创新，DeepSeek-V4 系列在处理超长序列时实现了计算效率的巨大飞跃。这一突破使模型能够高效支持一百万 token 的上下文长度，开启了下一代 LLM 的百万长度上下文时代。我们相信，高效处理超长序列的能力将开启测试时扩展的下一前沿，为长时程任务的深入研究铺平道路，并为探索诸如在线学习等未来范式奠定必要基础。

与 DeepSeek-V3 架构（DeepSeek-AI, 2024）相比，DeepSeek-V4 系列保留了 DeepSeekMoE 框架（Dai et al., 2024）和多 Token 预测（MTP）策略，同时在架构和优化上引入了若干关键创新。为提升长上下文效率，我们设计了一种结合压缩稀疏注意力（Compressed Sparse Attention, CSA）和重度压缩注意力（Heavily Compressed Attention, HCA）的混合注意力机制。CSA 沿序列维度压缩 KV cache，然后执行 DeepSeek Sparse Attention（DSA）（DeepSeek-AI, 2025）；而 HCA 则对 KV cache 施加更激进的压缩，但保留稠密注意力。为增强建模能力，我们引入了流形约束超连接（Manifold-Constrained Hyper-Connections, mHC）（Xie et al., 2026），以升级传统残差连接。此外，我们还将 Muon（Jordan et al., 2024; Liu et al., 2025）优化器用于 DeepSeek-V4 系列的训练，从而实现更快收敛和更好的训练稳定性。

为了让 DeepSeek-V4 系列实现高效训练与推理，并提升开发效率，我们还引入了若干基础设施优化。首先，我们为 MoE 模块设计并实现了单一融合 kernel，使计算、通信和内存访问能够完全重叠。其次，我们采用 TileLang（Wang et al., 2026）这一领域专用语言（DSL），以在开发效率与运行效率之间取得平衡。第三，我们提供了高效的 batch-invariant 和 deterministic kernel 库，以确保训练与推理过程中的按位可复现性。第四，我们在 MoE 专家权重以及索引器 QK 路径上引入了 FP4 量化感知训练，以降低内存与计算开销。第五，在训练框架方面，我们通过张量级 checkpointing 扩展了 autograd 框架，以实现细粒度的重计算控制；同时，还通过针对 Muon 优化器的混合 ZeRO 策略、借助重计算与融合 kernel 的高性价比 mHC 实现，以及用于管理压缩注意力的两阶段上下文并行，来提升训练效率。最后，在推理框架方面，我们设计了具有磁盘存储策略的异构 KV cache 结构，以实现高效的共享前缀复用。

通过采用混合 CSA 和 HCA，并结合在计算与存储上的精度优化，DeepSeek-V4 系列相较 DeepSeek-V3.2 实现了显著更低的推理 FLOPs 和大幅更小的 KV cache 尺寸，尤其是在长上下文场景下更是如此。图 1 右侧展示了 DeepSeek-V3.2 与 DeepSeek-V4 系列的估算单 token 推理 FLOPs 和累计 KV cache 大小。在 1M token 上下文场景中，即便是激活参数更多的 DeepSeek-V4-Pro，其单 token FLOPs（按等效 FP8 FLOPs 计）也仅为 DeepSeek-V3.2 的 \(2 7 \%\)，KV cache 大小仅为其 \(1 0 \%\)。此外，激活参数更少的 DeepSeek-V4-Flash 进一步提升了效率：在 1M token 上下文设置下，它的单 token FLOPs 仅为 DeepSeek-V3.2 的 \(1 0 \%\)，KV cache 大小仅为其 \(7 \%\)。另外，对于 DeepSeek-V4 系列，路由专家参数采用 FP4 精度。尽管在现有硬件上，\(\mathrm { F P 4 } \times \mathrm { F P 8 }\) 运算的峰值 FLOPs 目前与 \(\mathrm { F P 8 } \times \mathrm { F P 8 }\) 相同，但从理论上看，在未来硬件上它可以实现高出 1/3 的效率，这将进一步提升 DeepSeek-V4 系列的效率。

在预训练阶段，我们分别用 32T token 训练 DeepSeek-V4-Flash，用 33T token 训练 DeepSeek-V4-Pro。完成预训练后，这两个模型都可以原生且高效地支持 1M 长度上下文。在我们的内部评测中，凭借更高的参数效率设计，DeepSeek-V4-Flash-Base 已在大多数基准上超越 DeepSeek-V3.2-Base。DeepSeek-V4-Pro-Base 则进一步扩大了这一优势，为 DeepSeek 基础模型树立了新的性能标准，在推理、代码、长上下文和世界知识任务上实现了全面领先。

DeepSeek-V4 系列的后训练流程采用两阶段范式：先独立培养领域专长专家，再通过 on-policy distillation（Lu and Lab, 2025）完成统一模型整合。首先，对于每个目标领域 --- 如数学、编程、智能体以及指令跟随 --- 都会独立训练一个专门的专家模型。基础模型先在高质量的领域数据上进行监督微调（SFT），以建立基础能力。随后，再使用 Group Relative Policy Optimization（GRPO）（DeepSeek-AI, 2025）进行强化学习（RL），在面向特定成功标准设计的奖励模型引导下，进一步优化模型的领域对齐行为。该阶段会产出一组多样化的专长专家，每个专家都在各自领域表现出色。最后，为了整合这些不同的能力，我们通过 on-policy distillation 训练一个统一模型，其中统一模型作为学生，学习在教师模型指导下优化 reverse KL loss。

\bigskip
\phantomsection\label{summary-of-core-evaluation-results}
\noindent\textbf{核心评测结果摘要}

• 知识：在广泛世界知识评测中，DeepSeek-V4-Pro 的最大推理努力模式 DeepSeek-V4-Pro-Max 在 SimpleQA（OpenAI, 2024d）和 Chinese-SimpleQA（He et al., 2024）基准上显著优于领先的开源模型。在教育知识方面 --- 通过 MMLU-Pro（Wang et al., 2024b）、HLE（Phan et al., 2025）和 GPQA（Rein et al., 2023）评测 --- DeepSeek-V4-Pro-Max 也较开源同类模型略有领先。尽管在这些知识类评测上仍落后于领先的闭源模型 Gemini-3.1-Pro，但 DeepSeek-V4-Pro-Max 已显著缩小了与其之间的差距。

• 推理：通过扩展推理 token，DeepSeek-V4-Pro-Max 在标准推理基准上展现出相对于 GPT-5.2 和 Gemini-3.0-Pro 的更强性能。不过，其表现仍略逊于 GPT-5.4 和 Gemini-3.1-Pro，这表明其发展进度大约落后于最前沿模型 3 到 6 个月。此外，DeepSeek-V4-Flash-Max 也达到了与 GPT-5.2 和 Gemini-3.0-Pro 相当的性能，证明其在复杂推理任务上是一种极具性价比的架构。

\pandocbounded{\includegraphics[keepaspectratio,alt={image}]{images/2c5ffc992a56d87715c81c76ccc8e01e6186c02cf3a03d4a75ca416f22237b79.jpg}}

图 2 \textbar{} DeepSeek-V4 系列的整体架构。我们在注意力层使用混合 CSA（Compressed Sparse Attention）和 HCA（Heavily Compressed Attention），在前馈层使用 DeepSeekMoE，并使用 mHC 强化传统残差连接。

• 智能体：在公开基准上，DeepSeek-V4-Pro-Max 与 Kimi-K2.6 和 GLM-5.1 等领先开源模型表现相当，但略逊于前沿闭源模型。在我们的内部评测中，DeepSeek-V4-Pro-Max 优于 Claude Sonnet 4.5，并接近 Opus 4.5 的水平。

• 长上下文：DeepSeek-V4-Pro-Max 在 100 万 token 上下文窗口下的合成与真实用例中都表现强劲，甚至在学术基准上超过了 Gemini-3.1-Pro。

• DeepSeek-V4-Pro 与 DeepSeek-V4-Flash：由于参数规模更小，DeepSeek-V4-Flash-Max 在知识类评测中的表现较低。不过，当分配更大的思考预算时，它在推理任务上可以取得可比结果。在智能体评测中，尽管 DeepSeek-V4-Flash-Max 在若干基准上与 DeepSeek-V4-Pro-Max 表现相当，但在更复杂、更高难度的任务上仍落后于更大的版本。

\section{架构}\label{architecture}

总体而言，DeepSeek-V4 系列保留了 Transformer（Vaswani et al., 2017）架构和多 Token 预测（MTP）模块（DeepSeek-AI, 2024; Gloeckle et al., 2024），同时相较 DeepSeek-V3 引入了若干关键升级：(1) 首先，我们引入流形约束超连接（mHC）（Xie et al., 2026）以强化传统残差连接；

\begin{enumerate}
\def\labelenumi{(\arabic{enumi})}
\setcounter{enumi}{1}
\tightlist
\item
  其次，我们设计了一种混合注意力架构，通过压缩稀疏注意力和重度压缩注意力大幅提升长上下文效率。(3) 第三，我们采用 Muon（Jordan et al., 2024; Liu et al., 2025）作为优化器。对于混合专家（MoE）组件，我们仍然采用 DeepSeekMoE（Dai et al., 2024）架构，仅对 DeepSeek-V3 做了少量调整。多 Token 预测（MTP）（DeepSeek-AI, 2024; Gloeckle et al., 2024; Li et al., 2024; Qi et al., 2020）的配置与 DeepSeek-V3 完全一致。其余未特别说明的细节均遵循 DeepSeek-V3（DeepSeek-AI, 2024）中已建立的设定。图 2 展示了 DeepSeek-V4 的整体架构，具体细节如下所述。
\end{enumerate}

\subsection{继承自 DeepSeek-V3 的设计}\label{designs-inherited-from-deepseek-v3}

混合专家。与以往的 DeepSeek 系列模型（DeepSeek-AI, 2024; DeepSeek-AI, 2024）一致，DeepSeek-V4 系列在前馈网络（FFN）中同样采用 DeepSeekMoE 范式（Dai et al., 2024），其中设置了细粒度路由专家和共享专家。与 DeepSeek-V3 不同的是，我们将用于计算亲和分数的激活函数从 Sigmoid(·) 改为 Sqrt(Softplus(·))。在负载均衡方面，我们也采用了无辅助损失策略（DeepSeek-AI, 2024; Wang et al., 2024a），并辅以轻量的按序列均衡损失，以防止单个序列内部出现极端失衡。对于 DeepSeek-V4，我们移除了对路由目标节点数量的约束，并精心重新设计了并行策略，以维持训练效率。此外，相比 DeepSeek-V3，我们将最前面若干个 Transformer block 中的稠密 FFN 层替换为采用 Hash routing（Roller et al., 2021）的 MoE 层。Hash routing 策略会根据输入 token ID 对应的预定义哈希函数，为每个 token 确定目标专家。

多 Token 预测。与 DeepSeek-V3 一样，DeepSeek-V4 系列同样设置了 MTP 模块和目标。鉴于 MTP 策略已经在 DeepSeek-V3 中得到验证，我们在 DeepSeek-V4 系列中不加修改地采用同样的策略。

\subsection{流形约束超连接}\label{manifold-constrained-hyper-connections}

如图 2 所示，DeepSeek-V4 系列引入了流形约束超连接（Manifold-Constrained Hyper-Connections, mHC）（Xie et al., 2026），以强化相邻 Transformer block 之间的传统残差连接。与朴素超连接（Hyper-Connections, HC）（Zhu et al., 2025）相比，mHC 的核心思想是将残差映射约束到特定流形上，从而在保留模型表达能力的同时，增强跨层信号传播的稳定性。本小节将简要介绍标准 HC，并说明我们如何设计 mHC 以实现稳定训练。

标准超连接。标准 HC 将残差流的宽度按 \(n _ { \mathrm { h c } }\) 倍扩展。具体来说，残差流的形状会从 \(\mathbb { R } ^ { d }\) 扩展为 \(\mathbb { R } ^ { n _ { \mathrm { h c } } \times d }\)，其中 \(d\) 是实际层输入的隐藏维度。设 \(X _ { l } = [ \mathbf { x } _ { l , 1 } ; \ldots ; \mathbf { x } _ { l , n _ { \mathrm { h c } } } ] ^ { T } \in \mathbb { R } ^ { n _ { \mathrm { h c } } \times d }\) 为第 \(l\) 层之前的残差状态。HC 引入了三个线性映射：输入映射 \(A _ { l } \in \mathbb { R } ^ { 1 \times n _ { \mathrm { h c } } }\)，残差变换 \(B _ { l } \in \mathbb { R } ^ { n _ { \mathrm { h c } } \times n _ { \mathrm { h c } } }\)，以及输出映射 \(\bar { C _ { l } } \bar { \in } \mathbb { R } ^ { n _ { \mathrm { h c } } \times \bar { 1 } }\)。残差状态的更新形式如下：

\[
X _ {l + 1} = B _ {l} X _ {l} + C _ {l} \mathcal {F} _ {l} \left(A _ {l} X _ {l}\right), \tag {1}
\]

其中 \(\mathcal { F } _ { l }\) 表示第 \(l\) 层（例如某个 MoE 层），其输入和输出形状都为 \(\mathbb { R } ^ { d }\)。需要注意的是，实际层输入 \(A _ { l } X _ { l } \in \mathbb { R } ^ { d }\) 也是 \(d\) 维的，因此扩展后的残差宽度不会影响内部层的设计。HC 将残差宽度与实际隐藏维度解耦，以极小的计算开销提供了一个互补的扩展维度，因为 \(n _ { \mathrm { h c } }\) 通常远小于隐藏维度 \(d\)。然而，尽管 HC 已表现出提升模型性能的潜力，我们发现当堆叠多层时，训练过程经常会出现数值不稳定，这阻碍了 HC 的进一步扩展。

流形约束残差映射。mHC 的核心创新在于，将残差映射矩阵 \(B _ { l }\) 约束到双随机矩阵流形（即 Birkhoff 多面体）\(M _ { \odot }\) 上，从而增强跨层信号传播的稳定性：

\[
B _ {l} \in \mathcal {M} := \{M \in \mathbb {R} ^ {n \times n} \mid M \mathbf {1} _ {n} = \mathbf {1} _ {n}, \mathbf {1} _ {n} ^ {T} M = \mathbf {1} _ {n} ^ {T}, M \geqslant 0 \}. \tag {2}
\]

这一约束确保映射矩阵的谱范数 \(\| B _ { l } \| _ { 2 }\) 被限制在 1 以内，因此残差变换是非扩张的，从而提升前向传播和反向传播过程中的数值稳定性。此外，集合 M 对乘法封闭，这保证了在深层 mHC 堆叠场景下的稳定性。除此之外，输入变换 \(A _ { l }\) 和输出变换 \(C _ { l }\) 也通过 Sigmoid 函数被约束为非负且有界，以避免信号抵消的风险。

动态参数化。三个线性映射的参数采用动态生成方式，并被分解为动态（与输入相关）部分和静态（与输入无关）部分。给定输入 \(\bar { X _ { l } } \in \mathbb { R } ^ { n _ { \mathrm { h c } } \times d } .\)，我们首先将其展平并归一化：\(\hat { X } _ { l } = \bar { \mathrm { R M S N o r m } } ( \mathrm { v e c } ( X _ { l } ) ) \in \mathbb { R } ^ { 1 \times n _ { \mathrm { h c } } d }\)。随后，我们遵循常规 HC 生成无约束原始参数 \(\tilde { A } _ { l } \in \mathbb { R } ^ { 1 \times n _ { \mathrm { h c } } }\)、\(\tilde { B } _ { l } \in \mathbb { R } ^ { n _ { \mathrm { h c } } \times n _ { \mathrm { h c } } }\) 和 \(\tilde { C } _ { l } \in \mathbb { R } ^ { n _ { \mathrm { h c } } \times 1 }\)：

\[
\tilde {A} _ {l} = \alpha_ {l} ^ {\text {p r e}} \cdot \left(\hat {X} _ {l} W _ {l} ^ {\text {p r e}}\right) + S _ {l} ^ {\text {p r e}}, \tag {3}
\]

\[
\tilde {B} _ {l} = \alpha_ {l} ^ {\mathrm {r e s}} \cdot \operatorname {M a t} \left(\hat {X} _ {l} W _ {l} ^ {\mathrm {r e s}}\right) + S _ {l} ^ {\mathrm {r e s}}, \tag {4}
\]

\[
\tilde {C} _ {l} = \alpha_ {l} ^ {\text {p o s t}} \cdot \left(\hat {X} _ {l} W _ {l} ^ {\text {p o s t}}\right) ^ {T} + S _ {l} ^ {\text {p o s t}}, \tag {5}
\]

其中 \(W _ { l } ^ { \mathrm { p r e } } , W _ { l } ^ { \mathrm { p o s t } } \in \mathbb { R } ^ { n _ { \mathrm { h c } } d \times n _ { \mathrm { h c } } }\) 和 \(W _ { l } ^ { \mathrm { r e s } } \in \mathbb { R } ^ { n _ { \mathrm { h c } } d \times n _ { \mathrm { h c } } ^ { 2 } }\) 是用于生成动态部分的可学习参数；\(\mathrm { { M a t } ( \cdot ) }\) 将一个大小为 \(1 \times n _ { \mathrm { h c } } ^ { 2 }\) 的向量重塑为大小为 \(n _ { \mathrm { h c } } \times n _ { \mathrm { h c } }\) 的矩阵；\(S _ { l } ^ { \mathrm { p r e } } \in \mathbb { R } ^ { 1 \times n _ { \mathrm { h c } } } , S _ { l } ^ { \mathrm { p o s t } } \in \mathbb { R } ^ { n _ { \mathrm { h c } } \times 1 } ,\) 以及 \(S _ { l } ^ { \mathrm { r e s } } \in \mathbb { R } ^ { n _ { \mathrm { h c } } \times n _ { \mathrm { h c } } }\) 是可学习的静态偏置；而 \(\alpha _ { l } ^ { \mathrm { p r e } } , \alpha _ { l } ^ { \mathrm { r e s } } , \alpha _ { l } ^ { \mathrm { p o s t } } \in \mathbb { R }\) 是初始化为较小数值的可学习门控因子。

施加参数约束。在得到无约束原始参数 \(\tilde { A } _ { l } , \tilde { B } _ { l } , \tilde { C } _ { l } ,\) 后，我们再对其施加前述约束，以增强数值稳定性。具体而言，对于输入映射和输出映射，我们使用 Sigmoid 函数 \(\sigma ( \cdot )\) 来确保它们的非负性与有界性：

\[
A _ {l} = \sigma (\tilde {A} _ {l}), \tag {6}
\]

\[
C _ {l} = 2 \sigma (\tilde {C} _ {l}). \tag {7}
\]

至于残差映射 \({ \tilde { B } } _ { l } ,\) 我们将其投影到双随机矩阵流形 \(\mathcal { M }\) 上。这一过程通过 Sinkhorn-Knopp 算法实现：首先对 \(\tilde { B } _ { l }\) 应用指数函数以确保其为正，得到 \(M ^ { ( 0 ) } = \exp ( \tilde { B } _ { l } ) ,\)，随后迭代执行列归一化和行归一化：

\[
M ^ {(t)} = \mathcal {T} _ {r} \left(\mathcal {T} _ {c} \left(M ^ {(t - 1)}\right)\right), \tag {8}
\]

其中 \(\mathcal { T } _ { r }\) 和 \(\mathcal { T } _ { c }\) 分别表示行归一化与列归一化。该迭代会收敛到一个受约束的双随机矩阵 \(B _ { l } = M ^ { ( t _ { \operatorname* { m a x } } ) }\)。我们选择 \(t _ { \mathrm { m a x } } = 2 0\) 作为一个实用取值。

\pandocbounded{\includegraphics[keepaspectratio,alt={image}]{images/cff2b362b699adbc334a2f504449cbfbb7010bb6f736884475dc536b11b1d80b.jpg}}

图 3 \textbar{} CSA 的核心架构。它将 KV 条目的数量压缩为 \(\textstyle { \frac { 1 } { m } }\) 倍，然后应用 DeepSeek Sparse Attention 以进一步加速。此外，一小组滑动窗口 KV 条目会与选中的压缩 KV 条目结合，以增强局部细粒度依赖。

\subsection{结合 CSA 与 HCA 的混合注意力}\label{hybrid-attention-with-csa-and-hca}

当上下文长度达到极端规模时，注意力机制会成为模型中的主导计算瓶颈。针对 DeepSeek-V4，我们设计了两种高效注意力架构 --- 压缩稀疏注意力（CSA）和重度压缩注意力（HCA）--- 并采用它们交错的混合配置，从而显著降低长文本场景中的注意力计算开销。CSA 同时结合压缩和稀疏注意力策略：它首先将每 \(m\) 个 token 的 Key-Value（KV）cache 压缩为一个条目，然后应用 DeepSeek Sparse Attention（DSA）（DeepSeek-AI, 2025），其中每个查询 token 仅关注 \(k\) 个压缩 KV 条目。HCA 则追求极致压缩，将每 \(m ^ { \prime } \left( \gg m \right)\) 个 token 的 KV cache 合并为单个条目。CSA 与 HCA 的混合架构显著提升了 DeepSeek-V4 系列的长上下文效率，使一百万 token 上下文在实践中成为可能。本小节将介绍我们混合注意力架构的核心技术；此外，我们还提供了开源实现1，以无歧义地说明更多细节。

\subsubsection{压缩稀疏注意力}\label{compressed-sparse-attention}

图 3 展示了 CSA 的核心架构：它首先将每 \(m\) 个 token 的 KV cache 压缩为一个条目，然后应用 DeepSeek Sparse Attention 以进一步加速。

压缩 Key-Value 条目。设 \(H \in \mathbb { R } ^ { n \times d }\) 为输入隐藏状态序列，其中 \(n\) 是序列长度，\(d\) 是隐藏维度。CSA 首先计算两组 KV 条目 \(C ^ { a } , C ^ { b } \in \mathbb { R } ^ { \bar { n } \times c }\) 及其对应的压缩权重 \(Z ^ { a } , { \bar { Z } } ^ { b } \in \mathbb { R } ^ { n \times c }\)，其中 \(c\) 为头维度：

\[
C ^ {a} = H \cdot W ^ {a K V}, \quad C ^ {b} = H \cdot W ^ {b K V}, \tag {9}
\]

\[
Z ^ {a} = H \cdot W ^ {a Z}, \quad Z ^ {b} = H \cdot W ^ {b Z}, \tag {10}
\]

其中 \(W ^ { a K V } , W ^ { b K V } , W ^ { a Z } , W ^ { b Z } \in \mathbb { R } ^ { d \times c }\) 是可训练参数。接下来，\(C ^ { a }\) 和 \(C ^ { b }\) 中每 \(m\) 个 KV 条目会依据其压缩权重以及可学习的位置偏置 \(B ^ { a }\) \(\mathbf { \Phi } ^ { a } , B ^ { b } \in \mathbb { R } ^ { m \times c }\) 被压缩为一个条目，生成 \(C ^ { \mathsf { C o m p } } \in \mathbb { R } ^ { \frac { n } { m } \times c }\)。每个压缩条目 \(C _ { i } ^ { \mathrm { C o m p } } \in \mathbb { R } ^ { c }\) 的计算方式为

\[
\left[ S _ {m i: m (i + 1) - 1} ^ {a}; S _ {m (i - 1): m i - 1} ^ {b} \right] = \operatorname {S o f t m a x} _ {\text {r o w}} \left(\left[ Z _ {m i: m (i + 1) - 1} ^ {a} + B ^ {a}; Z _ {m (i - 1): m i - 1} ^ {b} + B ^ {b} \right]\right), \tag {11}
\]

\[
C _ {i} ^ {\text {C o m p}} = \sum_ {j = m i} ^ {m (i + 1) - 1} S _ {j} ^ {a} \odot C _ {j} ^ {a} + \sum_ {j = m (i - 1)} ^ {m i - 1} S _ {j} ^ {b} \odot C _ {j} ^ {b}, \tag {12}
\]

其中 \(\odot\) 表示 Hadamard 积；Softmaxrow(·) 表示沿行维度进行 softmax 操作，即在来自 \(Z ^ { a }\) 和 \(Z ^ { b }\) 的共 \(2 m\) 个元素上进行归一化。当 \(i = 0\) 时，\(Z _ { m ( i - 1 ) : m i - 1 } ^ { b }\) 用负无穷填充，\(C _ { m ( i - 1 ) : m i - 1 } ^ { b }\) 用零填充。注意，每个 \(C _ { i } ^ { \mathrm { C o m p } }\) 都由 \(2m\) 个 KV 条目导出，但用于 \(C _ { i } ^ { \mathrm { C o m p } }\) 的 \(C ^ { b }\) 索引与用于前一个压缩条目 \(C _ { i - 1 } ^ { \mathsf { C o m p } }\) 的 \(C ^ { a }\) 索引存在重叠。因此，CSA 实际上将序列长度压缩到了 \(\frac { 1 } { m }\) 倍。

用于稀疏选择的 Lightning 索引器。在得到压缩 KV 条目 \(C ^ { \mathrm { C o m p } }\) 后，CSA 应用 DSA 策略来为核心注意力选择 top-k 个压缩 KV 条目。首先，CSA 使用与 \(C ^ { \mathrm { C o m p } }\) 相同的压缩操作，得到压缩索引器 key \(K ^ { \mathrm { I C o m i p } } \in \mathbb { R } ^ { \frac { n } { m } \times c ^ { I } } .\)，其中 \(c ^ { I }\) 是索引器头维度。随后，对于查询 token \(t\)，我们以低秩方式生成索引器 query \(\{ \mathbf { q } _ { t , 1 } ^ { I } ; \mathbf { q } _ { t , 2 } ^ { I } ; . . . ; \mathbf { q } _ { t , n _ { h } ^ { I } } ^ { I } \}\)：

\[
\mathbf {c} _ {t} ^ {Q} = \mathbf {h} _ {t} \cdot W ^ {D Q}, \tag {13}
\]

\[
[ \mathbf {q} _ {t, 1} ^ {I}; \mathbf {q} _ {t, 2} ^ {I}; \dots ; \mathbf {q} _ {t, n _ {h} ^ {I}} ^ {I} ] = \mathbf {q} _ {t} ^ {I} = \mathbf {c} _ {t} ^ {Q} \cdot W ^ {I U Q}, \tag {14}
\]

其中 \(\mathbf { h } _ { t } \ \in \ \mathbb { R } ^ { d }\) 是查询 token \(t\) 的输入隐藏状态；\(\mathbf { c } _ { t } ^ { Q } \in \mathbb { R } ^ { d _ { c } }\) 是查询的压缩潜向量；\(d _ { c }\) 表示查询压缩维度；\(n _ { h } ^ { I }\) 表示索引器查询头的数量；\(W ^ { D Q } \in \mathbb { R } ^ { d \times d _ { c } }\) 和 \(W ^ { I U Q } \in \mathbb { R } ^ { d _ { c } \times c ^ { I } n _ { h } ^ { I } }\) 分别是索引器 query 的下投影与上投影矩阵。接下来，查询 token \(t\) 与前序压缩块 \(\textstyle { \bigl ( } s < \operatorname { F l o o r } ( { \frac { t } { m } } ) { \bigr ) }\) 之间的索引分数 \(I _ { t , s } \in \mathbb { R }\) 按如下方式计算：

\[
\left[ w _ {t, 1} ^ {I}; w _ {t, 2} ^ {I}; \dots ; w _ {t, n _ {h} ^ {I}} ^ {I} \right] = \mathbf {w} _ {t} ^ {I} = \mathbf {h} _ {t} \cdot W ^ {w}, \tag {15}
\]

\[
I _ {t, s} = \sum_ {h = 1} ^ {n _ {h} ^ {I}} w _ {t, h} ^ {I} \cdot \operatorname {R e L U} \left(\mathbf {q} _ {t, h} ^ {I} \cdot K _ {s} ^ {\text {I C o m p}}\right), \tag {16}
\]

其中 \(W ^ { w } \in \mathbb { R } ^ { d \times n _ { h } ^ { I } }\) 是可学习矩阵；\(\boldsymbol { w _ { t , h } ^ { I } } \in \mathbb { R }\) 是第 \(h\) 个索引器头的权重。对于查询 token \(t\)，给定其索引分数 \(I _ { t , : \prime }\)，我们采用一个 top-\(\mathbf { \nabla } \cdot \mathbf { k }\) 选择器，有选择地保留一部分压缩 KV 条目 \(C _ { t } ^ { \mathsf { S p r s C o m p } }\) 用于后续核心注意力：

\[
C _ {t} ^ {\text {S p r s C o m p}} = \left\{C _ {s} ^ {\text {C o m p}} \mid I _ {t, s} \in \operatorname {T o p - k} \left(I _ {t,:}\right) \right\}. \tag {17}
\]

\pandocbounded{\includegraphics[keepaspectratio,alt={image}]{images/3be80607df218b3fca89c7c8159b93be4102ea887a2d41db75764756d19c0dc0.jpg}}

图 4 \textbar{} HCA 的核心架构。它执行更强的压缩，其中 \(m ^ { \prime } \left( \gg m \right)\) 个 token 的 KV 条目会被合并为一个。此外，我们还额外引入了一小组滑动窗口 KV 条目，以增强局部细粒度依赖。

共享 Key-Value MQA。在选出稀疏 KV 条目之后，CSA 以 Multi-Query Attention（MQA）（Shazeer, 2019）的方式执行核心注意力，其中 \(C _ { t } ^ { \mathsf { S p r s C o m p } }\) 中的每个压缩 KV 条目都同时充当注意力 key 和 value。具体而言，对于查询 token \(t\)，我们首先从压缩潜向量 \(\mathbf { c } _ { t } ^ { Q }\) 生成注意力 query \(\{ \mathbf { q } _ { t , 1 } ; \mathbf { q } _ { t , 2 } ; . . . ; \mathbf { q } _ { t , n _ { h } } \}\)：

\[
\left[ \mathbf {q} _ {t, 1}; \mathbf {q} _ {t, 2}; \dots ; \mathbf {q} _ {t, n _ {h}} \right] = \mathbf {q} _ {t} = \mathbf {c} _ {t} ^ {Q} \cdot W ^ {U Q}, \tag {18}
\]

其中 \(n _ { h }\) 表示查询头数量；\(W ^ { U Q } \in \mathbb { R } ^ { d _ { c } \times c n _ { h } }\) 是 query 的上投影矩阵。需要注意的是，潜在查询向量 \(\mathbf { c } _ { t } ^ { Q }\) 与索引器 query 所使用的潜在查询向量是共享的。接下来，我们在 \(\{ \pmb q _ { t , i } \}\) 与 \(C _ { t } ^ { \mathsf { S p r s C o m p } }\) 上执行 MQA：

\[
\mathbf {o} _ {t, i} = \text {C o r e A t t n} \left(\text {q u e r y} = \mathbf {q} _ {t, i}, \text {k e y} = C _ {t} ^ {\text {S p r s C o m p}}, \text {v a l u e} = C _ {t} ^ {\text {S p r s C o m p}}\right), \tag {19}
\]

其中 \(\mathbf { o } _ { t , i } \in \mathbb { R } ^ { c }\) 是第 \(i\) 个头在第 \(t\) 个 token 处的核心注意力输出；CoreAttn(·) 表示核心注意力操作。

分组输出投影。在 DeepSeek-V4 的配置中，\(c n _ { h }\) 相当大。因此，若将核心注意力操作的输出 \(\left[ \mathbf { o } _ { t , 1 } ; \mathbf { o } _ { t , 2 } ; . . . ; \mathbf { o } _ { t , n _ { h } } \right] = \mathbf { o } _ { t } \in \mathbb { R } ^ { c n _ { h } }\) 直接投影到 \(d\) 维隐藏状态，将带来很大的计算负担。为降低这一成本，我们设计了分组输出投影策略。具体而言，我们先将 \(n _ { h }\) 个输出划分为 \(g\) 组，然后对每组输出 \({ \mathbf o } _ { t , i } ^ { G } \in \mathbb { R } ^ { c \frac { n _ { h } } { g } }\) 投影得到一个 \(d _ { g }\) 维中间输出 \({ \mathbf o } _ { t , i } ^ { G ^ { \prime } } \in \mathbb { R } ^ { d _ { g } }\)，其中 \(d _ { g } < c \frac { n _ { h } } { g }\)。最后，我们再将中间输出 \([ \mathbf { o } _ { t , 1 } ^ { G ^ { \prime } } ; \mathbf { o } _ { t , 2 } ^ { G ^ { \prime } } ; . . . ; \mathbf { o } _ { t , g } ^ { G ^ { \prime } } ] \in \mathbb { R } ^ { d _ { g } g }\) 投影为最终注意力输出 \(\hat { \mathbf { o } } _ { t } \in \mathbb { R } ^ { d }\)。

\subsubsection{重度压缩注意力}\label{heavily-compressed-attention}

图 4 展示了 HCA 的核心架构，它以更激进的方式压缩 KV cache，但不使用稀疏注意力。

压缩 Key-Value 条目。总体而言，HCA 的压缩策略与 CSA 相似，但采用了更大的压缩率 \(m ^ { \prime }\) \(( \gg m )\) )，并且不进行重叠压缩。设 \(H \in \mathbb { R } ^ { n \times d }\) 为输入隐藏状态序列，HCA 首先计算原始 KV 条目 \(C \in \mathbb { R } ^ { n \times c }\) 及其对应的压缩权重 \(Z \in \mathbb { R } ^ { n \times c }\)：

\[
C = H \cdot W ^ {K V}, \tag {20}
\]

\[
Z = H \cdot W ^ {Z}, \tag {21}
\]

其中 \(W ^ { K V }\) 和 \(W ^ { Z } \in \mathbb { R } ^ { d \times c }\) 是可训练参数。接下来，\(C\) 中每 \(m ^ { \prime }\) 个 KV 条目会依据压缩权重及可学习的位置偏置 \(B \in \mathbb { R } ^ { m ^ { \prime } \times c }\) 被压缩成一个条目，生成 \(C ^ { \mathsf { C o m p } } \in \mathbb { R } ^ { \frac { n } { m ^ { \prime } } \times c }\)。每个压缩条目 \(C _ { i } ^ { \mathrm { C o m p } } \in \mathbb { R } ^ { c }\) 按如下方式计算：

\[
S _ {m ^ {\prime} i: m ^ {\prime} (i + 1) - 1} = \operatorname {S o f t m a x} _ {\text {r o w}} \left(Z _ {m ^ {\prime} i: m ^ {\prime} (i + 1) - 1} + B\right), \tag {22}
\]

\[
C _ {i} ^ {\text {C o m p}} = \sum_ {j = m ^ {\prime} i} ^ {m ^ {\prime} (i + 1) - 1} S _ {j} \odot C _ {j}. \tag {23}
\]

通过这一压缩操作，HCA 将序列长度压缩到 \(\scriptstyle { \frac { 1 } { m ^ { \prime } } }\) 倍。

共享 Key-Value MQA 与分组输出投影。HCA 同样采用与 CSA 相同的共享 KV MQA 与分组输出投影策略。在 KV 压缩之后，对于查询 token \(t\)，HCA 首先以低秩方式生成注意力 query \(\{ \mathbf { q } _ { t , 1 } ; \mathbf { q } _ { t , 2 } ; . . . ; \mathbf { q } _ { t , n _ { h } } \}\)：

\[
\mathbf {c} _ {t} ^ {Q} = \mathbf {h} _ {t} \cdot W ^ {D Q}, \tag {24}
\]

\[
[ \mathbf {q} _ {t, 1}; \mathbf {q} _ {t, 2}; \dots ; \mathbf {q} _ {t, n _ {h}} ] = \mathbf {q} _ {t} = \mathbf {c} _ {t} ^ {Q} \cdot W ^ {U Q}, \tag {25}
\]

其中 \(\mathbf h _ { t } \in \mathbb R ^ { d }\) 是查询 token \(t\) 的输入隐藏状态；\(n _ { h }\) 表示查询头数量；\(W ^ { D Q } \in \mathbb { R } ^ { d \times d _ { c } }\) 和 \(W ^ { U Q } \in \mathbb { R } ^ { d _ { c } \times c n _ { h } }\) 分别是 query 的下投影和上投影矩阵。接下来，我们在 \(\{ \mathbf { q } _ { t , i } \}\) 和 \(C ^ { \mathrm { C o m p } }\) 上执行 MQA：

\[
\mathbf {o} _ {t, i} = \text {C o r e A t t n} \left(\text {q u e r y} = \mathbf {q} _ {t, i}, \text {k e y} = C ^ {\text {C o m p}}, \text {v a l u e} = C ^ {\text {C o m p}}\right), \tag {26}
\]

其中 \(\mathbf { o } _ { t , i } \in \mathbb { R } ^ { c }\) 是第 \(i\) 个头在第 \(t\) 个 token 处的核心注意力输出。接下来，与 CSA 一样，HCA 将 \(n _ { h }\) 个输出划分为 \(g\) 组，并对每组输出 \({ \mathbf o } _ { t , i } ^ { G } \in \mathbb { R } ^ { c \frac { n _ { h } } { g } }\) 投影得到一个 \(d _ { g }\) 维中间输出 \({ \mathbf o } _ { t , i } ^ { G ^ { \prime } } \in \mathbb { R } ^ { d _ { g } }\)，其中 \(d _ { g } < c \frac { n _ { h } } { g }\)。最后，HCA 将中间输出 \([ \mathbf { o } _ { t , 1 } ^ { G ^ { \prime } } ; \mathbf { o } _ { t , 2 } ^ { G ^ { \prime } } ; . . . ; \mathbf { o } _ { t , g } ^ { G ^ { \prime } } ] \in \mathbb { R } ^ { d _ { g } g }\) 投影为最终注意力输出 \(\hat { \mathbf { o } } _ { t } \in \mathbb { R } ^ { d }\)。

\subsubsection{其他细节}\label{other-details}

除了上述 CSA 和 HCA 的核心架构外，我们的混合注意力还融合了若干其他技术。为保证表述清晰，我们在前面的介绍中省略了这些附加技术，并将在本小节中作简要说明。此外，本小节只关注这些技术的核心思想，为了简洁起见可能会省略一些细小细节。我们鼓励读者参考我们的开源实现，以获得无歧义的细节说明。

查询与 Key-Value 条目归一化。对于 CSA 和 HCA，我们都会在核心注意力操作之前，对每个头上的 query 以及压缩 KV 条目唯一的头额外执行一次 RMSNorm 操作。这种归一化可以避免注意力 logit 爆炸，并可能提升训练稳定性。

部分旋转位置编码。对于 CSA 和 HCA，我们在注意力 query、KV 条目以及核心注意力输出上部分采用 Rotary Positional Embedding（RoPE）（Su et al., 2024）。具体而言，对于 CSA 和 HCA 中使用的每个 query 向量和 KV 条目向量，我们会对其最后 64 个维度应用 RoPE。由于 KV 条目同时充当注意力 key 和 value，朴素的核心注意力输出 \(\left\{ \mathbf { o } _ { t , i } \right\}\) 会携带由 KV 条目加权求和导出的绝对位置编码。作为应对措施，我们还会在每个 \(\mathbf { o } _ { t , i }\) 的最后 64 个维度上，以位置 \(- i\) 再应用一次 RoPE。这样一来，核心注意力的输出也会携带相对位置编码 --- 每个 KV 条目对核心注意力输出的贡献也会与查询和该 KV 条目之间的距离相关。

额外的滑动窗口注意力分支。为了在 CSA 和 HCA 中严格保持因果性，每个 query 只会关注其之前的压缩 KV 块。因此，一个 query 无法访问与其处于同一压缩块中的其他 token 信息。与此同时，在语言建模中，最近的 token 往往与当前 query token 更为相关。基于这些原因，我们为 CSA 和 HCA 都引入了一个额外的滑动窗口式注意力分支，以更好地建模局部依赖。具体来说，对于每个 query token，我们还会额外生成 \(n _ { \mathrm { w i n } }\) 个未压缩的 KV 条目，对应最近的 \(n _ { \mathrm { w i n } }\) 个 token。在 CSA 和 HCA 的核心注意力中，这些滑动窗口内的 KV 条目将与压缩 KV 条目一起使用。

Attention Sink。在 CSA 和 HCA 的核心注意力中，我们采用了 attention sink 技巧（OpenAI, 2025; Xiao et al., 2024）。具体而言，我们设置了一系列可学习的 sink logits \(\{ z _ { 1 } ^ { \prime } , z _ { 2 } ^ { \prime } , . . . , z _ { n _ { h } } ^ { \prime } \}\)。对于第 \(h \cdot\) 个注意力头，\(\mathrm { E x p } ( z _ { h } ^ { \prime } )\) 会被加入到注意力分数分母中：

\[
s _ {h, i, j} = \frac {\operatorname {E x p} \left(z _ {h , i , j}\right)}{\sum_ {k} \operatorname {E x p} \left(z _ {h , i , k}\right) + \operatorname {E x p} \left(z _ {h} ^ {\prime}\right)}, \tag {27}
\]

其中 \(s _ { h , i , j } , z _ { h , i , j } \in \mathbb { R }\) 表示第 \(h\) 个注意力头在第 \(i\) 个查询 token 与第 \(j \cdot\) 个前序 token 或压缩块之间的注意力分数和注意力 logit。该技术使得每个 query 头都可以将其总注意力分数调节为不必等于 1，甚至可以接近 0。

\subsubsection{效率讨论}\label{efficiency-discussion}

由于采用了混合 CSA 和 HCA，并结合低精度计算与存储，DeepSeek-V4 系列的注意力模块在注意力 FLOPs 和 KV cache 大小两方面都实现了显著效率提升，尤其是在长上下文场景中。首先，我们为 KV 条目采用混合存储格式：RoPE 维度使用 BF16 精度，其余维度使用 FP8 精度。与纯 BF16 存储相比，这种混合表示将 KV cache 大小几乎减半。其次，lightning indexer 内部的注意力计算采用 FP4 精度，这在极长上下文下加速了注意力操作。第三，相较 DeepSeek-V3.2，DeepSeek-V4 系列采用了更小的 attention top-k，从而提升了模型在短文本和中等长度文本上的效率。最后，也是最重要的一点，压缩注意力与混合注意力技术大幅降低了 KV cache 大小和计算 FLOPs。

以头维度为 128 的 BF16 GQA8（Ainslie et al., 2023）作为基线 --- 这是 LLM 注意力的一种常见配置 --- 在 1M 上下文设置下，DeepSeek-V4 系列的 KV cache 大小可显著降低至约为该基线的 \(2 \%\)。

算法 1 DeepSeek-V4 的 Muon 优化器

Require: Learning rate \(\eta\) , momentum \(\mu\) , weight decay
\(\lambda\) , update rescaling factor \(\gamma\)\\
1: for each training step \(t\) do\\
2: for each logically independent weight
\(W \in \mathbb{R}^{n \times m}\) do\\
3: \(G_{t} = \nabla_{W} \mathcal{L}_{t}(W_{t-1})\)\\
4: \(M_{t} = \mu M_{t-1} + G_{t}\)\\
5: \(O_{t}' = \text{Hybrid NewtonSchulz}(\mu M_{t} + G_{t})\)\\
6: \(O_{t} = O_{t}' \cdot \sqrt{\max(n, m)} \cdot \gamma\)\\
7: \(W_{t} = W_{t-1} \cdot (1 - \eta \lambda) - \eta O_{t}\)\\
8: end for\\
9: end for

此外，即便与 DeepSeek-V3.2（DeepSeek-AI, 2025）--- 一个本已高效的基线 --- 相比，DeepSeek-V4 系列依然展现出显著的效率优势。它们的推理 FLOPs 与 KV cache 大小对比见图 1 右侧。

\subsection{Muon 优化器}\label{muon-optimizer}

由于收敛更快、训练稳定性更好，我们在 DeepSeek-V4 系列的大多数模块中采用 Muon（Jordan et al., 2024; Liu et al., 2025）优化器。我们的 Muon 优化完整算法总结见算法 1。

基本配置。对于 embedding 模块、prediction head 模块、mHC 模块中的静态偏置与门控因子，以及所有 RMSNorm 模块的权重，我们继续使用 AdamW（Loshchilov and Hutter, 2017）优化器。其余所有模块都使用 Muon 更新。遵循 Liu et al.~(2025)，我们也会对 Muon 参数施加 weight decay，使用 Nesterov（Jordan et al., 2024; Nesterov, 1983）技巧，并对更新矩阵的 Root Mean Square（RMS）进行重缩放，以复用我们的 AdamW 超参数。与他们不同的是，我们采用 hybrid Newton-Schulz iterations 来进行正交化。

Hybrid Newton-Schulz 迭代。对于给定矩阵 \(M\)，设其奇异值分解（SVD）为 \(M = U \Sigma V ^ { T }\)。Newton-Schulz 迭代的目标是将 \(M\) 近似正交化为 \(U V ^ { T }\)。通常，\(M\) 会先被归一化为 \(M _ { 0 } = M / | | \boldsymbol { M } | | _ { F }\)，以确保其最大奇异值不超过 1。随后，每一步 Newton-Schulz 迭代执行如下操作：

\[
M _ {k} = a M _ {k - 1} + b \left(M _ {k - 1} M _ {k - 1} ^ {T}\right) M _ {k - 1} + c \left(M _ {k - 1} M _ {k - 1} ^ {T}\right) ^ {2} M _ {k - 1}. \tag {28}
\]

我们的 hybrid Newton-Schulz 分两个阶段共执行 10 次迭代。在前 8 步中，我们使用系数 \(( a , b , c ) = ( 3 . 4 4 4 5 , - 4 . 7 7 5 0 , 2 . 0 3 1 5 )\) 来推动快速收敛，使奇异值接近 1。在最后 2 步中，我们切换到系数 \(( a , b , c ) = ( 2 , - 1 . 5 , 0 . 5 ) _ { . }\)，从而将奇异值精确稳定在 1。

避免注意力 logit 爆炸。DeepSeek-V4 系列的注意力架构使我们能够直接在注意力 query 和 KV 条目上应用 RMSNorm，这可以有效防止注意力 logit 爆炸。因此，我们在 Muon 优化器中不使用 QK-Clip 技术（Liu et al., 2025）。
