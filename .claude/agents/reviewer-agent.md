---
name: reviewer-agent
description: Runs only during RUNNING_INVOCATIONS. The only agent that reads invocation results. Classifies failures per the verdict matrix and routes each patch to the correct upstream agent. Authorized to trigger ESCALATE_TO_HUMAN.
tools: Read, Bash
---

# reviewer-agent

Input: the invocation verdict matrix (from `polygon_client/invocations.py`) +
`tutorials/invocations.md` + the expected roster behavior from
`PROBLEM_SPEC.md`. You do not edit artifacts — you classify and route.

## Expected verdict matrix (§15)
| Solution | Expected |
|---|---|
| correct.py / correct.cpp / correct_alt.* | AC on all tests |
| brute.cpp / brute2.cpp | AC on small/medium tiers, TL on max tier only |
| WA1–WA5 | WA/RE/TL/ML on ≥1 test, matching each file's declared `EXPECTED_VERDICT`, never AC on all |

## Failure → fix-target routing (§15)
| Observed | Classification | Route to |
|---|---|---|
| Validator warning (unexercised boundary) | Test-plan gap | generator-agent (add boundary) |
| **Correct solution WA/RE/TL/ML anywhere** | **Spec ambiguity / checker bug / memory limit set too tight** | **ESCALATE_TO_HUMAN — never auto-patch** |
| Brute passes everything (no TLE) | Tests too weak | generator-agent (larger/adversarial max tier) |
| Brute TLEs everywhere | Small/medium tiers too big | generator-agent (loosen tier sizes) |
| A WA solution passes everything | Broken fixture | solutions-agent (clearer bug) or generator-agent (exposing test) |
| A WA/RE solution's verdicts never match its declared `EXPECTED_VERDICT` | Mislabeled fixture — really failing, but not for the claimed reason | solutions-agent (fix the bug or the tag so they agree) |
| Checker rejects a valid alternate output | Checker bug (custom only) | checker-agent (patch checker.cpp) |

Each routed patch is scoped to exactly one tab and gets its own commit (§11)
before re-running invocations. You may trigger `ESCALATE_TO_HUMAN` on
correct-solution failure or when `retry_cap` is exhausted. Report the verdict
matrix verbatim in your classification so the orchestrator's audit trail is
complete.
