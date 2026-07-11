"""Problem directory layout contract (§10).

A problem lives in a directory with:

    meta.json               {name, time_limit_ms, memory_mb, checker, main_solution,
                             solution_tags, tags, difficulty, too_slow_targets} —
                             written by spec-agent alongside PROBLEM_SPEC.md
                             (§8.1): the same numbers the human approved, in a
                             machine-readable form. `solution_tags` (filename
                             -> Polygon tag) is populated by solutions-agent
                             once the roster's actual filenames exist —
                             spec-agent cannot know them in advance.
    validator.cpp
    generators/*.cpp       flag/argv-driven generators
    script.txt             one line per generated test: "<gen> <args...>"
    samples/*.txt          optional verbatim sample inputs (sample-01.txt, ...)
    solutions/*.{py,cpp}   correct.*, brute.*, WA*.*
    validator_stress/*.txt >=10 malformed inputs (uploaded as INVALID Validator
                            tests; Polygon rejects them at build time)
    validator_valid/*.txt  genuinely-valid inputs (uploaded as VALID Validator
                            tests)

This is a pure data-loading module: it reads `meta.json` and lists files on
disk. It does not compile or execute anything — all correctness verification
happens on Polygon itself (see orchestrator/pipeline.py::build_and_verify).

`checker` is either a standard name like "std::ncmp.cpp" or {"custom": "checker.cpp"}.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Problem:
    dir: Path
    name: str
    time_limit_ms: int
    memory_mb: int
    checker: str | dict
    main_solution: str
    solution_tags: dict[str, str] = None  # type: ignore  # {filename: Polygon tag}
    tags: list[str] = None  # type: ignore  # topic tags, e.g. ["dp", "number theory"]
    difficulty: str | None = None  # free-form estimate, e.g. "CF 1400-1600"
    # Near-correct-but-too-slow submissions this problem's tests MUST reject
    # (§12.5). Each entry: {"name": "TLE1.cpp", "approach": "Dijkstra without the
    # stale-entry skip", "kills_with": "many-relaxations graph, not a line/path"}.
    # spec-agent names them; solutions-agent ships one TLE* file per entry,
    # tagged TL; generator-agent builds the adversarial test that forces it
    # over the limit; Polygon's buildPackage(verify=True) is the proof (a TL-
    # tagged solution that doesn't actually TLE fails the build). Empty is
    # legitimate only for problems with no plausible near-miss.
    too_slow_targets: list[dict] = None  # type: ignore

    @classmethod
    def load(cls, problem_dir: Path) -> "Problem":
        meta = json.loads((problem_dir / "meta.json").read_text())
        return cls(
            dir=problem_dir,
            name=meta["name"],
            time_limit_ms=int(meta.get("time_limit_ms", 1000)),
            memory_mb=int(meta.get("memory_mb", 256)),
            checker=meta.get("checker", "std::wcmp.cpp"),
            main_solution=meta["main_solution"],
            solution_tags=meta.get("solution_tags", {}),
            tags=meta.get("tags", []),
            difficulty=meta.get("difficulty"),
            too_slow_targets=meta.get("too_slow_targets", []),
        )

    def tag_for(self, filename: str) -> str:
        """Polygon solution tag for a file. Explicit meta.solution_tags wins —
        solutions-agent must declare it there since there is no local judge
        run to infer it from anymore; otherwise fall back to a filename
        heuristic (kept as a safety net, not the primary mechanism)."""
        if self.solution_tags and filename in self.solution_tags:
            return self.solution_tags[filename]
        if filename == self.main_solution:
            return "MA"
        low = filename.lower()
        if low.startswith("correct"):
            return "OK"
        if low.startswith("brute") or low.startswith("tle"):
            return "TL"
        if "rte" in low or "re." in low:
            return "RE"
        return "WA"

    # --- standard paths ---
    @property
    def solutions_dir(self) -> Path:
        return self.dir / "solutions"

    @property
    def generators_dir(self) -> Path:
        return self.dir / "generators"

    @property
    def stress_dir(self) -> Path:
        """Malformed-input corpus, uploaded as INVALID Validator-tab tests."""
        return self.dir / "validator_stress"

    @property
    def valid_dir(self) -> Path:
        """Genuinely-valid corpus, uploaded as VALID Validator-tab tests."""
        return self.dir / "validator_valid"

    def solution_files(self) -> list[Path]:
        if not self.solutions_dir.exists():
            return []
        return sorted(p for p in self.solutions_dir.iterdir()
                      if p.suffix in (".py", ".cpp"))

    def is_standard_checker(self) -> bool:
        return isinstance(self.checker, str)

    def standard_checker_stem(self) -> str:
        # "std::ncmp.cpp" -> "ncmp"
        assert self.is_standard_checker()
        return self.checker.split("::", 1)[1].removesuffix(".cpp")  # type: ignore
