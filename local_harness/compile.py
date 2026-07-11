"""Compile every C++ source with -Wall -Wextra -Werror; syntax-check Python (§10).

Zero tolerance for warnings. Returns (ok, report).
"""

from __future__ import annotations

import py_compile
from pathlib import Path

from ._exec import compile_cpp
from .problem import Problem


def compile_all(problem_dir: Path) -> tuple[bool, str]:
    p = Problem.load(problem_dir)
    lines: list[str] = []
    ok = True

    for src in p.cpp_sources():
        res = compile_cpp(src, p.build_dir / src.stem)
        if res.ok and not res.had_warnings:
            lines.append(f"  ✅ {src.name}")
        else:
            ok = False
            tag = "warnings" if res.had_warnings and res.ok else "errors"
            lines.append(f"  ❌ {src.name} ({tag})\n"
                         + "\n".join("      " + l for l in res.stderr.splitlines()[:8]))

    for src in p.solution_files():
        if src.suffix == ".py":
            try:
                py_compile.compile(str(src), doraise=True)
                lines.append(f"  ✅ {src.name} (py syntax)")
            except py_compile.PyCompileError as exc:
                ok = False
                lines.append(f"  ❌ {src.name}: {exc}")

    header = "compile: PASS" if ok else "compile: FAIL"
    return ok, header + "\n" + "\n".join(lines)


if __name__ == "__main__":
    import sys
    ok, report = compile_all(Path(sys.argv[1]))
    print(report)
    sys.exit(0 if ok else 1)
