\section{1. 引言}\label{introduction}

推理模型（DeepSeek-AI, 2025; OpenAI, 2024c）的出现建立了一种新的测试时扩展范式，为大语言模型（LLMs）带来了显著的性能提升。然而，这一扩展范式从根本上受制于原始注意力机制（Vaswani et al., 2017）的二次计算复杂度，这为超长上下文和推理过程带来了难以承受的瓶颈。与此同时，从复杂的智能体工作流到海量跨文档分析，长时程场景与任务的兴起，也使得对超长上下文的高效支持成为未来进展的关键。尽管近期的开源工作（Bai et al., 2025a; DeepSeek-AI, 2024; MiniMax, 2025; Qwen, 2025）推动了通用能力的发展，但在处理超长序列方面，这一核心架构低效性仍是主要障碍，它限制了测试时扩展带来的进一步收益，也阻碍了对长时程场景和任务的进一步探索。

为了打破超长上下文中的效率壁垒，我们开发了 DeepSeek-V4 系列，包括 DeepSeek-V4-Pro 的预览版本（总参数 1.6T，激活参数 49B）和 DeepSeek-V4-Flash 的预览版本（总参数 284B，激活参数 13B）。通过架构创新，DeepSeek-V4 系列在处理超长序列时实现了计算效率的巨大飞跃。这一突破使得对一百万 token 上下文长度的高效支持成为可能，为下一代大语言模型开启了百万长度上下文的新纪元。我们相信，高效处理超长序列的能力将解锁测试时扩展的下一个前沿，为长时程任务的更深入研究铺平道路，并为探索在线学习等未来范式奠定必要基础。

与 DeepSeek-V3 架构（DeepSeek-AI, 2024）相比，DeepSeek-V4 系列保留了 DeepSeekMoE 框架（Dai et al., 2024）和 Multi-Token Prediction（MTP）策略，同时在架构与优化上引入了若干关键创新。为了提升长上下文效率，我们设计了一种结合压缩稀疏注意力（CSA）和重度压缩注意力（HCA）的混合注意力机制。CSA 沿序列维度压缩 KV cache，然后执行 DeepSeek Sparse Attention（DSA）（DeepSeek-AI, 2025）；而 HCA 对 KV cache 采用更激进的压缩，但保持稠密注意力。为了增强建模能力，我们引入了流形约束超连接（mHC）（Xie et al., 2026），用于强化传统残差连接。此外，我们还将 Muon（Jordan et al., 2024; Liu et al., 2025）优化器引入 DeepSeek-V4 系列的训练中，从而获得更快的收敛速度和更好的训练稳定性。

为了使 DeepSeek-V4 系列的训练与推理更加高效，同时也提升开发效率，我们引入了多项基础设施优化。首先，我们为 MoE 模块设计并实现了一个单一融合内核，使计算、通信和内存访问得以完全重叠。其次，我们采用 TileLang（Wang et al., 2026）这一领域专用语言（DSL），以平衡开发效率与运行时效率。第三，我们提供了高效的批不变与确定性内核库，以确保训练和推理过程中的按位可复现性。第四，我们对 MoE 专家权重以及索引器的 QK 路径引入了 FP4 量化感知训练，以降低内存和计算开销。第五，在训练框架方面，我们通过张量级 checkpointing 扩展了 autograd 框架，以实现细粒度的重计算控制；同时，我们还通过面向 Muon 优化器的混合 ZeRO 策略、借助重计算与融合内核实现的低成本 mHC，以及用于管理压缩注意力的两阶段上下文并行，进一步提升训练效率。最后，在推理框架方面，我们设计了异构 KV cache 结构及其磁盘存储策略，以实现共享前缀的高效复用。

通过采用混合 CSA 与 HCA，并配合计算与存储精度优化，DeepSeek-V4 系列相比 DeepSeek-V3.2 在推理 FLOPs 和 KV cache 大小上都实现了显著下降，尤其是在长上下文设定中更为明显。图 1 右侧展示了 DeepSeek-V3.2 与 DeepSeek-V4 系列估算得到的单 token 推理 FLOPs 和累积 KV cache 大小。在 1M-token 上下文场景下，即使激活参数更多的 DeepSeek-V4-Pro，其单 token FLOPs（以等效 FP8 FLOPs 计）也仅为 DeepSeek-V3.2 的 \(2 7 \%\)，KV cache 大小仅为其 \(1 0 \%\)。进一步地，激活参数更少的 DeepSeek-V4-Flash 将效率推得更高：在 1M-token 上下文设定下，其单 token FLOPs 仅为 DeepSeek-V3.2 的 \(1 0 \%\)，KV cache 大小仅为其 \(7 \%\)。此外，在 DeepSeek-V4 系列中，路由专家参数使用 FP4 精度。尽管在现有硬件上，\(\mathrm { F P 4 } \times \mathrm { F P 8 }\) 运算的峰值 FLOPs 目前与 \(\mathrm { F P 8 } \times \mathrm { F P 8 }\) 相同，但从理论上讲，它们在未来硬件上可以实现高出 1/3 的效率，这将进一步提升 DeepSeek-V4 系列的效率。

在预训练阶段，我们分别用 32T token 训练 DeepSeek-V4-Flash，用 33T token 训练 DeepSeek-V4-Pro。经过预训练后，这两个模型都能够原生且高效地支持 1M 长度上下文。在我们的内部评测中，DeepSeek-V4-Flash-Base 凭借更高的参数效率设计，已经在大多数基准上超过了 DeepSeek-V3.2-Base。DeepSeek-V4-Pro-Base 则进一步扩大了这一优势，在 DeepSeek 基座模型中树立了新的性能标准，在推理、代码、长上下文和世界知识任务上都表现出全面优势。

DeepSeek-V4 系列的后训练流程采用两阶段范式：先独立培养领域专精专家，再通过 on-policy distillation（Lu and Lab, 2025）将其统一整合。首先，针对每个目标领域——例如数学、代码、智能体和指令跟随——分别独立训练一个专家模型。基座模型先在高质量的领域专用数据上进行监督微调（SFT），以建立基础能力。随后，再使用 Group Relative Policy Optimization（GRPO）（DeepSeek-AI, 2025）进行强化学习（RL），在面向特定成功标准设计的奖励模型引导下，进一步优化模型的领域对齐行为。该阶段产出一组多样化的专门专家模型，每个模型都在各自领域中表现突出。最后，为了整合这些不同专长，我们通过 on-policy distillation 训练一个统一模型，其中统一模型作为学生模型，学习在教师模型指导下优化反向 KL 损失。

\section{核心评测结果摘要}\label{summary-of-core-evaluation-results}

• 知识：在广泛世界知识评测中，DeepSeek-V4-Pro-Max 作为 DeepSeek-V4-Pro 的最大推理开销模式，在 SimpleQA（OpenAI, 2024d）和 Chinese-SimpleQA（He et al., 2024）基准上显著优于领先的开源模型。在教育知识方面——通过 MMLU-Pro（Wang et al., 2024b）、HLE（Phan et al., 2025）和 GPQA（Rein et al., 2023）评测——DeepSeek-V4-Pro-Max 也略微领先于其他开源对手。尽管在这些知识类评测中仍落后于领先的闭源模型 Gemini-3.1-Pro，DeepSeek-V4-Pro-Max 已经显著缩小了与其之间的差距。

• 推理：随着推理 token 数量的扩展，DeepSeek-V4-Pro-Max 在标准推理基准上表现优于 GPT-5.2 和 Gemini-3.0-Pro。不过，它的性能仍略逊于 GPT-5.4 和 Gemini-3.1-Pro，这表明其发展进度大约落后于最先进前沿模型 3 到 6 个月。进一步地，DeepSeek-V4-Flash-Max 在性能上可与 GPT-5.2 和 Gemini-3.0-Pro 相当，成为一种在复杂推理任务上极具性价比的架构。

\pandocbounded{\includegraphics[keepaspectratio,alt={image}]{images/2c5ffc992a56d87715c81c76ccc8e01e6186c02cf3a03d4a75ca416f22237b79.jpg}}

图 2 \textbar{} DeepSeek-V4 系列的整体架构。我们在注意力层使用混合 CSA（Compressed Sparse Attention）和 HCA（Heavily Compressed Attention），在前馈层使用 DeepSeekMoE，并通过 mHC 强化传统残差连接。

• 智能体：在公开基准上，DeepSeek-V4-Pro-Max 与 Kimi-K2.6 和 GLM-5.1 等领先开源模型大致相当，但略逊于前沿闭源模型。在我们的内部评测中，DeepSeek-V4-Pro-Max 优于 Claude Sonnet 4.5，并接近 Opus 4.5 的水平。

• 长上下文：DeepSeek-V4-Pro-Max 在 100 万 token 上下文窗口下的合成任务和真实用例上都取得了强劲结果，甚至在学术基准上超过了 Gemini-3.1-Pro。

• DeepSeek-V4-Pro 与 DeepSeek-V4-Flash 对比：由于参数规模更小，DeepSeek-V4-Flash-Max 在知识类评测中的表现较低。然而，当分配更大的思考预算时，它在推理任务上能够取得相当的结果。在智能体评测中，虽然 DeepSeek-V4-Flash-Max 在若干基准上与 DeepSeek-V4-Pro-Max 表现相当，但在更复杂、更高难度的任务上仍落后于其更大的对应模型。

\section{2. 架构}\label{architecture}

总体而言，DeepSeek-V4 系列保留了 Transformer（Vaswani et al., 2017）架构和 Multi-Token Prediction（MTP）模块（DeepSeek-AI, 2024; Gloeckle et al., 2024），同时相较于 DeepSeek-V3 引入了若干关键升级：（1）首先，我们引入了流形约束超连接（mHC）（Xie et al., 2026），以强化传统残差连接；

\begin{enumerate}
\def\labelenumi{(\arabic{enumi})}
\setcounter{enumi}{1}
\tightlist
\item
  其次，我们设计了一种混合注意力架构，通过压缩稀疏注意力和重度压缩注意力显著提升长上下文效率。（3）第三，我们采用 Muon（Jordan et al., 2024; Liu et al., 2025）作为优化器。对于专家混合（MoE）组件，我们仍采用 DeepSeekMoE（Dai et al., 2024）架构，仅在 DeepSeek-V3 的基础上做了少量调整。Multi-Token Prediction（MTP）（DeepSeek-AI, 2024; Gloeckle et al., 2024; Li et al., 2024; Qi et al., 2020）的配置则与 DeepSeek-V3 完全一致。其他未特别说明的细节均沿用 DeepSeek-V3（DeepSeek-AI, 2024）中已建立的设置。图 2 展示了 DeepSeek-V4 的整体架构，具体细节将在下文介绍。
\end{enumerate}

\section{2.1. 继承自 DeepSeek-V3 的设计}\label{designs-inherited-from-deepseek-v3}

专家混合。与先前的 DeepSeek 系列模型（DeepSeek-AI, 2024; DeepSeek-AI, 2024）一样，DeepSeek-V4 系列也在前馈网络（FFNs）中采用了 DeepSeekMoE 范式（Dai et al., 2024），其设置包括细粒度路由专家和共享专家。与 DeepSeek-V3 不同的是，我们将用于计算亲和分数的激活函数从 Sigmoid(·) 改为 Sqrt(Softplus(·))。在负载均衡方面，我们也采用了无辅助损失策略（DeepSeek-AI, 2024; Wang et al., 2024a），并增加了轻量的按序列平衡损失，以防止单个序列内部出现极端不均衡。对于 DeepSeek-V4，我们移除了对路由目标节点数量的约束，并仔细重新设计了并行策略，以维持训练效率。此外，与 DeepSeek-V3 相比，我们将最前面若干个 Transformer block 中的稠密 FFN 层替换为使用 Hash routing（Roller et al., 2021）的 MoE 层。Hash routing 策略会根据输入 token ID 上的预定义哈希函数，为每个 token 决定其目标专家。

多 Token 预测。与 DeepSeek-V3 相同，DeepSeek-V4 系列也设置了 MTP 模块与目标。鉴于 MTP 策略已在 DeepSeek-V3 中得到验证，我们对 DeepSeek-V4 系列直接采用相同策略而不做修改。

\section{2.2. 流形约束超连接}\label{manifold-constrained-hyper-connections}

如图 2 所示，DeepSeek-V4 系列引入了流形约束超连接（mHC）（Xie et al., 2026），用于强化相邻 Transformer block 之间的传统残差连接。与朴素的超连接（HC）（Zhu et al., 2025）相比，mHC 的核心思想是将残差映射约束到某个特定流形上，从而在保持模型表达能力的同时，增强跨层信号传播的稳定性。本小节将简要介绍标准 HC，并说明我们如何设计 mHC 以实现稳定训练。

标准超连接。标准 HC 将残差流的宽度扩展为原来的 \(n _ { \mathrm { h c } }\) 倍。具体来说，残差流的形状从 \(\mathbb { R } ^ { d }\) 扩展为 \(\mathbb { R } ^ { n _ { \mathrm { h c } } \times d }\)，其中 \(d\) 是实际层输入的隐藏维度。令
\(X _ { l } = [ \mathbf { x } _ { l , 1 } ; \ldots ; \mathbf { x } _ { l , n _ { \mathrm { h c } } } ] ^ { T } \in \mathbb { R } ^ { n _ { \mathrm { h c } } \times d }\)
表示第 \(l\) 层之前的残差状态。HC 引入了三个线性映射：输入映射
\(A _ { l } \in \mathbb { R } ^ { 1 \times n _ { \mathrm { h c } } }\)，残差变换
\(B _ { l } \in \mathbb { R } ^ { n _ { \mathrm { h c } } \times n _ { \mathrm { h c } } }\)，以及输出映射
\(C _ { l } \in \mathbb { R } ^ { n _ { \mathrm { h c } } \times 1 }\)。残差状态的更新形式为：

\[
X _ {l + 1} = B _ {l} X _ {l} + C _ {l} \mathcal {F} _ {l} \left(A _ {l} X _ {l}\right), \tag {1}
\]

其中 \(\mathcal { F } _ { l }\) 表示第 \(l\) 层（例如某个 MoE 层），其输入和输出形状均为 \(\mathbb { R } ^ { d }\)。注意，实际层输入 \(A _ { l } X _ { l } \in \mathbb { R } ^ { d }\) 仍然是 \(d\) 维的，因此扩展后的残差宽度不会影响内部层的设计。HC 将残差宽度与实际隐藏维度解耦，提供了一条互补的扩展轴，而且计算开销很小，因为 \(n _ { \mathrm { h c } }\) 通常远小于隐藏维度 \(d\)。然而，尽管 HC 在提升模型性能方面展现出潜力，我们发现当堆叠多层时，训练过程会频繁出现数值不稳定，从而阻碍 HC 的进一步扩展。

流形约束残差映射。mHC 的核心创新在于，将残差映射矩阵 \(B _ { l }\) 约束到双随机矩阵流形（Birkhoff polytope）\(\mathcal { M }\) 上，从而增强跨层信号传播的稳定性：

\[
B _ {l} \in \mathcal {M} := \{M \in \mathbb {R} ^ {n \times n} \mid M \mathbf {1} _ {n} = \mathbf {1} _ {n}, \mathbf {1} _ {n} ^ {T} M = \mathbf {1} _ {n} ^ {T}, M \geqslant 0 \}. \tag {2}
\]

这一约束保证了映射矩阵的谱范数 \(\| B _ { l } \| _ { 2 }\) 被限制在 1 以内，因此残差变换是非扩张的，这提升了前向传播和反向传播中的数值稳定性。此外，集合 \(\mathcal { M }\) 在乘法下是封闭的，这保证了在深层堆叠 mHC 的场景中依然稳定。除此之外，输入变换 \(A _ { l }\) 和输出变换 \(C _ { l }\) 也通过 Sigmoid 函数被约束为非负且有界，以避免信号抵消的风险。

动态参数化。三个线性映射的参数是动态生成的，并被分解为动态（依赖输入）部分和静态（不依赖输入）部分。给定输入
\(X _ { l } \in \mathbb { R } ^ { n _ { \mathrm { h c } } \times d }\)，首先对其进行展平和归一化：
\(\hat { X } _ { l } = \mathrm { R M S N o r m } ( \mathrm { v e c } ( X _ { l } ) ) \in \mathbb { R } ^ { 1 \times n _ { \mathrm { h c } } d }\)。
然后，我们沿用传统 HC 的方式生成不受约束的原始参数
\(\tilde { A } _ { l } \in \mathbb { R } ^ { 1 \times n _ { \mathrm { h c } } }\)，
\(\tilde { B } _ { l } \in \mathbb { R } ^ { n _ { \mathrm { h c } } \times n _ { \mathrm { h c } } }\)，以及
\(\tilde { C } _ { l } \in \mathbb { R } ^ { n _ { \mathrm { h c } } \times 1 }\)：

\[
\tilde {A} _ {l} = \alpha_ {l} ^ {\text {p r e}} \cdot \left(\hat {X} _ {l} W _ {l} ^ {\text {p r e}}\right) + S _ {l} ^ {\text {p r e}}, \tag {3}
\]

\[
\tilde {B} _ {l} = \alpha_ {l} ^ {\mathrm {r e s}} \cdot \operatorname {M a t} \left(\hat {X} _ {l} W _ {l} ^ {\mathrm {r e s}}\right) + S _ {l} ^ {\mathrm {r e s}}, \tag {4}
\]

\[
\tilde {C} _ {l} = \alpha_ {l} ^ {\text {p o s t}} \cdot \left(\hat {X} _ {l} W _ {l} ^ {\text {p o s t}}\right) ^ {T} + S _ {l} ^ {\text {p o s t}}, \tag {5}
\]

其中
\(W _ { l } ^ { \mathrm { p r e } } , W _ { l } ^ { \mathrm { p o s t } } \in \mathbb { R } ^ { n _ { \mathrm { h c } } d \times n _ { \mathrm { h c } } }\)
以及
\(W _ { l } ^ { \mathrm { r e s } } \in \mathbb { R } ^ { n _ { \mathrm { h c } } d \times n _ { \mathrm { h c } } ^ { 2 } }\)
是用于生成动态部分的可学习参数；
\(\mathrm { { M a t } ( \cdot ) }\) 会将大小为
\(1 \times n _ { \mathrm { h c } } ^ { 2 }\) 的向量重塑为大小
\(n _ { \mathrm { h c } } \times n _ { \mathrm { h c } }\) 的矩阵；
\(S _ { l } ^ { \mathrm { p r e } } \in \mathbb { R } ^ { 1 \times n _ { \mathrm { h c } } } , S _ { l } ^ { \mathrm { p o s t } } \in \mathbb { R } ^ { n _ { \mathrm { h c } } \times 1 }\)，以及
\(S _ { l } ^ { \mathrm { r e s } } \in \mathbb { R } ^ { n _ { \mathrm { h c } } \times n _ { \mathrm { h c } } }\)
是可学习的静态偏置；而
\(\alpha _ { l } ^ { \mathrm { p r e } } , \alpha _ { l } ^ { \mathrm { r e s } } , \alpha _ { l } ^ { \mathrm { p o s t } } \in \mathbb { R }\)
是初始化为较小数值的可学习门控因子。

施加参数约束。在获得不受约束的原始参数
\(\tilde { A } _ { l } , \tilde { B } _ { l } , \tilde { C } _ { l }\) 之后，我们再对它们施加前文描述的约束，以增强数值稳定性。具体来说，对于输入映射和输出映射，我们采用 Sigmoid 函数 \(\sigma ( \cdot )\) 来保证其非负性和有界性：

\[
A _ {l} = \sigma (\tilde {A} _ {l}), \tag {6}
\]

\[
C _ {l} = 2 \sigma (\tilde {C} _ {l}). \tag {7}
\]

至于残差映射 \(\tilde { B } _ { l }\)，我们将其投影到双随机矩阵流形 \(\mathcal { M }\) 上。这一过程通过 Sinkhorn-Knopp 算法实现：首先对 \(\tilde { B } _ { l }\) 应用指数函数以保证其为正，得到 \(M ^ { ( 0 ) } = \exp ( \tilde { B } _ { l } )\)，然后迭代执行列归一化和行归一化：

\[
M ^ {(t)} = \mathcal {T} _ {r} \left(\mathcal {T} _ {c} \left(M ^ {(t - 1)}\right)\right), \tag {8}
\]

其中 \(\mathcal { T } _ { r }\) 和 \(\mathcal { T } _ { c }\) 分别表示行归一化和列归一化。该迭代会收敛到一个受约束的双随机矩阵 \(B _ { l } = M ^ { ( t _ { \operatorname* { m a x } } ) }\)。我们选择 \(t _ { \mathrm { m a x } } = 2 0\) 作为一个实用取值。

\pandocbounded{\includegraphics[keepaspectratio,alt={image}]{images/cff2b362b699adbc334a2f504449cbfbb7010bb6f736884475dc536b11b1d80b.jpg}}

图 3 \textbar{} CSA 的核心架构。它将 KV 条目数量压缩为原来的 \(\textstyle { \frac { 1 } { m } }\)，然后进一步应用 DeepSeek Sparse Attention 进行加速。此外，还会将一小组滑动窗口 KV 条目与选中的压缩 KV 条目结合起来，以增强局部细粒度依赖。

\section{2.3. CSA 与 HCA 的混合注意力}\label{hybrid-attention-with-csa-and-hca}

随着上下文长度达到极端规模，注意力机制成为模型中的主要计算瓶颈。针对 DeepSeek-V4，我们设计了两种高效的注意力架构——压缩稀疏注意力（CSA）和重度压缩注意力（HCA）——并采用它们交错的混合配置，从而在长文本场景下显著降低注意力的计算成本。CSA 同时结合了压缩与稀疏注意力策略：它先将每 \(m\) 个词元的 Key-Value（KV）缓存压缩为一个条目，然后应用 DeepSeek Sparse Attention（DSA）（DeepSeek-AI, 2025），其中每个查询词元只关注 \(k\) 个压缩后的 KV 条目。HCA 则追求更极致的压缩，将每
\(m ^ { \prime } \left( \gg m \right)\) 个词元的 KV 缓存合并为一个条目。CSA 与 HCA 的混合架构显著提升了 DeepSeek-V4 系列的长上下文效率，使一百万词元上下文在实践中成为可能。本小节介绍我们混合注意力架构的核心技术，同时我们也提供了一个开源实现1，以更明确地说明更多细节。
