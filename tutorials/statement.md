# Statement writing — Newton house style

Read by `statement-agent`. Goal: short, precise, unambiguous. No story.

## Rules
- **No flavor text.** Never invent a narrative ("Alice has a garden…"). State
  the task directly.
- **Legend** = what to compute, in ≤ 4–5 sentences for a standard problem.
- **Input** = literal format: number of lines/tokens, order, exact ranges. Match
  the constraints table in the spec.
- **Output** = literal format: what to print, how many lines/tokens.
- **Notes** = only if a sample is genuinely non-obvious; otherwise omit.
- Math in `$...$`. Follow the Polygon statements TeX manual. Use `$10^9$`,
  `$1 \le n \le 10^5$`, etc.
- Multitest: state the `t` line explicitly ("The first line contains $t$ …").

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
