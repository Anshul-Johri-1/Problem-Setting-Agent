---
name: checker-agent
description: Post-approval only. Chooses a standard Polygon checker by default; writes a custom checker.cpp only when the spec's Answer Uniqueness is "no". Uses testlib readAns/readOuf for custom checkers.
tools: Read, Write, Edit
---

# checker-agent

Input: approved `PROBLEM_SPEC.md` + `tutorials/checker.md` +
`config/standard_checkers.yaml`.

## Decision tree (§14)
Default to **standard**. Consult the spec's `Answer Uniqueness`:

- **Unique answer** → pick a standard checker from
  `config/standard_checkers.yaml` (live-verified names):
  - exact token: `std::wcmp.cpp` (default)
  - integer sequence: `std::ncmp.cpp`
  - floats: `std::rcmp4/6/9.cpp` (match the spec's tolerance)
  - yes/no: `std::yesno.cpp` (or `std::nyesno.cpp` for many)
  - line tokens: `std::lcmp.cpp`; strict lines: `std::fcmp.cpp`
  - bignum: `std::hcmp.cpp`
  Output: just the chosen name (a config choice, no code) →
  `problems/<name>/checker.choice`.

- **Not unique** ("print any … such that") → write
  `problems/<name>/checker.cpp` from `templates/checker_custom_stub.cpp`, using
  testlib's `readAns`/`readOuf` pattern (never from scratch). Re-validate the
  jury answer with `readAns` and the contestant output with `readOuf`; accept
  any output that satisfies the stated property.
  - **Validate any participant-supplied index/reference against the input's
    declared bounds before using it** — don't trust `ouf.readInt()` as a safe
    array index without range-checking; malformed output can otherwise crash
    the checker itself, not just fail cleanly.
  - **Confirm the output satisfies basic format constraints** (right number
    of lines/tokens), not just that each individually-read value is locally
    valid.

For standard checkers, pick float precision from `PROBLEM_SPEC.md`'s
**Numerical Tolerance** field (spec-agent's reasoned error-magnitude
estimate) — never default to `rcmp6` reflexively.

There is no local compile or run of `checker.cpp` — Polygon compiles it and
runs it against the MA solution's output during `buildPackage(verify=True)`;
a broken checker fails the build with a compiler-error or rejection comment
(`orchestrator/reviewer.py` routes it back to you). Write it correctly up
front; there's no local iteration loop to lean on.
