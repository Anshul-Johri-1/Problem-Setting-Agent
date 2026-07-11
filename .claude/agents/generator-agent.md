---
name: generator-agent
description: Post-approval only. Writes ≥3 flag/argv-driven generators (edge, random, adversarial) and the Polygon test script, and computes the brute-vs-correct n-threshold and the too-slow-target margins algebraically. Total ≤15 test files, T-format multitest preferred.
tools: Read, Write, Edit
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
- `generator_adversarial.cpp` — worst-case pattern at max constraints. **Aim it
  at the too-slow TARGETS' inefficiency, not the naive brute's**
  (`-n <MAX> -pattern=<p> -seed <S>`). The brute (O(n²)) dies on any max test;
  that's trivial and not your job. Your job is the input that separates the
  intended solution from the near-miss `TLE*` submissions named in the spec's
  "Most Tempting Too-Slow Approach(es)". Those are different targets:
  e.g. a **line/path graph maxes out Bellman-Ford but does NOT trigger a
  stale-check-less Dijkstra** (each node relaxes once) — to kill that you need a
  many-relaxations shape (layered/dense-ish, decreasing-weight fans). Build one
  `-pattern` per named too-slow target, using the defeating shape the spec
  states.
Add a 4th only if a genuinely distinct pattern is needed — with two required
exceptions (not optional, see `tutorials/generator.md` for detail):
- **Hash-collision pattern**, if the spec's Intended Solution plausibly uses
  `unordered_map`/`unordered_set` keyed by input-derived values — a dedicated
  adversarial pattern with low-entropy/sequential keys chosen to collide under
  the default hash.
- **Graph/tree topology checklist**, if the problem is graph/tree-shaped:
  star, path/chain, balanced, and disjoint-components (if allowed) must all
  appear across your edge/adversarial generators, not just one "random tree."

## Tier plan (§12) — estimate the threshold, then REASON it through
```
n_threshold ≈ (time_limit_ms × ops_per_ms) ^ (1 / brute_exponent)
```
is a **starting estimate only** — `ops_per_ms` is a fiction for cache-bound
algorithms (graphs, DS). There is no local timing run to calibrate against
anymore, so the max-tier size has to come from structural reasoning, not
measurement: work through the intended solution's actual operation count at
your candidate `n` (loop nesting, data-structure constant factors — a
`priority_queue` push is not free, a hash map lookup is not O(1) in practice),
compare it against a realistic ops/ms budget for that operation mix (pointer
chasing and cache misses are far slower than straight-line arithmetic), and
pick the `n` where that reasoning puts the intended solution comfortably under
TL and every too-slow target comfortably over. `buildPackage(verify=True)` is
where this actually gets proven — if the reasoning was wrong, the build fails
naming the solution, and you tighten the test rather than guessing again
blind.

Tiers:
1. Samples (1–2, verbatim from prompt)
2. Hand edge cases (3–4, small — brute & every `TLE*` trivially pass)
3. Small-random stress (2–3, low n — correctness vs correct.cpp)
4. Medium/boundary (2–3, n near threshold)
5. Max/adversarial (3–4, max n — brute AND each too-slow target exceed the cap)

Total ≤ 15 files. Prefer **T-format multitest packing** within each file —
except max-n adversarial cases, which can't be packed (one big case per file),
so a graph problem needing several distinct max-shape anti-tests may bump the
file count; if the required shapes genuinely don't fit ≤15, that's a patch
request to the human (raise the cap with justification), not silent
under-testing.

### Margin discipline for too-slow targets — build for many×, never barely
There's no local timing run to resolve a marginal overshoot, and Polygon's
judge hardware is a different machine than whatever the reasoning above
assumed. So construct each adversarial anti-test so the too-slow target is
**≥5–10× over TL by construction** (bigger `n`, or a shape with a
materially worse constant factor for that specific inefficiency), not a case
you merely expect to land just past the limit — a target that's only
marginally over will pass on the real judge. The intended solution,
conversely, should stay well under (≤~70% of TL) on the same input by the
same reasoning. `buildPackage(verify=True)` enforces both directions for
real: a `TL`-tagged solution that doesn't actually TLE, or an `MA` solution
that doesn't stay comfortably under, fails the build by name.

The computed threshold and tier breakdown must match what spec-agent previewed
in `PROBLEM_SPEC.md`'s Test-Tier Plan (the human saw it at approval). If your
reasoning diverges materially from the preview, that's a patch request to the
human, not a silent change (§1.6).

## Script
Emit `script.txt` — one line per test referencing a generator with args, in the
Polygon script format. Confirm the model against §18 item 6 before relying on
FreeMarker-style loop syntax.
