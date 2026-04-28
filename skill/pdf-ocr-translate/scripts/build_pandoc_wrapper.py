#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


TEMPLATE = """---
header-includes:
  - \\usepackage{{pdfpages}}
geometry: margin=0cm
---

```{{=latex}}
\\includepdf[pages=-]{{{pdf_name}}}
```
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a minimal pandoc wrapper that inlines a compiled PDF.")
    parser.add_argument("--pdf", required=True, help="Compiled native PDF path to include")
    parser.add_argument("--output", required=True, help="Wrapper markdown path to write")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    out_path = Path(args.output)
    out_path.write_text(TEMPLATE.format(pdf_name=pdf_path.name))
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
