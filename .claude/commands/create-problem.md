---
description: Create a fully tested, packaged Polygon problem from one structured prompt. One human approval gate, then autonomous.
---

# /create-problem

Entry point for the problem-creation pipeline. Hand the input below to the
**orchestrator** agent, which owns the state machine and the approval gate.

## Input contract (§5)

```
/create-problem
name:            <lowercase-dashed-name>   # [a-z0-9-]+ only (Polygon rule)
statement:       <what the problem asks>
solution:        <intended algorithm + complexity>
constraints:     <t, n, value ranges>
time_limit:      <e.g. 2s>        # optional — orchestrator proposes if omitted
memory_limit:    <e.g. 256mb>     # optional
answer_unique:   <yes|no>         # optional — informs checker choice; inferred if omitted
num_tests:       <e.g. 12>        # optional — target test-file count, ≤15 (org cap)
num_solutions:   <e.g. 8>         # optional — target solution-file count, 7–10 (org range)
num_generators:  <e.g. 4>         # optional — target generator count, ≥3 (org minimum)
sample tests:
  Input:  <...>
  Output: <...>
```

Required: `name`, `statement`, `solution`, `constraints`, `sample tests`.
Everything else the orchestrator proposes and puts in the spec for approval.
The `num_*` fields are suggestions, not commands: spec-agent honors them if
they fit the org bounds in `config/org_defaults.yaml`; if a suggestion falls
outside those bounds, it clamps to the nearest allowed value and flags the
clamp under "Open Questions" for you to confirm at the approval gate.

## What happens

1. **orchestrator** creates `problems/<name>/`, initializes `state.json`, and
   dispatches **spec-agent** → `PROBLEM_SPEC.md`.
2. The spec is posted and the pipeline **STOPS** at `AWAITING_APPROVAL`. This is
   the one hard gate — enforced in code by `orchestrator/dispatch.py`, so no
   generation or Polygon call can happen before you reply.
3. Reply **"approved"** (or request revisions — spec-agent loops). On approval
   the orchestrator runs generation → local self-check → tab-by-tab upload +
   commit → invocation loop → package build, fully autonomously.
4. You get back the Polygon link. If `config/org_defaults.yaml` lists any
   required collaborators, you also get a manual reminder to grant them access
   (Polygon has no API for this — §9.5); empty by default.

Nothing after the approval reply pauses for review except an escalation
(correct-solution failure or retry-cap exhaustion), which returns a diagnostic
report instead of a link.
