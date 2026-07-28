\section{通用基础设施}\label{general-infrastructures}

\subsection{专家并行中细粒度的通信-计算重叠}\label{fine-grained-communication-computation-overlap-in-expert-parallelism}

专家混合（MoE）可以通过专家并行（EP）加速。然而，EP 需要复杂的节点间通信，并对互连带宽和延迟提出了很高要求。为了缓解 EP 中的通信瓶颈，并在更低互连带宽要求下实现更高的端到端性能，我们提出了一种细粒度 EP 方案，将通信与计算融合进单个流水化 kernel 中，以实现通信-计算重叠。

通信延迟可以被隐藏。我们 EP 方案的关键洞见在于：在 MoE 层中，通信延迟可以有效隐藏在计算之下。如图 5 所示，在 DeepSeek-V4 系列中，每个 MoE 层主要可分解为四个阶段：两个受通信约束的阶段 Dispatch 和 Combine，以及两个受计算约束的阶段 Linear-1 和 Linear-2。我们的性能分析表明，在单个 MoE 层内，通信总时长小于计算总时长。因此，在将通信和计算融合为统一流水线之后，计算仍然是主要瓶颈，这意味着系统可以在不降低端到端性能的情况下容忍更低的互连带宽。

\begin{enumerate}
\def\labelenumi{(\alph{enumi})}
\tightlist
\item
  朴素方案
\end{enumerate}

\pandocbounded{\includegraphics[keepaspectratio,alt={image}]{images/f2ac4523895a5705584644bf4da73ddd23ac322af58e6d2291935e790c9fe5bc.jpg}}

\begin{enumerate}
\def\labelenumi{(\alph{enumi})}
\setcounter{enumi}{1}
\tightlist
\item
  Comet
\end{enumerate}

\pandocbounded{\includegraphics[keepaspectratio,alt={image}]{images/f525fd1a5cb552ce5b9a894259033d70ef4d8f2447ace4bc72cd0c1a8062d7ae.jpg}}

\begin{enumerate}
\def\labelenumi{(\alph{enumi})}
\setcounter{enumi}{2}
\tightlist
\item
  我们的方法
\end{enumerate}

\pandocbounded{\includegraphics[keepaspectratio,alt={image}]{images/b626abcfe97688178c9180f4a61338b18821e9443ba872ab14ed8278c6d8f829.jpg}}

图 5 \textbar{} 我们的 EP 方案及相关工作的示意图。Comet（Zhang et al., 2025b）分别将 Dispatch 与 Linear-1、以及 Linear-2 与 Combine 进行重叠。我们的 EP 方案通过将专家切分并调度为多个 wave，实现了更细粒度的重叠。理论加速比是在 DeepSeek-V4-Flash 架构配置下评估的。

细粒度 EP 方案。为了进一步降低互连带宽需求并放大重叠带来的收益，我们引入了更细粒度的专家划分方案。受多项相关工作启发（Aimuyo et al., 2025; Zhang et al., 2025b），我们将专家切分并调度为多个 wave。每个 wave 由一小部分专家组成。一旦某个 wave 中的所有专家完成通信，计算就可以立刻开始，而无需等待其他专家。在稳态下，当前 wave 的计算、下一 wave 的 token 传输以及已完成专家的结果发送会并发进行，如图 5 所示。这在专家之间形成了细粒度流水线，使得计算和通信在整个 wave 期间都能持续进行。基于 wave 的调度也提升了极端场景下的性能，例如强化学习（RL）rollout，这类场景通常会遇到长尾小批次。

性能与开源 Mega-Kernel。我们在 NVIDIA GPU 和 HUAWEI Ascend NPU 平台上验证了这一细粒度 EP 方案。与强大的非融合基线相比，它在一般推理工作负载上实现了 \(1 . 5 0 \sim 1 . 7 3 \times\) 的加速，在 RL rollout 和高速 agent 服务等延迟敏感场景下最高可达 \(1 . 9 6 \times\)。我们已将这一基于 CUDA 的 mega-kernel 实现开源，名称为 MegaMoE2，并作为 DeepGEMM 的一个组件发布。

观察与建议。我们分享 kernel 开发中的观察与经验，并向硬件厂商提出一些建议，希望有助于高效硬件设计，并实现更好的软硬件协同设计：

• 计算-通信比。完全的通信-计算重叠取决于计算-通信比，而不只是带宽本身。记峰值计算吞吐为 \(C\)，互连带宽为 \(B\)，当
\(C / B \leqslant V _ { \mathrm { c o m p } } / V _ { \mathrm { c o m m } }\) 时，通信可以被完全隐藏，其中 \(V _ { \mathrm { c o m p } }\) 表示计算量，\(V _ { \mathrm { c o m m } }\) 表示通信量。对于 DeepSeek-V4-Pro，每个 token-expert 对需要 \(6hd\) FLOPs（SwiGLU 的 gate、up 和 down 投影），但通信只需 \(3 h\) 字节（FP8 Dispatch \(^ +\) BF16 Combine），因此可化简为：

\[
\frac {C}{B} \leqslant 2 d = 6 1 4 4 \mathrm {F L O P s / B y t e}.
\]

也就是说，每 1 GBps 的互连带宽足以隐藏 6.1 TFLOP/s 计算所对应的通信。一旦带宽达到这一阈值，它就不再是瓶颈，而继续投入更多硅面积来提升带宽的收益将迅速递减。我们鼓励未来硬件设计瞄准这样的平衡点，而不是无条件地扩展带宽。

• 功耗预算。极致的 kernel 融合会同时让计算、内存和网络处于高负载状态，因此功耗限频会成为关键性能限制因素。我们建议未来的硬件设计为这种完全并发的工作负载提供充足的功耗余量。

• 通信原语。我们采用了 pull-based 方法，即每个 GPU 主动从远端 GPU 读取数据，从而避免细粒度 push 所带来的高通知延迟。若未来硬件能提供更低延迟的跨 GPU 信号机制，push 将变得可行，并支持更自然的通信模式。

• 激活函数。我们建议用一种低成本的逐元素激活函数替换 SwiGLU，该函数不涉及指数或除法运算。这会直接减轻 GEMM 后处理开销；并且在相同参数预算下，移除 gate 投影还能扩大中间维度 \(d\)，从而进一步放宽带宽要求。

\subsection{使用 TileLang 进行灵活高效的 Kernel 开发}\label{flexible-and-efficient-kernel-development-with-tilelang}

在实践中，我们精心设计的模型架构本会产生数百个细粒度的 Torch ATen 算子。我们采用 TileLang（Wang et al., 2026）开发了一组融合 kernel，替代其中绝大多数算子，以最小开发成本获得最优性能。它也使我们能够在验证阶段快速原型化诸如注意力变体之类的算子。这些 kernel 在模型架构开发、大规模训练，以及最终推理服务的生产部署中都发挥着关键作用。作为一种领域专用语言（DSL），TileLang 在开发效率与运行时性能之间取得了平衡，既支持快速开发，也支持在同一代码库中进行深入、迭代式优化。此外，我们还与 TileLang 社区紧密协作，以推动更加敏捷、高效且稳定的 kernel 开发生态。

通过 Host Codegen 降低调用开销。随着加速器性能持续提升，CPU 侧编排开销变得愈发突出。对于小型但高度优化的 kernel，这类固定的 host 开销很容易限制利用率和吞吐。此类开销的一个常见来源是 host 端逻辑，例如运行时契约检查，通常为了灵活性而以 Python 编写，因此会引入固定的每次调用开销。

我们通过 Host Codegen 缓解这一问题，它将大部分 host 侧逻辑迁移到生成式 host 代码中。具体而言，我们首先在 IR（Intermediate Representation）层面协同生成 device kernel 和轻量级 host launcher，并嵌入从语言前端解析出的必要元数据，例如数据类型、rank/shape 约束以及 stride/layout 假设。随后，该 launcher 会被 lowering 到基于 TVM-FFI（Chen et al., 2018）框架构建的 host 源码中，其紧凑的调用约定和零拷贝 tensor 互操作共同将 host 侧开销降到最低。在运行时，这些生成出来的 host 代码负责执行校验与参数封送，从而把每次调用的检查逻辑完全移出 Python 执行路径。我们的测量表明，CPU 侧校验开销已从数十到数百微秒降至每次调用不足一微秒。

借助 SMT 求解器的形式化整数分析。TileLang kernel 涉及复杂的张量索引整数运算，这需要强大的形式化整数分析能力。在布局推断、内存 hazard 检测和边界分析等编译过程里，编译器必须验证整数表达式是否满足特定性质，才能启用相应优化。因此，更强的形式化分析能力能够释放更高级、更复杂的优化机会。

为此，我们将 Z3 SMT 求解器（De Moura and Bjørner, 2008）集成到 TileLang 的代数系统中，为张量程序中的大多数整数表达式提供形式化分析能力。我们通过将 TileLang 的整数表达式翻译为 Z3 的无量词非线性整数算术（QF\_NIA），在计算开销与形式化表达能力之间取得平衡。基于整数线性规划（ILP）求解器，QF\_NIA 可以无缝处理 kernel 中常见的标准线性整数表达式。此外，其内在的非线性推理能力也能有效应对诸如可变张量形状上的向量化等高级挑战。在合理资源限制下，Z3 能显著提升整体优化效果，同时将编译时间开销限制在几秒之内。其影响覆盖多个编译过程，包括向量化、barrier 插入和代码简化。

数值精度与按位可复现性。在生产环境中，数值正确性和可复现性与原始吞吐同样重要。因此，我们默认优先保证精度：在编译器层面禁用 fast-math 优化，而影响精度的近似仅通过显式、可选启用的前端算子提供（例如 T.\_\_exp、T.\_\_log 和 T.\_\_sin）。相反，当需要严格的 IEEE-754 语义时，TileLang 提供带显式舍入模式的 IEEE 兼容 intrinsic（例如 T.ieee\_fsqrt、T.ieee\_fdiv 和 T.ieee\_add），使开发者能够精确指定数值行为。

我们还追求按位可复现，以便将 kernel 与手写 CUDA 基线进行校验。我们让 TileLang 的代数化简和 lowering 规则与主流 CUDA 工具链（例如 NVCC）保持一致，避免引入非预期的位级差异变换。布局标注（例如 T.annotate\_layout）还允许用户固定依赖布局的 lowering 决策，使求值和累加顺序与参考 CUDA 实现保持一致，从而在需要时实现按位完全一致的输出。

我们的评估表明，这些面向精度和可复现性的设计选择并未牺牲性能：在保守默认设置下，TileLang kernel 仍然具有竞争力，同时也提供了可按需放宽数值约束以换取更高速度的调节开关。

\subsection{高性能、批不变且确定性的 Kernel 库}\label{high-performance-batch-invariant-and-deterministic-kernel-libraries}

为了实现高效训练与推理，我们开发了一套完整的高性能计算 kernel。除了提供基础功能和最大化硬件利用率之外，另一个关键设计目标是确保预训练、后训练与推理流程之间的训练可复现性与按位对齐。因此，我们以尽可能小的性能开销实现了端到端、按位批不变且确定性的 kernel。这些 kernel 有助于调试、稳定性分析以及保证后训练行为的一致性。

批不变性。批不变性保证任意给定词元的输出都在比特级保持一致，而不受其在一个 batch 中位置的影响。为了实现批不变性，主要挑战如下：

• 注意力。为了实现批不变性，我们不能使用 split-KV 方法（Dao et al., 2023）。该方法会将单个序列的注意力计算分配到多个流式多处理器（SM）上，以平衡各 SM 的负载。然而，放弃这一技术会导致严重的 wave-quantization 问题3，并可能对 GPU 利用率造成不利影响。为了解决这一问题，我们开发了面向批不变解码的双 kernel 策略。第一个 kernel 在单个 SM 内计算整个序列的注意力输出，以保证在 wave 被完全占满时具有高吞吐。第二个 kernel 则为了最小化最后一个部分填充 wave 的延迟、从而缓解 wave-quantization，使用多个 SM 共同处理单个序列。为了让这两个 kernel 在比特级上保持一致，我们仔细设计了第二个 kernel 的计算路径，确保其累加顺序与第一个 kernel 相同。此外，第二个 kernel 利用了 thread-block cluster 内的 distributed shared memory4，从而支持 SM 之间的高速数据交换。这种双 kernel 方法将批不变解码带来的开销有效控制到可以忽略不计。

• 矩阵乘法。传统的 cuBLAS 库（NVIDIA Corporation, 2024）无法实现批不变性。因此，我们用 DeepGEMM（Zhao et al., 2025）在端到端范围内替换了它。此外，在极小 batch size 下，常规实现通常会采用 split-k（Osama et al., 2023）技术以提升性能。不幸的是，split-k 技术无法保证批不变性，而这正是 DeepSeek-V4 的关键特性。

因此，我们在大多数场景下放弃了 split-k，但这可能带来性能下降。为此，我们引入了一系列优化，使我们的矩阵乘法实现能够在大多数主要场景中达到甚至超过标准 split-k 的性能。

确定性。确定性训练对于调试硬件或软件问题非常有帮助。此外，当训练中出现 loss spike 等异常时，确定性能帮助研究者更容易定位数值原因，并进一步改进模型设计。训练中的非确定性通常源于非确定性的累加顺序，而这往往是由 atomic add 指令的使用导致的。这个问题主要出现在反向传播阶段，尤其体现在以下部分：

• 注意力反向传播。在稀疏注意力反向传播的常规实现中，我们使用 atomicAdd 来为 KV 词元累加梯度。由于浮点加法不满足结合律，这会引入非确定性。为了解决这个问题，我们为每个 SM 分配独立的累加缓冲区，随后再在所有缓冲区之上执行全局确定性求和。

• MoE 反向传播。当来自不同 rank 的多个 SM 并发向接收 rank 上的同一个缓冲区写数据时，写入位置的协商也会引入非确定性。为了解决这一问题，我们设计了单个 rank 内的词元顺序预处理机制，并结合跨多个 rank 的缓冲区隔离策略。这一策略确保了专家并行发送结果的确定性，以及 MoE 反向传播中累加顺序的确定性。

• mHC 中的矩阵乘法。mHC 包含一个输出维度仅为 24 的矩阵乘法。在极小 batch size 下，我们不得不使用 split-k（Osama et al., 2023）算法，而其朴素实现会导致非确定性。为了解决这一问题，我们分别输出每个 split 部分，并在后续 kernel 中执行确定性归约，从而同时保持性能与确定性。

\subsection{FP4 量化感知训练}\label{fp4-quantization-aware-training}

为了在部署时实现推理加速和内存节省，我们在后训练阶段引入量化感知训练（QAT）（Jacob et al., 2018），使模型能够适应量化带来的精度退化。我们将 FP4（MXFP4）量化（Rouhani et al., 2023）应用到两个部分：（1）MoE 专家权重，这是 GPU 内存占用的主要来源之一（OpenAI, 2025）；（2）CSA 中索引器的 Query-Key（QK）路径，其中 QK 激活会完全以 FP4 进行缓存、加载和乘法运算，从而加速长上下文场景中的注意力分数计算。此外，在这一 QAT 过程中，我们还将索引分数 \(I _ { : , i }\) 从 FP32 进一步量化到 BF16。该优化使 top-k 选择器实现了 \(2 \times\) 加速，同时保持了 \(9 9 . 7 \%\) 的 KV 条目召回率。

对于 MoE 专家权重，遵循 QAT 的常见做法，优化器维护的 FP32 主权重会先量化到 FP4，再反量化回 FP8 进行计算。值得注意的是，我们的 FP4 到 FP8 反量化是无损的。这是因为，相比 FP4（E2M1），FP8（E4M3）额外拥有 2 个指数位，因此具有更大的动态范围。于是，只要每个 FP8 量化块（\(128 \times 128\) tiles）内 FP4 子块（\(1 \times 32\) tiles）的最大与最小缩放因子之比不超过某个阈值，细粒度的缩放信息就可以被 FP8 扩展后的动态范围完全吸收。我们通过实验验证了当前权重满足这一条件。这使得整个 QAT 流程能够在不做任何修改的情况下，完全复用现有的 FP8 训练框架。在反向传播中，梯度是相对于前向传播中使用的同一份 FP8 权重计算的，并直接回传给 FP32 主权重，这等价于在量化操作上应用直通估计器（STE）。这也避免了对转置权重重新量化的需求。

在 RL 训练的推理与 rollout 阶段，由于不涉及反向传播，我们直接使用真实的 FP4 量化权重，而不是模拟量化。这确保了采样阶段的模型行为与在线部署完全一致，同时也减少了 kernel 的内存加载，从而带来真实加速，并显著降低内存消耗。我们对 CSA 索引器中的 QK 路径也采用了类似处理。

\subsection{训练框架}\label{training-framework}

我们的训练框架建立在为 DeepSeek-V3（DeepSeek-AI, 2024）开发的可扩展且高效的基础设施之上。在训练 DeepSeek-V4 时，我们继承了这一坚实基础，同时引入了若干关键创新，以适配其新的架构组件——具体包括 Muon 优化器、mHC 和混合注意力机制——同时保持高训练效率与稳定性。

\subsubsection{Muon 的高效实现}\label{efficient-implementation-of-muon}

Muon 优化器需要完整的梯度矩阵来计算参数更新，这在与零冗余优化器（ZeRO）（Rajbhandari et al., 2020）结合时带来了挑战。传统 ZeRO 是为 AdamW 这类逐元素优化器设计的，在这类优化器中，单个参数矩阵可以在多个 rank 之间切分并更新。为了解决这一冲突，我们为 Muon 设计了一种混合式 ZeRO bucket 分配策略。

对于稠密参数，我们限制 ZeRO 并行的最大规模，并采用背包算法将参数矩阵分配到这些 rank 上，以确保每个 rank 管理的负载大致均衡。每个 rank 上的 bucket 都会被填充到与各 rank 中最大 bucket 相同的大小，以便高效执行 reduce-scatter 操作。在我们的设置中，每个 rank 管理的参数矩阵不超过五个，因此这种填充通常带来的内存开销不到 \(1 0 \%\)。当数据并行的整体规模超过 ZeRO 的限制时，我们会在额外的数据并行组上冗余计算 Muon 更新，用计算换取更低的总 bucket 内存占用。

对于 MoE 参数，我们独立优化每个专家。我们首先将所有层中所有专家在 SwiGLU（Shazeer, 2020）里的 down projection 矩阵全部展平，接着展平 up projection 矩阵和 gate 矩阵。随后，我们对展平后的向量进行填充，以确保可以在不切分任何逻辑独立矩阵的前提下，将该向量均匀分配到所有 rank 上。由于专家数量很多，我们不对 MoE 参数施加 ZeRO 并行规模限制，因此填充开销也可以忽略不计。

此外，在每个 rank 上，形状相同且相邻的参数会被自动合并，从而可以批量执行 Newton-Schulz 迭代，以获得更好的硬件利用率。进一步地，我们观察到 Muon 中的 Newton-Schulz 迭代在使用 BF16 矩阵乘法计算时依然稳定。基于这一点，我们进一步以随机舍入方式，将需要在数据并行 rank 间同步的 MoE 梯度量化到 BF16 精度，从而将通信量减半。为避免低精度加法器引入的累加误差，我们用两阶段方法替代传统的基于树或环的 reduce-scatter collective。首先，通过一次 all-to-all 操作在各 rank 间交换本地梯度；然后，每个 rank 在本地以 FP32 执行求和。这一设计保持了数值鲁棒性。

\subsubsection{mHC 的低成本且内存高效实现}\label{cost-effective-and-memory-efficient-implementation-of-mhc}

mHC 的引入相比传统残差连接增加了激活内存消耗以及流水线阶段之间的通信量。为了缓解这些成本，我们实现了若干优化策略。

首先，我们为训练和推理都精心设计并实现了 mHC 的融合 kernel。其次，我们引入了一种重计算策略，对中间张量进行选择性 checkpoint。具体而言，我们会重算层间的大多数隐状态以及所有归一化后的层输入，同时避免重算计算密集型操作。这在内存节省与计算开销之间取得了平衡。第三，我们调整了 DualPipe1F1B 重叠方案，以适配增加后的流水线通信，并支持 mHC 中部分操作的并发执行。

综合来看，这些优化将 mHC 的墙钟时间开销限制到了重叠 1F1B 流水线阶段的 \(6 . 7 \%\)。更多工程优化细节可参见专门的 mHC 论文（Xie et al., 2026）。

\subsubsection{面向长上下文注意力的上下文并行}\label{contextual-parallelism-for-long-context-attention}

传统上下文并行（CP）会沿序列维度进行切分，每个 rank 维护连续的 \(s\) 个词元。这给我们的压缩注意力机制（即 CSA 和 HCA）带来了两个挑战。一方面，训练样本由多个序列打包而成，每个序列都会以 \(m\)（或 \(m ^ { \prime }\)）为因子独立压缩，而末尾少于 \(m\) 的词元会被丢弃。因此，压缩后的 KV 长度通常小于 \(\frac { s } { m }\)，并且在不同 rank 之间会有所不同。另一方面，压缩过程需要连续的 \(m\) 个 KV 条目，而这可能会跨越相邻两个 CP rank 的边界。

为了解决这些挑战，我们设计了一种两阶段通信方法。在第一阶段，每个 rank \(i\) 将其最后 \(m\) 个未压缩 KV 条目发送给 rank \(i + 1\)。然后，rank \(i + 1\) 将收到的部分条目与其本地的 \(s\) 个未压缩 KV 条目一起压缩，生成固定长度为 \(\textstyle { \frac { s } { m } } + 1\) 的压缩条目，其中会存在一些 padding 条目。在第二阶段，跨所有 CP rank 的 all-gather 操作会收集各自本地压缩得到的 KV 条目。随后，一个融合的 select-and-pad 算子会将它们重新组织成完整的压缩 KV 条目集合，总长度为 cp\_size · \(\frac { s } { m }\)。所有 padding 条目都会被放置在尾部。对于 HCA 和 CSA 中的索引器，每个查询词元可见的压缩 KV 条目范围都可以通过规则预先计算。对于 CSA 中的稀疏注意力，top- \(k\) 选择器则会显式指定每个查询可见压缩 KV 条目的索引。

\subsubsection{面向灵活激活检查点的扩展自动微分}\label{extended-automatic-differentiation-for-flexible-activation-checkpointing}

传统的激活检查点实现以整个模块为粒度，决定是否在反向传播时保留或重算其输出激活。这种粗粒度方式往往会在重计算成本与激活内存占用之间产生次优折中。另一种做法是手动实现整层的前向和反向逻辑，并显式管理张量 checkpoint 状态。虽然这种方法能提供细粒度控制，但它失去了自动微分框架的便利性，从而显著增加了开发复杂度。

为了在不牺牲编程效率的前提下实现细粒度控制，我们实现了一种支持自动微分的张量级激活检查点机制。借助这一机制，开发者只需实现前向传播，并对单个张量选择性地添加标注，以便自动执行 checkpoint 与重计算。我们的框架利用 TorchFX（Reed et al., 2022）追踪完整计算图。对于每个被标注的张量，它都会执行一次反向遍历，以识别其重计算所需的最小子图。我们将这些最小子图定义为重计算图，并在对应梯度计算之前将其插入到反向逻辑中。

与手工实现相比，这一设计在训练期间不会引入额外开销。该框架中的重计算是通过直接释放被标注张量的 GPU 内存，并复用重计算后张量的存储指针来实现的，无需任何 GPU 内存拷贝。此外，由于图追踪会具体执行模型，我们能够跟踪每个张量底层的存储指针，这使得对共享存储的张量（例如 reshape 操作的输入和输出）能够自动去重其重计算。这让开发者在标注重计算时无需再推理底层内存细节。

\subsection{推理框架}\label{inference-framework}

我们的推理框架大体继承自 DeepSeek-V3，但在 KV Cache 管理上存在一些差异。

\subsubsection{KV Cache 结构与管理}\label{kv-cache-structure-and-management}

为了高效管理 DeepSeek-V4 中由混合注意力机制产生的异构 KV cache，我们设计了一种定制化的 KV cache 布局。该布局如图 6 所示，下面我们将详细介绍。

DeepSeek-V4 中的异构 KV 条目。DeepSeek-V4 系列中的混合注意力机制引入了多种类型的 KV 条目，它们具有不同的 Key-Value（KV）cache 大小和更新规则。用于稀疏选择的闪电索引器为 KV cache 引入了额外维度，其嵌入大小与主注意力中的嵌入大小不同。CSA 和 HCA 中采用的压缩技术会分别将序列长度缩减为原来的 \(\frac { 1 } { m }\) 和 \(\frac { 1 } { m ^ { \prime } }\)，从而减少整体 KV cache 大小。因此，不同层之间的 KV cache 大小并不相同。此外，滑动窗口注意力（SWA）层也具有不同的 KV cache 大小，并采用独立的 cache 命中与淘汰策略。在压缩分支中，每 \(m\) 个词元会生成一个 KV 条目。当剩余词元数量不足以执行压缩时，所有待处理词元及其对应的隐状态都必须暂存在缓冲区中，直到可以执行压缩操作为止。这些缓冲中的词元表示一种由位置上下文决定的序列状态，也被纳入 KV cache 框架进行管理。

混合注意力 KV Cache 管理的挑战。混合注意力机制违背了 PagedAttention 及其变体背后的一些基本假设。尽管近期的混合 KV cache 管理算法（例如 Jenga（Zhang et al., 2025a）和 Hymba（Dong et al., 2025））面向通用混合注意力模型或特定结构，但在 PagedAttention 框架下，将所有层的 KV cache 统一整合仍面临两个主要障碍：

• 多样化的 cache 策略，例如滑动窗口注意力中使用的策略。

• 高性能注意力 kernel 所施加的约束，包括对齐要求。

\pandocbounded{\includegraphics[keepaspectratio,alt={image}]{images/8ff12c133c03a2b14799e17f210141b34549caddea4948c4b7e8a173ffa24a15.jpg}}

\pandocbounded{\includegraphics[keepaspectratio,alt={image}]{images/800a99ab9f9feb3ebdc99b4393370f0adc02c831d08080111240efd26617b7ba.jpg}}

图 6 \textbar{} DeepSeek-V4 的 KV cache 布局示意图。KV cache 被组织为两个主要部分：用于 CSA/HCA 的经典 KV cache，以及用于 SWA 和 CSA/HCA 中尚未满足压缩条件词元的状态 cache。在状态 cache 中，每个请求都会被分配一个固定大小的 cache block。在该 block 内，SWA 段存储最近 \(n _ { \mathrm { w i n } }\) 个词元对应的 KV 条目，而 CSA/HCA 段则存储尚未满足压缩条件的未压缩尾部状态。在经典 KV cache 中，我们为每个请求分配多个 block。每个 cache block 覆盖 \(\mathrm { l c m } ( m , m ^ { \prime } )\) 个原始词元，并产生
\(\begin{array} { r } { k _ { 1 } = \frac { \operatorname { l c m } ( m , m ^ { \prime } ) } { m } } \end{array}\)
个 CSA 压缩词元，以及
\(\begin{array} { r } { k _ { 2 } = \frac { \operatorname { l c m } ( m , m ^ { \prime } ) } { m ^ { \prime } } } \end{array}\)
个 HCA 压缩词元。

为了高效管理 DeepSeek-V4 的 KV cache，我们设计了相应策略来克服上述两个挑战。

用于 SWA 和未压缩尾部词元的状态 Cache。为了解决第一个障碍，我们采用了一种替代性的 cache 管理机制。由于 SWA 的设计目标是在受限 KV cache 大小下增强性能，因此，将它与压缩分支中未压缩的尾部词元一并视为一种状态空间模型是合理的。相应的 KV cache 因而可以被看作仅依赖当前位置的序列特定状态。据此，我们预先分配一个固定且有限大小的状态 cache 池，并将其动态分配给每条序列。

稀疏注意力 Kernel 协同设计。对于第二个障碍，传统高性能注意力 kernel 通常假设每个 block 具有固定数量 \(B\) 个词元以优化性能，这在 CSA 中对应 \(B \cdot m\) 个原始词元，在 HCA 中对应 \(B \cdot m ^ { \prime }\) 个原始词元。通过使用高性能稀疏注意力 kernel，不同层能够在不损失性能的情况下支持可变的每块词元数。实现这一点需要对 KV cache 布局和稀疏注意力 kernel 进行协同设计。例如，将 block 填充到与 cache line 对齐可以提升性能。因此，对于压缩率为 \(m\) 的 CSA 和压缩率为 \(m ^ { \prime }\) 的 HCA，每个 block 所含的原始词元数都可以是 \(\operatorname { l c m } ( m , m ^ { \prime } )\) 的任意整数倍，也就是这两个压缩率的最小公倍数。

\subsubsection{磁盘上的 KV Cache 存储}\label{on-disk-kv-cache-storage}

在服务 DeepSeek-V4 时，我们利用一种基于磁盘的 KV cache 存储机制，以消除共享前缀请求中的重复 prefilling。对于 CSA/HCA 中的压缩 KV 条目，以及滑动窗口注意力（SWA）中的未压缩 KV 条目，我们分别设计了不同的存储管理方案。

对于 CSA 和 HCA，我们直接将所有压缩 KV 条目存储到磁盘中。当某个请求命中已存储前缀时，我们会读取并复用该前缀对应的压缩 KV 条目，直到最后一个完整压缩 block。特别地，对于尾部不完整 block 中属于前缀的词元，我们仍然需要重新计算，以恢复未压缩 KV 条目，因为 CSA 和 HCA 中的未压缩 KV 条目并不会被存储。

对于 SWA 的 KV 条目，由于它们未被压缩且存在于每一层，其体积大约是压缩后 CSA 和 HCA KV 条目的 8 倍。为了高效处理这些庞大的 SWA KV 条目，我们提出并实现了三种不同的磁盘 SWA KV 条目管理策略，它们分别在存储开销与计算冗余之间提供不同的权衡：

• 完整 SWA 缓存。该策略为所有词元存储完整的 SWA KV 条目，从而实现计算零冗余。在这种策略下，命中前缀对应的 SWA KV 条目只需读取该前缀中最后 \(n _ { \mathrm { w i n } }\) 个词元的磁盘 cache 即可重建。尽管计算零冗余，这种策略对于现代基于 SSD 的存储系统并不高效——对于每个命中请求，只会访问所存储 SWA KV cache 的一小部分，从而形成一种不均衡、偏写密集的访问模式。

• 周期性 Checkpoint。该策略每隔 \(p\) 个词元，对最近 \(n _ { \mathrm { w i n } }\) 个词元的 SWA KV 条目进行一次 checkpoint，其中 \(p\) 是可调参数。对于一个命中前缀，我们加载最近一次 checkpoint 的状态，然后重算剩余的尾部词元。通过调节 \(p\)，该策略能够按需在存储与计算之间进行权衡。

• 零 SWA 缓存。该策略不存储任何 SWA KV 条目。对于命中前缀，我们需要执行更多重计算来恢复 SWA KV 条目。具体来说，在每个注意力层中，每个词元的 SWA KV 条目只依赖前一层中最近 \(n _ { \mathrm { W i n } }\) 个词元的 SWA KV 条目。因此，借助已缓存的 CSA 和 HCA KV 条目，只需重算最后 \(n _ { \mathrm { w i n } } \cdot L\) 个词元，就足以为一个 \(L\) 层模型恢复最后 \(n _ { \mathrm { w i n } }\) 个 SWA KV 条目。

我们会根据具体部署场景选择最合适的策略，以实现期望的存储-计算权衡。
