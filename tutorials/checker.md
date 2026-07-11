# Checker decision tree

Read by `checker-agent`. Reference: Codeforces checkers tutorial (entry 18431).
Standard-checker names are in `config/standard_checkers.yaml` (live-verified).

## Decide from the spec's "Answer Uniqueness"

**Unique answer → STANDARD checker (no code):**

| Output shape | Checker |
|---|---|
| single/space-separated tokens, exact | `std::wcmp.cpp` (default) |
| sequence of signed integers | `std::ncmp.cpp` |
| floating point, tol 1e-4 / 1e-6 / 1e-9 | `std::rcmp4/6/9.cpp` |
| single YES/NO | `std::yesno.cpp` |
| many YES/NO | `std::nyesno.cpp` |
| line tokens, whitespace-tolerant | `std::lcmp.cpp` |
| strict per-line | `std::fcmp.cpp` |
| single bignum | `std::hcmp.cpp` |

Pick float precision to match `PROBLEM_SPEC.md`'s **Numerical Tolerance**
field (spec-agent fills this with reasoning about expected error magnitude —
not a reflexive `1e-6`). Output only the chosen name to `checker.choice`.

**Not unique ("print any …") → CUSTOM checker:**
Start from `templates/checker_custom_stub.cpp`. Use `registerTestlibCmd`, read
input via `inf`, contestant output via `ouf.read*`, jury answer via `ans.read*`.
Verify the *property* the problem asks for; only compare to `ans` when that's
meaningful. Never hand-roll token parsing. `quitf(_ok/_wa, ...)`. Compile clean.

**Two required defensive-writing rules for custom checkers:**
1. **Validate any participant-supplied index/reference against the input's
   declared bounds BEFORE using it.** A checker verifying a constructive
   property (e.g. "the output is a valid coloring/matching/permutation") has
   to read participant-supplied indices and use them — if you trust
   `ouf.readInt()` as a safe array index without range-checking it first, a
   malformed (even if unintentionally so) submission can crash the checker
   itself with undefined behavior, not just fail cleanly with `_wa`.
2. **Confirm the output satisfies basic format constraints, not just that
   individual values are locally valid.** If the problem says "print exactly
   k lines," verify exactly k lines were printed (e.g. via `ouf.seekEof()`
   after reading the k'th value) — a checker that validates each line it
   reads without confirming the participant didn't print extra/fewer lines
   than required is a common, real correctness gap in custom checkers.

## Sanity
`std::acmp.cpp` does NOT exist on the server. Bare names (`wcmp.cpp`) are
rejected — always use the `std::<name>.cpp` form.
