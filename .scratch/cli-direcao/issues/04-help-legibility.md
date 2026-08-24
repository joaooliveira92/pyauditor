# 04 — Help-string legibility in the parser

- **Type:** grilling
- **Status:** claimed
- **Blocked by:** —

## Question

Finding 7, the clearest legibility regression in the repo. `cli/parser.py:82-383`
help strings are forced `'word' 'word'` concatenations by the 80-col line rule —
`'-v:umeventoporindicador;-vv:detalhesdeleitura/validação/cálculo'`
(parser.py:82) and the report/consolidate/run `--final-month` help is a 10-line
concatenation (parser.py:194-208). Same pattern at main.py:419-427.

Decision: how to keep single-line (or at most readable multi-line) help strings
without fighting the line-length rule — e.g. a `_HELP` constant block, an
`add_argument(help=...)` reformat that allows long string literals, or a
documented carve-out to the 80-col rule for help text. The decision is where the
rule bends and how it stays enforced.

## Answer

(to be appended on resolution)