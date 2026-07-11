"""Uploader abstraction over the Polygon tab-by-tab upload (§9, §11).

The orchestrator drives an `Uploader` so the upload sequence is testable without
touching Polygon. `PolygonUploader` is the real one (wraps `polygon_client`);
`RecordingUploader` records calls for tests and dry runs.

`PolygonUploader` REQUIRES a `problem_dir` and independently re-verifies a
genuine approval on EVERY call, not just once at construction and not just
when driven through `Orchestrator.upload()`. This is deliberate: relying on
"the caller already checked" is exactly the assumption that broke once
already — code with direct access to this class can otherwise skip
Orchestrator entirely and drive it by hand. See orchestrator/state.py's
`StateStore.has_transitioned_through` for what "genuine" means here, and
`.claude/GUARDRAILS.md` for the broader rule this backs: the ONLY sanctioned
way to construct a real PolygonUploader is `orchestrator/cli.py`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class Uploader:
    def create(self, name: str) -> dict: raise NotImplementedError
    def update_working_copy(self, pid: int) -> None: raise NotImplementedError
    def save_statement(self, pid: int, **fields) -> None: raise NotImplementedError
    def save_validator(self, pid: int, source: str) -> None: raise NotImplementedError
    def save_validator_test(self, pid: int, index: int, test_input: str, verdict: str) -> None: raise NotImplementedError
    def set_checker(self, pid: int, checker: str | dict) -> None: raise NotImplementedError
    def save_generator(self, pid: int, name: str, source: str) -> None: raise NotImplementedError
    def save_script(self, pid: int, source: str) -> None: raise NotImplementedError
    def save_test(self, pid: int, index: int, test_input: str, sample: bool) -> None: raise NotImplementedError
    def save_solution(self, pid: int, name: str, source: str, tag: str) -> None: raise NotImplementedError
    def set_limits(self, pid: int, time_ms: int, memory_mb: int) -> None: raise NotImplementedError
    def save_tags(self, pid: int, tags: list[str]) -> None: raise NotImplementedError
    def commit(self, pid: int, message: str) -> None: raise NotImplementedError
    def build_package(self, pid: int) -> str: raise NotImplementedError  # returns final state


# --------------------------------------------------------------------------- #
class PolygonUploader(Uploader):
    def __init__(self, session, problem_dir: Path):
        """`problem_dir` is REQUIRED (not optional, no default) — every
        mutating call re-verifies that this exact directory's state.json
        shows a genuine approval before touching Polygon. There is no
        constructor path that skips this."""
        from polygon_client import methods as m
        self.s = session
        self.m = m
        self.problem_dir = Path(problem_dir)

    def _guard(self) -> None:
        from .state import StateStore, State, UnapprovedUploadError
        store = StateStore.load(self.problem_dir)
        if not store.has_transitioned_through(State.AWAITING_APPROVAL, State.APPROVED):
            raise UnapprovedUploadError(
                f"REFUSING live Polygon call: {self.problem_dir}/state.json's "
                f"audit trail contains no genuine AWAITING_APPROVAL → APPROVED "
                f"transition. This is not a false alarm — either this problem "
                f"was never actually approved by a human, or something "
                f"hand-forged state.json instead of going through "
                f"orchestrator.approve(). The sanctioned way to run anything "
                f"real is `python3 -m orchestrator.cli finish <name>`, which "
                f"performs this same check before doing anything."
            )

    def create(self, name):
        self._guard()
        return self.m.create_problem(self.s, name)

    def update_working_copy(self, pid):
        self._guard()
        self.m.update_working_copy(self.s, pid)

    def save_statement(self, pid, **fields):
        self._guard()
        self.m.save_statement(self.s, pid, **fields)

    def save_validator(self, pid, source):
        self._guard()
        self.m.save_file(self.s, pid, type_="source", name="validator.cpp", source=source)
        self.m.set_validator(self.s, pid, "validator.cpp")

    def save_validator_test(self, pid, index, test_input, verdict):
        self._guard()
        self.m.save_validator_test(self.s, pid, index, test_input, verdict)

    def set_checker(self, pid, checker):
        self._guard()
        if isinstance(checker, str):
            self.m.set_checker(self.s, pid, checker)
        else:  # custom
            name = checker["custom"]
            self.m.save_file(self.s, pid, type_="source", name=name, source=checker["source"])
            self.m.set_checker(self.s, pid, name)

    def save_generator(self, pid, name, source):
        self._guard()
        self.m.save_file(self.s, pid, type_="source", name=name, source=source)

    def save_script(self, pid, source):
        self._guard()
        self.m.save_script(self.s, pid, source)

    def save_test(self, pid, index, test_input, sample):
        self._guard()
        self.m.save_test(self.s, pid, "tests", index, test_input, use_in_statements=sample)

    def save_solution(self, pid, name, source, tag):
        self._guard()
        self.m.save_solution(self.s, pid, name, source, tag)

    def set_limits(self, pid, time_ms, memory_mb):
        self._guard()
        self.m.update_info(self.s, pid, timeLimit=time_ms, memoryLimit=memory_mb)

    def save_tags(self, pid, tags):
        self._guard()
        if tags:
            self.m.save_tags(self.s, pid, ", ".join(tags))

    def commit(self, pid, message):
        self._guard()
        self.m.commit_changes(self.s, pid, message)

    def build_package(self, pid):
        self._guard()
        self.m.build_package(self.s, pid, full=True, verify=True)
        for _ in range(60):
            time.sleep(3)
            pkgs = self.m.packages(self.s, pid) or []
            if pkgs:
                newest = max(pkgs, key=lambda p: p.get("id", 0))
                if newest.get("state") in ("READY", "FAILED"):
                    return newest["state"]
        return "TIMEOUT"


# --------------------------------------------------------------------------- #
@dataclass
class RecordingUploader(Uploader):
    """Records every call; returns plausible values. For tests / dry runs.
    Intentionally NOT gated — it never touches real credentials or Polygon,
    so there's nothing to protect; gating it would only slow down tests."""
    owner: str = "test_owner"
    calls: list[tuple[str, tuple]] = field(default_factory=list)
    _pid: int = 4242

    def _rec(self, name: str, *args):
        self.calls.append((name, args))

    def create(self, name):
        self._rec("create", name)
        return {"id": self._pid, "owner": self.owner, "name": name}

    def update_working_copy(self, pid): self._rec("update_working_copy", pid)
    def save_statement(self, pid, **f): self._rec("save_statement", pid, tuple(sorted(f)))
    def save_validator(self, pid, source): self._rec("save_validator", pid, len(source))
    def save_validator_test(self, pid, index, test_input, verdict): self._rec("save_validator_test", pid, index, verdict)
    def set_checker(self, pid, checker): self._rec("set_checker", pid, checker)
    def save_generator(self, pid, name, source): self._rec("save_generator", pid, name)
    def save_script(self, pid, source): self._rec("save_script", pid)
    def save_test(self, pid, index, test_input, sample): self._rec("save_test", pid, index, sample)
    def save_solution(self, pid, name, source, tag): self._rec("save_solution", pid, name, tag)
    def set_limits(self, pid, time_ms, memory_mb): self._rec("set_limits", pid, time_ms, memory_mb)
    def save_tags(self, pid, tags): self._rec("save_tags", pid, tuple(tags or ()))
    def commit(self, pid, message): self._rec("commit", pid, message)
    def build_package(self, pid): self._rec("build_package", pid); return "READY"

    def call_names(self) -> list[str]:
        return [c[0] for c in self.calls]
