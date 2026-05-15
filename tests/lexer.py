#!/usr/bin/env python3

import glob
import os
import subprocess
import argparse

C = {
    "red": "\033[91m",
    "grn": "\033[92m",
    "yel": "\033[93m",
    "blu": "\033[94m",
    "cyn": "\033[96m",
    "bld": "\033[1m",
    "dim": "\033[90m",
    "rst": "\033[0m",
}


def natural_sort_key(path):
    """
    Natural sorting for filenames with numeric prefixes.
    """

    name = os.path.basename(path)
    prefix = name.split("_")[0]

    if prefix.isdigit():
        return (int(prefix), name)

    return (float("inf"), name)


def collect_example_files():
    """
    Collect lexer test inputs.

    NOTE:
    We intentionally use only `.f` files here because the equivalence between
    `.f` (fixed format) and `.f90` (free format) is already validated in
    `formats.py`, where both formats are preprocessed and compared at the
    token level.

    This keeps lexer testing focused on token generation correctness without
    duplicating format-equivalence checks.
    """

    root_examples = []
    line_continuation = []

    # Main examples (.f only)
    root_examples.extend(glob.glob("examples/*.f"))

    # Exclude unwanted test cases
    root_examples = [
        f for f in root_examples
        if "errors/" not in f
        and not os.path.basename(f).startswith("0_mismatched")
        and os.path.basename(f) != "9_full_program.f"
        and os.path.basename(f) != "empty.f"
    ]

    # Line continuation examples (.f only)
    line_continuation.extend(
        glob.glob("examples/line_continuation/*.f")
    )

    root_examples.sort(key=natural_sort_key)
    line_continuation.sort(key=natural_sort_key)

    return {
        "Main Examples": root_examples,
        "Line Continuation": line_continuation,
    }


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


def print_block(text, color=None, indent=4):

    if not text.strip():
        return

    prefix = " " * indent

    for line in text.rstrip().splitlines():
        if color:
            print(f"{prefix}{color}{line}{C['rst']}")
        else:
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