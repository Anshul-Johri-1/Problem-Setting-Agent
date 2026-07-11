"""The orchestrator driver (§7) — connects spec-agent, local_harness, and the
Polygon uploader into one state-machine-governed pipeline.

Agent work (writing the spec, generating artifacts) is delegated to an injected
`runner(agent_name, payload) -> Any`, dispatched through the gate-checked
`dispatch()` so the approval guard (§1.1) holds structurally. In production the
runner wraps an LLM subagent; in tests it's a fixture-backed stub.

Upload is delegated to an injected `Uploader` (PolygonUploader in production,
RecordingUploader in tests). Local verification uses `local_harness`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Any

from .state import State, StateStore
from .gate import assert_can_dispatch
from .dispatch import dispatch
from .input_parse import CreateProblemInput
from .reviewer import classify, Classification
from .uploader import Uploader

from local_harness.problem import Problem
from local_harness.run import run_all
from local_harness.materialize import materialize
from polygon_client.invocations import LocalHarnessInvocations
from polygon_client.access import access_reminder

Runner = Callable[[str, dict], Any]


class PipelineHalt(RuntimeError):
    """Raised to stop the pipeline (escalation or the approval gate)."""


def _require_genuine_approval(store: StateStore) -> None:
    """Defense-in-depth for §1.1: `assert_can_dispatch` only protects calls
    that go through `dispatch()` (i.e. `generate()`). It does nothing to stop
    code with direct access to `StateStore`/`Uploader` from hand-forging
    `state.json` (`store.state = X; store._write()`, skipping `transition()`
    entirely) and then calling `upload()`/`finalize()` directly — which is a
    real, observed failure mode, not a hypothetical one. Every live,
    side-effecting call re-checks the AUDIT TRAIL itself, not just the current
    state value, before touching Polygon. See StateStore.has_transitioned_through.
    """
    if not store.has_transitioned_through(State.AWAITING_APPROVAL, State.APPROVED):
        raise PipelineHalt(
            "REFUSING to make live Polygon calls: state.json's history contains "
            "no genuine AWAITING_APPROVAL → APPROVED transition. Either this "
            "problem was never actually approved, or `state` was hand-forged "
            "(direct attribute assignment instead of orchestrator.approve()) "
            "rather than reached through the sanctioned dispatch path.")


def _dedup_solution_name(filename: str, seen: set[str]) -> str:
    """Return a Polygon-safe solution name with a base unique among `seen`.

    Polygon rejects two solutions whose names differ only by extension (verified
    live 2026-07-11). On collision, fold the extension into the base:
    `correct.py` → `correct_py.py`. Mutates `seen`.
    """
    stem, dot, ext = filename.rpartition(".")
    stem = stem or filename
    base, name = stem, filename
    if stem in seen:
        base = f"{stem}_{ext}"
        name = f"{base}.{ext}" if dot else base
    seen.add(base)
    return name


def _to_polygon_script(local_script: str, sample_count: int) -> str:
    """Translate the harness script format into Polygon's.

    Local:   `generator_edge --case=min`
    Polygon: `generator_edge --case=min > 2`   (index after the sample tests)

    Generators are referenced by name; each line must end with `> <testIndex>`.
    Verified live 2026-07-11 (§18 item 6).
    """
    out_lines = []
    idx = sample_count
    for raw in local_script.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        idx += 1
        out_lines.append(f"{line} > {idx}")
    return "\n".join(out_lines) + "\n"


@dataclass
class Orchestrator:
    problems_root: Path
    runner: Runner
    uploader: Uploader
    create_input: CreateProblemInput | None = None
    retry_cap: int = 5
    _local_matrix: dict = None  # type: ignore  # verdict matrix from local_check

    # ------------------------------------------------------------------ #
    @property
    def problem_dir(self) -> Path:
        assert self.create_input is not None
        return self.problems_root / self.create_input.name

    def _store(self) -> StateStore:
        return StateStore.load(self.problem_dir)

    # --- Stage 0: spec + the hard gate (§6) --------------------------- #
    def start(self, create_input: CreateProblemInput) -> Path:
        self.create_input = create_input
        self.problem_dir.mkdir(parents=True, exist_ok=True)
        (self.problem_dir / "spec_input.json").write_text(
            json.dumps(create_input.__dict__, default=lambda o: o.__dict__, indent=2))
        store = StateStore.init(self.problem_dir, create_input.name)

        dispatch(self.problem_dir, "spec-agent",
                 {"create_input": create_input.__dict__}, self.runner)
        store.transition(State.AWAITING_APPROVAL, "spec drafted; awaiting human approval")
        return self.problem_dir / "PROBLEM_SPEC.md"

    def approve(self) -> None:
        self._store().transition(State.APPROVED, "human approved the spec")

    def request_revision(self, feedback: str) -> Path:
        store = self._store()
        store.transition(State.DRAFTING_SPEC, f"revision requested: {feedback[:80]}")
        dispatch(self.problem_dir, "spec-agent",
                 {"create_input": self.create_input.__dict__, "feedback": feedback},
                 self.runner)
        store.transition(State.AWAITING_APPROVAL, "spec revised; awaiting approval")
        return self.problem_dir / "PROBLEM_SPEC.md"

    # --- Generation + local self-check (§10) -------------------------- #
    def generate(self) -> None:
        store = self._store()
        # Structural gate: raises GateError if we are not post-approval.
        assert_can_dispatch("solutions-agent", store.state)
        store.transition(State.GENERATING_ARTIFACTS, "generating artifacts")
        # samples/*.txt is spec-derived DATA (the human's raw sample tests,
        # given verbatim), not agent judgment — the orchestrator materializes
        # it directly rather than leaving it as an undocumented, easy-to-miss
        # step for whichever generation agent happens to think of it.
        self._materialize_samples()
        for agent in ("statement-agent", "validator-agent", "checker-agent",
                      "solutions-agent", "generator-agent"):
            dispatch(self.problem_dir, agent,
                     {"spec_dir": str(self.problem_dir)}, self.runner)

    def _materialize_samples(self) -> None:
        """Write both the sample INPUT (samples/) and the human's stated
        expected OUTPUT (samples_expected/), so local_harness.judge can verify
        the intended solution actually reproduces what the human typed in the
        /create-problem prompt — the first thing every contestant reads, and
        nothing previously checked it against the real solution's behavior."""
        samples_dir = self.problem_dir / "samples"
        expected_dir = self.problem_dir / "samples_expected"
        samples_dir.mkdir(exist_ok=True)
        expected_dir.mkdir(exist_ok=True)
        for old in list(samples_dir.glob("*.txt")) + list(expected_dir.glob("*.txt")):
            old.unlink()
        for i, sample in enumerate(self.create_input.samples, start=1):
            name = f"sample-{i:02d}.txt"
            (samples_dir / name).write_text(sample.input)
            (expected_dir / name).write_text(sample.output)

    def local_check(self) -> Any:
        store = self._store()
        store.transition(State.LOCAL_SELF_CHECK, "running local self-check")
        report = run_all(self.problem_dir)
        self._local_matrix = report.matrix
        if not report.ok:
            store.transition(State.GENERATING_ARTIFACTS,
                             "local self-check RED; targeted regeneration needed")
        return report

    # --- Tab-by-tab upload (§11) -------------------------------------- #
    def upload(self) -> dict:
        store = self._store()
        _require_genuine_approval(store)
        p = Problem.load(self.problem_dir)

        created = self.uploader.create(p.name)
        store.problem_id = created["id"]
        store._write()
        self.uploader.update_working_copy(created["id"])
        pid = created["id"]

        # 1. statement
        store.transition(State.UPLOADING_STATEMENT, "uploading statement")
        self._upload_statement(pid)
        self.uploader.commit(pid, "Add problem statement")

        # 2. validator (+ validator tests on the Validator tab, §8.3/§11)
        store.transition(State.UPLOADING_VALIDATOR, "uploading validator")
        self.uploader.save_validator(pid, (p.dir / "validator.cpp").read_text())
        n_valid, n_invalid = self._upload_validator_tests(pid, p)
        self.uploader.commit(pid,
                             f"Add input validator (+{n_valid} valid / {n_invalid} invalid tests)")

        # 3. checker
        store.transition(State.UPLOADING_CHECKER, "uploading checker")
        self.uploader.set_checker(pid, p.checker)
        self.uploader.commit(pid, f"Use checker: {p.checker}")

        # 4. tests (generators + script + sample tests)
        store.transition(State.UPLOADING_TESTS, "uploading tests")
        n_gen = self._upload_tests(pid, p)
        self.uploader.commit(pid, f"Add test set ({n_gen} generators)")

        # 5. solutions. Polygon requires unique base names (extension-insensitive),
        #    so correct.cpp and correct.py collide — disambiguate on upload while
        #    keeping local filenames. Upload the main solution first so it keeps
        #    its clean name.
        store.transition(State.UPLOADING_SOLUTIONS, "uploading solutions")
        sols = p.solution_files()
        main = next((s for s in sols if s.name == p.main_solution), None)
        ordered = ([main] if main else []) + [s for s in sols if s is not main]
        seen: set[str] = set()
        n_sol = 0
        for sol in ordered:
            upload_name = _dedup_solution_name(sol.name, seen)
            tag = self._solution_tag(sol.name, p)
            self.uploader.save_solution(pid, upload_name, sol.read_text(), tag)
            n_sol += 1
        self.uploader.commit(pid, f"Add reference solutions ({n_sol} files)")

        # 6. limits + tags. Polygon enforces timeLimit >= 250ms (verified live);
        #    the local harness may use a tighter limit for brute separation.
        #    Tags/difficulty ride along here (simple metadata, like limits) so
        #    problem.saveTags — real, live-verified, previously never called —
        #    actually gets used instead of being dead functionality.
        store.transition(State.SETTING_LIMITS, "setting limits")
        self.uploader.set_limits(pid, max(250, p.time_limit_ms), p.memory_mb)
        self.uploader.save_tags(pid, p.tags)
        self.uploader.commit(pid, "Set time/memory limits" +
                             (f" and tags ({', '.join(p.tags)})" if p.tags else ""))

        return created

    def _solution_tag(self, filename: str, p: Problem) -> str:
        """Polygon solution tag, derived from the local verdict matrix when
        available so it always matches actual behavior (Polygon strictly
        enforces tags at package build). Mixed failing verdicts → 'RJ' (generic
        rejected). Falls back to the static meta/inference tag."""
        if filename == p.main_solution:
            return "MA"
        matrix = self._local_matrix or {}
        row = matrix.get(filename)
        if row:
            failing = {v for v in row.values() if v != "AC"}
            if not failing:
                return "OK"
            if len(failing) == 1:
                return next(iter(failing))  # WA / TL / RE / ML
            return "RJ"  # mixed failing verdicts — generic rejected
        return p.tag_for(filename)

    def _upload_validator_tests(self, pid: int, p: Problem) -> tuple[int, int]:
        """Upload validator tests to the Validator tab (§8.3): genuinely-valid
        inputs as VALID, the validator-agent's malformed corpus as INVALID
        (≥10 per org_defaults).

        Polygon's saveValidatorTest trims the trailing newline off any input
        uploaded this way. A validator using a bare `inf.readEoln()` on its
        last line will reject the trimmed VALID test and fail the package
        build ("Validator test #N got INVALID, but VALID expected") — the fix
        is guarding ONLY that last `readEoln()` with
        `if (!inf.eof()) inf.readEoln();` in the validator itself (see
        tutorials/validator.md). `local_harness.validator_stress` already
        checks every validator_valid/ candidate BOTH raw and trimmed as part of
        the local self-check gate (§10), so by the time upload() runs (only
        after a green local_check), every candidate here is already known to
        survive Polygon's trim — this is not re-validated here, just uploaded.

        VALID source: validator_valid/ if present and non-empty, else the
        sample tests (backward-compatible fallback for older problems that
        predate validator_valid/). Empty inputs are never uploaded (Polygon
        rejects an empty testInput)."""
        idx = 0
        n_valid = 0
        valid_files = sorted(p.valid_dir.glob("*.txt")) if p.valid_dir.exists() else []
        valid_files = [vf for vf in valid_files if vf.read_text() != ""]
        if not valid_files:
            samples_dir = p.dir / "samples"
            if samples_dir.exists():
                valid_files = [s for s in sorted(samples_dir.glob("*.txt"))
                               if s.read_text() != ""]
        for vf in valid_files:
            idx += 1
            n_valid += 1
            self.uploader.save_validator_test(pid, idx, vf.read_text(), "VALID")

        malformed = sorted(p.stress_dir.glob("*.txt")) if p.stress_dir.exists() else []
        nonempty = [mf for mf in malformed if mf.read_text() != ""]
        if len(nonempty) < 10:
            raise PipelineHalt(
                f"only {len(nonempty)} non-empty malformed validator tests "
                f"(need ≥10 per org_defaults). validator-agent must produce more.")
        n_invalid = 0
        for mf in nonempty:
            idx += 1
            n_invalid += 1
            self.uploader.save_validator_test(pid, idx, mf.read_text(), "INVALID")
        return n_valid, n_invalid

    def _upload_statement(self, pid: int) -> None:
        sj = self.problem_dir / "statement.json"
        if sj.exists():
            fields = json.loads(sj.read_text())
        else:  # fall back to the create-problem input
            ci = self.create_input
            fields = {"name": ci.name, "legend": ci.statement,
                      "input_": ci.constraints, "output": "", "notes": ""}
        self.uploader.save_statement(pid, **fields)

    def _upload_tests(self, pid: int, p: Problem) -> int:
        # 1. sample tests as manual tests, indices 1..k, flagged for statements
        samples_dir = p.dir / "samples"
        samples = sorted(samples_dir.glob("*.txt")) if samples_dir.exists() else []
        for i, sample in enumerate(samples, start=1):
            self.uploader.save_test(pid, i, sample.read_text(), sample=True)

        # 2. generator sources
        n_gen = 0
        if p.generators_dir.exists():
            for gen in sorted(p.generators_dir.glob("*.cpp")):
                self.uploader.save_generator(pid, gen.name, gen.read_text())
                n_gen += 1

        # 3. translate the local script into Polygon format: each line references
        #    a generator by name and MUST end with '> <testIndex>'. Script tests
        #    are numbered after the k sample tests.
        script = p.dir / "script.txt"
        if script.exists():
            self.uploader.save_script(pid, _to_polygon_script(script.read_text(), len(samples)))
        return n_gen

    # --- Invocation loop (§15) ---------------------------------------- #
    def run_invocations(self) -> Classification:
        store = self._store()
        store.transition(State.RUNNING_INVOCATIONS, "running invocations")
        backend = LocalHarnessInvocations(problem_dir=self.problem_dir)
        run_id = backend.run(store.problem_id or 0)
        vm = backend.results(store.problem_id or 0, run_id)
        result = classify(vm.results)
        if result.escalate:
            store.transition(State.ESCALATE_TO_HUMAN, result.escalate_reason)
            raise PipelineHalt(result.escalate_reason)
        return result

    # --- Finalize (§16, §17) ------------------------------------------ #
    def finalize(self, created: dict) -> str:
        store = self._store()
        _require_genuine_approval(store)
        store.transition(State.FINAL_COMMIT, "all checks clean; final commit")
        self.uploader.commit(store.problem_id, "Finalize: all checks passing")
        store.transition(State.BUILDING_PACKAGE, "building package")
        state = self.uploader.build_package(store.problem_id)
        if state != "READY":
            store.transition(State.ESCALATE_TO_HUMAN, f"package build {state}")
            raise PipelineHalt(f"package build ended {state}")
        store.transition(State.LINK_READY, "package READY; link ready")
        return self._final_output(created)

    def _final_output(self, created: dict) -> str:
        from polygon_client.methods import problem_url
        link = problem_url(created["owner"], created["name"])
        reminder = access_reminder(created["owner"], created["name"])
        out = f"✅ Problem ready: {created['name']}\n\nPolygon: {link}"
        if reminder:
            out += f"\n\n{reminder}"
        return out

    # --- Convenience: post-approval autonomous run -------------------- #
    def run_after_approval(self) -> str:
        report = self.local_check()
        if not report.ok:
            raise PipelineHalt("local self-check RED:\n" + report.text())
        created = self.upload()
        self.run_invocations()
        return self.finalize(created)
