#!/usr/bin/env python3

import re

###
# Custom exceptions for preprocessor errors
###

class PreprocessorError(Exception):
    """
    Base class for all preprocessing exceptions.
    """
    pass

class PreprocessorFormatError(PreprocessorError):
    """
    Raised when a line violates fixed-format rules.
    """
    pass

class PreprocessorContinuationError(PreprocessorError):
    """
    Raised when an orphaned continuation character is detected
    without a leading statement.
    """
    pass

class PreprocessorLabelError(PreprocessorError):
    """
    Raised when a statement label violates numeric or
    length constraints (1-5 digits).
    """
    pass

###
# Public preprocess function
###

def preprocess(raw_input: str, format: str = "fixed") -> str:
    """
    Entry point to normalize Fortran source into a canonical format for the
    lexer.

    This function acts as a dispatcher between fixed-format (F77 and earlier)
    and free-format (F90+) source structures. It ensures that regardless of the
    input style, the lexer receives a unified stream of pseudo-FORTRAN where:
    1. Labels are explicitly tagged with @LABEL().
    2. Comments are normalized to the "!" prefix.
    3. Statements with continuations are normalized with the "&" suffix.

    See `_preprocess_fixed_format` for fixed-format details,
    and `_preprocess_free_format` for free-format details.

    Args:
        raw_input (str): The raw Fortran source code.
        format (str): "fixed" for column-dependent format, "free" for F90 style.

    Returns:
        str: Preprocessed Fortran code suitable for lexing.

    Raises:
        ValueError: If a format other than "fixed" or "free" is provided.
    """
    if format == "fixed":
        return _preprocess_fixed_format(raw_input)
    elif format == "free":
        return _preprocess_free_format(raw_input)
    else:
        raise ValueError(f"Unknown format: {format}")

###
# Fixed-format preprocessing
###

def _preprocess_fixed_format(raw_input: str) -> str:
    """
    Normalizes fixed-format Fortran 77 code into a more modern, lexer-friendly
    pseudo-code.

    Rationale:
        Fixed-format is highly column-sensitive (Label 1-5, Cont 6, Stmt 7-72).
        Since standard Lexers (like PLY) are not column-aware, this function
        normalizes the structure, ensuring a 1:1 mapping of input lines to
        output allowing the lexer to operate on a more uniform token stream,
        and preserving the original line numbers for accurate error reporting.

    Args:
        raw_input (str): The raw fixed-format Fortran source code.

    Returns:
        str: Normalized Fortran code with pseudo-tokens and preserved
            line-mapping.

    Raises:
        PreprocessorFormatError: If a line exceeds 72 columns.
        PreprocessorContinuationError: If a continuation appears without a
            preceding statement.
        PreprocessorLabelError: If the label field contains non-numeric
            characters.
    """
    lines = raw_input.splitlines()
    out = []

    # Track the index of the last statement line to add continuation symbol (&)
    last_stmt_idx = None

    for lineno, line in enumerate(lines, start=1):
        # Preserve empty lines for accurate line mapping
        if not line.strip():
            out.append("")
            continue

        # Strict column validation
        if len(line) > 72:
            raise PreprocessorFormatError(
                f"Line exceeds 72 columns at line {lineno}"
            )

        # Ensure line has at least 6 characters for safe fixed-format slicing
        if len(line) < 6:
            line = line.ljust(6)

        col1 = line[0]
        label_field = line[:5]
        cont_field = line[5]
        stmt_field = line[6:72]

        # Handle full-line comments
        if col1 in ["C", "c", "*"]:
            out.append("!" + line[1:])
            continue

        # Handle Labels
        label = label_field.strip()
        if label:
            if not re.match(r"^\d{1,5}$", label):
                raise PreprocessorLabelError(
                    f"Invalid label '{label}' at line {lineno}"
                )
            stmt_field = f"@LABEL({label}) {stmt_field}"

        # Handle Continuations
        if cont_field not in [" ", "0"]:
            if last_stmt_idx is None:
                raise PreprocessorContinuationError(
                    f"Orphaned continuation at line {lineno} without a leading "
                    "statement"
                )

            # append "&" to previous statement to indicate continuation
            out[last_stmt_idx] = out[last_stmt_idx].rstrip() + " &"

        # Append the statement to the output
        out.append(stmt_field)
        last_stmt_idx = len(out) - 1  # Update last statement index

    return "\n".join(out)

###
# Free-format preprocessing
###

def _preprocess_free_format(raw_input: str) -> str:
    """
    Normalizes free-format (F90+) source by converting labels into @LABEL()
    pseudo-tokens while preserving the original line structure for accurate
    error reporting.

    Args:
        raw_input (str): The raw free-format Fortran source code.

    Returns:
        str: Normalized Fortran code with pseudo-tokens and preserved
            line-mapping.
    """
    lines = raw_input.splitlines()
    out = []

    # Regex breakdown for matching a valid free-format label:
    # ^\s* : Matches optional leading whitespace.
    # (\d{1,5})  : Capture group 1: Matches exactly 1 to 5 digits.
    # (?=\s|!|$) : Positive lookahead: Ensures the digits are immediately
    #              followed by whitespace, an inline comment (!), or the EOL.
    label_pattern = re.compile(r"^\s*(\d{1,5})(?=\s|!|$)")

    for lineno, line in enumerate(lines, start=1):
        # Preserve empty lines for line-mapping
        if not line.strip():
            out.append("")
            continue

        # Handle full-line comments
        if line.startswith("!"):
            out.append(line)
            continue

        # Handle Labels
        label_match = label_pattern.match(line)
        if label_match:
            line = (
                f"{line[:label_match.start()]}"     # Preserve whitespace
                f"@LABEL({label_match.group(1)}) "  # Insert @LABEL() token
                f"{line[label_match.end():]}"       # Original line content
            )

        # Append the statement to the output
        out.append(line)

    return "\n".join(out)

###
# Main function for testing
###

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Preprocess Fortran source code."
    )
    parser.add_argument("--format", choices=["fixed", "free"], default="fixed",
                        help="The source format (default: fixed)")
    args = parser.parse_args()

    import sys
    raw_input = sys.stdin.read()

    preprocessed_code = preprocess(raw_input, format=args.format)
    print(preprocessed_code)
