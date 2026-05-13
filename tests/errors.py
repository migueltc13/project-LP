#!/usr/bin/env python3

from pathlib import Path
import subprocess
import sys


C = {
    "red": "\033[91m",
    "grn": "\033[92m",
    "prp": "\033[95m",
    "yel": "\033[93m",
    "rst": "\033[0m",
}

ROOT = Path(__file__).resolve().parents[1]
ERROR_ROOT = ROOT / "examples" / "errors"


def run_parser(filepath: Path) -> subprocess.CompletedProcess:
    fmt = "free" if filepath.suffix == ".f90" else "fixed"

    return subprocess.run(
        [sys.executable, "src/parser.py", "--format", fmt],
        input=filepath.read_text(),
        text=True,
        stdout=subprocess.PIPE,
        cwd=ROOT,
    )


if __name__ == "__main__":
    error_files = sorted(ERROR_ROOT.rglob("*.f")) + sorted(ERROR_ROOT.rglob("*.f90"))

    if not error_files:
        print("No error files found in examples/errors/")
        raise SystemExit(1)

    matched_errors = 0
    ignored_successes = 0

    for filepath in error_files:
        relative_path = filepath.relative_to(ROOT)

        print(f"\n{C['prp']}== {relative_path} =={C['rst']}", file=sys.stderr, flush=True)

        result = run_parser(filepath)

        if result.returncode == 0:
            ignored_successes += 1
            print(f"  {C['yel']}ignored{C['rst']}: parser succeeded for this fixture", file=sys.stderr, flush=True)
        else:
            matched_errors += 1

    print(
        f"\n{C['grn']}Matched parser errors for {matched_errors} files{C['rst']}"
        f"; {ignored_successes} fixture(s) were ignored."
        ,
        file=sys.stderr,
        flush=True,
    )

    raise SystemExit(0)
