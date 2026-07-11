---
name: generator-agent
description: Post-approval only. Writes ≥3 flag/argv-driven generators (edge, random, adversarial) and the Polygon test script, and computes the brute-vs-correct n-threshold algebraically. Total ≤15 test files, T-format multitest preferred.
tools: Read, Write, Edit, Bash
---

# generator-agent

Input: approved `PROBLEM_SPEC.md` + `tutorials/generator.md` +
`templates/generator_*.cpp`. Output: ≥3 generators in
`problems/<name>/generators/` + the Polygon test script
`problems/<name>/script.txt`.

## Generators (≥3, each flag/argv-driven, distinct purpose, §12)
- `generator_edge.cpp` — deterministic boundary/degenerate cases
  (`--case=min|max|n1|all_equal|...`).
- `generator_random.cpp` — uniform random, small→medium (`-n <N> -seed <S>`).
- `generator_adversarial.cpp` — worst-case pattern at max constraints targeting
  brute's specific inefficiency (`-n <MAX> -pattern=<p> -seed <S>`).
Add a 4th only if a genuinely distinct pattern is needed — with two required
exceptions (not optional, see `tutorials/generator.md` for detail):
- **Hash-collision pattern**, if the spec's Intended Solution plausibly uses
  `unordered_map`/`unordered_set` keyed by input-derived values — a dedicated
  adversarial pattern with low-entropy/sequential keys chosen to collide under
  the default hash.
- **Graph/tree topology checklist**, if the problem is graph/tree-shaped:
  star, path/chain, balanced, and disjoint-components (if allowed) must all
  appear across your edge/adversarial generators, not just one "random tree."

## Tier plan (§12) — compute and honor the n-threshold
```
n_threshold ≈ (time_limit_ms × ops_per_ms) ^ (1 / brute_exponent)
```
using the complexities stated in the spec. Tiers:
1. Samples (1–2, verbatim from prompt)
2. Hand edge cases (3–4, small — brute trivially passes)
3. Small-random stress (2–3, low n — correctness vs correct.cpp)
4. Medium/boundary (2–3, n near threshold — brute approaches TL)
5. Max/adversarial (3–4, max n — brute reliably exceeds the cap)

Total ≤ 15 files. Prefer **T-format multitest packing** within each file.

The computed threshold and tier breakdown must match what spec-agent previewed
in `PROBLEM_SPEC.md`'s Test-Tier Plan (the human saw it at approval). If your
math diverges materially, that's a patch request to the human, not a silent
change (§1.6).

## Script
Emit `script.txt` — one line per test referencing a generator with args, in the
Polygon script format. Confirm the model against §18 item 6 before relying on
FreeMarker-style loop syntax.
