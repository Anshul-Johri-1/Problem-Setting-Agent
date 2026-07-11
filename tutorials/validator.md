# Validator writing (testlib)

Read by `validator-agent`. Reference: Codeforces validators tutorial (entry 18426).

## Structure
- `registerValidation(argc, argv)` first.
- Read the multitest header `t` with an explicit range, then loop; call
  `setTestCase(tc)` inside the loop so errors report the offending case.
- Read every token with a range: `readInt(lo, hi, "name")`,
  `readLong`, `readDouble`, `readToken`, etc.
- Enforce exact whitespace: `readSpace()` between tokens on a line,
  `readEoln()` at line ends, `readEof()` at the very end.

## Required: guard ONLY the file's truly-last `readEoln()`, never the others
`registerValidation()` sets `inf.strict = true`. Under strict mode, testlib's
`readEoln()` requires a literal `\n` character — it does **not** accept true EOF
as a substitute for the final newline (confirmed by reading testlib's `eoln()`
source: the EOF-tolerant branch is gated on `!strict`).

This matters because **Polygon's `problem.saveValidatorTest` API trims the
trailing newline off any input you upload as a manual Validator-tab test.**
A validator using a bare `inf.readEoln();` on its last line will therefore
REJECT an otherwise-perfectly-valid test the moment it's uploaded that way —
the package build then fails with `"Validator test #N got INVALID, but VALID
expected"` even though nothing is actually wrong with the test data.

**Fix — but ONLY at the true end of the file, right before `inf.readEof()`:**
```cpp
static inline void readFinalEoln() {
    if (!inf.eof()) inf.readEoln();
}
```
Use `inf.eof()`, **not** `inf.seekEof()`. `seekEof()` calls `skipBlanks()`
first, which physically **consumes** any pending whitespace (spaces, tabs,
`\n`) before checking — so it would silently accept a stray trailing space or
an extra blank line at the end of the file, which should still be rejected.
Plain `eof()` reports true only when literally nothing remains right now (no
skipping), so it tolerates exactly one thing — a missing final newline — and
nothing else. Verified locally against all four cases: a proper trailing
newline (passes), a missing trailing newline (passes), a trailing space before
the newline (still rejected), and an extra blank line at the end (still
rejected).

This guard is also only meaningful at the file's true end. Used mid-file,
`eof()` correctly returns `false` (there's more real content coming) and falls
through to a normal, fully strict `readEoln()` — but there's no reason to pay
for the extra check anywhere except the one place it matters.

**The only safe place to use `readFinalEoln()` is the file's last line** — i.e.
the last line of the last test case, immediately before the trailing
`inf.readEof()`. Everywhere else (the `t` line, every line between/within
non-final test cases) keep a plain `inf.readEoln();`, exactly as before. For a
per-test-case loop this typically looks like:
```cpp
for (int tc = 1; tc <= t; ++tc) {
    ...
    if (tc < t) inf.readEoln();
    else        readFinalEoln();
}
```
See `templates/validator.cpp` for the full pattern.

## Must reject
trailing whitespace · extra tokens · missing tokens · wrong line count ·
out-of-range values · wrong `t` · non-integer where integer expected ·
blank/duplicated lines · wrong separators.

## Separate bounds — THREE axes, not two
Validate `t` bounds **and** per-test-case bounds **independently** — a valid `t`
with an out-of-range case must still fail, and vice versa.

**If the spec's Multitest Decision states a sum-across-test-cases cap** (e.g.
"sum of n over all tests ≤ 2·10^5" — check `PROBLEM_SPEC.md`), that is a
**third, separate bound** and the single most common real multitest-validator
bug is forgetting it: a validator that's individually correct per test case
still lets a participant construct `t=10^4` tests each at max `n`, blowing
total input size/work far past what the time limit assumes. Track the running
sum incrementally across the test-case loop and `ensuref()` it stays within
the stated cap, checked as soon as it's exceeded rather than only at the end:
```cpp
long long sumN = 0;
for (int tc = 1; tc <= t; ++tc) {
    setTestCase(tc);
    int n = inf.readInt(1, N_MAX, "n");
    sumN += n;
    ensuref(sumN <= SUM_N_CAP, "sum of n exceeds %lld (got at least %lld)",
           (long long)SUM_N_CAP, sumN);
    // ... rest of the test case ...
}
```

## Negative corpus (≥10)
Emit ≥10 malformed inputs under `validator_stress/`. Suggested set: empty file,
value below min, value above max, extra trailing token, missing token, wrong
count vs `t`, trailing space, non-integer token, blank line, oversized value,
wrong separator. `local_harness/validator_stress.py` requires each to be
REJECTED and every real test to PASS. Compile clean under `-Wall -Wextra`.

## Positive corpus — also required, not just the malformed set
The Validator tab on Polygon should show genuine VALID coverage, not only
rejections. Emit a handful (≥3) of hand-picked genuinely-valid inputs under
`validator_valid/` — reuse the sample(s) plus 1–2 small edge cases (e.g. `t=1`
with minimum-size input, and one with maximum-size tokens). These get uploaded
to Polygon as `VALID` validator tests alongside the `INVALID` malformed corpus.
`local_harness/validator_stress.py` checks each file in `validator_valid/`
**twice**: once as-is, and once with its trailing newline(s) stripped
(simulating exactly what Polygon's upload does) — both must PASS. If the
trimmed check fails, that's a signal the `readFinalEoln()` fix above hasn't
been applied to the file's last line; fix the validator, don't just drop the
test.
