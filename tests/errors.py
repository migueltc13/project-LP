#!/usr/bin/env python3

from utils.descriptions import DESCRIPTIONS
from pathlib import Path
from utils.utils import C
import shutil
import subprocess
import argparse
import sys
import re


ROOT = Path(__file__).resolve().parents[1]
ERROR_ROOT = ROOT / "examples" / "errors"



# ============================================================
# Helpers
# ============================================================

def run_parser(filepath: Path) -> subprocess.CompletedProcess:
    fmt = "free" if filepath.suffix == ".f90" else "fixed"

    return subprocess.run(
        [sys.executable, "src/parser.py", "--format", fmt],
        input=filepath.read_text(),
        text=True,
        capture_output=True,
        cwd=ROOT,
    )


def colorize_diagnostics(text: str) -> str:
    lines = []
    severity = None

    for line in text.splitlines():
        if line.startswith("error:"):
            message = line[len("error:"):].lstrip()
            severity = "error"
            lines.append(
                f"{C['red']}{C['bld']}error{C['rst']}: "
                f"{C['bld']}{message}{C['rst']}"
            )
        elif line.startswith("warning:"):
            message = line[len("warning:"):].lstrip()
            severity = "warning"
            lines.append(
                f"{C['yel']}{C['bld']}warning{C['rst']}: "
                f"{C['bld']}{message}{C['rst']}"
            )
        elif line.lstrip().startswith("-->"):
            match = re.match(r"^(\s*)(-->)(.*)$", line)

            if match is not None:
                lines.append(
                    f"{match.group(1)}{C['blu']}{match.group(2)}{C['rst']}"
                    f"{match.group(3)}"
                )
            else:
                lines.append(line)
        elif line.lstrip().startswith("= hint:"):
            match = re.match(r"^(\s*)(= hint:)(.*)$", line)

            if match is not None:
                lines.append(
                    f"{match.group(1)}{C['cyn']}{C['bld']}{match.group(2)}"
                    f"{C['rst']}{C['cyn']}{match.group(3)}{C['rst']}"
                )
            else:
                lines.append(line)
        elif severity in {"error", "warning"}:
            match = re.match(r"^(\s*\|\s*)(\^+)(\s*)$", line)

            if match is not None:
                color = C['red'] if severity == "error" else C['yel']
                lines.append(
                    f"{match.group(1)}{color}{C['bld']}{match.group(2)}"
                    f"{C['rst']}{match.group(3)}"
                )
            else:
                lines.append(line)
        else:
            lines.append(line)

        if line.strip() == "":
            severity = None

    return "\n".join(lines)


def program_preview_command(filepath: Path) -> list[str]:
    bat = shutil.which("bat") or shutil.which("batcat")

    if bat is not None:
        return [
            bat,
            "--style=numbers",
            "--color=always",
            "--paging=never",
            str(filepath),
        ]

    return ["cat", str(filepath)]


def section(title: str):
    print(
        f"\n{C['cyn']}════════════════════════════════════════════════════════════{C['rst']}"
    )
    print(f"{C['cyn']} {title}{C['rst']}")
    print(
        f"{C['cyn']}════════════════════════════════════════════════════════════{C['rst']}"
    )


def print_program(filepath: Path):
    if not VERBOSE:
        return

    print(f"\n{C['blu']}Program:{C['rst']}")

    preview = subprocess.run(
        program_preview_command(filepath),
        text=True,
        capture_output=True,
        cwd=ROOT,
    )

    print(preview.stdout.rstrip())


def print_output(result: subprocess.CompletedProcess):
    if not VERBOSE:
        return

    print(f"\n{C['blu']}Parser output:{C['rst']}")

    output = result.stdout.strip()
    errors = result.stderr.strip()

    if output:
        print(output)

    if errors:
        print(colorize_diagnostics(errors))

    if not output and not errors:
        print(f"{C['gry']}<no output>{C['rst']}")


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    VERBOSE = args.verbose

    sections = [
        ("LEXICAL ERRORS", ERROR_ROOT / "lexical"),
        ("SYNTAX ERRORS", ERROR_ROOT / "syntax"),
        ("SEMANTIC ERRORS", ERROR_ROOT / "semantic"),
        ("TYPE SEMANTIC ERRORS", ERROR_ROOT / "semantic" / "types"),
        ("FUNCTION SEMANTIC ERRORS", ERROR_ROOT / "semantic" / "functions"),
    ]

    total_passed = 0
    total_failed = 0

    for section_name, section_path in sections:

        section(section_name)

        error_files = (
            sorted(section_path.glob("*.f"))
            + sorted(section_path.glob("*.f90"))
        )

        if not error_files:
            print(f"{C['yel']}No files found.{C['rst']}")
            continue

        for filepath in error_files:

            relative_path = filepath.relative_to(ROOT)

            print(
                f"\n{C['prp']}▶ {relative_path}{C['rst']}"
            )

            # ------------------------------------------------
            # Description
            # ------------------------------------------------

            desc = DESCRIPTIONS.get(
                filepath.name,
                "No description available."
            )

            print(f"\n{C['yel']}Test Description:{C['rst']}")
            print(f"  {desc}")

            # ------------------------------------------------
            # Program source
            # ------------------------------------------------

            print_program(filepath)

            # ------------------------------------------------
            # Run parser
            # ------------------------------------------------

            result = run_parser(filepath)

            # ------------------------------------------------
            # Output
            # ------------------------------------------------

            print_output(result)

            # ------------------------------------------------
            # Result
            # ------------------------------------------------

            if result.returncode != 0:
                total_passed += 1

                print(
                    f"\n{C['grn']}✓ PASS{C['rst']} "
                    f"(error correctly detected)"
                )

            else:
                total_failed += 1

                print(
                    f"\n{C['red']}✗ FAIL{C['rst']} "
                    f"(parser accepted invalid program)"
                )

    # ========================================================
    # Summary
    # ========================================================

    print(
        f"\n{C['cyn']}════════════════════════════════════════════════════════════{C['rst']}"
    )

    print(
        f"{C['grn']}Passed:{C['rst']} {total_passed}"
    )

    print(
        f"{C['red']}Failed:{C['rst']} {total_failed}"
    )

    print(
        f"{C['cyn']}════════════════════════════════════════════════════════════{C['rst']}"
    )

    raise SystemExit(0 if total_failed == 0 else 1)