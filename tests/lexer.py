#!/usr/bin/env python3

import argparse
import subprocess
from utils.utils import C, collect_example_files, print_block
from pathlib import Path


def detect_format(filepath):
    """
    Detect source format from extension.
    """
    if filepath is None:
        return "fixed"

    suffix = Path(filepath).suffix.lower()

    if suffix in {".f", ".for", ".ftn"}:
        return "fixed"

    if suffix in {".f90", ".f95", ".f03", ".f08"}:
        return "free"

    return "fixed"


def run_lexer(filepath, format="fixed"):
    """
    Run lexer.py in test mode.
    """

    with open(filepath, "r") as f:
        source = f.read()

    return subprocess.run(
        [
            "python3",
            "src/lexer.py",
            "--test",
            f"--format={format}",
        ],
        input=source,
        text=True,
        capture_output=True,
    )


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    categories = collect_example_files()

    total = 0
    passed = 0
    failed = 0

    all_files = [
        filepath
        for files in categories.values()
        for filepath in files
    ]

    width = max(len(path) for path in all_files)

    for category, files in categories.items():

        print()
        print(f"{C['bld']}{C['blu']}== {category} =={C['rst']}")

        for filepath in files:

            total += 1
            result = run_lexer(filepath, format=detect_format(filepath))

            aligned = filepath.ljust(width)

            if result.returncode == 0:

                passed += 1

                print(f"{C['grn']}✓ Passed:{C['rst']} {aligned}")

                if args.verbose:
                    print(f"{C['cyn']}Generated Tokens:{C['rst']}")
                    print_block(result.stdout)

            else:

                failed += 1

                print(f"{C['red']}✗ Failed:{C['rst']} {aligned}")

                print(f"    {C['yel']}Lexer Error:{C['rst']}")

                if result.stderr.strip():
                    print_block(result.stderr, color=C["red"])

                if result.stdout.strip():
                    print()
                    print(f"    {C['cyn']}Partial Tokens:{C['rst']}")
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
