#!/usr/bin/env python3

from utils.utils import C, collect_example_files, print_block
import subprocess
import argparse


def detect_format(filepath):
    """
    Detect source format from extension.
    """

    return "fixed"


def run_lexer(filepath):
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
            "--format=fixed",
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
            result = run_lexer(filepath)

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