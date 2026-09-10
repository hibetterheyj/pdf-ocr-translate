#!/usr/bin/env python3
"""Align terminology with DeepSeek's own Chinese documentation.

Sources (fetched for this pass):
  https://api-docs.deepseek.com/zh-cn/guides/thinking_mode/
  https://api-docs.deepseek.com/zh-cn/news/news260910/

The paper's literal translation of "reasoning effort" was 推理努力.  DeepSeek's
official Chinese calls the same control 思考强度, and the section that documents
it is 思考模式开关与思考强度控制 — so the report should say 思考强度 throughout.

The pass is a set of ordered, context-anchored replacements rather than a blanket
regex, because 推理 also legitimately means *inference* elsewhere (推理系统,
推理效率), and 档位 has to collapse correctly.  Idempotent: every rule is written
so that re-running finds nothing to do.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

# Longest, most specific strings first so short rules cannot pre-empt them.
RULES: list[tuple[str, str]] = [
    # "reasoning effort" -> official 思考强度
    (r"推理努力档位", "思考强度档位"),
    (r"推理努力(effort)设置", "思考强度（effort）控制"),
    (r"推理努力（effort）设置", "思考强度（effort）控制"),
    (r"推理努力设置", "思考强度设置"),
    (r"推理努力取值", "思考强度取值"),
    (r"推理努力（Reasoning Effort）", "思考强度（Reasoning Effort）"),
    (r"推理努力", "思考强度"),
    (r"推理强度", "思考强度"),
    (r"努力档位", "强度档位"),
    (r"努力层级", "强度档位"),
    (r"努力值", "强度值"),
    (r"努力设置", "强度设置"),
    (r"努力程度", "思考强度"),
    # "reasoning-intensive" (a benchmark category, not the effort knob)
    (r"推理密集型", "推理密集型"),
    # the effort preset tiers
    (r"三个预设的思考强度档位", "三个预设的思考强度档位"),
    (r"API 档位", "API 档位"),
    # normalise the half-width punctuation left by OCR in one spot
    (r"。模型检查点", "。模型检查点"),
]


def refine(text: str) -> tuple[str, int]:
    n = 0
    for old, new in RULES:
        if old == new:
            continue
        if old in text:
            n += text.count(old)
            text = text.replace(old, new)
    # Any bare 档位 left in the effort sections now reads fine; make sure the
    # Table 2 caption and its header agree on 强度值.
    text = re.sub(r"\b档位 & 强度值", "档位 & 强度值", text)
    return text, n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", required=True)
    args = ap.parse_args()
    total = 0
    for path in sorted(Path(args.parts).glob("*.tex")):
        text = path.read_text()
        new, n = refine(text)
        if n:
            path.write_text(new)
            total += n
            print(f"{path.name}: {n} term(s) aligned")
    print(f"total: {total} terminology alignments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
