#!/usr/bin/env python3

from utils.utils import C, collect_example_files, print_block
import subprocess
import argparse


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