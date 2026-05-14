#!/usr/bin/env python3

from pathlib import Path
import shutil
import subprocess
import sys
import re


C = {
    "red": "\033[91m",
    "grn": "\033[92m",
    "bld": "\033[1m",
    "prp": "\033[95m",
    "yel": "\033[93m",
    "cyn": "\033[96m",
    "blu": "\033[94m",
    "gry": "\033[90m",
    "rst": "\033[0m",
}

ROOT = Path(__file__).resolve().parents[1]
ERROR_ROOT = ROOT / "examples" / "errors"


# ============================================================
# Test descriptions
# ============================================================

DESCRIPTIONS = {
    "invalid_character.f":
        "Tests the presence of an invalid character.",

    "invalid_character_sequence.f":
        "Tests invalid character sequences.",

    "invalid_label.f":
        "Tests invalid label formats.",

    "line_too_long.f":
        "Tests lines that exceed the maximum length for fixed-format source files.",

    "orphaned_continuation.f":
        "Tests orphaned continuation lines.",

    "unterminated_string.f":
        "Tests string literals that are not properly terminated.",

    "duplicate_procedures.f":
        "Tests multiple subroutines with the same name in the same file.",

    "function_used_as_subroutine.f":
        "Tests a function being called without using its return value, like a "
        "subroutine call.",

    "subroutine_used_as_function.f":
        "Tests a subroutine being called in an expression, like a function call.",

    "unknown_function.f":
        "Tests a call to an undefined function.",

    "unknown_subroutine.f":
        "Tests a call to an undefined subroutine.",

    "wrong_nr_function_args.f":
        "Tests a function call with the wrong number of arguments.",

    "wrong_nr_subroutine_args.f":
        "Tests a subroutine call with the wrong number of arguments.",

    "labels.f":
        "Tests undefined, redefined, referenced but not defined, defined but "
        "never referenced, and DO loop labels that do not match the corresponding"
        " CONTINUE statement.",

    "multiple_program.f":
        "Tests multiple main program units defined in the same source file.",

    "return_outside.f":
        "Tests a RETURN statement outside of any function or subroutine context.",

    "variables.f":
        "Tests the use of: already declared variables, variables used before "
        "initialization, use of undeclared variables, assignment to undeclared "
        "variables, and variables declared but never used.",

    "bad_if_syntax.f":
        "Tests invalid syntax in IF statements, like missing THEN or END IF.",

    "bad_read_syntax.f":
        "Tests invalid syntax in READ statements, like missing a comma.",

    "missing_do_lbl.f":
        "Tests a DO statement without a missing numeric label.",

    "missing_end.f":
        "Tests a program with a missing END statement.",

    "misspelled_function.f":
        "Tests a misspelled function name in a function call.",

    "arith_with_string.f":
        "Tests an arithmetic operation involving a string literal.",

    "if_cond_non_logical.f":
        "Tests an IF statement with a non-logical condition.",

    "invalid_narrowing.f":
        "Tests an assignment of a REAL literal to an INTEGER variable.",

    "logical_expr_mismatch.f":
        "Tests a logical expression with incompatible operand types.",

    "wrong_assignment_type.f":
        "Tests an assignment with incompatible types (assign a CHARACTER to an "
        "INTEGER)."
}


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
    print(f"\n{C['blu']}Program:{C['rst']}")

    preview = subprocess.run(
        program_preview_command(filepath),
        text=True,
        capture_output=True,
        cwd=ROOT,
    )

    print(preview.stdout.rstrip())


def print_output(result: subprocess.CompletedProcess):
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