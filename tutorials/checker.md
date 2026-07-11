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

Pick float precision to match the spec's stated tolerance. Output only the
chosen name to `checker.choice`.

**Not unique ("print any …") → CUSTOM checker:**
Start from `templates/checker_custom_stub.cpp`. Use `registerTestlibCmd`, read
input via `inf`, contestant output via `ouf.read*`, jury answer via `ans.read*`.
Verify the *property* the problem asks for; only compare to `ans` when that's
meaningful. Never hand-roll token parsing. `quitf(_ok/_wa, ...)`. Compile clean.

## Sanity
`std::acmp.cpp` does NOT exist on the server. Bare names (`wcmp.cpp`) are
rejected — always use the `std::<name>.cpp` form.
