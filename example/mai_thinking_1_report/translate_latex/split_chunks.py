#!/usr/bin/env python3
"""Split MAI-Thinking-1 OCR tex into translation chunks.

Reads the cleaned working-copy tex, removes page-marker footer lines,
and writes parts/chunk_NN_*.tex plus parts/CHUNK_MAP.json (chunk -> PDF pages).
"""
import json
import re
from pathlib import Path

WS = Path('archive/MAI-Thinking-1_translate')
SRC = WS / 'MinerU_latex_MAI-Thinking-1.tex'
PARTS = WS / 'parts'

lines = SRC.read_text(encoding='utf-8').split('\n')
N = len(lines)
print(f'file lines: {N}')

HEAD = re.compile(r'\\(sub)*section\s*\{')

def heading_lines(pat=None):
    out = []
    for i, l in enumerate(lines):
        if HEAD.search(l) and (pat is None or re.search(pat, l)):
            out.append(i)
    return out

# --- 1. page markers: standalone ints flanked by blanks forming chain 1..109 ---
markers = [i for i in range(1, N - 1)
           if re.fullmatch(r'\d{1,3}', lines[i].strip())
           and lines[i-1].strip() == '' and lines[i+1].strip() == '']
chain, prev = [], 0
for i in markers:
    v = int(lines[i].strip())
    if v == prev + 1:
        chain.append(i)
        prev = v
print(f'markers: {len(markers)}, chain 1..{prev}: {len(chain)}')
assert prev == 109 and len(chain) == 109, 'page marker chain incomplete'
for i in chain:
    lines[i] = ''

# --- 2. locate boundaries by label (anchored to heading start) ---
def find(pat):
    hs = [i for i, l in enumerate(lines) if re.search(r'\\subsection\{' + pat, l)]
    assert len(hs) == 1, f'{pat}: {hs}'
    return hs[0]

b = {
    'abstract':  find(r'Abstract'),
    'contents':  find(r'Contents'),
    's2':        find(r'2 Pre'),
    's2_3':      find(r'2\.3 '),
    's2_5':      find(r'2\.5 '),
    's2_7':      find(r'2\.7 '),
    's3':        find(r'3 The Reinforcement'),
    's3_1':      find(r'3\.1 Reinforcement'),
    's3_2':      find(r'3\.2 '),
    's3_3':      find(r'3\.3 '),
    's3_4':      find(r'3\.4 '),
    's3_5':      find(r'3\.5 '),
    's3_6':      find(r'3\.6 Reinforcement'),
    's4':        find(r'4 Evaluations'),
    's5':        find(r'5 Safety'),
    's6_1':      find(r'6\.1 '),
    's7':        find(r'7 Conclusion'),
    'refs':      find(r'References'),
    'a':         find(r'A Citation'),
    'b':         find(r'B Pre'),
    'c':         find(r'C Long'),
    'd':         find(r'D Evolution'),
    'd2':        find(r'D\.2 '),
    'e':         find(r'E SWE'),
    'f':         find(r'F Constraint'),
    'g':         find(r'G Infrastructure'),
    'h':         find(r'H STEM'),
    'i':         find(r'I Agentic'),
    'j':         find(r'J Safety'),
    'k':         find(r'K General'),
    'l':         find(r'L Cluster'),
}
end = lines.index(r'\end{document}') if r'\end{document}' in lines else N
print('end doc line:', end)

chunks = [
    ('00_preamble',        0,        b['abstract']),
    ('01_frontmatter',     b['abstract'], b['contents']),
    ('02_contents',        b['contents'], b['s2']),
    ('03_s2a_arch',        b['s2'],   b['s2_3']),
    ('04_s2b_eval_data',   b['s2_3'], b['s2_5']),
    ('05_s2c_mixture',     b['s2_5'], b['s2_7']),
    ('06_s2d_recipe_yolo', b['s2_7'], b['s3']),
    ('07_s3_rl_recipe',    b['s3'],   b['s3_2']),
    ('08_s3_2_stem',       b['s3_2'], b['s3_3']),
    ('09_s3_3_agentic',    b['s3_3'], b['s3_4']),
    ('10_s3_4_help_safety', b['s3_4'], b['s3_5']),
    ('11_s3_5_6_cons_infra', b['s3_5'], b['s4']),
    ('12_s4_evals',        b['s4'],   b['s5']),
    ('13_s5_redteam',      b['s5'],   b['s6_1']),
    ('14_s6_7_cluster_conc', b['s6_1'], b['refs']),
    ('15_refs_a',          b['refs'], b['refs'] + 500),
    ('16_refs_b',          b['refs'] + 500, b['refs'] + 1000),
    ('17_refs_c',          b['refs'] + 1000, b['a']),
    ('18_app_a_b',         b['a'],    b['c']),
    ('19_app_c',           b['c'],    b['d']),
    ('20_app_d1_stem_cot', b['d'],    b['d2']),
    ('21_app_d2_agent_cot', b['d2'],  b['e']),
    ('22_app_e_f',         b['e'],    b['g']),
    ('23_app_g',           b['g'],    b['h']),
    ('24_app_h',           b['h'],    b['j']),
    ('25_app_i_j',         b['i'],    b['k']),
    ('26_app_k',           b['k'],    b['l']),
    ('27_app_l',           b['l'],    end),
]

# --- 3. page range per chunk (markers inside chunk bounds) ---
page_by_line = {}
for i, v in zip(chain, range(1, 110)):
    page_by_line[i] = v

chunk_map = []
PARTS.mkdir(exist_ok=True)
for name, s, e in chunks:
    seg = lines[s:e]
    pages = [v for v in (page_by_line.get(i) for i in range(s, e)) if v]
    body = '\n'.join(seg).strip('\n') + '\n'
    out = PARTS / f'chunk_{name}.tex'
    out.write_text(body, encoding='utf-8')
    nlines = len(seg)
    flag = 'DROP_AT_MERGE' if name == '02_contents' else ''
    pages_rng = f'{min(pages)}-{max(pages)}' if pages else '-'
    chunk_map.append({'chunk': name, 'file': out.name, 'lines': nlines,
                      'pages': pages_rng, 'note': flag})
    print(f"{name:26s} lines {nlines:5d}  pages {pages_rng:8s} {flag}")

(PARTS / 'CHUNK_MAP.json').write_text(
    json.dumps(chunk_map, indent=2, ensure_ascii=False), encoding='utf-8')
print('chunks written to', PARTS)
