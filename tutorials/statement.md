# Statement writing — Newton house style

Read by `statement-agent`. Goal: short, precise, unambiguous. No story.

## Rules
- **No flavor text.** Never invent a narrative ("Alice has a garden…"). State
  the task directly.
- **Legend** = what to compute, in ≤ 4–5 sentences for a standard problem.
- **Structural semantics are ALWAYS stated, never left implicit** — pull
  these directly from `PROBLEM_SPEC.md`'s "Indexing & Semantics" section (a
  required field, not conditional on whether a sample happens to clarify it):
  0- vs 1-indexed, whether a subarray/substring must be contiguous, whether
  the empty case counts, tie-breaking rules. Terseness is fine; ambiguity is
  not — this is the single most common source of contest-time clarification
  floods, and unlike "explain a tricky sample," it's never optional.
- **Input** = literal format: number of lines/tokens, order, exact ranges. Match
  the constraints table in the spec.
- **Output** = literal format: what to print, how many lines/tokens.
- **Notes** = explain a sample if genuinely non-obvious; this is separate from
  and doesn't substitute for the structural-semantics requirement above.
- Math in `$...$`. Follow the Polygon statements TeX manual. Use `$10^9$`,
  `$1 \le n \le 10^5$`, etc.
- Multitest: state the `t` line explicitly ("The first line contains $t$ …"),
  and if there's a sum-across-test-cases cap, state that too.

## Anti-patterns
- Backstory, characters, jokes, world-building.
- Restating constraints in prose that contradict the table.
- Leaving output format tolerances implicit — say "any valid answer" only when
  the checker is custom (answer not unique).

## Checklist before done
- [ ] Legend states the task in the first sentence.
- [ ] Input/Output are literal and match the constraints.
- [ ] Sample I/O matches the generated sample tests exactly.
- [ ] Compiles as Polygon TeX with no errors.
