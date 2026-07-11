"""The structural approval gate (§1.1, §6).

This is the enforcement point the spec insists must be CODE, not a prompt:

    "the dispatch tool itself is the enforcement point, not the model's
     judgment alone."

`assert_can_dispatch` is called by `dispatch()` before EVERY agent invocation.
If a generation-stage agent is dispatched before the human has approved the
spec (state ∈ {DRAFTING_SPEC, AWAITING_APPROVAL}), it raises `GateError` — no
message, urgency, or model reasoning can bypass it, because the check happens
here in Python, not in the model.
"""

from __future__ import annotations

from .state import State


class GateError(RuntimeError):
    """Raised when an agent is dispatched in a state where it is not allowed."""


# States that exist only before the human approval gate.
_PRE_APPROVAL = {State.DRAFTING_SPEC, State.AWAITING_APPROVAL}

# Everything from APPROVED onward — the only window in which any generation,
# file-write, or Polygon call is permitted.
_POST_APPROVAL = {s for s in State if s not in _PRE_APPROVAL
                  and s is not State.ESCALATE_TO_HUMAN}

# Per-agent allow-lists. The generation agents share the post-approval window;
# spec-agent is the ONLY agent allowed pre-approval; reviewer-agent only runs
# while reading invocation results.
_AGENT_ALLOWED: dict[str, set[State]] = {
    # Stage 0 — the only pre-approval agent
    "spec-agent": {State.DRAFTING_SPEC, State.AWAITING_APPROVAL},
    # Generation-stage agents — post-approval only (§1.1). Includes the
    # invocation-loop re-run states so targeted patches (§15) can re-dispatch.
    "statement-agent": set(_POST_APPROVAL),
    "validator-agent": set(_POST_APPROVAL),
    "checker-agent": set(_POST_APPROVAL),
    "solutions-agent": set(_POST_APPROVAL),
    "generator-agent": set(_POST_APPROVAL),
    # Reviewer only reads the Polygon build failure comment (§8.7).
    "reviewer-agent": {State.BUILDING_PACKAGE},
}

# Agents that manage the pipeline itself are not gated (they drive transitions).
_UNGATED = {"orchestrator"}


def agent_allowed_states(agent_name: str) -> set[State]:
    if agent_name in _UNGATED:
        return set(State)
    if agent_name not in _AGENT_ALLOWED:
        raise GateError(f"unknown agent '{agent_name}' — not in the dispatch allow-list")
    return _AGENT_ALLOWED[agent_name]


def assert_can_dispatch(agent_name: str, state: State) -> None:
    """Raise GateError unless `agent_name` may run in `state`.

    The hard guarantee (§1.1): any generation-stage agent dispatched while
    state is pre-approval raises here, in code.
    """
    if agent_name in _UNGATED:
        return
    allowed = agent_allowed_states(agent_name)
    if state not in allowed:
        # Make the most important failure mode unmistakable in the message.
        if agent_name != "spec-agent" and state in _PRE_APPROVAL:
            raise GateError(
                f"BLOCKED: '{agent_name}' is a generation-stage agent and cannot "
                f"run before spec approval (current state: {state.value}). "
                f"No generation, file writes, or Polygon calls happen until the "
                f"human approves PROBLEM_SPEC.md (§1.1, §6)."
            )
        raise GateError(
            f"BLOCKED: '{agent_name}' cannot be dispatched in state "
            f"{state.value} (allowed: {sorted(s.value for s in allowed)})."
        )
