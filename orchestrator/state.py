"""Pipeline state machine with a per-problem `state.json` audit trail (§7).

Every transition is appended to history with a timestamp and a diff summary, so
`state.json` is a full audit log, not just the current state. The state file
lives at `<problem_dir>/state.json`.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class State(str, Enum):
    # Stage 0 — the hard checkpoint (§6)
    DRAFTING_SPEC = "DRAFTING_SPEC"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    # Generation + local verification (§10)
    GENERATING_ARTIFACTS = "GENERATING_ARTIFACTS"
    LOCAL_SELF_CHECK = "LOCAL_SELF_CHECK"
    # Tab-by-tab upload + commit (§11)
    UPLOADING_STATEMENT = "UPLOADING_STATEMENT"
    UPLOADING_VALIDATOR = "UPLOADING_VALIDATOR"
    UPLOADING_CHECKER = "UPLOADING_CHECKER"
    UPLOADING_TESTS = "UPLOADING_TESTS"
    UPLOADING_SOLUTIONS = "UPLOADING_SOLUTIONS"
    SETTING_LIMITS = "SETTING_LIMITS"
    # Judge loop (§15)
    RUNNING_INVOCATIONS = "RUNNING_INVOCATIONS"
    FINAL_COMMIT = "FINAL_COMMIT"
    BUILDING_PACKAGE = "BUILDING_PACKAGE"
    LINK_READY = "LINK_READY"
    # Terminal escalation
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"


# Allowed forward edges (§7). ESCALATE_TO_HUMAN is reachable from any active
# state (handled specially in `transition`), so it is not enumerated per-state.
_TRANSITIONS: dict[State, set[State]] = {
    State.DRAFTING_SPEC: {State.AWAITING_APPROVAL},
    # revision requests loop back to drafting; approval moves forward
    State.AWAITING_APPROVAL: {State.APPROVED, State.DRAFTING_SPEC},
    State.APPROVED: {State.GENERATING_ARTIFACTS},
    State.GENERATING_ARTIFACTS: {State.LOCAL_SELF_CHECK},
    # local self-check can bounce back for targeted regeneration (§10)
    State.LOCAL_SELF_CHECK: {State.GENERATING_ARTIFACTS, State.UPLOADING_STATEMENT},
    State.UPLOADING_STATEMENT: {State.UPLOADING_VALIDATOR},
    State.UPLOADING_VALIDATOR: {State.UPLOADING_CHECKER},
    State.UPLOADING_CHECKER: {State.UPLOADING_TESTS},
    State.UPLOADING_TESTS: {State.UPLOADING_SOLUTIONS},
    State.UPLOADING_SOLUTIONS: {State.SETTING_LIMITS},
    State.SETTING_LIMITS: {State.RUNNING_INVOCATIONS},
    # invocation loop: clean → final; issues → re-upload the responsible tab
    State.RUNNING_INVOCATIONS: {
        State.FINAL_COMMIT,
        State.UPLOADING_STATEMENT, State.UPLOADING_VALIDATOR,
        State.UPLOADING_CHECKER, State.UPLOADING_TESTS,
        State.UPLOADING_SOLUTIONS, State.SETTING_LIMITS,
    },
    State.FINAL_COMMIT: {State.BUILDING_PACKAGE},
    State.BUILDING_PACKAGE: {State.LINK_READY},
    State.LINK_READY: set(),
    State.ESCALATE_TO_HUMAN: set(),
}


class InvalidTransition(RuntimeError):
    pass


class UnapprovedUploadError(RuntimeError):
    """Raised by PolygonUploader itself (not just Orchestrator) when a live
    Polygon call is attempted against a problem whose state.json audit trail
    shows no genuine AWAITING_APPROVAL -> APPROVED transition. See
    StateStore.has_transitioned_through and orchestrator/uploader.py."""


@dataclass
class HistoryEntry:
    ts: int
    from_state: str
    to_state: str
    summary: str

    def to_dict(self) -> dict:
        return {
            "ts": self.ts, "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.ts)),
            "from": self.from_state, "to": self.to_state, "summary": self.summary,
        }


@dataclass
class StateStore:
    """Reads/writes `<problem_dir>/state.json`. Single source of pipeline state."""
    problem_dir: Path
    state: State = State.DRAFTING_SPEC
    problem_id: int | None = None
    retry_count: int = 0
    history: list[HistoryEntry] = field(default_factory=list)

    @property
    def path(self) -> Path:
        return self.problem_dir / "state.json"

    # ---------------------------------------------------------------- #
    @classmethod
    def init(cls, problem_dir: Path, name: str) -> "StateStore":
        problem_dir.mkdir(parents=True, exist_ok=True)
        store = cls(problem_dir=problem_dir)
        store.history.append(HistoryEntry(
            int(time.time()), "-", State.DRAFTING_SPEC.value,
            f"initialized pipeline for '{name}'"))
        store._write()
        return store

    @classmethod
    def load(cls, problem_dir: Path) -> "StateStore":
        data = json.loads((problem_dir / "state.json").read_text())
        return cls(
            problem_dir=problem_dir,
            state=State(data["state"]),
            problem_id=data.get("problem_id"),
            retry_count=data.get("retry_count", 0),
            history=[HistoryEntry(h["ts"], h["from"], h["to"], h["summary"])
                     for h in data.get("history", [])],
        )

    # ---------------------------------------------------------------- #
    def transition(self, to: State, summary: str, *, allow_escalate: bool = True) -> None:
        if to == State.ESCALATE_TO_HUMAN and allow_escalate:
            pass  # escalation is always reachable from any active state
        elif to not in _TRANSITIONS.get(self.state, set()):
            raise InvalidTransition(
                f"illegal transition {self.state.value} → {to.value}")
        self.history.append(HistoryEntry(
            int(time.time()), self.state.value, to.value, summary))
        self.state = to
        self._write()

    def has_transitioned_through(self, frm: State, to: State) -> bool:
        """True iff the AUDIT TRAIL (not just the current `state` value)
        contains a legitimate from->to transition record.

        This exists specifically to detect state forged by direct attribute
        assignment (`store.state = X; store._write()`) instead of going
        through `transition()` — that pattern skips `history.append()`
        entirely, so a forged jump into e.g. GENERATING_ARTIFACTS leaves NO
        corresponding history entry, while a genuine `approve()` call always
        does. Live-side-effecting calls (Orchestrator.upload/finalize) check
        this before touching Polygon, so hand-forging `state.json` to skip
        the approval gate no longer silently works even if the caller bypasses
        Orchestrator.approve()/generate() entirely and drives StateStore
        directly. This is NOT tamper-proof against a determined attacker who
        also fabricates matching history entries — no in-process check can be
        — but it closes the specific, observed failure mode of forging
        `state` without bothering to forge history too.
        """
        return any(h.from_state == frm.value and h.to_state == to.value
                  for h in self.history)

    def bump_retry(self) -> int:
        self.retry_count += 1
        self._write()
        return self.retry_count

    def _write(self) -> None:
        self.path.write_text(json.dumps({
            "state": self.state.value,
            "problem_id": self.problem_id,
            "retry_count": self.retry_count,
            "history": [h.to_dict() for h in self.history],
        }, indent=2))
