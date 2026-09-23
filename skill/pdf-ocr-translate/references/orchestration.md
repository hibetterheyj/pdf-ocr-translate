# Orchestrating the Translation Agents

The chunking workflow is mechanical; the agent coordination is where runs
succeed or stall. These notes come from a 15-chunk, 13-agent run on a 51-page
technical report, and the pattern they converge on is simple: **checking and
translating are separate jobs, and the translator should never be the one
checking.**

## Give every agent a bounded, self-contained brief

Each agent gets exactly one chunk file. It should not need to look at the rest
of the document, and it should not be asked to decide what to do — only to do it.

A brief that works:

- the absolute path to the chunk, and the instruction to overwrite it in place
- the path to the shared policy file, with "read this once"
- **its own printed-page range** and the exact filenames to read
- the specific things to verify for this chunk (see below)
- an explicit budget: "at most ~10 tool calls", "do not open any other file"

Those last two lines do real work. Without them agents wander into unrelated
files and re-derive facts they already have.

## State the page mapping explicitly, because it is a trap

The extracted pages are `pdf_pages/page_NNN.txt`, where **printed page N is
`page_NNN.txt`** — but the PDF *file's* page N is one further along, because the
first page is usually an unnumbered title. Both facts are true at once and it is
very easy to tell an agent the wrong one.

Agents told the wrong mapping mostly still find the right text — they can read
the footer — but they spend turns discovering the discrepancy, and one wrote a
confused note back about it. Just state both facts up front.

## The failure mode: verification loops

Across the run, 5 of 13 agents stopped before writing anything. Every one of them
was doing the same thing: reading the PDF over and over to be sure. One spent 23
turns and exhausted its context without producing a single character of
translation. The chunk it was working on finished in 5 turns once re-briefed.

So:

- **Pre-verify, then hand over the results.** Do the PDF checking in its own pass
  (or a dedicated agent whose only output is a list of corrections), and give the
  translator that list with "these are settled, do not re-investigate".
- **Cap the investigation.** "Skim these pages once for obvious numeric
  discrepancies" beats "cross-check everything against the PDF", which invites an
  exhaustive audit.
- **Tell it what an acceptable answer is.** "If you find no discrepancies, say so"
  prevents an agent from manufacturing work to justify the effort it has spent.

A useful split for hard chunks: one agent finds and reports the corrections,
another applies them and translates. The second one is cheap and fast.

## When an agent does stall

An agent that returns with `total_tokens: 0` and a half-sentence ("Let me verify
how the algorithm is rendered...") produced nothing — it ran out of context
mid-thought. Check the file before believing anything: `len(re.findall(r'[一-鿿]', text))`
is a fast "did it write anything" test.

Then either resume it with the findings you already have, or start a fresh agent
with the scope narrowed. Resuming works when the agent had *established* answers
and only needed to write them down — but if it stalled twice, start fresh. A
fresh agent with a tight brief is more reliable than a resumed one carrying its
own bloat.

## Tell agents what kind of repair you do and do not want

Agents asked to translate will also fix things, and which things they fix is a
judgement call you should make explicitly:

- **Wanted**: OCR text errors — ligature loss, lost hyphens, split model names,
  corrupted table cells. These need the PDF and the translator has it open.
- **Unwanted**: rewriting the paper's structure, "improving" prose, or adding
  content. One agent deleted a heading it judged redundant — it had been
  instructed to drop a duplicate, but the deletion also removed the abstract
  heading that belonged in the preamble. Say what you want preserved.
- **Ask, don't assume**: when an agent finds something genuinely ambiguous (a
  stray axis label that leaked into the text flow), have it keep the content and
  flag it, rather than silently deleting.

## Verify the claims

Agents report corrections as `file | line | OCR text → corrected text | PDF page`.
These reports are the evidence that cross-validation happened, so spot-check them
with `verify_corrections.py`. Two outcomes are worth catching at this stage:

- a correction that is not in the PDF at all (fabricated, or applied to the wrong
  place)
- a correction that is right in the PDF but wrong in the *document* — the run's
  one real semantic error was a `λ`→`τ` swap in a recovery table that a
  translator caught and a mechanical check could not

Trust the reports enough to act on them, not enough to skip checking. Note that
"the correction" being right does not mean "the thing that was corrected" was the
right thing to change — read the surrounding sentence.

## Order the passes so later work sees earlier work

The reason to recover math symbols, fix headings, and size tables *before*
translating is that the translators then see the final structure. If you fix a
table's column layout after translation, you have to redo the fix on every
rebuild — and a rebuild regenerates the chunks.

Keep one script that rebuilds the chunks from the un-translated source, and make
it refuse to run once the chunks contain translated text:

```bash
# regenerating would destroy the translation
if [ -d parts ] && "$PY" -c "
import sys, pathlib
for p in pathlib.Path('parts').glob('*.tex'):
    if any('一' <= c <= '鿿' for c in p.read_text(errors='ignore')):
        sys.exit(0)
sys.exit(1)
"; then
    echo "refusing to overwrite parts/: it contains translated text" >&2; exit 1
fi
```

Fix the *source* for anything that must survive a rebuild; fix only merged output
for things that are genuinely merge-time (like inserting the table of contents).

### Keep every pass idempotent, and run it twice to prove it

In practice the structural passes run in both places: on the source before
splitting, and again on the merged file, because a translation may predate the
fix. That makes idempotency a correctness property, not a nicety — and a pass
that is only correct on its first run fails silently.

A real one: the table-sizing pass found each table's wrapper by searching the
whole file for the marker `{\def\LTcaptype{none}`. Every wrapper looked like that
on a fresh import, so the first run was fine — but the pass *rewrites* the
wrapper to `{\footnotesize\def\LTcaptype{none}`, so the second run searched past
those, latched onto the previous un-sized table's wrapper, and re-emitted
everything between the two tables. Seven tables became nine and one table
silently inherited another's column widths. Nothing errored; the compile stayed
green.

The general rule: **anchor on the structure you are editing, not on text you
have already rewritten.** Walk up from the table's own `\begin{longtable}` rather
than searching for a marker string, and key passes on document order rather than
on content that an earlier pass may have changed.

Both fixes are cheap to validate — run the pass twice and diff.

## Keep a structure baseline

Before translation, record the counts of `\label`, `\caption`, `\tag`,
`\includegraphics` and friends with `check_structure.py --baseline`. Compare
afterwards. Translators dropping one `\label` out of seventy compiles fine and
fails later; this catches it in seconds. Expect a few deliberate deltas and
confirm each one is intended.
