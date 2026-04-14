#!/usr/bin/env python3

import glob
import os
import subprocess
import difflib

C = {
    "red":    "\033[91m",
    "grn":    "\033[92m",
    "cyn":    "\033[96m",
    "red_bg": "\033[41m",
    "grn_bg": "\033[42m",
    "rst":    "\033[0m",
}

def pretty_diff(f90_out: str, f_out: str, indent: int = 4):
    diff = difflib.ndiff(
        f90_out.splitlines(keepends=True),
        f_out.splitlines(keepends=True),
    )

    print(f"{' ' * indent}--- {C["red_bg"]}Free-format output (.f90){C['rst']}")
    print(f"{' ' * indent}+++ {C["grn_bg"]}Fixed-format output (.f){C['rst']}")

    for line in diff:
        # Separate content and newline
        if line.endswith('\n'):
            content = line[:-1]
            nl = '\n'
        else:
            content = line
            nl = ''

        # Select color
        if content.startswith('+'):
            colored = f"{C['grn']}{content}{C['rst']}"
        elif content.startswith('-'):
            colored = f"{C['red']}{content}{C['rst']}"
        # elif content.startswith('---'):
        #     colored = f"{C['red_bg']}{content}{C['rst']}"
        # elif content.startswith('+++'):
        #     colored = f"{C['grn_bg']}{content}{C['rst']}"
        # elif content.startswith('@@'):
        #     colored = f"{C['cyn']}{content}{C['rst']}"
        else:
            colored = content

        print(f"{' ' * indent}{colored}", end=nl)


if __name__ == "__main__":
    f90_files = glob.glob("examples/*.f90")
    if not f90_files:
        print("No .f90 files found in examples/")
        exit(1)

    for f90_file in f90_files:
        # Get the corresponding .f file name
        base_name = os.path.splitext(os.path.basename(f90_file))[0]
        f_file = f"examples/{base_name}.f"
        if not os.path.exists(f_file):
            continue

        # print(f"Comparing lexer for {f90_file} and {f_file}...")

        # Run "python3 src/lexer.py --test --format=free < {f90_file}"
        f90_result = subprocess.run(
            ["python3", "src/lexer.py", "--test", "--format=free"],
            input=open(f90_file).read(),
            text=True,
            capture_output=True,
        )
        if f90_result.returncode != 0:
            print(f"Error processing {f90_file}: {f90_result.stderr}")
            continue

        # Run "python3 src/lexer.py --test --format=fixed < {f_file}"
        f_result = subprocess.run(
            ["python3", "src/lexer.py", "--test", "--format=fixed"],
            input=open(f_file).read(),
            text=True,
            capture_output=True,
        )
        if f_result.returncode != 0:
            print(f"Error processing {f_file}: {f_result.stderr}")
            continue

        # Compare the outputs
        if f90_result.stdout != f_result.stdout:
            print(f"{C['red']}✗ Failed: {f90_file} != {f_file}{C['rst']}")
            pretty_diff(f90_result.stdout, f_result.stdout)
        else:
            print(f"{C['grn']}✓ Passed: {f90_file} == {f_file}{C['rst']}")
