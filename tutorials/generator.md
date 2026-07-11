# Generator design & tier plan

Read by `generator-agent`. Reference: Codeforces generators tutorial (entry 18291).

## Three generators, distinct purposes (§12)
- `generator_edge.cpp` — deterministic boundaries (`--case=...`). Small.
- `generator_random.cpp` — uniform random, small→medium (`-n -seed`).
- `generator_adversarial.cpp` — worst case at max n (`-n -pattern -seed`).
Each is flag/argv-driven. testlib seeds RNG from the full argv, so vary args
(especially `-seed`) to get distinct tests. Add a 4th only for a truly distinct
pattern — with two required exceptions below, which are NOT optional even
though they'd otherwise count as "just" a 4th pattern.

### Required: hash-collision test, if the intended solution plausibly hashes
If `PROBLEM_SPEC.md`'s Intended Solution uses (or a strong competitor's
solution would plausibly use) `unordered_map`/`unordered_set` keyed by
input-derived values, the adversarial generator MUST include a pattern that
targets that hash specifically — sequential or low-entropy keys chosen to
collide under the standard library's default hash, blowing up an
`unordered_map`'s buckets from O(1) to O(n) per operation. This is not
optional generator-agent improvisation; it's required whenever hashing is in
play, because a weak-hash submission that would get hacked in a real contest
should also fail in this pipeline's own local judging, not slip through
because the adversarial test happened to use large random values instead.

### Required checklist for graph/tree-shaped problems
Three generic generators (edge/random/adversarial) are not enough shape
coverage for a graph or tree problem — at minimum, cover these canonical
adversarial topologies across your edge/adversarial generators before
considering the tier plan complete:
- **star** (one hub, all others degree 1) — punishes anything assuming
  balanced degree.
- **path/chain** (a straight line) — punishes recursion depth (stack
  overflow) and anything assuming logarithmic tree height.
- **balanced** (e.g. complete binary tree) — the "well-behaved" case;
  necessary but not sufficient on its own.
- **disjoint components** (if the problem allows a non-connected graph) —
  punishes code that silently assumes connectivity.
This checklist applies in addition to, not instead of, the standard 5-tier
size/scale plan below.

## n-threshold (compute, then honor)
```
n_threshold ≈ (time_limit_ms × ops_per_ms) ^ (1 / brute_exponent)
```
`ops_per_ms ≈ 1e5..1e6` depending on constant factor; state your assumption.
This must match spec-agent's Test-Tier Plan preview (the human approved it).

## Tiers (total ≤ 15 files)
1. Samples — 1–2, verbatim from the prompt.
2. Edge — 3–4, small (brute trivially passes).
3. Small-random stress — 2–3, low n (correctness vs correct.cpp).
4. Medium/boundary — 2–3, n near threshold (brute approaches TL).
5. Max/adversarial — 3–4, max n (brute reliably exceeds the cap).

Prefer **T-format multitest** packing within each file. The distribution must
give brute a PARTIAL TLE pattern (§0): passes small/medium, times out on max.

## Script
`script.txt`: one line per test, e.g. `gen_random -n 2000 -seed 2`. Confirm the
Polygon script-line-per-test model / FreeMarker loop syntax against §18 item 6.
