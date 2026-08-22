# pdf-ocr-translate

一个面向论文与技术文档场景的 OCR LaTeX 翻译示例目录，核心目标是把来自 MinerU 或其他 OCR大模型等软件应用生成的 OCR LaTeX 工程，结合原始 PDF 做交叉校验、高清图片替换、标题层级正规化与多段并行翻译，最终整理为高质量中文 PDF。

## 目录结构

```text
pdf-ocr-translate/
├── skill/
│   └── pdf-ocr-translate/
├── example/
│   ├── kimi_k3_report/
│   ├── deepseek_v4_report/
│   ├── spatiotemporal_composability_report/
│   ├── mai_thinking_1_report/
│   │   ├── MAI-Thinking-1.pdf
│   │   ├── MAI-Thinking-1_CN.pdf
│   │   ├── ocr_latex/
│   │   ├── pdf_pages/
│   │   └── translate_latex/
│   ├── DeepSeek_V4.pdf
│   └── DeepSeek_V4_CN.pdf
├── README.md
└── .gitignore
```

## 内容说明

- `skill/pdf-ocr-translate/`
  放置完整的 `pdf-ocr-translate` skill 源码，包括：

  - OCR LaTeX 翻译工作流说明
  - OCR 分块 / 合并脚本（页码残行剔除、TOC 注入、共享标题去重）
  - 标题层级正规化脚本（A-Z 附录与 letter.N 子标题）
  - 高清图片抽取脚本
  - 一致性检查脚本
  - XeLaTeX / pandoc 包装编译脚本
  - MinerU 失败模式目录（`references/ocr-failure-patterns.md`）
  - DeepSeek_V4 风格模块化 starter template
- `example/<报告名>/ocr_latex/`
  放置 OCR 原始 LaTeX 工程示例，保留 OCR 输出状态，便于观察原始噪声、图片切分和符号问题。
- `example/<报告名>/translate_latex/`
  放置基于 OCR 工程和原始 PDF 交叉校验后整理出来的中文翻译 LaTeX 工程示例，包含：

  - 分块翻译后的 `parts/`
  - 标题层级正规化后的主 TeX
  - 切分 / 合并脚本与共享翻译策略
  - 升级后的 `images_hi/`（部分示例）
  - native XeLaTeX 输出与 pandoc 包装输出（部分示例）
- `example/<报告名>/<原名>_CN.pdf`
  示例中文翻译 PDF（各示例目录顶层）。
- 每个示例目录自带 README，记录该案例的翻译统计与经验教训（Kimi K3、DeepSeek V4、Spatiotemporal Composability、MAI-Thinking-1 四个示例）。

## 适用场景

这个 skill 适合处理以下任务：

- OCR 识别后的论文 LaTeX/Markdown 存在大量脏数据
- 需要保留公式、表格与整体 LaTeX 可编译性
- 需要使用多个 subagent 并行翻译长文档
- 需要结合原始 PDF 校验 OCR 文本和章节结构
- 需要从原始 PDF 提取更清晰的截图或图表
- 需要最终输出高质量中文 PDF

## 示例来源与致谢

本目录中的示例基于公开论文与技术报告整理：

- DeepSeek_V4：感谢 DeepSeek-AI，论文来源：
  `https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/blob/main/DeepSeek_V4.pdf`
- MAI-Thinking-1：微软 AI 团队技术报告（本仓 `archive/` 内原始副本）

各示例仅用于展示 OCR LaTeX 翻译、校验和编译工作流，不改变原论文署名与参考文献归属。
