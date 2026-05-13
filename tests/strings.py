#!/usr/bin/env python3

from pathlib import Path
import subprocess
import sys
import re


C = {
    "red": "\033[91m",
    "grn": "\033[92m",
    "prp": "\033[95m",
    "yel": "\033[93m",
    "rst": "\033[0m",
}

ROOT = Path(__file__).resolve().parents[1]
LEXER = ROOT / "src" / "lexer.py"


STRING_CASES = [
    {
        "name": "escaped delimiter, free format",
        "format": "free",
        "source": 'PRINT *, "He said \\"HI\\""',
        "expected_tokens": [
            ("PRINT", "PRINT"),
            ("ASTERISK", "*"),
            (",", ","),
            ("STRING", 'He said "HI"'),
        ],
    },
    {
        "name": "string with escaped quotes",
        "format": "free",
        "source": 'PRINT *, "She said \\\"hello\\\" and left"',
        "expected_tokens": [
            ("PRINT", "PRINT"),
            ("ASTERISK", "*"),
            (",", ","),
            ("STRING", 'She said "hello" and left'),
        ],
    },
    {
        "name": "empty string literal",
        "format": "free",
        "source": 'PRINT *, ""',
        "expected_tokens": [
            ("PRINT", "PRINT"),
            ("ASTERISK", "*"),
            (",", ","),
            ("STRING", ""),
        ],
    },
    {
        "name": "strings next to commas and operators",
        "format": "free",
        "source": 'PRINT *, "A", "B" + "C"',
        "expected_tokens": [
            ("PRINT", "PRINT"),
            ("ASTERISK", "*"),
            (",", ","),
            ("STRING", "A"),
            (",", ","),
            ("STRING", "B"),
            ("PLUS", "+"),
            ("STRING", "C"),
        ],
    },
    {
        "name": "string containing exclamation mark",
        "format": "free",
        "source": 'PRINT *, "A!B"',
        "expected_tokens": [
            ("PRINT", "PRINT"),
            ("ASTERISK", "*"),
            (",", ","),
            ("STRING", "A!B"),
        ],
    },
    {
        "name": "comment after string",
        "format": "free",
        "source": 'PRINT *, "abc" ! comment',
        "expected_tokens": [
            ("PRINT", "PRINT"),
            ("ASTERISK", "*"),
            (",", ","),
            ("STRING", "abc"),
        ],
    },
    {
        "name": "escaped delimiter, fixed format",
        "format": "fixed",
        "source": '      PRINT *, "He said \\"HI\\""',
        "expected_tokens": [
            ("PRINT", "PRINT"),
            ("ASTERISK", "*"),
            (",", ","),
            ("STRING", 'He said "HI"'),
        ],
    },
    {
        "name": "unterminated string literal",
        "format": "free",
        "source": 'PRINT *, "hello',
        "expect_failure": True,
    },
    {
        "name": "multiline string rejected",
        "format": "free",
        "source": 'PRINT *, "First line\nSecond line"',
        "expect_failure": True,
    },
]


def run_lexer(source: str, fmt: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(LEXER), "--test", "--format", fmt],
        input=source,
        text=True,
        capture_output=True,
        cwd=ROOT,
    )


def parse_tokens(stdout: str):
    parsed = []

    token_pattern = re.compile(
        r"LexToken\((.+?),\s*('(?:\\\\.|[^'])*'|\"(?:\\\\.|[^\"])*\"),\s*(\d+)\)"
    )

    for line in stdout.splitlines():
        line = line.strip()

        match = token_pattern.match(line)

        if not match:
            continue

        token_type = match.group(1)
        token_value = match.group(2)

        try:
            token_value = eval(token_value)
        except Exception:
            pass

        parsed.append((token_type, token_value))

    return parsed


def pretty_case(case: dict) -> str:
    lines = [
        f"{C['prp']}format{C['rst']}: {case['format']}",
        f"{C['prp']}source{C['rst']}:",
    ]

    for line in case["source"].splitlines():
        lines.append(f"  {line}")

    if "expected_tokens" in case:
        lines.append(f"{C['prp']}expected tokens{C['rst']}:")
        for token_type, token_value in case["expected_tokens"]:
            lines.append(f"  ({token_type}, {repr(token_value)})")
    else:
        lines.append(f"{C['prp']}expected result{C['rst']}: lexer failure")

    return "\n".join(lines)


def print_failure(result: subprocess.CompletedProcess):
    print(
        f"{C['red']}✗ Failed{C['rst']}",
        file=sys.stderr,
        flush=True,
    )

    if result.stdout:
        print(
            result.stdout,
            end="" if result.stdout.endswith("\n") else "\n",
            file=sys.stderr,
        )

    if result.stderr:
        print(
            result.stderr,
            end="" if result.stderr.endswith("\n") else "\n",
            file=sys.stderr,
        )


if __name__ == "__main__":
    exit_code = 0
    passed = 0

    for case in STRING_CASES:

        print(
            f"\n{C['prp']}== {case['name']} =={C['rst']}",
            file=sys.stderr,
            flush=True,
        )

        print(
            pretty_case(case),
            file=sys.stderr,
            flush=True,
        )

        result = run_lexer(case["source"], case["format"])

        if "expected_tokens" in case:

            actual_tokens = parse_tokens(result.stdout)

            if (
                result.returncode != 0
                or actual_tokens != case["expected_tokens"]
            ):
                print_failure(result)
                exit_code = 1
            else:
                passed += 1
                print(
                    f"{C['grn']}✓ Passed{C['rst']}",
                    file=sys.stderr,
                    flush=True,
                )

            continue

        if result.returncode == 0:
            print_failure(result)
            exit_code = 1
        else:
            passed += 1
            print(
                f"{C['grn']}✓ Passed{C['rst']}",
                file=sys.stderr,
                flush=True,
            )

    print(
        f"\n{C['grn']}Passed {passed}/{len(STRING_CASES)} string lexer checks{C['rst']}",
        file=sys.stderr,
        flush=True,
    )

    raise SystemExit(exit_code)