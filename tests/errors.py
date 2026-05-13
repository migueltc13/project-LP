#!/usr/bin/env python3

from pathlib import Path
import subprocess
import sys


C = {
    "red": "\033[91m",
    "grn": "\033[92m",
    "prp": "\033[95m",
    "yel": "\033[93m",
    "cyn": "\033[96m",
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


def section(title: str):
    print(
        f"\n{C['cyn']}══════════════════════════════════════════════════{C['rst']}",
        file=sys.stderr,
    )
    print(
        f"{C['cyn']} {title}{C['rst']}",
        file=sys.stderr,
    )
    print(
        f"{C['cyn']}══════════════════════════════════════════════════{C['rst']}",
        file=sys.stderr,
    )


if __name__ == "__main__":

    sections = [
        ("LEXICAL ERRORS", ERROR_ROOT / "lexical"),
        ("SEMANTIC ERRORS", ERROR_ROOT / "semantic"),
        ("SYNTAX ERRORS", ERROR_ROOT / "syntax"),
    ]

    total_matched = 0
    total_ignored = 0

    for section_name, section_path in sections:

        section(section_name)

        error_files = (
            sorted(section_path.glob("*.f"))
            + sorted(section_path.glob("*.f90"))
        )

        if not error_files:
            print(
                f"{C['yel']}No files found.{C['rst']}",
                file=sys.stderr,
                flush=True,
            )
            continue

        matched_errors = 0
        ignored_successes = 0

        for filepath in error_files:
            relative_path = filepath.relative_to(ROOT)

            print(
                f"\n{C['prp']}== {relative_path} =={C['rst']}",
                file=sys.stderr,
                flush=True,
            )

            result = run_parser(filepath)

            if result.returncode == 0:
                ignored_successes += 1

                print(
                    f"  {C['yel']}ignored{C['rst']}: parser succeeded for this fixture",
                    file=sys.stderr,
                    flush=True,
                )
            else:
                matched_errors += 1

        total_matched += matched_errors
        total_ignored += ignored_successes

        print(
            f"\n{C['grn']}Matched parser errors for {matched_errors} files{C['rst']}"
            f"; {ignored_successes} fixture(s) were ignored.",
            file=sys.stderr,
            flush=True,
        )

    print(
        f"\n{C['grn']}TOTAL:{C['rst']} "
        f"{total_matched} matched error file(s), "
        f"{total_ignored} ignored fixture(s).",
        file=sys.stderr,
        flush=True,
    )

    raise SystemExit(0)