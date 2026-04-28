\section{2.3.1. 压缩稀疏注意力}\label{compressed-sparse-attention}

CSA 的核心架构如图 3 所示。它首先将每 \(m\) 个词元的 KV 缓存压缩为一个条目，然后应用 DeepSeek 稀疏注意力以进一步加速。

压缩的 Key-Value 条目。设
\(H \in \mathbb { R } ^ { n \times d }\) 为输入隐藏状态序列，其中
\(n\) 是序列长度，\(d\) 是隐藏维度。CSA 首先计算两组 KV
条目
\(C ^ { a } , C ^ { b } \in \mathbb { R } ^ { n \times c }\)
及其对应的压缩权重
\(Z ^ { a } , Z ^ { b } \in \mathbb { R } ^ { n \times c }\)
，其中 \(c\) 是头维度：

\[
C ^ {a} = H \cdot W ^ {a K V}, \quad C ^ {b} = H \cdot W ^ {b K V}, \tag {9}
\]

\[
Z ^ {a} = H \cdot W ^ {a Z}, \quad Z ^ {b} = H \cdot W ^ {b Z}, \tag {10}
\]

其中
\(W ^ { a K V } , W ^ { b K V } , W ^ { a Z } , W ^ { b Z } \in \mathbb { R } ^ { d \times c }\)
是可训练参数。接下来，\(C ^ { a }\)
和 \(C ^ { b }\) 中每 \(m\) 个 KV 条目会根据其压缩权重以及可学习的位置偏置
\(B ^ { a } , B ^ { b } \in \mathbb { R } ^ { m \times c }\)
被压缩为一个条目，生成
\(C ^ { \mathsf { C o m p } } \in \mathbb { R } ^ { \frac { n } { m } \times c }\)
。每个压缩条目
\(C _ { i } ^ { \mathrm { C o m p } } \in \mathbb { R } ^ { c }\)
按如下方式计算：

\[
\left[ S _ {m i: m (i + 1) - 1} ^ {a}; S _ {m (i - 1): m i - 1} ^ {b} \right] = \operatorname {S o f t m a x} _ {\text {r o w}} \left(\left[ Z _ {m i: m (i + 1) - 1} ^ {a} + B ^ {a}; Z _ {m (i - 1): m i - 1} ^ {b} + B ^ {b} \right]\right), \tag {11}
\]

\[
C _ {i} ^ {\text {C o m p}} = \sum_ {j = m i} ^ {m (i + 1) - 1} S _ {j} ^ {a} \odot C _ {j} ^ {a} + \sum_ {j = m (i - 1)} ^ {m i - 1} S _ {j} ^ {b} \odot C _ {j} ^ {b}, \tag {12}
\]

其中 \(\odot\) 表示 Hadamard 积；Softmaxrow(·) 表示沿行维度执行的 softmax 操作，它会对来自
\(Z ^ { a }\) 和 \(Z ^ { b }\) 的总计 \(2 m\) 个元素进行归一化。当 \(i = 0\) 时，
\(Z _ { m ( i - 1 ) : m i - 1 } ^ { b }\) 会用负无穷填充，而 \(C _ { m ( i - 1 ) : m i - 1 } ^ { b }\) 会用零填充。注意，每个 \(C _ { i } ^ { \mathrm { C o m p } }\) 是由 \(2m\) 个 KV 条目导出的，但用于
\(C _ { i } ^ { \mathrm { C o m p } }\) 的 \(C ^ { b }\) 的索引与用于
\(C _ { i - 1 } ^ { \mathsf { C o m p } }\) 的 \(C ^ { a }\) 的索引存在重叠。因此，CSA 实际上将序列长度压缩为 \(\frac { 1 } { m }\) 倍。

用于稀疏选择的 Lightning 索引器。在得到压缩后的
KV 条目 \(C ^ { \mathrm { C o m p } }\) 之后，CSA 应用 DSA 策略，为核心注意力选择 top-k 个压缩 KV 条目。首先，CSA 对
\(C ^ { \mathrm { C o m p } }\) 使用相同的压缩操作，得到压缩后的索引器键
\(K ^ { \mathrm { I C o m p } } \in \mathbb { R } ^ { \frac { n } { m } \times c ^ { I } } .\)
，其中 \(c ^ { I }\) 是索引器头维度。随后，对于查询词元 \(t ,\) 我们以低秩方式生成索引器查询
\(\{ \mathbf { q } _ { t , 1 } ^ { I } ; \mathbf { q } _ { t , 2 } ^ { I } ; . . . ; \mathbf { q } _ { t , n _ { h } ^ { I } } ^ { I } \}\)：

\[
\mathbf {c} _ {t} ^ {Q} = \mathbf {h} _ {t} \cdot W ^ {D Q}, \tag {13}
\]

\[
[ \mathbf {q} _ {t, 1} ^ {I}; \mathbf {q} _ {t, 2} ^ {I}; \dots ; \mathbf {q} _ {t, n _ {h} ^ {I}} ^ {I} ] = \mathbf {q} _ {t} ^ {I} = \mathbf {c} _ {t} ^ {Q} \cdot W ^ {I U Q}, \tag {14}
\]

其中 \(\mathbf { h } _ { t } \in \mathbb { R } ^ { d }\) 是查询词元 \(t\) 的输入隐藏状态；
\(\mathbf { c } _ { t } ^ { Q } \in \mathbb { R } ^ { d _ { c } }\) 是查询的压缩潜向量；\(d _ { c }\) 表示查询压缩维度；\(n _ { h } ^ { I }\) 表示 indexer 查询头的数量；
\(W ^ { D Q } \in \mathbb { R } ^ { d \times d _ { c } }\) 和
\(W ^ { I U Q } \in \mathbb { R } ^ { d _ { c } \times c ^ { I } n _ { h } ^ { I } }\)
分别是索引器查询的下投影矩阵和上投影矩阵。接下来，查询词元 \(t\) 与先前某个压缩块 \(s\)
\(\textstyle { \bigl ( } s < \operatorname { F l o o r } ( { \frac { t } { m } } ) { \bigr ) }\)
之间的索引分数 \(I _ { t , s } \in \mathbb { R }\) 计算如下：

\[
\left[ w _ {t, 1} ^ {I}; w _ {t, 2} ^ {I}; \dots ; w _ {t, n _ {h} ^ {I}} ^ {I} \right] = \mathbf {w} _ {t} ^ {I} = \mathbf {h} _ {t} \cdot W ^ {w}, \tag {15}
\]

\[
I _ {t, s} = \sum_ {h = 1} ^ {n _ {h} ^ {I}} w _ {t, h} ^ {I} \cdot \operatorname {R e L U} \left(\mathbf {q} _ {t, h} ^ {I} \cdot K _ {s} ^ {\text {I C o m p}}\right), \tag {16}
\]

其中 \(W ^ { w } \in \mathbb { R } ^ { d \times n _ { h } ^ { I } }\)
是可学习矩阵；
\(\boldsymbol { w _ { t , h } ^ { I } } \in \mathbb { R }\) 是第 \(h\) 个索引器头的权重。对于查询词元 \(t ,\) 给定其索引分数 \(I _ { t , : }\)，我们使用一个 top-\(k\) 选择器来有选择地保留一部分压缩 KV 条目
\(C _ { t } ^ { \mathsf { S p r s C o m p } }\)，供后续核心注意力使用：

\[
C _ {t} ^ {\text {S p r s C o m p}} = \left\{C _ {s} ^ {\text {C o m p}} \mid I _ {t, s} \in \operatorname {T o p - k} \left(I _ {t,:}\right) \right\}. \tag {17}
\]

\pandocbounded{\includegraphics[keepaspectratio,alt={image}]{images/3be80607df218b3fca89c7c8159b93be4102ea887a2d41db75764756d19c0dc0.jpg}}

图 4 \textbar{} HCA 的核心架构。它执行更重度的压缩，其中
\(m ^ { \prime } \left( \gg m \right)\) 个词元的 KV 条目会被合并为一个。此外，我们还额外引入了一小组滑动窗口 KV 条目，以增强局部的细粒度依赖关系。

共享 Key-Value MQA。在选出稀疏 KV 条目之后，CSA 以 Multi-Query Attention (MQA) (Shazeer, 2019) 的方式执行核心注意力，其中
\(C _ { t } ^ { \mathsf { S p r s C o m p } }\) 中的每个压缩 KV 条目同时作为注意力的键和值。具体来说，对于查询词元 \(t ,\) 我们首先由压缩潜向量 \(\mathbf { c } _ { t } ^ { Q }\) 生成注意力查询
\(\{ \mathbf { q } _ { t , 1 } ; \mathbf { q } _ { t , 2 } ; . . . ; \mathbf { q } _ { t , n _ { h } } \}\)：

\[
\left[ \mathbf {q} _ {t, 1}; \mathbf {q} _ {t, 2}; \dots ; \mathbf {q} _ {t, n _ {h}} \right] = \mathbf {q} _ {t} = \mathbf {c} _ {t} ^ {Q} \cdot W ^ {U Q}, \tag {18}
\]

其中 \(n _ { h }\) 表示查询头的数量；
\(W ^ { U Q } \in \mathbb { R } ^ { d _ { c } \times c n _ { h } }\) 是查询的上投影矩阵。注意，潜在查询向量
\(\mathbf { c } _ { t } ^ { Q }\) 与索引器查询所使用的潜向量是共享的。接下来，我们在
\(\{ \mathbf { q } _ { t , i } \}\) 和 \(C _ { t } ^ { \mathsf { S p r s C o m p } }\)
上执行 MQA：

\[
\mathbf {o} _ {t, i} = \text {C o r e A t t n} \left(\text {q u e r y} = \mathbf {q} _ {t, i}, \text {k e y} = C _ {t} ^ {\text {S p r s C o m p}}, \text {v a l u e} = C _ {t} ^ {\text {S p r s C o m p}}\right), \tag {19}
\]

其中 \(\mathbf { o } _ { t , i } \in \mathbb { R } ^ { c }\) 是第 \(i\) 个头在第 \(t\) 个词元处的核心注意力输出；CoreAttn(·) 表示核心注意力操作。

分组输出投影。在 DeepSeek-V4 的配置中，
\(c n _ { h }\) 相当大。因此，若直接将核心注意力操作的输出
\(\left[ \mathbf { o } _ { t , 1 } ; \mathbf { o } _ { t , 2 } ; . . . ; \mathbf { o } _ { t , n _ { h } } \right] = \mathbf { o } _ { t } \in \mathbb { R } ^ { c n _ { h } }\)
投影到一个 \(d\) 维隐藏状态上，会带来相当大的计算负担。为缓解这一成本，我们设计了分组输出投影策略。具体而言，我们首先将 \(n _ { h }\) 个输出拆分为 \(g\) 组，然后对于每组输出
\({ \mathbf o } _ { t , i } ^ { G } \in \mathbb { R } ^ { c \frac { n _ { h } } { g } }\)
，将其投影到一个 \(d _ { g }\) 维的中间输出
\({ \mathbf o } _ { t , i } ^ { G ^ { \prime } } \in \mathbb { R } ^ { d _ { g } }\)
，其中 \(d _ { g } \ < \ c \frac { n _ { h } } { g }\) 。最后，我们将中间输出
\([ \mathbf { o } _ { t , 1 } ^ { G ^ { \prime } } ; \mathbf { o } _ { t , 2 } ^ { G ^ { \prime } } ; . . . ; \mathbf { o } _ { t , g } ^ { G ^ { \prime } } ] \in \mathbb { R } ^ { d _ { g } g }\)
投影为最终的注意力输出
\(\hat { \mathbf { o } } _ { t } \in \mathbb { R } ^ { d }\) 。

\section{2.3.2. 重度压缩注意力}\label{heavily-compressed-attention}

HCA 的核心架构如图 4 所示。它以更重的方式压缩 KV 缓存，但不使用稀疏注意力。

压缩的 Key-Value 条目。总体而言，HCA 的压缩策略与 CSA 类似，但采用更大的压缩率
\(m ^ { \prime }\) \(( \gg m )\) ，并且不执行重叠压缩。设 \(H \in \mathbb { R } ^ { n \times d }\) 为输入隐藏状态序列，HCA 首先计算原始 KV 条目
\(C \in \mathbb { R } ^ { n \times c }\) 及其对应的压缩权重 \(Z \in \mathbb { R } ^ { n \times c }\)：

\[
C = H \cdot W ^ {K V}, \tag {20}
\]

\[
Z = H \cdot W ^ {Z}, \tag {21}
\]

其中 \(W ^ { K V }\) 、\(W ^ { Z } \in \mathbb { R } ^ { d \times c }\)
是可训练参数。接下来，\(C\) 中每 \(m ^ { \prime }\) 个 KV 条目会根据压缩权重和可学习的位置偏置
\(B \in \mathbb { R } ^ { m ^ { \prime } \times c }\)
被压缩为一个条目，生成
\(C ^ { \mathsf { C o m p } } \in \mathbb { R } ^ { \frac { n } { m ^ { \prime } } \times c }\)
。每个压缩条目
\(C _ { i } ^ { \mathrm { C o m p } } \in \mathbb { R } ^ { c }\) 的计算如下：

\[
S _ {m ^ {\prime} i: m ^ {\prime} (i + 1) - 1} = \operatorname {S o f t m a x} _ {\text {r o w}} \left(Z _ {m ^ {\prime} i: m ^ {\prime} (i + 1) - 1} + B\right), \tag {22}
\]

\[
C _ {i} ^ {\text {C o m p}} = \sum_ {j = m ^ {\prime} i} ^ {m ^ {\prime} (i + 1) - 1} S _ {j} \odot C _ {j}. \tag {23}
\]

通过这一压缩操作，HCA 将序列长度压缩为 \(\scriptstyle { \frac { 1 } { m ^ { \prime } } }\) 倍。

共享 Key-Value MQA 与分组输出投影。HCA 也与 CSA 一样采用共享 KV MQA 和分组输出投影策略。在 KV 压缩之后，对于查询词元 \(t ,\) HCA 首先以低秩方式生成注意力查询
\(\{ \mathbf { q } _ { t , 1 } ; \mathbf { q } _ { t , 2 } ; . . . ; \mathbf { q } _ { t , n _ { h } } \}\)：

\[
\mathbf {c} _ {t} ^ {Q} = \mathbf {h} _ {t} \cdot W ^ {D Q}, \tag {24}
\]

\[
[ \mathbf {q} _ {t, 1}; \mathbf {q} _ {t, 2}; \dots ; \mathbf {q} _ {t, n _ {h}} ] = \mathbf {q} _ {t} = \mathbf {c} _ {t} ^ {Q} \cdot W ^ {U Q}, \tag {25}
\]

其中 \(\mathbf h _ { t } \in \mathbb R ^ { d }\) 是查询词元 \(t\) 的输入隐藏状态；\(n _ { h }\) 表示查询头的数量；\(W ^ { D Q } \in \mathbb { R } ^ { d \times d _ { c } }\)
和 \(W ^ { U Q } \in \mathbb { R } ^ { d _ { c } \times c n _ { h } }\)
分别是查询的下投影矩阵和上投影矩阵。接下来，我们在
\(\{ \mathbf { q } _ { t , i } \}\) 和 \(C ^ { \mathrm { C o m p } }\)
上执行 MQA：

\[
\mathbf {o} _ {t, i} = \text {C o r e A t t n} \left(\text {q u e r y} = \mathbf {q} _ {t, i}, \text {k e y} = C ^ {\text {C o m p}}, \text {v a l u e} = C ^ {\text {C o m p}}\right), \tag {26}
\]

其中 \(\mathbf { o } _ { t , i } \in \mathbb { R } ^ { c }\) 是第 \(i\) 个头在第 \(t\) 个词元处的核心注意力输出。接下来，如同 CSA 一样，HCA 将 \(n _ { h }\) 个输出拆分为 \(g\) 组，并且对于每组输出
\({ \mathbf o } _ { t , i } ^ { G } \in \mathbb { R } ^ { c \frac { n _ { h } } { g } }\)
，HCA 会将其投影到一个 \(d _ { g }\) 维的中间输出
\({ \mathbf o } _ { t , i } ^ { G ^ { \prime } } \in \mathbb { R } ^ { d _ { g } }\)
，其中 \(d _ { g } < c \frac { n _ { h } } { g }\) 。最后，HCA 将中间输出
\([ \mathbf { o } _ { t , 1 } ^ { G ^ { \prime } } ; \mathbf { o } _ { t , 2 } ^ { G ^ { \prime } } ; . . . ; \mathbf { o } _ { t , g } ^ { G ^ { \prime } } ] \in \mathbb { R } ^ { d _ { g } g }\)
投影为最终的注意力输出 \(\hat { \mathbf { o } } _ { t } \in \mathbb { R } ^ { d }\) 。

\section{2.3.3. 其他细节}\label{other-details}

除了上文介绍的 CSA 和 HCA 核心架构之外，我们的混合注意力还融合了若干其他技术。为了行文清晰，我们在上述介绍中省略了这些附加技术，并将在本小节中对其进行简要说明。另外，本小节只关注这些技术的核心思想，为简洁起见可能会省略一些细微细节。我们鼓励读者参考我们的开源实现，以获取明确无歧义的细节。

查询与 Key-Value 条目归一化。对于 CSA 和 HCA，我们都会在核心注意力操作之前，对查询的每个头以及压缩 KV 条目的唯一一个头额外执行一次 RMSNorm 操作。该归一化能够避免注意力 logits 爆炸，并可能提升训练稳定性。

部分 Rotary Positional Embedding。对于 CSA 和 HCA，我们在注意力查询、KV 条目和核心注意力输出上部分使用 Rotary Positional Embedding (RoPE) (Su et al., 2024)。具体来说，对于 CSA 和 HCA 中使用的每个查询向量和 KV 条目向量，我们会在其最后 64 个维度上应用 RoPE。由于 KV 条目同时充当 attention keys 和 values，朴素的核心注意力输出
\(\left\{ \mathbf { o } _ { t , i } \right\}\)
会携带绝对位置嵌入，这来自对 KV 条目的加权求和。作为对策，我们还会在每个 \(\mathbf { o } _ { t , i }\) 的最后 64 个维度上应用位置为 \(- i\) 的 RoPE。这样一来，核心注意力的输出也会携带相对位置嵌入，即每个 KV 条目对核心注意力输出的贡献也会与查询和该 KV 条目之间的距离相关。

滑动窗口注意力的额外分支。为了在 CSA 和 HCA 中严格保持因果性，每个查询只关注先前的压缩 KV 块。因此，一个查询无法获取其自身压缩块内其他词元的信息。与此同时，在语言建模中，最近的词元通常与查询词元具有更强的相关性。基于这些原因，我们以滑动窗口的方式为 CSA 和 HCA 都引入了一个补充性的注意力分支，以更好地建模局部依赖。具体来说，对于每个查询词元，我们会额外生成
\(n _ { \mathrm { w i n } }\) 个未压缩的 KV 条目，它们对应最近的
\(n _ { \mathrm { w i n } }\) 个词元。在 CSA 和 HCA 的核心注意力中，这些滑动窗口中的 KV 条目会与压缩 KV 条目一同使用。

Attention Sink。在 CSA 和 HCA 的核心注意力中，我们采用 attention sink 技巧 (OpenAI, 2025; Xiao et al., 2024)。具体来说，我们设置一组可学习的 sink logits
\(\{ z _ { 1 } ^ { \prime } , z _ { 2 } ^ { \prime } , . . . , z _ { n _ { h } } ^ { \prime } \}\)
。对于第 \(h\) 个注意力头，
\(\operatorname {E x p} ( z _ { h } ^ { \prime } )\) 会被加入到注意力分数的分母中：

\[
s _ {h, i, j} = \frac {\operatorname {E x p} \left(z _ {h , i , j}\right)}{\sum_ {k} \operatorname {E x p} \left(z _ {h , i , k}\right) + \operatorname {E x p} \left(z _ {h} ^ {\prime}\right)}, \tag {27}
\]

其中 \(s _ { h , i , j } , z _ { h , i , j } \in \mathbb { R }\) 分别表示第 \(h\) 个注意力头在第 \(i\) 个查询词元与第 \(j\) 个先前词元或压缩块之间的注意力分数和注意力 logit。该技术允许每个查询头将其总注意力分数调整为不等于 1，甚至接近 0。

\section{2.3.4. 效率讨论}\label{efficiency-discussion}

由于采用了混合的 CSA 与 HCA，并结合低精度计算和存储，DeepSeek-V4 系列的注意力模块在注意力 FLOPs 和 KV 缓存大小两方面都实现了显著效率提升，尤其是在长上下文场景中。首先，我们为 KV 条目采用混合存储格式：Rotary Positional Embedding (RoPE) 维度使用 BF16 精度，而其余维度使用 FP8 精度。与纯 BF16 存储相比，这种混合表示几乎将 KV 缓存大小减半。其次，lightning 索引器内部的注意力计算采用 FP4 精度，从而在超长上下文下加速注意力操作。第三，相较于 DeepSeek-V3.2，DeepSeek-V4 系列采用了更小的 attention top-k，从而提升了模型在短文本和中等长度文本上的效率。最后，也是最重要的一点，压缩注意力和混合注意力技术大幅降低了 KV 缓存大小和计算 FLOPs。

以头维度为 128 的 BF16 GQA8 (Ainslie et al., 2023) 作为基线，这也是 LLM 注意力的一种常见配置；在 1M 上下文设置下，DeepSeek-V4 系列的 KV 缓存大小可以大幅降低到约为该基线的 \(2 \%\)。

算法 1 DeepSeek-V4 的 Muon 优化器

输入: 学习率 \(\eta\) ，动量 \(\mu\) ，权重衰减
\(\lambda\) ，更新重缩放因子 \(\gamma\)\\
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

此外，即使与 DeepSeek-V3.2 (DeepSeek-AI, 2025) 这一已经相当高效的基线相比，DeepSeek-V4 系列在效率上仍然表现出显著优势。它们在推理 FLOPs 和 KV 缓存大小上的对比见图 1 右侧部分。

\section{2.4. Muon 优化器}\label{muon-optimizer}

由于收敛更快且训练稳定性更好，我们在 DeepSeek-V4 系列中的大多数模块上采用 Muon (Jordan et al., 2024; Liu et al., 2025) 优化器。我们的 Muon 优化完整算法总结于算法 1。

基础配置。我们仍然对嵌入模块、预测头模块、mHC 模块的静态偏置和门控因子，以及所有 RMSNorm 模块的权重使用 AdamW (Loshchilov and Hutter, 2017) 优化器。其余所有模块均使用 Muon 更新。遵循 Liu et al.~(2025)，我们也对 Muon 参数施加权重衰减，使用 Nesterov (Jordan et al., 2024; Nesterov, 1983) 技巧，并对更新矩阵的 Root Mean Square (RMS) 进行重缩放，以复用我们的 AdamW 超参数。与他们不同的是，我们使用混合 Newton-Schulz 迭代来完成正交化。

混合 Newton-Schulz 迭代。对于给定矩阵 \(M\) ，设其 Singular Value Decomposition (SVD) 为 \(M = U \Sigma V ^ { T }\) 。Newton-Schulz 迭代的目标是将 \(M\) 近似正交化为
\(U V ^ { T }\) 。通常，\(M\) 会先被归一化为
\(M _ { 0 } = M / | | \boldsymbol { M } | | _ { F }\)，以确保其最大奇异值不超过 1。然后，每次 Newton-Schulz 迭代执行如下操作：

\[
M _ {k} = a M _ {k - 1} + b \left(M _ {k - 1} M _ {k - 1} ^ {T}\right) M _ {k - 1} + c \left(M _ {k - 1} M _ {k - 1} ^ {T}\right) ^ {2} M _ {k - 1}. \tag {28}
\]

我们的混合 Newton-Schulz 由两个不同阶段的 10 次迭代组成。在前 8 步中，我们使用系数
\(( a , b , c ) = ( 3 . 4 4 4 5 , - 4 . 7 7 5 0 , 2 . 0 3 1 5 )\)
以推动快速收敛，使奇异值接近 1。在最后 2 步中，我们切换为系数
\(( a , b , c ) = ( 2 , - 1 . 5 , 0 . 5 )\) ，从而将奇异值稳定地精确保持在 1。

避免注意力 Logits 爆炸。DeepSeek-V4 系列的注意力架构允许我们直接在注意力查询和 KV 条目上应用 RMSNorm，这能够有效防止注意力 logits 爆炸。因此，我们在 Muon 优化器中不使用 QK-Clip 技术 (Liu et al., 2025)。
