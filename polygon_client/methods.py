"""Thin wrappers over confirmed Polygon API methods (§9.1).

Each wrapper is a one-liner over `PolygonSession.call`. They exist so agents can
call semantically-named tools and so idempotency/keyword-arg shape is
documented in one place. Every mutating call takes the problem's working copy
into account; the orchestrator is responsible for updateWorkingCopy /
commitChanges sequencing (§11).

Only methods confirmed present in the live API (cross-checked against polyman's
enumeration) are wrapped here. A dedicated invocations endpoint (running
solutions / reading a per-test verdict matrix) does NOT exist (§9.4, confirmed
live) — `build_package`+`packages` (verify=True, then poll for state+comment)
is the only live judge signal, consumed directly by
`orchestrator/pipeline.py::build_and_verify` and classified in
`orchestrator/reviewer.py`. Access-granting is also not exposed — see
access.py.
"""

from __future__ import annotations

from typing import Any

from .auth import PolygonSession


# --------------------------------------------------------------------------- #
# Problem lifecycle
# --------------------------------------------------------------------------- #
def create_problem(s: PolygonSession, name: str) -> dict[str, Any]:
    """problem.create → {id, name, owner, ...}. Name must be globally unique."""
    return s.call("problem.create", {"name": name})


def problem_info(s: PolygonSession, problem_id: int) -> dict[str, Any]:
    """problem.info → {timeLimit, memoryLimit, inputFile, outputFile,
    interactive, wellFormed}.

    NOTE (verified live 2026-07-11): contrary to spec §16, problem.info does
    NOT return owner or name — only limits/IO config. Owner + name come from
    the `problem.create` result (see `problem_url`). Kept for reading limits.
    """
    return s.call("problem.info", {"problemId": problem_id})


def problem_url(owner: str, name: str) -> str:
    """Construct the Polygon working link (§16).

    owner + name must come from the `problem.create` result (NOT problem.info).
    Polygon returns `owner` already lowercased; use it verbatim.
    """
    return f"https://polygon.codeforces.com/p/{owner}/{name}"


def update_info(s: PolygonSession, problem_id: int, **fields: Any) -> Any:
    """problem.updateInfo(timeLimit, memoryLimit, interactive, inputFile, ...)."""
    return s.call("problem.updateInfo", {"problemId": problem_id, **fields})


def update_working_copy(s: PolygonSession, problem_id: int) -> Any:
    return s.call("problem.updateWorkingCopy", {"problemId": problem_id})


def discard_working_copy(s: PolygonSession, problem_id: int) -> Any:
    return s.call("problem.discardWorkingCopy", {"problemId": problem_id})


def commit_changes(s: PolygonSession, problem_id: int, message: str,
                   minor: bool = False) -> Any:
    """problem.commitChanges. Per-tab commits (§11) each call this once."""
    return s.call("problem.commitChanges", {
        "problemId": problem_id, "message": message, "minorChanges": minor,
    })


# --------------------------------------------------------------------------- #
# Statement
# --------------------------------------------------------------------------- #
def save_statement(s: PolygonSession, problem_id: int, *, lang: str = "english",
                   legend: str = "", input_: str = "", output: str = "",
                   notes: str = "", name: str = "", scoring: str = "") -> Any:
    return s.call("problem.saveStatement", {
        "problemId": problem_id, "lang": lang, "legend": legend,
        "input": input_, "output": output, "notes": notes,
        "name": name, "scoring": scoring,
    })


# --------------------------------------------------------------------------- #
# Validator / Checker / Interactor
# --------------------------------------------------------------------------- #
def save_file(s: PolygonSession, problem_id: int, *, type_: str, name: str,
              source: str, source_type: str | None = None) -> Any:
    """problem.saveFile. type_ ∈ {'source','resource','aux'}; used for
    validator/checker/generator source uploads. source_type e.g. 'cpp.g++17'
    (Polygon usually auto-detects from the extension when omitted)."""
    params: dict[str, Any] = {
        "problemId": problem_id, "type": type_, "name": name, "file": source,
    }
    if source_type:
        params["sourceType"] = source_type
    return s.call("problem.saveFile", params)


def set_validator(s: PolygonSession, problem_id: int, filename: str) -> Any:
    return s.call("problem.setValidator", {"problemId": problem_id, "validator": filename})


def set_checker(s: PolygonSession, problem_id: int, filename: str) -> Any:
    """Accepts a standard checker filename (e.g. 'std::wcmp.cpp') directly.
    autoUpdate=false so Polygon doesn't silently swap the checker later."""
    return s.call("problem.setChecker", {
        "problemId": problem_id, "checker": filename, "autoUpdate": False,
    })


def set_interactor(s: PolygonSession, problem_id: int, filename: str) -> Any:
    return s.call("problem.setInteractor", {"problemId": problem_id, "interactor": filename})


# --------------------------------------------------------------------------- #
# Solutions
# --------------------------------------------------------------------------- #
def save_solution(s: PolygonSession, problem_id: int, name: str, source: str,
                  tag: str) -> Any:
    """problem.saveSolution. tag ∈ {MA, OK, RJ, TL, TO, WA, PE, ML, RE, ...}."""
    return s.call("problem.saveSolution", {
        "problemId": problem_id, "name": name, "file": source, "tag": tag,
    })


def solutions(s: PolygonSession, problem_id: int) -> Any:
    return s.call("problem.solutions", {"problemId": problem_id})


# --------------------------------------------------------------------------- #
# Tests / Generators / Script
# --------------------------------------------------------------------------- #
def save_script(s: PolygonSession, problem_id: int, source: str,
                testset: str = "tests") -> Any:
    return s.call("problem.saveScript", {
        "problemId": problem_id, "testset": testset, "source": source,
    })


def save_test(s: PolygonSession, problem_id: int, testset: str, index: int,
              test_input: str, *, use_in_statements: bool = False,
              description: str = "") -> Any:
    return s.call("problem.saveTest", {
        "problemId": problem_id, "testset": testset, "testIndex": index,
        "testInput": test_input, "testUseInStatements": use_in_statements,
        "testDescription": description,
    })


def tests(s: PolygonSession, problem_id: int, testset: str = "tests") -> Any:
    return s.call("problem.tests", {"problemId": problem_id, "testset": testset})


def save_validator_test(s: PolygonSession, problem_id: int, index: int,
                        test_input: str, verdict: str) -> Any:
    """problem.saveValidatorTest — adds a test to the Validator tab so it shows
    in the UI and runs on every commit. verdict ∈ {'VALID','INVALID'}."""
    assert verdict in ("VALID", "INVALID")
    return s.call("problem.saveValidatorTest", {
        "problemId": problem_id, "testIndex": index,
        "testInput": test_input, "testVerdict": verdict,
    })


# --------------------------------------------------------------------------- #
# Tags / Packages
# --------------------------------------------------------------------------- #
def save_tags(s: PolygonSession, problem_id: int, tags: str) -> Any:
    return s.call("problem.saveTags", {"problemId": problem_id, "tags": tags})


def build_package(s: PolygonSession, problem_id: int, *, full: bool = True,
                  verify: bool = True) -> Any:
    return s.call("problem.buildPackage", {
        "problemId": problem_id, "full": full, "verify": verify,
    })


def packages(s: PolygonSession, problem_id: int) -> Any:
    return s.call("problem.packages", {"problemId": problem_id})


def test_answer(s: PolygonSession, problem_id: int, index: int,
                testset: str = "tests") -> str:
    """problem.testAnswer — the answer Polygon generated for a test by running
    the MA solution (only meaningful after a build). Returns raw text (this
    endpoint is not a JSON envelope). Used post-build to confirm the MA
    solution reproduces the human's literal stated sample output — purely an
    API read + text diff, no local execution (see
    orchestrator/pipeline.py::verify_samples)."""
    raw = s.call("problem.testAnswer", {
        "problemId": problem_id, "testset": testset, "testIndex": index,
    }, raw=True)
    return raw.decode("utf-8")
