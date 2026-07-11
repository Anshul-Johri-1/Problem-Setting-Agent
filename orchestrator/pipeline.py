"""The orchestrator driver (§7) — connects spec-agent, generation agents, and
the Polygon uploader into one state-machine-governed pipeline.

Agent work (writing the spec, generating artifacts) is delegated to an injected
`runner(agent_name, payload) -> Any`, dispatched through the gate-checked
`dispatch()` so the approval guard (§1.1) holds structurally. In production the
runner wraps an LLM subagent; in tests it's a fixture-backed stub.

Upload is delegated to an injected `Uploader` (PolygonUploader in production,
RecordingUploader in tests).

There is no local compilation or execution anywhere in this module. The one
verification gate is Polygon's own `buildPackage(verify=True)` — see
`build_and_verify()`. Polygon has no invocations API (§9.4, confirmed live:
`docs/POLYGON_API_FINDINGS.md`), so the only diagnostic on a failed build is
the free-text `comment` on `problem.packages`; `orchestrator/reviewer.py`
classifies it.
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
from .reviewer import classify_build_failure, Classification, BuildResult
from .uploader import Uploader
from .problem import Problem
from polygon_client.access import access_reminder

Runner = Callable[[str, dict], Any]


class PipelineHalt(RuntimeError):
    """Raised to stop the pipeline (escalation or the approval gate)."""


class BuildFailure(RuntimeError):
    """Raised when a Polygon build fails without implicating a reference
    solution (§1.5) — a non-escalating halt. The caller (orchestrator agent,
    via reviewer-agent) reads `.result` to decide which artifact to patch,
    then re-runs `finish`; `upload()` is idempotent so this is safe."""

    def __init__(self, result: BuildResult):
        self.result = result
        super().__init__(f"Polygon build {result.state}: {result.comment or '(no comment)'}")


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
    """Translate the local script format into Polygon's.

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

    # --- Generation (§10) ---------------------------------------------- #
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
        expected OUTPUT (samples_expected/), so `verify_samples()` can later
        confirm the MA solution's Polygon-generated answer actually
        reproduces what the human typed in the /create-problem prompt — the
        first thing every contestant reads."""
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

    # --- Tab-by-tab upload (§11) --------------------------------------- #
    def upload(self) -> dict:
        """Idempotent: safe to call again after a build failure + patch.

        `create()` only runs once (its result — id + owner — is persisted in
        `state.json`); every retry reuses the existing problem and just
        re-sends every tab. Re-sending unchanged tabs is a handful of cheap
        API calls, not local execution, and is far simpler/more robust than
        tracking exactly which tab a patch touched.
        """
        store = self._store()
        _require_genuine_approval(store)
        p = Problem.load(self.problem_dir)

        if store.problem_id is None:
            created = self.uploader.create(p.name)
            store.problem_id = created["id"]
            store.owner = created["owner"]
            store._write()
        pid = store.problem_id
        created = {"id": pid, "owner": store.owner, "name": p.name}
        self.uploader.update_working_copy(pid)

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
            tag = p.tag_for(sol.name)
            self.uploader.save_solution(pid, upload_name, sol.read_text(), tag)
            n_sol += 1
        self.uploader.commit(pid, f"Add reference solutions ({n_sol} files)")

        # 6. limits + tags. Polygon enforces timeLimit >= 250ms (verified live);
        #    tags/difficulty ride along here (simple metadata, like limits).
        store.transition(State.SETTING_LIMITS, "setting limits")
        self.uploader.set_limits(pid, max(250, p.time_limit_ms), p.memory_mb)
        self.uploader.save_tags(pid, p.tags)
        self.uploader.commit(pid, "Set time/memory limits" +
                             (f" and tags ({', '.join(p.tags)})" if p.tags else ""))

        return created

    def _upload_validator_tests(self, pid: int, p: Problem) -> tuple[int, int]:
        """Upload validator tests to the Validator tab (§8.3): genuinely-valid
        inputs as VALID, the validator-agent's malformed corpus as INVALID
        (≥10 per org_defaults). Polygon runs the real validator against every
        one of these at build time (§10) — that IS the verification; nothing
        pre-checks them locally first.

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

    # --- Build + verify (§15) — the one verification gate -------------- #
    def build_and_verify(self) -> BuildResult:
        """Trigger `buildPackage(full, verify=True)` and classify the result.

        On READY: transition SAMPLE_VERIFY-ward and return. On FAILED/TIMEOUT:
        `classify_build_failure` decides whether this implicates a reference
        solution (§1.5 — escalate, never auto-patch) or is a routable defect.
        A routable defect bumps the retry counter (escalating past
        `retry_cap`) and bounces back to GENERATING_ARTIFACTS for a targeted
        patch, then raises `BuildFailure` so the caller (orchestrator agent,
        via reviewer-agent reading `.result.comment`) knows to patch and
        re-run `finish` — `upload()` is idempotent, so that's always safe.
        """
        store = self._store()
        _require_genuine_approval(store)
        store.transition(State.FINAL_COMMIT, "all tabs uploaded; final commit")
        self.uploader.commit(store.problem_id, "Finalize: ready for build")
        store.transition(State.BUILDING_PACKAGE, "building package (verify=True)")

        p = Problem.load(self.problem_dir)
        state, comment = self.uploader.build_package(store.problem_id)
        result = BuildResult(state=state, comment=comment)

        if result.state == "READY":
            return result

        references = [s.name for s in p.solution_files() if p.tag_for(s.name) == "OK"]
        classification = classify_build_failure(result, p.main_solution, references)
        if classification.escalate:
            store.transition(State.ESCALATE_TO_HUMAN, classification.escalate_reason)
            raise PipelineHalt(classification.escalate_reason)

        retries = store.bump_retry()
        if retries > self.retry_cap:
            reason = (f"retry_cap ({self.retry_cap}) exhausted after {retries} build "
                      f"attempts; last failure: {result.comment or result.state}")
            store.transition(State.ESCALATE_TO_HUMAN, reason)
            raise PipelineHalt(reason)

        store.transition(State.GENERATING_ARTIFACTS,
                         f"Polygon build {result.state}; targeted patch needed "
                         f"(attempt {retries}/{self.retry_cap})")
        raise BuildFailure(result)

    # --- Sample verify (§16) — online, no local execution --------------- #
    def verify_samples(self) -> None:
        """Confirm the MA solution's Polygon-generated answer for each sample
        test matches the human's literal stated sample output. Pure API read
        (`problem.testAnswer`) + text diff — no local execution. A mismatch
        escalates exactly like a correct-solution failure (§1.5 spirit: never
        silently ship a sample that doesn't match what the human typed)."""
        store = self._store()
        _require_genuine_approval(store)
        store.transition(State.SAMPLE_VERIFY, "verifying sample outputs")

        expected_dir = self.problem_dir / "samples_expected"
        expected_files = sorted(expected_dir.glob("*.txt")) if expected_dir.exists() else []
        mismatches = []
        for i, exp in enumerate(expected_files, start=1):
            got = self.uploader.test_answer(store.problem_id, i)
            if got.split() != exp.read_text().split():
                mismatches.append(f"  sample {i} ({exp.name}): expected\n"
                                  f"    {exp.read_text()!r}\n  got (from Polygon's MA "
                                  f"solution)\n    {got!r}")
        if mismatches:
            reason = ("MA solution's Polygon-generated output disagrees with the "
                      "human's literal stated sample output — likely spec ambiguity. "
                      "Halting per §1.5 (never auto-patched):\n" + "\n".join(mismatches))
            store.transition(State.ESCALATE_TO_HUMAN, reason)
            raise PipelineHalt(reason)

    # --- Finalize (§16, §17) ------------------------------------------- #
    def finalize(self, created: dict) -> str:
        store = self._store()
        _require_genuine_approval(store)
        store.transition(State.LINK_READY, "package READY; samples verified; link ready")
        return self._final_output(created)

    def _final_output(self, created: dict) -> str:
        from polygon_client.methods import problem_url
        link = problem_url(created["owner"], created["name"])
        reminder = access_reminder(created["owner"], created["name"])
        out = f"✅ Problem ready: {created['name']}\n\nPolygon: {link}"
        if reminder:
            out += f"\n\n{reminder}"
        return out

    # --- Convenience: post-approval autonomous run ---------------------- #
    def run_after_approval(self) -> str:
        created = self.upload()
        self.build_and_verify()
        self.verify_samples()
        return self.finalize(created)
