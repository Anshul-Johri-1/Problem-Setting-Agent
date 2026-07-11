"""The single choke point every agent invocation passes through (§6).

`dispatch()` is deliberately the ONLY sanctioned way to invoke a subagent. It:
  1. Loads current pipeline state from `state.json`.
  2. Calls `assert_can_dispatch` — the structural gate. Raises before any work
     if the agent isn't allowed in the current state.
  3. Appends a dispatch record to the audit trail.
  4. Hands off to the provided `runner` (the actual model/subagent call).

The runner is injected so this module stays framework-agnostic: in Claude Code
it wraps a Task-tool call; in tests it's a stub. The gate check is identical
regardless of runner — that's the whole point.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Any

from .state import StateStore, State
from .gate import assert_can_dispatch


DispatchRunner = Callable[[str, dict], Any]


def dispatch(problem_dir: Path, agent_name: str, payload: dict,
             runner: DispatchRunner) -> Any:
    """Gate-checked dispatch of a single subagent.

    Raises GateError (from assert_can_dispatch) BEFORE the runner is ever
    called if the agent is not permitted in the current state.
    """
    store = StateStore.load(problem_dir)

    # --- structural enforcement: this line is the guardrail (§1.1) ---
    assert_can_dispatch(agent_name, store.state)

    # audit: record the dispatch attempt (§7, §9.2)
    _log(problem_dir, {
        "ts": int(time.time()),
        "event": "dispatch",
        "agent": agent_name,
        "state": store.state.value,
        "payload_keys": sorted(payload.keys()),
    })

    result = runner(agent_name, payload)

    _log(problem_dir, {
        "ts": int(time.time()),
        "event": "dispatch_complete",
        "agent": agent_name,
        "state": store.state.value,
    })
    return result


def _log(problem_dir: Path, entry: dict) -> None:
    """Append one JSON line to the problem's audit trail."""
    import json
    log_path = problem_dir / "audit.log.jsonl"
    with log_path.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")
