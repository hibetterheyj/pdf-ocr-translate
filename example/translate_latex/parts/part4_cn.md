\section{后训练}\label{post-training}

\subsection{后训练流程}\label{post-training-pipeline}

在预训练之后，我们开展了后训练阶段，以得到 DeepSeek-V4 系列的最终模型。尽管训练流程在很大程度上沿用了 DeepSeek-V3.2 的方案，但其中发生了一项关键的方法学替换：混合强化学习（RL）阶段被完全替换为在策略蒸馏（On-Policy Distillation, OPD）。

\subsubsection{专家训练}\label{specialist-training}

领域专家的开发是通过适配 DeepSeek-V3.2 的训练流程来完成的。具体而言，每个模型都依次经过初始微调阶段，以及在领域特定提示和奖励信号引导下进行的后续强化学习（RL）阶段。对于 RL 阶段，我们实现了 Group Relative Policy Optimization（GRPO）算法，并保持超参数与我们此前研究中的设置高度一致（DeepSeek-AI,2025; DeepSeek-AI, 2025）。

推理强度。众所周知，模型在推理任务上的性能从根本上受所投入计算量的支配。因此，我们在不同的 RL 配置下训练了不同的专家模型，以推动面向不同推理能力优化的模型开发。如表 2 所示，DeepSeek-V4-Pro 和 DeepSeek-V4-Flash 都支持三种特定的推理强度模式。对于每一种模式，我们在 RL 训练中施加不同的长度惩罚和上下文窗口，因此会产生不同的推理输出 token 长度。为了整合这些不同的推理模式，我们采用由 <think> 和 </think> token 界定的专门响应格式。此外，对于 ``Think Max'' 模式，我们会在系统提示开头添加一条特定指令，以引导模型的推理过程，如表 3 所示。

生成式奖励模型。通常，易于验证的任务可以通过简单的基于规则的验证器或测试用例得到有效优化。相比之下，难以验证的任务传统上依赖基于人类反馈的强化学习（RLHF），这需要大量人工标注来训练标量奖励模型。然而，在 DeepSeek-V4 系列的后训练阶段，我们不再使用这些传统的标量奖励模型。相反，为了处理难以验证的任务，我们构建了由评分准则引导的 RL 数据，并采用生成式奖励模型（GRM）来评估策略轨迹。关键在于，我们直接对 GRM 本身施加 RL 优化。在这一范式下，actor 网络天然地充当 GRM，从而使模型能够在其标准生成能力之外，同时联合优化其评估（判别）能力。通过统一这两种角色，模型内部的推理能力自然地融入了评估过程，从而带来了高度稳健的打分表现。此外，这种方法仅需极少量多样化的人类标注便可取得更优性能，因为模型能够利用自身逻辑在复杂任务之间进行泛化。

表 2 \textbar{} 三种推理模式的比较

{\def\LTcaptype{none} % do not increment counter
\begin{longtable}[]{@{}|l|l|l|l|@{}}
\toprule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
\hline
推理模式 & 特征 & 典型使用场景 & 响应格式 \\
\hline
Non-think & 基于习惯或简单规则的快速、直觉式响应。 & 日常例行任务、紧急反应、低风险决策。 &
\textless/think\textgreater{} 总结 \\
\hline
Think High & 有意识的逻辑分析，更慢但更准确。 &
复杂问题求解、规划、中等风险决策。 &
\textless think\textgreater{} 思考 token
\textless/think\textgreater{} 总结 \\
\hline
Think Max & 将推理能力推向极限。速度较慢但更强大。 &
探索模型推理能力的边界。 & 1. 开头加入一条特殊系统提示。 2. \textless think\textgreater{}
思考 token \textless/think\textgreater{} 总结 \\
\hline
\end{longtable}
}

表 3 \textbar{} 为 ``Think Max'' 模式注入到系统提示中的指令。

\medskip
\phantomsection\label{injected-instruction}
\noindent\textbf{注入的指令}

推理强度：绝对最大化，不允许任何捷径。

你必须非常彻底地思考，并全面拆解问题以定位根因，同时对你的逻辑在所有潜在路径、边界情况和对抗场景下进行严格压力测试。

请明确写出你的完整思考过程，记录每一个中间步骤、考虑过的替代方案以及被否决的假设，确保没有任何一个假设未经检验。

工具调用 Schema 与特殊 token。与上一版本一致，我们使用专门的 <think></think> 标签来界定推理路径。在 DeepSeek-V4 系列中，我们引入了一种新的工具调用 schema，它使用特殊的 ``\textbar DSML\textbar{}'' token，并采用基于 XML 的工具调用格式，如表 4 所示。我们的实验表明，XML 格式能够有效缓解转义失败并减少工具调用错误，为模型与工具的交互提供更稳健的接口。

交错思考。DeepSeek-V3.2 引入了一种上下文管理策略：在工具结果往返轮次之间保留推理轨迹，但在新用户消息到来时将其丢弃。虽然这种方法有效，但在复杂的智能体工作流中仍会造成不必要的 token 浪费——每一轮新的用户输入都会清空累积的推理内容，迫使模型从头重建其问题求解状态。借助 DeepSeek-V4 系列扩展后的 1M-token 上下文窗口，我们进一步完善了这一机制，以最大化交错思考在智能体环境中的效果：

表 4 \textbar{} DeepSeek-V4 系列的工具调用 schema。

\medskip
\phantomsection\label{tool-call-schema}
\noindent\textbf{工具调用 Schema}

\begin{Shaded}
\begin{Highlighting}[]
\NormalTok{\#\# Tools}
\NormalTok{你可以使用一组工具来帮助回答用户的问题。你可以通过写出如下所示的 "\textless{}|DSML|tool\_calls\textgreater{}" 代码块来调用工具：}
\NormalTok{\textless{}|DSML|tool\_calls\textgreater{}}
\NormalTok{\textless{}|DSML|invoke name="$TOOL\_NAME"\textgreater{}}
\NormalTok{\textless{}|DSML|parameter name="$PARAMETER\_NAME" string="true|false"\textgreater{}$PARAMETER\_VALUE \textless{}/|DSML|parameter\textgreater{}}
\NormalTok{...}
\NormalTok{\textless{}/|DSML|invoke\textgreater{}}
\NormalTok{\textless{}|DSML|invoke name="$TOOL\_NAME2"\textgreater{}}
\NormalTok{...}
\NormalTok{\textless{}/|DSML|invoke\textgreater{}}
\NormalTok{\textless{}/|DSML|tool\_calls\textgreater{}}
\NormalTok{字符串参数应按原样指定，并设置 \textquotesingle{}string="true"\textquotesingle{}。对于所有其他类型（数字、布尔值、数组、对象），请以 JSON 格式传入其值，并设置 \textquotesingle{}string="false"\textquotesingle{}。如果启用了 thinking\_mode（由 \textless{}think\textgreater{} 触发），你必须在任何工具调用或最终响应之前，将完整推理输出在 \textless{}think\textgreater{}...\textless{}/think\textgreater{} 中。}
\NormalTok{否则，请在 \textless{}/think\textgreater{} 之后直接输出工具调用或最终响应。}
\NormalTok{\#\# Available Tool Schemas}
\NormalTok{\{Tool Definition...\}}
\NormalTok{你必须严格遵循上面定义的工具名称和参数 schema 来调用工具。}
\end{Highlighting}
\end{Shaded}

• 工具调用场景。如图 7(a) 所示，所有推理内容都会在整个对话过程中被完整保留。不同于 DeepSeek-V3.2 会在每个新的用户轮次到来时丢弃思考轨迹，DeepSeek-V4 系列会跨越所有轮次保留完整的推理历史，包括跨用户消息边界的部分。这使模型能够在长时程智能体任务中维持连贯且累积的思维链。

• 一般对话场景。如图 7(b) 所示，原有策略仍被保留：当新的用户消息到来时，上一轮的推理内容会被丢弃，从而在持久化推理轨迹收益有限的场景中保持上下文简洁。

与 DeepSeek-V3.2 一样，那些通过用户消息来模拟工具交互的智能体框架（例如 Terminus）可能不会触发工具调用上下文路径，因此也未必能从增强的推理持久化中受益。对于这类架构，我们仍然建议使用 non-think 模型。

\pandocbounded{\includegraphics[keepaspectratio,alt={image}]{images/4be752e05d87cef59ec7af493df9496715a6bc784d70c4211ed49472fa3d170a.jpg}}

\begin{enumerate}
\def\labelenumi{\alph{enumi})}
\tightlist
\item
  使用工具进行思考
\end{enumerate}

\pandocbounded{\includegraphics[keepaspectratio,alt={image}]{images/24960dcda89eda0cde433e9ee38d0be1707fe778a521bc2f8fc0b6bf09235192.jpg}}

\begin{enumerate}
\def\labelenumi{\alph{enumi})}
\setcounter{enumi}{1}
\tightlist
\item
  不使用工具进行思考
\end{enumerate}

图 7 \textbar{} DeepSeek-V4 系列的思考管理。

快速指令。在聊天机器人场景中，一系列辅助任务（例如判断是否要触发网页搜索、意图识别等）必须在生成响应之前执行。传统上，这些任务由一个单独的小模型处理，由于它无法复用已有的 KV cache，因此会带来冗余的预填充。为了解决这一限制，我们引入了 Quick Instruction。我们将一组专用特殊 token 直接附加到输入序列中，其中每个 token 对应一个特定的辅助任务。通过直接复用已计算好的 KV cache，这一机制完全避免了冗余预填充，并允许某些任务（如生成搜索查询以及判断权威性和领域）并行执行。因此，这种方法显著降低了用户感知到的首 token 时间（TTFT），并消除了维护和迭代额外小模型带来的工程开销。支持的 Quick Instruction token 总结见表 5。

\subsubsection{在策略蒸馏}\label{on-policy-distillation}

在通过专门微调和强化学习训练出多个领域特定专家之后，我们采用多教师在策略蒸馏（OPD）作为将专家能力合并进最终模型的主要技术。OPD 已成为一种有效的后训练范式，可高效地将领域专家的知识与能力迁移到单一统一模型中。这一过程通过让学生模型在其自身生成的轨迹上学习教师模型的输出分布来实现。形式化地，给定一组 \(N\) 个专家模型

表 5 \textbar{} 用于辅助任务的 Quick Instruction 特殊 token。

{\def\LTcaptype{none} % do not increment counter
\begin{longtable}[]{@{}|l|l|l|@{}}
\toprule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
\hline
特殊 Token & 描述 & 格式 \\
\hline
\textless\textbar action\textbar\textgreater{} & 判断用户提示是否需要网页搜索，或者是否可以直接回答。 &
...\textless\textbar User\textbar\textgreater\{prompt\}\textless\textbar Assistant\textbar\textgreater\textless think\textgreater\textless\textbar action\textbar\textgreater{} \\
\hline
\textless\textbar title\textbar\textgreater{} & 在首次 assistant 响应后生成简洁的对话标题。 &
...\textless\textbar Assistant\textbar\textgreater\{response\}\textless\textbar end\_of\_sentence\textbar\textgreater\textless\textbar title\textbar\textgreater{} \\
\hline
\textless\textbar query\textbar\textgreater{} & 为用户提示生成搜索查询。 &
...\textless\textbar User\textbar\textgreater\{prompt\}\textless\textbar query\textbar\textgreater{} \\
\hline
\textless\textbar authority\textbar\textgreater{} & 对用户提示中对信息源权威性的需求进行分类。 &
...\textless\textbar User\textbar\textgreater\{prompt\}\textless\textbar authority\textbar\textgreater{} \\
\hline
\textless\textbar domain\textbar\textgreater{} & 识别用户提示所属的领域。 &
...\textless\textbar User\textbar\textgreater\{prompt\}\textless\textbar domain\textbar\textgreater{} \\
\hline
\textless\textbar extracted\_url\textbar\textgreater{} & 判断用户提示中的每个 URL 是否应被抓取并读取。 &
...\textless\textbar User\textbar\textgreater\{prompt\}\textless\textbar extracted\_url\textbar\textgreater\{url\}\textless\textbar read\_url\textbar\textgreater{} \\
\hline
\end{longtable}
}

\(\{ \pi _ { E _ { 1 } } , \pi _ { E _ { 2 } } , \ldots , \pi _ { E _ { N } } \} ,\)
，OPD 目标函数定义为：

\[
\mathcal {L} _ {\mathrm {O P D}} (\theta) = \sum_ {i = 1} ^ {N} w _ {i} \cdot \mathrm {D} _ {\mathrm {K L}} \left(\pi_ {\theta} \| \pi_ {E _ {i}}\right). \tag {29}
\]

在这一表述中，\(w _ { i }\) 表示分配给每个专家的权重，通常由该专家的相对重要性决定。计算反向 KL 损失
\(\operatorname { D } _ { \mathrm { K L } } \left( \pi _ { \theta } \parallel \pi _ { E _ { i } } \right)\)
需要从学生模型 \(\pi _ { \theta }\) 中采样训练轨迹，以保持在策略学习。其底层逻辑是，统一策略 \(\pi _ { \theta }\) 会有选择地从与当前任务上下文相关的专门专家中学习（例如，在数学推理任务上对齐数学专家，在编程任务上对齐代码专家）。借助这一机制，物理上彼此独立的专家权重所蕴含的知识通过 logits 级对齐被整合进统一的参数空间，从而在实践中避免了传统权重合并或混合 RL 技术中经常出现的性能退化。在这一阶段，我们使用了十多个覆盖不同领域的教师模型来蒸馏一个单一学生模型。

在处理上述 OPD 目标时，以往工作通常会将全词表 KL 损失简化为每个 token 位置上的 token 级 KL 估计，并通过将 \(\operatorname {sg} \bigl [ \log \frac { \pi _ { E _ { i } } ( y _ { t } | x , y _ { < t } ) } { \pi _ { \theta } ( y _ { t } | x , y _ { < t } ) } \bigr ]\)（其中 \(\operatorname {sg}\) 表示 stop gradient 操作）作为策略损失计算中的逐 token advantage estimate，来复用 RL 框架。尽管这种方法资源效率较高，但会导致梯度估计方差很大，并常常引发训练不稳定。因此，我们在 OPD 中采用全词表 logit 蒸馏。在计算反向 KL 损失时保留完整的 logit 分布，可以带来更稳定的梯度估计，并确保对教师知识的忠实蒸馏。在下一小节中，我们将介绍使全词表 OPD 能够大规模可行的工程工作。

\subsection{RL 与 OPD 基础设施}\label{rl-and-opd-infrastructures}

我们的后训练基础设施建立在为 DeepSeek-V3.2 开发的可扩展框架之上。具体来说，我们集成了第 3.5 节所描述的同一分布式训练栈，以及前文引入的用于高效自回归采样的 rollout 引擎。在此基础上，我们在本工作中引入了以下几项关键增强。这些设计使得涉及十多个不同教师模型的超长上下文 RL 与 OPD 合并任务可以高效执行，从而显著加快模型发布的迭代周期。

\subsubsection{FP4 量化集成}\label{fp4-quantization-integration}

我们应用 FP4（MXFP4）量化来加速 rollouts 以及所有仅推理的前向过程，包括教师模型和参考模型的前向过程，从而降低内存流量和采样延迟。如第 3.4 节所述，在 rollout 和推理阶段我们直接使用原生 FP4 权重。对于训练步骤，则通过无损的 FP4-to-FP8 反量化步骤来模拟 FP4 量化，从而无缝复用现有的 FP8 混合精度框架及其 FP32 主权重，而无需修改反向传播流水线。

\subsubsection{面向全词表 OPD 的高效教师调度}\label{efficient-teacher-scheduling-for-full-vocabulary-opd}

我们的框架支持全词表在策略蒸馏（OPD），可容纳实际上无上限数量的教师模型，而每个教师模型都可能拥有万亿级参数。为实现这一点，所有教师权重都会被卸载到集中式分布式存储中，并在教师前向过程中按需加载，同时采用类似 ZeRO 的参数分片，以缓解 I/O 与 DRAM 压力。此外，对于词表大小为 \(\vert V \vert > 1 0 0 \mathrm { k }\) 的情形，如果为所有教师模型直接物化 logits，即使写入磁盘也是不可承受的。为此，我们在前向过程中只将教师模型最后一层的隐藏状态缓存到集中式缓冲区中。在训练时，再取回这些缓存状态，并通过相应的 prediction head 模块在线重建完整 logits。该设计带来的重计算开销可以忽略不计，同时彻底规避了显式 logits 物化带来的内存负担。为了缓解教师 prediction head 的 GPU 内存占用，我们在数据分发时按教师索引对训练样本排序。这种安排确保每个不同的教师 head 在每个 mini-batch 中只需加载一次，并且任意时刻设备内存中至多驻留一个教师 head。所有参数和隐藏状态的加载/卸载操作都在后台异步进行，不会阻塞关键路径上的计算。最后，教师与学生 logits 之间的精确 KL 散度由专门的 TileLang kernel 计算，从而加速计算并抑制动态内存分配。

\subsubsection{可抢占且容错的 Rollout 服务}\label{preemptible-and-fault-tolerant-rollout-service}

为了最大化 GPU 资源利用率，同时支持为高优先级任务快速调配硬件资源，我们的 GPU 集群采用了集群级可抢占任务调度器，任何运行中的任务都可能在任意时刻被抢占。此外，在大规模 GPU 集群中，硬件故障也十分常见。为此，我们实现了一个面向 RL/OPD rollout 的可抢占且容错的大语言模型生成服务。

具体而言，我们为每个生成请求实现了一个按 token 粒度记录的预写日志（WAL）。每当某个请求生成出一个新 token，我们就会立即将其追加到该请求的 WAL 中。在发生抢占时，我们暂停推理引擎，并保存未完成请求的 KV cache。

对于尚未完成的请求，在恢复时我们利用持久化保存的 WAL 和保存下来的 KV cache 继续解码。即使发生致命硬件错误，我们也可以利用 WAL 中持久化的 token 重新运行 prefill 阶段，以重建 KV cache。

需要强调的是，从头重新生成未完成请求在数学上是不正确的，因为这会引入长度偏差。由于较短的响应更有可能在中断中幸存，从头重新生成会使模型在发生中断时更倾向于产生更短的序列。如果推理栈在 batch 维度上不变且具有确定性，那么这一正确性问题也可以通过使用与采样器中伪随机数生成器一致的种子进行重新生成来解决。然而，这种方法仍然需要额外重新运行解码阶段，因此其效率远低于我们按 token 粒度的 WAL 方法。

\subsubsection{面向百万 Token 上下文的 RL 框架扩展}\label{scaling-rl-framework-for-million-token-context}

我们针对百万 token 序列上的高效 RL 与 OPD 引入了定向优化。在 rollout 阶段，我们采用了第 5.2.3 节中详细介绍的可抢占且容错的 rollout 服务。对于推理和训练阶段，我们将 rollout 数据格式拆分为轻量级元数据和重量级逐 token 字段。在数据分发过程中，可以先加载整个 rollout 数据的元数据，以执行全局打乱和 packing 布局计算。重量级逐 token 字段则通过共享内存数据加载器加载，以消除节点内数据冗余，并在按 mini-batch 粒度消费后立即释放，从而显著降低 CPU 和 GPU 内存压力。设备端 mini-batch 的数量会根据工作负载动态确定，以在计算吞吐和 I/O 重叠之间实现高效权衡。

\subsubsection{面向智能体 AI 的沙箱基础设施}\label{sandbox-infrastructure-for-agentic-ai}

为了满足后训练与评估期间智能体 AI 的多样化执行需求，我们构建了一个生产级沙箱平台 DeepSeek Elastic Compute（DSec）。DSec 由三个 Rust 组件构成——API 网关（Apiserver）、每主机代理（Edge）以及集群监控器（Watcher）——它们通过自定义 RPC 协议互联，并在 3FS 分布式文件系统之上水平扩展（DeepSeek-AI, 2025）。在生产环境中，单个 DSec 集群可管理数十万个并发沙箱实例。

DSec 的设计源于四点观察：（1）智能体工作负载高度异构，既包括轻量级函数调用，也包括完整的软件工程流水线，而且它们对操作系统和安全性的要求各不相同；（2）环境镜像数量众多且体积庞大，但又必须能够快速加载并支持迭代定制；（3）高密度部署要求高效利用 CPU 与内存；（4）沙箱生命周期必须与 GPU 训练调度协同，包括抢占以及基于检查点的恢复。基于这些观察，我们在下文分别阐述 DSec 的四项核心设计。

统一接口背后的四种执行底座。DSec 提供单一的 Python SDK（libdsec），用于抽象四种执行底座。Function Call 会将无状态调用分发到预热好的容器池中，从而消除冷启动开销。Container 完全兼容 Docker，并利用 EROFS（Gao et al., 2019）的按需加载能力高效组装镜像。microVM 基于 Firecracker（Agache et al., 2020）构建，为对安全敏感且高密度的部署增加了虚拟机级隔离。fullVM 基于 QEMU（Bellard, 2005）构建，支持任意客户机操作系统。这四种执行底座共享统一的 API 接口——命令执行、文件传输和 TTY 访问——在它们之间切换只需修改一个参数。

通过分层存储实现快速镜像加载。DSec 通过分层按需加载机制，在快速启动与不断增长的大规模环境镜像库之间取得平衡。对于容器，基础镜像和文件系统提交会作为由 3FS 支撑的只读 EROFS 层存储，并直接挂载到 overlay lowerdirs 中。我们在挂载时使文件元数据可以直接从本地磁盘获取；与此同时，数据块则按需从 3FS 拉取。对于 microVM，DSec 使用 overlaybd（Li et al., 2020）磁盘格式：只读基础层位于 3FS 上以供跨实例共享，而写入则进入本地 copy-on-write 层。此类快照可形成链式结构，从而支持高效版本管理和毫秒级恢复。

海量并发下的密度优化。为了让每个集群容纳数十万个沙箱，DSec 重点解决了两个资源瓶颈。首先，它缓解了虚拟化环境中的重复 page-cache 占用，并通过内存回收来支持安全的超额分配。其次，它减轻了容器运行时中的 spinlock 争用，从而降低单沙箱的 CPU 开销，并显著提升单主机装箱密度。

轨迹日志与安全抢占恢复。DSec 为每个沙箱维护全局有序的轨迹日志，持久化记录每一次命令调用及其结果。该轨迹有三个用途：（1）客户端快进——当训练任务被抢占时，沙箱资源仍然保留；恢复后，DSec 会重放此前已完成命令的缓存结果，从而加速任务恢复，并防止重新执行非幂等操作带来的错误；（2）细粒度溯源——每次状态变化的来源及其对应结果都可追踪；（3）确定性回放——任何历史会话都可以基于其轨迹被忠实复现。

\subsection{标准基准评估}\label{standard-benchmark-evaluation}

\subsubsection{评估设置}\label{evaluation-setup}

知识与推理。知识与推理数据集包括 MMLU-Pro（Wanget al., 2024b）、GPQA（Rein et al., 2023）、Human Last Exam（Phan et al., 2025）、Simple-QA Verified（Haas et al., 2025）、Chinese-SimpleQA（He et al., 2024）、LiveCodeBench-v6（Jain et al., 2024）、CodeForces（内部基准）、HMMT 2026 Feb、Apex（Balunovi´c et al., 2025）、Apex Short-list（Balunovi´c et al., 2025）、IMOAnswerBench（Luong et al., 2025）以及 PutnamBench（Tsoukalaset al., 2024）。

对于代码任务，我们在 LiveCodeBench-v6 和一个内部 Codeforces 基准上评估 DeepSeek-V4 系列。对于 Codeforces，我们收集了 14 场 Codeforces Division 1 比赛，共包含 114 道题目（2025 年 5 月至 2025 年 11 月）。Elo 评分的计算方式如下。对每场比赛，我们为每道题生成 32 个候选解。对每道题独立地，我们从这些解中无放回地抽样 10 个，并按随机顺序排列，形成提交序列。每次提交都由领域专家构建的测试集进行评判。对于成功解出的题目，其得分遵循 OpenAI（2025）的惩罚规则：模型获得的是在人类参赛者中，解决同一题目且具有相同先前失败次数者所得分数的中位数。由此可得到每条采样提交序列的总比赛得分，再将其转换为比赛名次，并进一步依据标准 Codeforces 评级系统换算为估计 rating。比赛级期望 rating 定义为：对每题那 10 次提交的所有可能随机选择与排序下估计 rating 的期望。模型的总体 rating 则是这 14 场比赛中各比赛级期望 rating 的平均值。

对于推理与知识任务，我们分别将 Non-think、High 和 Max 模式的 temperature 设为 1.0，并将上下文窗口设为 8K、128K 和 384K tokens。对于数学任务（如 HMMT、IMOAnswerBench、Apex 和 HLE），我们使用如下模板进行评估：``\{question\}\texttt{\textbackslash n}请逐步推理，并将你的最终答案放在 \texttt{\textbackslash boxed\{\}} 中。'' 对于数学任务上的 DeepSeek-V4-Pro-Max，我们使用如下模板来诱导更深层的推理：``请解决下面的问题。该问题可能要求你证明一个命题，也可能要求你给出一个答案。如果需要求出答案，你应当先得到该答案，并且你的最终解答还应当是对该答案有效性的严格证明。\texttt{\textbackslash n\textbackslash n}\{question\}''。

对于形式化数学任务，我们在 Lean v4.28.0-rc1（Moura andUllrich, 2021）的智能体设置中进行评估，允许访问 Lean 编译器与语义 tactic 搜索引擎，并在最大推理强度下最多运行 500 次工具调用。此外，我们还评估了一条计算开销更大的流程：先生成候选自然语言解答，并通过自验证（Shao et al., 2025）进行筛选，然后将保留下来的解答作为指导提供给形式化智能体，用于证明对应的 Lean 陈述。这一设计利用非形式化推理提升探索能力，同时通过形式化验证保持严格正确性。只有当严格验证器 Comparator 在两种设置下都接受某个提交时，我们才将其记为正确。

对于 K2.6 和 GLM-5.1，我们留空了部分条目，因为它们的 API 过于繁忙，无法对我们的查询返回响应。

1M-Token 上下文。由于 DeepSeek-V4 系列支持 1M-token 上下文，我们选取 OpenAI MRCR（OpenAI, 2024b）和 CorpusQA（Lu et al., 2026）作为基准，在长上下文场景下评估模型性能。为了统一所有模型的配置，我们重新评估了 Claude Opus 4.6 和 Gemini 3.1Pro 在这些任务上的表现。我们没有评估 GPT-5.4，因为它的 API 对我们相当一部分查询都没有响应。

智能体。智能体数据集包括 Terminal Bench 2.0（Merrill et al., 2026）、SWE-Verified（OpenAI,2024e）、SWE Multilingual（Yang et al., 2025）、SWE-Pro（Deng et al., 2025）、BrowseComp（Weiet al., 2025）、MCPAtlas（Bandi et al., 2026）的公开评测集、GDPval-AA（AA, 2025;Patwardhan et al., 2025）以及 Tool-Decathlon（Li et al., 2025）。

对于代码智能体任务（SWE-Verified、Terminal-Bench、SWE-Pro、SWE Multilingual），我们使用内部开发的评估框架来评估 DeepSeek-V4 系列。该框架提供一组最小工具——bash 工具和文件编辑工具。最大交互步数设为 500，最大上下文长度设为 512K tokens。对于 Terminal-Bench 2.0，我们注意到 GLM-5.1 所指出的环境相关问题。尽管如此，为保持一致性，我们仍报告在原始 Terminal-Bench 2.0 数据集上的性能。在 Terminal-Bench 2.0 Verified 子集上，DeepSeek-V4-Pro 取得了约 72.0 的得分。

对于搜索智能体任务（BrowseComp、HLE w/ tool），我们同样使用内部 harness，并提供 websearch 和 Python 工具，同时将最大交互步数设为 500，最大上下文长度设为 512K tokens。对于 BrowseComp，我们采用与 DeepSeek-V3.2（DeepSeek-AI, 2025）相同的 discard-all 上下文管理策略。

\subsubsection{评估结果}\label{evaluation-results-1}

表 6 \textbar{} DeepSeek-V4-Pro-Max 与闭源/开源模型的比较。``Max''、``xHigh'' 和 ``High'' 表示推理强度。最佳结果以粗体标出，次优结果以下划线标出。

{\def\LTcaptype{none} % do not increment counter
\begin{longtable}[]{@{}llllllll@{}}
\toprule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
\multicolumn{2}{@{}l}{%
基准（指标）} & Opus-4.6 Max & GPT-5.4 xHigh & Gemini-3.1-Pro High
& K2.6 Thinking & GLM-5.1 Thinking & DS-V4-Pro Max \\
\multirow{11}{*}{知识 \& 推理} & MMLU-Pro (EM) & 89.1 & 87.5 &
91.0 & 87.1 & 86.0 & 87.5 \\
& SimpleQA-Verified (Pass@1) & 46.2 & 45.3 & 75.6 & 36.9 & 38.1 &
57.9 \\
& Chinese-SimpleQA (Pass@1) & 76.4 & 76.8 & 85.9 & 75.9 & 75.0 & 84.4 \\
& GPQA Diamond (Pass@1) & 91.3 & 93.0 & 94.3 & 90.5 & 86.2 & 90.1 \\
& HLE (Pass@1) & 40.0 & 39.8 & 44.4 & 36.4 & 34.7 & 37.7 \\
& LiveCodeBench (Pass@1) & 88.8 & - & 91.7 & 89.6 & - & 93.5 \\
& Codeforces (Rating) & - & 3168 & 3052 & - & - & 3206 \\
& HMMT 2026 Feb (Pass@1) & 96.2 & 97.7 & 94.7 & 92.7 & 89.4 & 95.2 \\
& IMOAnswerBench (Pass@1) & 75.3 & 91.4 & 81.0 & 86.0 & 83.8 & 89.8 \\
& Apex (Pass@1) & 34.5 & 54.1 & 60.9 & 24.0 & 11.5 & 38.3 \\
& Apex Shortlist (Pass@1) & 85.9 & 78.1 & 89.1 & 75.5 & 72.4 & 90.2 \\
\multirow{2}{*}{长上下文} & MRCR 1M (MMR) & 92.9 & - & 76.3 & - & - &
83.5 \\
& CorpusQA 1M (ACC) & 71.7 & - & 53.8 & - & - & 62.0 \\
\multirow{9}{*}{智能体} & Terminal Bench 2.0 (Acc) & 65.4 & 75.1 & 68.5
& 66.7 & 63.5 & 67.9 \\
& SWE Verified (Resolved) & 80.8 & - & 80.6 & 80.2 & - & 80.6 \\
& SWE Pro (Resolved) & 57.3 & 57.7 & 54.2 & 58.6 & 58.4 & 55.4 \\
& SWE Multilingual (Resolved) & 77.5 & - & - & 76.7 & 73.3 & 76.2 \\
& BrowseComp (Pass@1) & 83.7 & 82.7 & 85.9 & 83.2 & 79.3 & 83.4 \\
& HLE w/ tools (Pass@1) & 53.1 & 52.0 & 51.6 & 54.0 & 50.4 & 48.2 \\
& GDPval-AA (Elo) & 1619 & 1674 & 1314 & 1482 & 1535 & 1554 \\
& MCPAtlas Public(Pass@1) & 73.8 & 67.2 & 69.2 & 66.6 & 71.8 & 73.6 \\
& Toolathlon (Pass@1) & 47.2 & 54.6 & 48.8 & 50.0 & 40.7 & 51.8 \\
\end{longtable}
}

DeepSeek-V4-Pro-Max 与其他闭源/开源模型的比较见表 6。此外，我们还评估了 DeepSeek-V4-Flash 和 DeepSeek-V4-Pro 的不同模式，结果见表 7。

知识。在通用世界知识评估中，DeepSeek-V4-Pro-Max 作为 DeepSeek-V4-Pro 的最高推理强度模式，在开源大语言模型中创下了新的最先进水平。正如 SimpleQA-Verified 所展示的那样，DeepSeek-V4-Pro-Max 以 20 个绝对百分点的优势显著超过了现有所有开源基线。尽管取得了这些进展，它目前仍落后于领先的专有模型 Gemini-3.1-Pro。在教育知识与推理领域，DeepSeek-V4-Pro-Max 在 MMLU-Pro、GPQA 和 HLE 基准上略微优于 Kimi 和 GLM，但仍落后于领先的专有模型。总体而言，DeepSeek-V4-Pro-Max 在提升开源模型世界知识能力方面标志着一个重要里程碑。

此外，DeepSeek-V4-Flash 与 DeepSeek-V4-Pro 在知识类任务上存在显著性能差距；这是可以预期的，因为更大的参数规模有助于在预训练期间保留更多知识。值得注意的是，这两个模型在获得更高推理强度时，都在知识基准上呈现出更好的结果。

表 7 \textbar{} DeepSeek-V4 系列不同规模与模式的比较。``Non-Think''、``High'' 和 ``Max'' 表示推理强度。

{\def\LTcaptype{none} % do not increment counter
\begin{longtable}[]{@{}llllllll@{}}
\toprule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
\multirow{2}{*}{} & \multirow{2}{*}{基准（指标）} &
\multicolumn{3}{l}{%
DeepSeek-V4-Flash} & \multicolumn{3}{l@{}}{%
DeepSeek-V4-Pro} \\
& & Non-Think & High & Max & Non-Think & High & Max \\
\multirow{11}{*}{知识 \& 推理} & MMLU-Pro (EM) & 83.0 & 86.4 &
86.2 & 82.9 & 87.1 & 87.5 \\
& SimpleQA-Verified (Pass@1) & 23.1 & 28.9 & 34.1 & 45.0 & 46.2 &
57.9 \\
& Chinese-SimpleQA (Pass@1) & 71.5 & 73.2 & 78.9 & 75.8 & 77.7 & 84.4 \\
& GPQA Diamond (Pass@1) & 71.2 & 87.4 & 88.1 & 72.9 & 89.1 & 90.1 \\
& HLE (Pass@1) & 8.1 & 29.4 & 34.8 & 7.7 & 34.5 & 37.7 \\
& LiveCodeBench (Pass@1-COT) & 55.2 & 88.4 & 91.6 & 56.8 & 89.8 &
93.5 \\
& Codeforces (Rating) & - & 2816 & 3052 & - & 2919 & 3206 \\
& HMMT 2026 Feb (Pass@1) & 40.8 & 91.9 & 94.8 & 31.7 & 94.0 & 95.2 \\
& IMOAnswerBench (Pass@1) & 41.9 & 85.1 & 88.4 & 35.3 & 88.0 & 89.8 \\
& Apex (Pass@1) & 1.0 & 19.1 & 33.0 & 0.4 & 27.4 & 38.3 \\
& Apex Shortlist (Pass@1) & 9.3 & 72.1 & 85.7 & 9.2 & 85.5 & 90.2 \\
\multirow{2}{*}{长上下文} & MRCR 1M(MMR) & 37.5 & 76.9 & 78.7 & 44.7 & 83.3
& 83.5 \\
& CorpusQA 1M(ACC) & 15.5 & 59.3 & 60.5 & 35.6 & 56.5 & 62.0 \\
\multirow{9}{*}{智能体} & Terminal Bench 2.0 (Acc) & 49.1 & 56.6 & 56.9
& 59.1 & 63.3 & 67.9 \\
& SWE Verified (Resolved) & 73.7 & 78.6 & 79.0 & 73.6 & 79.4 & 80.6 \\
& SWE Pro (Resolved) & 49.1 & 52.3 & 52.6 & 52.1 & 54.4 & 55.4 \\
& SWE Multilingual (Resolved) & 69.7 & 70.2 & 73.3 & 69.8 & 74.1 &
76.2 \\
& BrowseComp (Pass@1) & - & 53.5 & 73.2 & - & 80.4 & 83.4 \\
& HLE w/ tools (Pass@1) & - & 40.3 & 45.1 & - & 44.7 & 48.2 \\
& MCPAtlas Public (Pass@1) & 64.0 & 67.4 & 69.0 & 69.4 & 74.2 & 73.6 \\
& GDPval-AA (Elo) & - & - & 1395 & - & - & 1554 \\
& Toolathlon (Pass@1) & 40.7 & 43.5 & 47.8 & 46.3 & 49.0 & 51.8 \\
\end{longtable}
}

推理。DeepSeek-V4-Pro-Max 在各项推理基准上都优于以往所有开源模型，并在许多指标上追平了最先进的闭源模型；与此同时，规模更小的 DeepSeek-V4-Flash-Max 也在代码和数学推理任务上超过了此前最佳开源模型 K2.6-Thinking。同时，DeepSeek-V4-Pro 和 DeepSeek-V4-Flash 在编程竞赛中表现出色。根据我们的评估，它们的表现可与 GPT-5.4 相比肩，这是开源模型首次在该任务上追平闭源模型。在 Codeforces 排行榜上，DeepSeek-V4-Pro-Max 目前在人类参赛者中排名第 23。DeepSeek-V4 在形式化数学任务上也在智能体设置和高算力设置下表现强劲。在智能体设置下，它取得了最先进结果，如图 8 所示，超过了 Seed Prover（Chen et al., 2025）等先前模型。在计算开销更大的流程下，其性能进一步提升，超过了 Aristotle(Achim et al., 2025) 等系统，并追平了这一设置下已知的最佳结果。

智能体。DeepSeek-V4 系列在评估中展现出强劲的智能体能力。对于代码智能体任务，DeepSeek-V4-Pro 取得了与 K2.6 和 GLM-5.1 可比的结果，尽管这些开源模型整体上仍落后于对应的闭源模型。DeepSeek-V4-Flash 在编码任务上的表现逊于 DeepSeek-V4-Pro，尤其是在 Terminal Bench 2.0 上。类似趋势也出现在其他智能体评估中。值得注意的是，DeepSeek-V4-Pro 在 MCPAtlas 和 Toolathlon 上表现良好——这两个评测集包含了广泛的工具和 MCP 服务——这表明我们的模型具有出色的泛化能力，而不仅仅是在内部框架上表现良好。

实用范式 Putnam-200 Pass@8，仅使用最少工具且采样受限。

\pandocbounded{\includegraphics[keepaspectratio,alt={image}]{images/033e143b8217ed1d5ac9c328c9993ffd61514d8e04df84d9320917cc51238dfa.jpg}}

前沿范式 Putnam-2025，采用形式化-非形式化混合推理并进行大规模算力扩展。

\pandocbounded{\includegraphics[keepaspectratio,alt={image}]{images/01305727e84924cb89df98d0699b8d023302eadc02fe675342c2cfd1cee0f6b5.jpg}}

图 8 \textbar{} 实用范式与前沿范式下的形式化推理。左图：Putnam-200 Pass@8 按照 Seed-Prover 提出的设置，从 PutnamBench（Tsoukalas et al., 2024）中选取一个固定的随机子集进行评估；所有模型都在同一题目集上测试。我们遵循 Seed-Prover 协议，但将专有搜索工具替换为开源 LeanExplore（Asher,2025），从而得到一个仅使用最少智能体工具且采样受限的轻量级设置。右图：Putnam-2025 探索了放大后的形式化-非形式化混合范式下数学推理的前沿，在该范式中，非形式化推理与形式化验证相结合，以暴露缺口并提升严谨性；DeepSeek-V4 达到了完美证明的 120/120。

\pandocbounded{\includegraphics[keepaspectratio,alt={image}]{images/a7065923549538da2b7d0ead2a01c83fbbad9968a5da8a07efdb572247e4f193.jpg}}

图 9 \textbar{} DeepSeek-V4 系列在 MRCR 任务上的表现。

1M-Token 上下文。DeepSeek-V4-Pro 在衡量上下文内检索能力的 MRCR 任务上优于 Gemini-3.1-Pro，但仍落后于 Claude Opus 4.6。如图 9 所示，在 128K 上下文窗口内，检索性能保持高度稳定。尽管在超过 128K 之后性能下降开始变得可见，但与闭源和开源对手相比，该模型在 1M tokens 下的检索能力依然非常强劲。与 MRCR 不同，CorpusQA 更接近真实场景。评估结果也表明，DeepSeek-V4-Pro 优于 Gemini-3.1-Pro。

推理强度。如表 7 所示，Max 模式使用更长的上下文，并在 \({ \mathrm { R L } } ,\) 中采用更小的长度惩罚，因此在最具挑战性的任务上优于 High 模式。图 10 展示了 DeepSeek-V4-Pro、DeepSeek-V4-Flash 和 DeepSeek-V3.2 在代表性推理与智能体任务上的性能和成本对比。通过扩大测试时计算量，DeepSeek-V4 系列相较前代取得了显著提升。此外，在 HLE 这类推理任务上，DeepSeek-V4-Pro 表现出比

\pandocbounded{\includegraphics[keepaspectratio,alt={image}]{images/253b09ee67a4e46163ee468aa73d814efa6f7583bcfb245ba2971937515544b3.jpg}}

\pandocbounded{\includegraphics[keepaspectratio,alt={image}]{images/610e79b834f385384649cf97fe6162ed2c0e51a46557b9913a0d08cd823db490.jpg}}

图 10 \textbar{} 不同推理强度下 HLE 和 Terminal Bench 2.0 的表现。``None'' 表示 Non-think 模式，``Speciale'' 表示 DeepSeek-V3.2-Speciale 模型。

DeepSeek-V3.2 更高的 token 效率。

\subsection{真实世界任务上的表现}\label{performance-on-real-world-tasks}

标准化基准往往难以捕捉多样化真实世界任务的复杂性，从而在测试结果与实际用户体验之间形成落差。为了弥合这一差距，我们开发了专有的内部指标体系，相比传统基准更加优先关注真实使用模式。这种方法确保我们的优化能够转化为切实可感的收益。我们的评估框架专门针对 DeepSeek API 和 Chatbot 的主要使用场景，使模型性能与实际需求保持一致。

\subsubsection{中文写作}\label{chinese-writing}

中文写作是 DeepSeek 的主要使用场景之一。我们对功能性写作和创意写作进行了严格评估。表 12 展示了 DeepSeek-V4-Pro 与 Gemini-3.1-Pro 在功能性写作任务上的两两比较。这些任务由常见的日常写作请求构成，提示通常简洁直接。之所以选择 Gemini-3.1-Pro 作为基线，是因为它在我们的评估中是中文写作方面表现最好的外部模型。结果表明，DeepSeek-V4-Pro 以总体胜率 \(6 2 . 7 \%\) 对 \(3 4 . 1 \%\) 超过该基线；这主要是因为在中文写作场景中，Gemini 有时会让其固有的风格偏好压过用户的明确要求。

表 13 展示了创意写作对比，其评估沿两个维度展开：指令遵循和写作质量。与 Gemini-3.1-Pro 相比，DeepSeek-V4-Pro 在指令遵循上的胜率为 \(6 0 . 0 \%\)，在写作质量上的胜率为 \(7 7 . 5 \%\)，表明它在指令遵循上有小幅提升，而在写作质量上则有显著增益。尽管 DeepSeek-V4-Pro 在整体用户案例分析中表现更优，但若将评估限制在最具挑战性的提示上——尤其是涉及高复杂度约束或多轮场景的提示——则 Claude Opus 4.5 仍然保持着相对于 DeepSeek-V4-Pro 的性能优势。如表 14 所示，Claude Opus 4.5 的胜率为 \(5 2 . 0 \%\)，而 DeepSeek-V4-Pro 为 \(4 5 . 9 \%\)。

\subsubsection{搜索}\label{search}

搜索增强问答是 DeepSeek 聊天机器人的核心能力。在 DeepSeek web 与 app 中，``non-think'' 模式采用 Retrieval-Augmented Search（RAG），而 ``thinking'' 模式则使用智能体式搜索。

检索增强搜索。我们在客观和主观两类 Q\&A 任务上，对 DeepSeek-V4-Pro 与 DeepSeek-V3.2 进行了成对评估。如表 11 所示，DeepSeek-V4-Pro 以显著优势超过了 DeepSeek-V3.2，并在两类任务上都体现出一致领先。最显著的提升出现在单值搜索以及 planning \& strategy 任务上，这表明 DeepSeek-V4-Pro 擅长从检索到的上下文中定位精确事实答案，并综合形成结构化方案。然而，DeepSeek-V3.2 在对比与推荐任务上仍然相对具有竞争力，这说明在需要基于搜索结果进行平衡、多视角推理的场景中，DeepSeek-V4-Pro 仍有改进空间。

智能体式搜索。与标准 RAG 不同，智能体式搜索使模型能够针对每个查询迭代调用搜索与抓取工具，从而显著提升整体搜索性能。对于 DeepSeek-Chat 中的 thinking 模式，我们优化了智能体式搜索功能，以在预定义的 ``thinking budget'' 内最大化响应准确性。如表 9 所示，智能体式搜索始终优于 RAG，尤其是在复杂任务上。此外，它的成本依然非常高效，智能体式搜索仅比标准 RAG 略贵一些（见表 10）。

\subsubsection{白领任务}\label{white-collar-task}

为了严格评估模型在复杂企业生产力场景中的实用性，我们构建了一套包含 30 个高级中文专业任务的综合评测集。这些工作流有意覆盖高层次认知需求，包括深入的信息分析、完整的文档生成和细致入微的文档编辑，并横跨 13 个关键行业（如金融、教育、法律和科技）。评估是在一个配备了基础工具（包括 Bash 和 web search）的内部智能体 harness 中完成的。

鉴于这些任务具有开放性，自动化指标通常难以捕捉高质量响应中的细微差别。因此，我们进行了人工评估，以比较 DeepSeek-V4-Pro-Max 与 Opus-4.6-Max 的表现。标注者在盲评条件下从四个维度对模型输出进行评估：

• 任务完成度：核心问题是否得到成功解决。

• 指令遵循：是否遵守特定约束与指令。

• 内容质量：事实准确性、逻辑连贯性与专业语气。

• 格式美观度：版式可读性和视觉呈现。

如图 11 所示，DeepSeek-V4-Pro-Max 在多样化的中文白领任务上优于 Opus-4.6-Max，取得了令人印象深刻的不败率 \(6 3 \%\)，并在分析、生成和编辑任务上都展现出稳定优势。图 12 所示的详细维度得分凸显了该模型在任务完成度和

内容质量方面的主要优势。具体来说，DeepSeek-V4-Pro-Max 会主动预判用户的隐含意图，经常提供补充洞见和自我验证步骤。它在长篇生成方面也表现突出，能够产出深入、连贯的叙述，而不是像 Opus-4.6-Max 那样经常依赖过于简单的项目符号列表。此外，该模型严格遵循正式的专业规范，例如标准化的中文层级编号。然而，在指令遵循方面，它偶尔会忽视特定格式约束，略微落后于 Opus。进一步地，该模型在将大量文本输入压缩为简洁摘要方面还不够擅长。最后，其格式美观度在演示文稿整体视觉设计方面仍有相当大的提升空间。图 13、14 和 15 展示了一些测试案例；由于某些输出过长，这里仅展示部分页面。

\pandocbounded{\includegraphics[keepaspectratio,alt={image}]{images_hi/p43-000.jpg}}

图 11 \textbar{} 分析、生成、编辑任务及整体表现上的胜率比较。

\pandocbounded{\includegraphics[keepaspectratio,alt={image}]{images/1e3ce11719ce0f4f4fff751f62a32e1bc409b360e1a143e0205e6cb2a80dc98d.jpg}}

图 12 \textbar{} 详细维度得分，包括任务完成度、内容质量、格式美观度和指令遵循。

\pandocbounded{\includegraphics[keepaspectratio,alt={image}]{images/9e26dfa1a5b969aa0ad1e3954a0003685e7a8e4257e5c4850e66ac3db8bd65e7.jpg}}

\pandocbounded{\includegraphics[keepaspectratio,alt={image}]{images/9d70ed5a9b53ac2dbfb1c011b88257ce21004760efc9459ae1df5ed29b9b69a9.jpg}}

图 13 \textbar{} 某项任务的示例输出：该任务要求为一个热门奶茶品牌与北京地铁撰写联合营销方案。

\subsubsection{代码智能体}\label{code-agent}

为了对我们的代码智能体能力进行基准评测，我们从真实的内部研发工作负载中整理任务。我们从 \(5 0 +\) 名内部工程师那里收集了 \({ \sim } 2 0 0\) 个具有挑战性的任务，覆盖功能开发、缺陷修复、重构和诊断，并横跨包括 PyTorch、CUDA、Rust 和 \({ { C + + } }\) 在内的多种技术栈。每个任务都附带其原始代码仓库、对应的执行环境以及人工标注的评分准则；经过严格的质量筛选后，最终保留 30 个任务作为评测集。如表 8 所示，DeepSeek-V4-Pro 显著优于 Claude Sonnet 4.5，并接近 Claude Opus 4.5 的水平。

表 8 \textbar{} 研发代码基准对比（外部模型仅为评估目的纳入）。

{\def\LTcaptype{none} % do not increment counter
\begin{longtable}[]{@{}|l|l|l|l|l|l|l|@{}}
\toprule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
\hline
模型 & Haiku 4.5 & Sonnet 4.5 & DeepSeek-V4-Pro-Max & Opus 4.5 & Opus
4.5 Thinking & Opus 4.6 Thinking \\
\hline
通过率 (\%) & 13 & 47 & 67 & 70 & 73 & 80 \\
\hline
\end{longtable}
}

在一项针对 DeepSeek 开发者和研究员 \(( N = 8 5 )\) 的调查中——这些受访者都在日常工作中使用过 DeepSeek-V4-Pro 进行智能体式编程——我们询问他们：与其他前沿模型相比，DeepSeek-V4-Pro 是否已准备好成为其默认且主要的代码模型。结果显示，\(5 2 \%\) 的受访者回答“是”，\(3 9 \%\) 倾向于“是”，而回答“否”的不足 \(9 \%\)。受访者认为 DeepSeek-V4-Pro 在大多数任务上都能给出令人满意的结果，但也指出它会出现琐碎错误、误解模糊提示，以及偶尔过度思考。
