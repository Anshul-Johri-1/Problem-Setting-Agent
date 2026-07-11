# PROBLEM_SPEC: eqpairs

## Title & Summary
Count pairs of equal elements.

## Statement (draft)
Count the number of unordered pairs (i, j), i < j, with a_i = a_j.

## Constraints
| Variable | Range | Notes |
|---|---|---|
| $t$ | $1 \le t \le 10$ | number of test cases |
| $n$ | $1 \le n \le 100000$ | array length |
| $a_i$ | $1 \le a_i \le 1000000000$ | array values |

Time limit: 100ms (fixture — tight on purpose for local brute separation).
Memory limit: 256mb.

## Indexing & Semantics
1-indexed pairs (i, j) with i < j; all n(n-1)/2 pairs considered.

## Intended Solution
Frequency map, sum C(v,2) over distinct values. O(n) per test.

## Answer Uniqueness
yes

## Numerical Tolerance
N/A — integer/exact answer.

## Multitest Decision
yes. No sum-across-test-cases cap for this fixture problem.

## Edge Cases Identified
- n=1 (answer 0)
- all values equal (maximizes the answer)

## Most Tempting Wrong Approach(es)
Off-by-one in the C(v,2) formula (using v*(v+1)/2 instead of v*(v-1)/2).

## Test-Tier Plan (preview)
See tests/fixtures/eqpairs/script.txt.

## Solution Roster (preview)
See tests/fixtures/eqpairs/solutions/.

## Tags & Difficulty
data structures, combinatorics — CF 900-1100

## Open Questions For Human Reviewer
None — this is a test fixture, not a real spec-agent output.
