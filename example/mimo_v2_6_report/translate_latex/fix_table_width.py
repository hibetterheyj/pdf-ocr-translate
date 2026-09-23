#!/usr/bin/env python3
"""Size the longtables so they fit the text block.

MinerU emits every table with `l` columns, and `l` never wraps: one long
benchmark label or a row of model names runs straight off the page.  Measured
on the first compile of the MiMo-V2.6 run, one table overshot the text block by
1247pt — over twice the page width — and another by 153pt.

Per table this pass:

  * rebinds the label and model columns to a fixed-width, ragged-right `L{}`
    (or centred `C{}` for names) so their contents wrap, leaving the genuinely
    numeric columns as `l` so the digits stay aligned;
  * wraps the whole `{\\def\\LTcaptype{none} ... }` group in `{\\footnotesize
    ... }`, which shrinks every column at once;
  * halves `\\tabcolsep` for the widest tables, where the gutter alone eats
    84-108pt.

Two placement rules that produce confusing errors if you get them wrong:

  * the size command must wrap the *enclosing group*, not the alignment
    preamble — `\\footnotesize` after `\\endlastfoot` raises
    `Misplaced \\noalign`;
  * the pass has to be **idempotent**, because it typically runs both before
    splitting and again at merge time.  Locate each table's wrapper by walking
    up from its own `\\begin{{longtable}}` line, never by a global search for
    the marker text: once some tables have been rewritten to
    `{{\\footnotesize\\def\\LTcaptype{{none}}`, a global search skips past them
    and latches onto the previous un-sized table's wrapper, which silently
    duplicates the whole region between the two tables.

Choosing the widths
-------------------
This is the one part that is per-document.  Measure the *original* PDF's column
positions (pymupdf `page.get_text("dict")`, or the x of each header span) and
rescale them so the columns plus their gutter fill `\\textwidth`.  Filling it
matters: longtable centres a narrower table, so a table that is only, say, 75%
of the text width sits inset from both margins and lines up with neither its own
caption nor the body prose.  Give the script the result as JSON:

    {"1": [[0, "L{13em}"], [1, "L{22em}"]],
     "3": [[0, "L{0.26\\linewidth}"]]}

with the table's ordinal (its order in the document) as the key.  Fractions of
`\\linewidth` are more robust than `em` when the caption font differs.

Measured `\\textwidth` from the PDF page rect rather than assuming: US Letter
with 2cm margins is 498.6pt, A4 is 481.9pt, and a 17pt error is enough to make
a full-width table overflow.

Usage:  fix_table_width.py main.tex [--plan widths.json]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

MARKER = "\\def\\LTcaptype{none}"
BEGIN = re.compile(r"\\begin\{longtable\}(?:\[[^\]]*\])?\{@\{\}(.*?)@\{\}\}")
END = r"\end{longtable}"
# A column descriptor: a bare l/c/r, or a `L{...}`/`C{...}` we wrote earlier.
COLUMN_TOKEN = re.compile(r"[lcr](?!\{)|[LC]\{[^}]*\}")

# Worked example — the plan measured for the MiMo-V2.6 report, kept so the
# script runs out of the box and so the shape of a plan is visible.  Re-measure
# for your own document (see the module docstring) and pass it with --plan.
#
# Keyed by ordinal: the table's position in the document, 1-based, which matches
# the number it carries because tables appear in order.  Keying on the *caption
# text* does not work — MinerU floats one table's caption after its body, so the
# nearest preceding "Table 2 ..." is a cross-reference in the prose.
EXAMPLE_PLAN: dict[str, list[list]] = {
    # Model config.  Col 0 is a \multirow group label ("Audio Tokenizer
    # Encoder"), and \multirow does not wrap, so it needs the full width of the
    # longest label rather than a wrapping width.
    #
    # These are the *original report's* column proportions, measured off its
    # page 6 (label 126pt / config 155pt / Flash 89pt / Pro 79pt of a 449pt
    # table) and rescaled so the four columns plus their 48pt of gutter fill the
    # 498.6pt text block.
    "1": [[0, r"L{0.252\linewidth}"], [1, r"L{0.310\linewidth}"],
          [2, r"C{0.178\linewidth}"], [3, r"C{0.158\linewidth}"]],
    # Two columns of running prose.
    "2": [[0, r"L{0.26\linewidth}"], [1, r"L{0.66\linewidth}"]],
    # A label column plus six model columns.
    "3": [[0, "L{13em}"]] + [[i, "C{7em}"] for i in range(1, 7)],
    # Two SFT/RL sub-columns sit under a multicolumn, so only col 0 is sized.
    "6": [[0, "L{17em}"]],
    # Eight data columns of the form "mini-harness1".
    "7": [[0, "L{14em}"]] + [[i, "C{5em}"] for i in range(1, 9)],
}

# Tables whose column count leaves no slack for the default 6pt gutter.  At
# seven and nine columns the inter-column padding alone is 84pt and 108pt, so
# the gutter is halved.  Ordinals, same keying as the plan.
EXAMPLE_TIGHT = {3, 7}


def rewrite_spec(spec: str, columns: list[tuple[int, str]]) -> str:
    """Replace the nth column descriptor in `spec` with its new definition.

    The `|` rules and any leftover descriptors are left where they are, so this
    is safe to run again over a spec that already carries `L{}`/`C{}` columns —
    replacing a descriptor by index rather than by counting `l`/`c`/`r`
    characters, which a `L{0.26\\linewidth}` would fool (the `l` in
    `\\linewidth` is not a column).
    """
    matches = list(COLUMN_TOKEN.finditer(spec))
    out, cursor = [], 0
    for idx, new in columns:
        if idx >= len(matches):
            continue
        m = matches[idx]
        out.append(spec[cursor:m.start()])
        out.append(new)
        cursor = m.end()
    out.append(spec[cursor:])
    return "".join(out)


def load_plan(path: str | None) -> tuple[dict[int, list[tuple[int, str]]], set[int]]:
    """Return ({ordinal: [(col, spec)]}, {ordinals that get a 3pt gutter}).

    Accepts either ``{"1": [[0, "L{13em}"]]}`` or the richer
    ``{"columns": {...}, "tight": [3, 7]}``.
    """
    if not path:
        raw, tight = EXAMPLE_PLAN, EXAMPLE_TIGHT
    else:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        tight = set(raw.get("tight", ()))
        raw = raw.get("columns", raw)
    columns = {int(k): [(int(i), s) for i, s in v] for k, v in raw.items()}
    return columns, set(tight)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tex", nargs="?", default="main.tex")
    ap.add_argument("--plan", help="JSON column plan; defaults to the MiMo-V2.6 "
                                   "worked example (see the module docstring)")
    args = ap.parse_args()
    path = Path(args.tex)
    columns, tight = load_plan(args.plan)
    lines = path.read_text(encoding="utf-8").split("\n")

    done: list[str] = []
    ordinal = 0
    for i, line in enumerate(lines):
        if not BEGIN.search(line):
            continue
        ordinal += 1
        if ordinal not in columns:
            continue

        # The wrapper opener is the nearest non-blank line above; anchoring the
        # search there (rather than a global rfind on the marker text) matters
        # once *some* tables already carry `{\footnotesize\def\LTcaptype{none}`:
        # a global rfind then skips past those and latches onto the previous
        # un-sized table's wrapper, which silently duplicates the whole region.
        j = i - 1
        while j >= 0 and not lines[j].strip():
            j -= 1
        opener = lines[j] if j >= 0 else ""
        if not (opener.lstrip().startswith("{")
                and (MARKER in opener or "\\footnotesize" in opener)):
            print(f"  WARNING: no wrapper found above the table at line {i + 1}")
            continue

        close = next((k for k in range(i, len(lines)) if lines[k].strip() == END), None)
        if close is None or lines[close + 1].strip() != "}":
            print(f"  WARNING: malformed block at line {i + 1}")
            continue

        lines[i] = BEGIN.sub(
            lambda m: m.group(0).replace(
                m.group(1), rewrite_spec(m.group(1), columns[ordinal])),
            line, count=1)
        lines[j] = "{\\footnotesize" + (
            "\\setlength{\\tabcolsep}{3pt}" if ordinal in tight else "")
        done.append(str(ordinal))

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"sized tables: {', '.join(done) if done else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
