#!/usr/bin/env python3

import re


def lstrip(text: str, n: int = 4) -> str:
    "Strips n spaces from the beginning of each line."
    prefix = " " * n

    return "\n".join(
        line[n:] if line.startswith(prefix) else line
        for line in text.strip("\n").splitlines()
    )


def extract_parser_rules(file_path: str) -> list[str]:
    "Extracts parser rules from a given file."
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        r'''
        def\s+p_\w+\s*\([^)]*\)\s*:\s*
        """(?P<rule>.*?)"""
        ''',
        re.DOTALL | re.VERBOSE,
    )

    rules = []
    for match in pattern.finditer(content):
        rule = match.group("rule")
        rules.append(lstrip(rule))

    return rules


def main():
    output_file = ".assets/captured_parser_rules.txt"
    input_files = [
        "src/parser.py",
        "src/parser_rules/statements.py",
        "src/parser_rules/expressions.py",
        "src/parser_rules/conditionals.py",
        "src/parser_rules/io.py",
        "src/parser_rules/common.py",
    ]

    rules = []
    for input_file in input_files:
        rules.extend(extract_parser_rules(input_file))

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(rules))

    print(f"Wrote {len(rules)} captured parser rules to {output_file}")


if __name__ == "__main__":
    main()
