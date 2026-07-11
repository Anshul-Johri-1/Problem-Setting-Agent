# PROBLEM_SPEC: <name>

## Title & Summary
<one line>

## Statement (draft)
<short, precise — no flavor text. Legend / Input / Output / Examples / Notes only>

## Constraints
| Variable | Range | Notes |
|---|---|---|
| t | 1 ≤ t ≤ 10^4 | number of test cases |
| ... | | |

Time limit: <proposed, WITH a stated safety-margin assumption — e.g. "TL set to
~3x the reference solution's measured max-test runtime, to absorb
judge-hardware/compiler variance and weaker-language multipliers">
Memory limit: <proposed>

## Indexing & Semantics
<state explicitly, regardless of whether a sample happens to clarify it:
0- or 1-indexed; inclusive/exclusive ranges; is a subarray/substring
contiguous; is the empty case counted; tie-breaking rules if any. This is
required, not optional — ambiguous structural semantics is the single most
common source of contest-time clarification floods>

## Intended Solution
<algorithm, complexity, in prose>

## Answer Uniqueness
<yes/no — determines checker choice, see tutorials/checker.md>

## Numerical Tolerance
<REQUIRED if the answer involves floating point; otherwise "N/A — integer/exact
answer". State the expected error magnitude given the actual operations
involved (not a reflexive 1e-6) and the resulting rcmp4/6/9 choice, with
reasoning — this is what checker-agent reads to pick precision>

## Multitest Decision
<yes/no and why. If yes: state explicitly whether there's a sum-across-test-
cases cap (e.g. "sum of n over all tests ≤ 2·10^5") — this is a separate,
easy-to-forget axis from the per-test-case bound, and validator-agent must
enforce it as a third, independent check>

## Edge Cases Identified
- <min bounds>
- <max bounds>
- <degenerate: n=1, all-equal, etc.>

## Most Tempting Wrong Approach(es)
<name the 1-2 incorrect ideas a strong competitor is most likely to reach for
for THIS specific problem — not a generic category, the actual trap this
problem's structure invites. At least one WA file in the Solution Roster below
must specifically target each one; the generic off-by-one/greedy/overflow/RTE
taxonomy fills any remaining slots, but isn't the starting point>

## Most Tempting Too-Slow Approach(es)
<the near-correct-but-slow submissions a strong competitor actually writes —
the intended algorithm with a fatal inefficiency, NOT the naive brute. For
EACH, name the input SHAPE that defeats it, because that shape (not a generic
max test) is what the adversarial generator must build. Examples:
 - "Dijkstra without `if d > dist[u]: continue`" → killed by a
   many-relaxations graph; a line/path graph does NOT trigger it.
 - "plain `queue` instead of a priority queue" → killed by weight patterns
   that force many re-relaxations.
 - "`unordered_map` with the default hash" → killed by colliding keys.
Each becomes a `TLE*` file in the roster below. If the problem has no plausible
near-miss, write "None — no near-correct-but-slow approach exists" explicitly;
do not leave this blank>

## Test-Tier Plan (preview)
<brute complexity vs. correct complexity vs. time limit → an ESTIMATED
n-threshold (algebraic, a starting point). State plainly that the final
max-tier size is whatever generator-agent MEASURES separates the intended
solution (comfortably under TL) from each too-slow target (comfortably over) —
not the made-up ops_per_ms constant. per §12/§12.5>

## Solution Roster (preview)
<which 7 core + which additional files, and why each WA file is wrong —
cross-reference which WA targets which entry from "Most Tempting Wrong
Approach(es)" above, and which `TLE*` file targets which entry from "Most
Tempting Too-Slow Approach(es)">

## Tags & Difficulty
<topic tags (comma-separated, e.g. "dp, number theory") and a rough difficulty
estimate (e.g. "CF 1400-1600" or "ICPC regional, easy/medium/hard"). Written to
meta.json and uploaded via problem.saveTags>

## Open Questions For Human Reviewer
<anything ambiguous the agent noticed>
