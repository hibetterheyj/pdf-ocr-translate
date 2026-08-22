#!/usr/bin/env python3
"""Merge translated parts into main_cn.tex.

- chunk_00: preamble + title block + authors
- chunk_01..: body in order, skipping chunk_02 (hand-built Contents)
- Insert \tableofcontents with Chinese name after the title/authors
- Fix reported leftovers: Table 2 header pandoc escapes, $50M, section-I dup
"""
from pathlib import Path
import re

WS = Path('archive/MAI-Thinking-1_translate')
PARTS = WS / 'parts'

ORDER = [
    'chunk_00_preamble.tex',
    'chunk_01_frontmatter.tex',
    # chunk_02_contents dropped -> replaced by \tableofcontents
    'chunk_03_s2a_arch.tex',
    'chunk_04_s2b_eval_data.tex',
    'chunk_05_s2c_mixture.tex',
    'chunk_06_s2d_recipe_yolo.tex',
    'chunk_07_s3_rl_recipe.tex',
    'chunk_08_s3_2_stem.tex',
    'chunk_09_s3_3_agentic.tex',
    'chunk_10_s3_4_help_safety.tex',
    'chunk_11_s3_5_6_cons_infra.tex',
    'chunk_12_s4_evals.tex',
    'chunk_13_s5_redteam.tex',
    'chunk_14_s6_7_cluster_conc.tex',
    'chunk_15_refs_a.tex',
    'chunk_16_refs_b.tex',
    'chunk_17_refs_c.tex',
    'chunk_18_app_a_b.tex',
    'chunk_19_app_c.tex',
    'chunk_20_app_d1_stem_cot.tex',
    'chunk_21_app_d2_agent_cot.tex',
    'chunk_22_app_e_f.tex',
    'chunk_23_app_g.tex',
    'chunk_24_app_h.tex',
    'chunk_25_app_i_j.tex',
    'chunk_26_app_k.tex',
    'chunk_27_app_l.tex',
]

parts_text = {}
for f in ORDER:
    parts_text[f] = (PARTS / f).read_text(encoding='utf-8')

# ---- fix 1: Table 2 header pandoc escapes -> proper math subscripts ----
t = parts_text['chunk_03_s2a_arch.tex']
old_header = (
    '& \\textbackslash mathtt \\{ E G \\} \\_ \\{ \\textbackslash mathtt \\{ F L O P\n'
    's \\} \\} & \\textbackslash mathbf \\{ E G \\} \\_ \\{ \\textbackslash mathrm \\{\n'
    'T i m e \\} \\} & \\textbackslash tt E G \\_ \\{ \\textbackslash tt F L O P s\n'
    '\\} & \\textbackslash mathbf \\{ E G \\} \\_ \\{ \\textbackslash mathrm \\{ T i\n'
    'm e \\} \\} \\\\'
)
new_header = (
    '& $\\mathtt{EG}_{\\mathtt{FLOPs}}$ & $\\mathbf{EG}_{\\mathrm{Time}}$ '
    '& $\\mathtt{EG}_{\\mathtt{FLOPs}}$ & $\\mathbf{EG}_{\\mathrm{Time}}$ \\\\'
)
assert old_header in t, 'Table 2 header pattern not found'
t = t.replace(old_header, new_header, 1)
# EG = ~1.3 line: \textasciitilde -> \sim
t = t.replace('$\\mathrm { E G } \\textasciitilde{} = \\textasciitilde{} 1 . 3 $',
              '$\\mathrm{EG} \\sim = \\sim 1.3$')
parts_text['chunk_03_s2a_arch.tex'] = t

# ---- fix 2: drop duplicated section-I tail from chunk_24 (kept in chunk_25) ----
t24 = parts_text['chunk_24_app_h.tex']
marker = '\\subsection{I 智能体编码评测}'
idx = t24.find(marker)
assert idx > 0, 'section I not found in chunk_24'
t24 = t24[:idx].rstrip() + '\n'
parts_text['chunk_24_app_h.tex'] = t24

# ---- fix 3: escaped dollar in chunk_14 ($50M) ----
t14 = parts_text['chunk_14_s6_7_cluster_conc.tex']
t14 = t14.replace('\\$50M', '$50M') if '\\$50M' in t14 else t14
parts_text['chunk_14_s6_7_cluster_conc.tex'] = t14

# ---- assemble ----
body_blocks = []
for f in ORDER[1:]:
    body_blocks.append(parts_text[f].rstrip())

body = '\n\n'.join(body_blocks)

# ---- TOC: insert right after authors line (inside chunk_01, before Abstract) ----
chunk01 = body_blocks[0]  # first body block is chunk_01_frontmatter
abstract_marker = '\\subsection{摘要}\\label{abstract}'
assert abstract_marker in chunk01, 'abstract marker missing'
toc_block = (
    '\\renewcommand{\\contentsname}{目录}\n'
    '\\tableofcontents\n'
)
chunk01 = chunk01.replace(abstract_marker, toc_block + '\n' + abstract_marker, 1)
body_blocks[0] = chunk01
body = '\n\n'.join(body_blocks)

main_cn = parts_text[ORDER[0]].rstrip() + '\n\n' + body + '\n\n\\end{document}\n'
out = WS / 'main_cn.tex'
out.write_text(main_cn, encoding='utf-8')
print(f'merged -> {out} ({len(main_cn.splitlines())} lines)')

# sanity checks
checks = [
    ('\\begin{document}', 1),
    ('\\end{document}', 1),
    ('\\tableofcontents', 1),
    ('\\subsection{参考文献}\\label{references}', 1),
    ('\\subsection{I 智能体编码评测}', 1),
    ('\\textbackslash', 0),
    ('\\$', 0),
]
text = main_cn
for pat, want in checks:
    got = text.count(pat)
    print(f"  {pat!r}: {got} (want {want}) {'OK' if got == want else '<<< CHECK'}")
