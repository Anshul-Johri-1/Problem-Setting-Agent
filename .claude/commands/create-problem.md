---
description: Create a fully tested, packaged Polygon problem from one structured prompt. One human approval gate, then autonomous.
---

# /create-problem

Entry point for the problem-creation pipeline. Hand the input below to the
**orchestrator** agent, which owns the state machine and the approval gate.

## Input contract (§5)

```
/create-problem
name:          <lowercase-dashed-name>     # [a-z0-9-]+ only (Polygon rule)
statement:     <what the problem asks>
solution:      <intended algorithm + complexity>
constraints:   <t, n, value ranges>
time_limit:    <e.g. 2s>        # optional — orchestrator proposes if omitted
memory_limit:  <e.g. 256mb>     # optional
answer_unique: <yes|no>         # optional — informs checker choice; inferred if omitted
sample tests:
  Input:  <...>
  Output: <...>
```

Required: `name`, `statement`, `solution`, `constraints`, `sample tests`.
Everything else the orchestrator proposes and puts in the spec for approval.

## What happens

1. **orchestrator** creates `problems/<name>/`, initializes `state.json`, and
   dispatches **spec-agent** → `PROBLEM_SPEC.md`.
2. The spec is posted and the pipeline **STOPS** at `AWAITING_APPROVAL`. This is
   the one hard gate — enforced in code by `orchestrator/dispatch.py`, so no
   generation or Polygon call can happen before you reply.
3. Reply **"approved"** (or request revisions — spec-agent loops). On approval
   the orchestrator runs generation → local self-check → tab-by-tab upload +
   commit → invocation loop → package build, fully autonomously.
4. You get back the Polygon link plus one manual reminder: grant `newton_school`
   WRITE access (Polygon has no API for this — §9.5).

Nothing after the approval reply pauses for review except an escalation
(correct-solution failure or retry-cap exhaustion), which returns a diagnostic
report instead of a link.
