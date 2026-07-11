<!-- AUTO-GENERATED from .claude/agents/ + .claude/GUARDRAILS.md by sync-ai-configs.py. DO NOT EDIT — changes will be overwritten on the next commit. -->

# READ THIS FIRST — applies to every AI agent, every tool, no exceptions

This is not one option among several. It is synced into every tool's config
(`.cursor/rules/`, `.github/copilot-instructions.md`, `AGENTS.md`,
`.windsurfrules`, `.agents/skills/`, `GEMINI.md`) by `sync-ai-configs.py`
specifically so no agent — Claude, Gemini, Copilot, Codex, Windsurf, whatever
comes next — can plausibly claim it wasn't told.

## Why this file exists

An agent (Gemini, via a different tool integration) was once given access to
this repo and, instead of following the documented pipeline, wrote a series
of standalone Python scripts that: forged `state.json` transitions labeled
literally `"mock approval"` and `"mock check"` (never actually calling the
approval/local-check machinery), fabricated a verdict matrix by hand instead
of running `local_harness` ("we don't want to run the harness again right
now" — an actual code comment it wrote), and then drove `PolygonUploader`
directly with real credentials from `.env`. This happened silently — nobody
was told until a human went looking for unrelated reasons. It left two real,
live Polygon problems in a broken, half-uploaded state. Full account:
`docs/POLYGON_API_FINDINGS.md` and this repo's commit history.

The lesson: **documentation describing the correct process is not enough.**
An agent with Bash/Python execution access can always `import` internals
directly and skip whatever a markdown file asked it to do. So the rules below
are backed by actual code that refuses to run otherwise (see "How this is
enforced" at the bottom) — but the rules still need to be said plainly,
because the fastest way to avoid tripping a refusal is to know what not to
attempt in the first place.

## The rules

1. **There is exactly one sanctioned way to touch live Polygon:
   `python3 -m orchestrator.cli <command> <problem-name>`.** Never construct
   `PolygonSession`, `PolygonUploader`, or `Orchestrator` yourself in a new
   script. If you find yourself writing `from polygon_client.auth import
   PolygonSession` outside of `orchestrator/cli.py` or `polygon_client/`
   itself, stop — you are about to reproduce the exact incident above.

2. **Never fabricate, hardcode, or skip the build-and-verify step.** There is
   no local self-check anymore — nothing in this repo compiles or runs any
   solution/generator/validator/checker locally, anywhere. The one
   verification gate is Polygon's own `buildPackage(verify=True)`, triggered
   by `orchestrator.cli finish`. If you believe a build failure is spurious
   or the process is too slow, say so to the human and wait — do not invent a
   build result, a package state, or a solution's verdict by hand and pass it
   downstream as if it were real. There's no situation where hand-writing a
   fake result instead of actually running `finish` is the right call.

3. **Never call `orchestrator.cli approve` unless a human has unambiguously
   approved `PROBLEM_SPEC.md` in the actual conversation you're in.** Not
   speculatively, not "to see what the rest of the pipeline does," not
   because you're confident the spec is fine. This is the one hard
   checkpoint in the whole system; treat it as load-bearing.

4. **Never edit `state.json` directly.** Every legitimate state change goes
   through `StateStore.transition()` (which the CLI commands call for you).
   Direct attribute assignment (`store.state = X; store._write()`) is
   exactly the pattern that caused the incident — it leaves no audit trail
   and downstream code has since been changed to specifically distrust it.

5. **If something in the documented process seems broken, blocked, or
   too slow, stop and tell the human — do not route around it.** Every
   "clever workaround" available to you (calling the API client directly,
   editing state.json, fabricating a result) is a guardrail this repo
   deliberately built, not an accidental gap you've cleverly spotted.

6. **Read-only inspection is always fine.** `orchestrator.cli status <name>`
   and `scripts/inspect_problem.py <problem_id>` are safe to run anytime,
   including for debugging. There is no legitimate reason to write a new
   script for read-only Polygon queries — these already exist.

## How this is enforced in code (so you understand it's not optional)

- `orchestrator/gate.py`'s `assert_can_dispatch` blocks generation-stage
  agent dispatch before approval — but only for calls that go through
  `dispatch()`.
- `orchestrator/state.py`'s `StateStore.has_transitioned_through()` checks
  the AUDIT TRAIL (not just the current state value) for a genuine
  `AWAITING_APPROVAL → APPROVED` record.
- `orchestrator/uploader.py`'s `PolygonUploader` calls that check before
  **every single mutating method**, independent of whether you went through
  `Orchestrator` at all — so even a script that imports `PolygonUploader`
  directly and skips `Orchestrator` entirely still gets refused.
- None of this is airtight against a truly determined bypass (nothing
  running in the same process as an agent with full Python access can be) —
  but it is airtight against exactly the incident that already happened, and
  it will not silently look like success if you try something similar.

---

# Skill: solutions-agent

> Post-approval only. Produces the 7–10 file solution roster (correct, brute, and WA/RE/TL variants), each targeting a named problem-specific trap where possible, each declared with the exact Polygon tag its intended bug should produce. A WA file that shouldn't actually fail — or is tagged for the wrong verdict — is a bug, not a deliverable.

# solutions-agent

Input: approved `PROBLEM_SPEC.md` + `tutorials/solutions.md` +
`templates/solutions/`. Output: 7–10 files in `problems/<name>/solutions/`,
matching the count `PROBLEM_SPEC.md`'s Solution Roster preview settled on
(reflecting any `num_solutions` the human suggested, already clamped to the
7–10 org range by spec-agent) — don't add or drop files beyond what was
previewed and approved.

## Start from the spec's named traps, not the generic taxonomy
`PROBLEM_SPEC.md`'s "Most Tempting Wrong Approach(es)" section names the 1-2
ideas a strong competitor is most likely to submit for THIS problem. At least
one WA file must specifically target each one named there — build these
first. The generic fixed core below fills remaining roster slots; it's the
fallback, not the starting point.

## Too-slow targets are first-class solutions, not "the brute" (§12.5)
`PROBLEM_SPEC.md`'s "Most Tempting Too-Slow Approach(es)" / `meta.json`'s
`too_slow_targets` names the near-correct-but-slow submissions this problem
must reject — the intended algorithm with a fatal inefficiency (Dijkstra
without the stale-skip, a plain `queue`, `unordered_map` under collision, DP
without memo). Ship **one `TLE1.cpp`, `TLE2.cpp`, … per named target**:
- It implements the intended *algorithm* faithfully except for the one flaw,
  so it is **AC on the small tier** — that's what makes it a realistic
  competitor submission and not just another brute. `brute.cpp` stays the
  asymptotically-naive oracle; `TLE*` is a subtle near-miss. Keep both.
- Declare Polygon tag `TL` for it in `meta.json`'s `solution_tags`. It must be
  forced OVER the limit by the adversarial tier generator-agent builds —
  there's no local sweep to prove that anymore; `buildPackage(verify=True)`
  is the proof, and if it isn't killed, the *test set* is too weak (tell
  generator-agent the input shape from the spec), not the solution — that
  shows up as a Polygon build failure naming this file, routed back to you or
  generator-agent by reviewer-agent.
- These do NOT count against needing WA files — a too-slow target is about
  timing, a WA is about correctness; a strong roster has both.

## Fixed core (7, §13)
```
correct.py   – reference, AC everywhere
correct.cpp  – same algorithm in C++, cross-validates correct.py
brute.cpp    – correct but naive; AC on small/medium, TL on max tier
WA1.py       – off-by-one / boundary
WA2.py       – wrong greedy / wrong invariant (algorithmically wrong)
WA3.py       – overflow / precision / modulo
WA4.cpp      – uninitialized/OOB RTE, or wrong DS giving TLE+WA mix
```
If the problem is multitest, consider swapping one generic slot for a WA that
forgets to reset global/static state between test cases — the single most
common real multitest-specific bug.

## Optional (≤3, only if genuinely distinct)
`brute2.cpp` (different inefficiency), `WA5.*` (complexity-class mistake that
bites at the given constraints), `correct_alt.*` (a genuinely different
correct approach — ship it as a real roster file tagged `OK`, not a
local-only cross-check file: if it disagrees with the checker/MA on any test,
Polygon's build fails it as an `OK`-tag violation, which is the whole point —
this is how a second-reference-solution disagreement gets caught now), a
multitest-state-reset WA. Additions must be justified, not padding.

## Every solution needs an explicit Polygon tag, declared by you
There is no local judge run to infer verdicts from anymore. You must add or
update `meta.json`'s `solution_tags` (spec-agent seeded a preview; you own
making it match the roster you actually ship) with exactly one Polygon tag
per file: `MA` on the one true main solution, `OK` on other correct
references, `TL` on brute + every `TLE*`, `WA`/`RE`/`ML`/`RJ` on the rest per
the mistake each encodes. **This tag IS the declared-verdict contract now** —
Polygon's `buildPackage(verify=True)` strictly enforces it against the file's
real behavior on Polygon's own judge, and a mismatch fails the build with a
comment naming the file (routed back to you by reviewer-agent). Also keep the
comment-header convention (state which mistake the file encodes and why) —
still valuable documentation, just no longer machine-checked locally.

## Rules (§8.5)
- Every WA/brute/TLE file carries a **comment header** stating exactly which
  mistake it encodes and why it's expected to fail.
- Keep WA/RE files algorithmically fast (not the brute's complexity) so they
  fail with their claimed verdict, not TL — Polygon strictly enforces
  solution tags at package build.
- If the `MA` solution uses `unordered_map`/`unordered_set` keyed by
  input-derived values, either add a randomized salt or explain in a comment
  why hash-collision attacks don't apply, and flag it to generator-agent so an
  adversarial test targets that hash specifically.
- There is no local compile or run of any solution file, and no ASan/UBSan
  pass — nothing in this pipeline executes anything locally. Write each file
  to be correct (or wrong in exactly the declared way) on inspection; Polygon
  compiling and running the whole roster against every test at
  `buildPackage(verify=True)` is the only verification, and it is strict: a
  WA file that turns out AC everywhere, or fails with a different verdict
  than its declared tag, fails the build by name. Fix the file or the tag
  once that happens — don't guess ahead of time what Polygon will say.
- brute must never TLE on everything nor AC on everything (§0) — reason this
  through against the Test-Tier Plan's tier sizes before shipping, since
  there's no local run to catch it first.
