"""Problem directory layout contract for the local harness (§10).

A problem lives in a directory with:

    meta.json              {name, time_limit_ms, memory_mb, checker, main_solution}
    validator.cpp
    generators/*.cpp       flag/argv-driven generators
    script.txt             one line per generated test: "<gen> <args...>"
    samples/*.txt          optional verbatim sample inputs (sample-01.txt, ...)
    solutions/*.{py,cpp}   correct.*, brute.*, WA*.*
    validator_stress/*.txt >=10 malformed inputs (must all be rejected)
    tests/                 materialized inputs (built by materialize.py)
    _build/                harness scratch: compiled binaries, run outputs

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
        )

    def tag_for(self, filename: str) -> str:
        """Polygon solution tag for a file. Explicit meta.solution_tags wins;
        otherwise infer from the filename."""
        if self.solution_tags and filename in self.solution_tags:
            return self.solution_tags[filename]
        if filename == self.main_solution:
            return "MA"
        low = filename.lower()
        if low.startswith("correct"):
            return "OK"
        if low.startswith("brute"):
            return "TL"
        if "rte" in low or "re." in low:
            return "RE"
        return "WA"

    # --- standard paths ---
    @property
    def build_dir(self) -> Path:
        d = self.dir / "_build"
        d.mkdir(exist_ok=True)
        return d

    @property
    def tests_dir(self) -> Path:
        return self.dir / "tests"

    @property
    def solutions_dir(self) -> Path:
        return self.dir / "solutions"

    @property
    def generators_dir(self) -> Path:
        return self.dir / "generators"

    @property
    def stress_dir(self) -> Path:
        return self.dir / "validator_stress"

    @property
    def valid_dir(self) -> Path:
        return self.dir / "validator_valid"

    def solution_files(self) -> list[Path]:
        if not self.solutions_dir.exists():
            return []
        return sorted(p for p in self.solutions_dir.iterdir()
                      if p.suffix in (".py", ".cpp"))

    def cpp_sources(self) -> list[Path]:
        """Every C++ file the harness must compile clean."""
        out: list[Path] = []
        if (self.dir / "validator.cpp").exists():
            out.append(self.dir / "validator.cpp")
        if isinstance(self.checker, dict) and "custom" in self.checker:
            out.append(self.dir / self.checker["custom"])
        out += sorted(self.generators_dir.glob("*.cpp")) if self.generators_dir.exists() else []
        out += [p for p in self.solution_files() if p.suffix == ".cpp"]
        return out

    def is_standard_checker(self) -> bool:
        return isinstance(self.checker, str)

    def standard_checker_stem(self) -> str:
        # "std::ncmp.cpp" -> "ncmp"
        assert self.is_standard_checker()
        return self.checker.split("::", 1)[1].removesuffix(".cpp")  # type: ignore
