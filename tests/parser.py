#!/usr/bin/env python3

from email import parser
import glob
import os
import subprocess

import parser
import argparse

C = {
    "red": "\033[91m",
    "grn": "\033[92m",
    "yel": "\033[93m",
    "blu": "\033[94m",
    "cyn": "\033[96m",
    "bld": "\033[1m",
    "rst": "\033[0m",
}


def natural_sort_key(path):
    name = os.path.basename(path)
    prefix = name.split("_")[0]

    if prefix.isdigit():
        return (int(prefix), name)

    return (float("inf"), name)


def collect_example_files():
    """
    Parser tests use only `.f` files.

    Reason:
    `.f` vs `.f90` equivalence is already validated in `tests/formats.py`,
    so parser tests focus on AST construction and semantic correctness.
    """

    main_examples = glob.glob("examples/*.f")
    line_continuation = glob.glob("examples/line_continuation/*.f")

    main_examples = [
        f for f in main_examples
        if "errors/" not in f
        and not os.path.basename(f).startswith("0_mismatched")
        and os.path.basename(f) != "9_full_program.f"
        and os.path.basename(f) != "empty.f"
    ]

    main_examples.sort(key=natural_sort_key)
    line_continuation.sort(key=natural_sort_key)

    return {
        "Main Examples": main_examples,
        "Line Continuation": line_continuation,
    }


def run_parser(filepath):
    """
    Run parser exactly as it is executed manually in terminal.
    IMPORTANT: this preserves preprocessing + full pipeline behavior.
    """

    return subprocess.run(
        ["python3", "src/parser.py", filepath],
        text=True,
        capture_output=True,
    )


def print_block(text, indent=4):
    if not text.strip():
        return

    prefix = " " * indent

    for line in text.rstrip().splitlines():
        print(f"{prefix}{line}")


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    categories = collect_example_files()

    total = 0
    passed = 0
    failed = 0

    all_files = [
        f for files in categories.values() for f in files
    ]

    width = max(len(f) for f in all_files)

    for category, files in categories.items():

        print()
        print(f"{C['bld']}{C['blu']}== {category} =={C['rst']}")

        for filepath in files:

            total += 1
            result = run_parser(filepath)

            aligned = filepath.ljust(width)

            # SUCCESS
            if result.returncode == 0:

                passed += 1

                print(f"{C['grn']}✓ Passed:{C['rst']} {aligned}")

                if args.verbose:
                    print(f"    {C['cyn']}AST Output:{C['rst']}")
                    print_block(result.stdout)

            # FAILURE
            else:

                failed += 1

                print(f"{C['red']}✗ Failed:{C['rst']} {aligned}")

                print(f"    {C['yel']}Error Output:{C['rst']}")

                if result.stderr.strip():
                    print_block(result.stderr)

                if result.stdout.strip():
                    print()
                    print(f"    {C['cyn']}Partial Output:{C['rst']}")
                    print_block(result.stdout)

            print()

    print(f"{C['bld']}========================================{C['rst']}")
    print(f"{C['bld']}Summary{C['rst']}")
    print(f"{C['grn']}Passed:{C['rst']} {passed}")
    print(f"{C['red']}Failed:{C['rst']} {failed}")
    print(f"Total:  {total}")

    if failed > 0:
        exit(1)


if __name__ == "__main__":
    main()