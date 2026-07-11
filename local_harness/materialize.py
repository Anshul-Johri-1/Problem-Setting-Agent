"""Materialize the test set into tests/ from samples + script.txt (§12).

samples/*.txt are copied verbatim first (in filename order), then each line of
script.txt is executed as "<generator> <args...>", its stdout captured as the
next test. Generators must be compiled first (compile_all). Produces
tests/001, tests/002, ... and returns an ordered list of (index, path, source).
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path

from ._exec import run
from .problem import Problem


@dataclass
class MaterializedTest:
    index: int
    path: Path
    source: str  # "sample:<file>" or the script line


def materialize(problem_dir: Path) -> tuple[bool, list[MaterializedTest], str]:
    p = Problem.load(problem_dir)
    p.tests_dir.mkdir(exist_ok=True)
    for old in p.tests_dir.glob("*"):
        old.unlink()

    tests: list[MaterializedTest] = []
    idx = 0
    log: list[str] = []

    # 1. samples verbatim
    samples_dir = p.dir / "samples"
    if samples_dir.exists():
        for sample in sorted(samples_dir.glob("*.txt")):
            idx += 1
            dest = p.tests_dir / f"{idx:03d}"
            dest.write_bytes(sample.read_bytes())
            tests.append(MaterializedTest(idx, dest, f"sample:{sample.name}"))
            log.append(f"  {idx:03d} ← {sample.name}")

    # 2. script-driven generation
    script = p.dir / "script.txt"
    if script.exists():
        for raw in script.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = shlex.split(line)
            gen_name, args = parts[0], parts[1:]
            gen_bin = p.build_dir / Path(gen_name).stem
            if not gen_bin.exists():
                return False, tests, f"generator binary missing: {gen_name} (compile first)"
            res = run([str(gen_bin), *args], timeout_ms=10000)
            if res.exit_code != 0:
                return False, tests, f"generator failed: {line}\n{res.stderr[:300]}"
            idx += 1
            dest = p.tests_dir / f"{idx:03d}"
            dest.write_text(res.stdout)
            tests.append(MaterializedTest(idx, dest, line))
            log.append(f"  {idx:03d} ← {line}")

    ok = len(tests) > 0
    header = f"materialize: {'PASS' if ok else 'FAIL'} ({len(tests)} tests)"
    return ok, tests, header + "\n" + "\n".join(log)
