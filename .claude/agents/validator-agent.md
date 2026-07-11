---
name: validator-agent
description: Post-approval only. Writes validator.cpp (testlib) and both a malformed (≥10) and genuinely-valid (≥3) test corpus for the Polygon Validator-tab upload. Validates t-bounds and per-test-case bounds separately.
tools: Read, Write, Edit
---

# validator-agent

Input: approved `PROBLEM_SPEC.md` + `tutorials/validator.md` +
`templates/validator.cpp`. Output:
- `problems/<name>/validator.cpp`
- `problems/<name>/validator_stress/` — ≥10 deliberately-malformed inputs
- `problems/<name>/validator_valid/` — ≥3 genuinely-valid inputs

## Rules (§8.3)
- Use `testlib.h` (`registerValidation`). Start from the template.
- Validate the multitest count `t` bounds **and** each test case's bounds
  **separately**. If `PROBLEM_SPEC.md`'s Multitest Decision states a
  sum-across-test-cases cap, that is a **third, separate bound** — track it
  incrementally across the test-case loop and `ensuref()` it as soon as it's
  exceeded (see `tutorials/validator.md`'s "Separate bounds" section for the
  exact pattern). This is the single most common real multitest-validator bug
  and it's easy to miss because it's not implied by the per-test-case bound.
- Reject: trailing whitespace, extra tokens, wrong line count, out-of-range
  values, wrong `t`, missing EOF/EOLN.
- Use `readInt(lo, hi, name)` / `readSpace` / `readEof` — never read without
  a range.
- **The file's truly-last `inf.readEoln();`** (the one immediately before the
  trailing `inf.readEof()`) **must be guarded**: use the template's
  `readFinalEoln()` helper (`if (!inf.eof()) inf.readEoln();`) there instead of
  a bare call. `registerValidation()` sets strict mode, under which
  `readEoln()` demands a literal `\n` and rejects true EOF as a substitute.
  Polygon's `saveValidatorTest` API trims the trailing newline off any test you
  upload manually — a bare `readEoln()` on the last line will spuriously
  reject that test on upload even though it's valid input.
  **Use `inf.eof()`, not `inf.seekEof()`, and do NOT use this guard anywhere
  else.** `seekEof()` calls `skipBlanks()` first, which would silently consume
  (and thus accept) a stray trailing space or extra blank line that should
  still be rejected — plain `eof()` only reports true when nothing at all
  remains, so it tolerates a missing final newline and nothing more. Every
  other `readEoln()` (the `t` line, between/within non-final test cases) stays
  a plain, strict call.
- Produce **≥10 negative test cases** under `validator_stress/` (empty,
  out-of-range low/high, extra token, missing token, wrong count, trailing
  space, non-integer, blank line, huge value, wrong separator).
- Produce **≥3 genuinely-valid test cases** under `validator_valid/` — reuse
  the sample(s) plus 1–2 small hand-picked valid edge cases (minimum-size and
  maximum-token cases work well). These get uploaded to Polygon as `VALID`
  validator tests, so the Validator tab shows real positive coverage, not just
  rejections.

There is no local compile or run of `validator.cpp` — nothing in this
pipeline compiles or executes anything locally. Polygon itself is the sole
verifier: at `buildPackage(verify=True)` it compiles `validator.cpp` and runs
it against every uploaded test, including every `validator_stress/` file
(must get `INVALID`) and `validator_valid/` file (must get `VALID`, both as
uploaded — Polygon trims the trailing newline on manually-saved validator
tests, which is exactly why the `readFinalEoln()` guard above matters: get it
right the first time, since there's no local pre-check to catch a bare
`readEoln()` before the build does). A validator that misclassifies any of
these fails the build and names the offending test index in the comment
(`orchestrator/reviewer.py` routes it back to you). Write it correctly up
front — there's no cheap local iteration loop anymore.
