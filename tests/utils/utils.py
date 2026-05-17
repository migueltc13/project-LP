#!/usr/bin/env python3

import os
import glob

# ============================================================
# ANSI Color Codes
# ============================================================
C = {
    "red":    "\033[91m",
    "grn":    "\033[92m",
    "yel":    "\033[93m",
    "blu":    "\033[94m",
    "prp":    "\033[95m",
    "cyn":    "\033[96m",
    "gry":    "\033[90m",
    "dim":    "\033[90m",
    "bld":    "\033[1m",
    "red_bg": "\033[41m",
    "grn_bg": "\033[42m",
    "rst":    "\033[0m",
}

# ============================================================
# File Sorting and Collection
# ============================================================
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
    Collect test inputs (.f files), excluding specific test files.
    """
    main_examples = []
    line_continuation = []

    main_examples.extend(glob.glob("examples/general/*.f"))

    # Exclude unwanted test cases
    main_examples = [
        f for f in main_examples
        if not os.path.basename(f).startswith("0_mismatched")
        and os.path.basename(f) != "9_full_program.f"
        and os.path.basename(f) != "empty.f"
    ]

    line_continuation.extend(
        glob.glob("examples/line_continuation/*.f")
    )

    main_examples.sort(key=natural_sort_key)
    line_continuation.sort(key=natural_sort_key)

    return {
        "Main Examples": main_examples,
        "Line Continuation": line_continuation,
    }

# ============================================================
# Console Formatting
# ============================================================
def print_block(text, color=None, indent=4):
    """
    Prints a block of text with optional indentation and color.
    """
    if not text.strip():
        return

    prefix = " " * indent

    for line in text.rstrip().splitlines():
        if color:
            print(f"{prefix}{color}{line}{C['rst']}")
        else:
            print(f"{prefix}{line}")