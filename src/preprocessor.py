#!/usr/bin/env python3

import re

# TODO consider adding a @CONT token to increase lexer lineno
# when a continuation line is detected.

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
    Entry point to normalize Fortran source into a canonical format for the lexer.

    This function acts as a dispatcher between fixed-format (F77 and earlier)
    and free-format (F90+) source structures. It ensures that regardless of the
    input style, the lexer receives a unified stream of pseudo-FORTRAN where:
    1. Statements (with continuations) are logically joined.
    2. Labels are explicitly tagged with @LABEL().
    3. Comments are normalized to the '!' prefix.

    See `_preprocess_fixed_format` for fixed-format details,
    and `_preprocess_free_format` for free-format details.

    Args:
        raw_input (str): The raw Fortran source code buffer.
        format (str): "fixed" for column-dependent source, "free" for F90+ style.

    Returns:
        str: Preprocessed Fortran code suitable for lexing.

    Raises:
        ValueError: If a format other than 'fixed' or 'free' is provided.
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
        "flattens" the structure. It merges continuation lines into their parent
        statements while inserting empty line placeholders to ensure that the
        lexer's internal `lineno` counter remains accurate to the source file.

    Processing Steps:
        1.  Normalization: Pads lines < 6 chars to allow safe slicing.
        2.  Comments: Converts 'C', 'c', or '*' in Col 1 to '!'.
        3.  Labels: Extracts digits in Col 1-5 and wraps them in @LABEL(...).
        4.  Continuations: If Col 6 contains a non-space/non-zero character, the
            statement content is appended to the previous logical statement.
        5.  Placeholders: Appends an empty string for every line merged to
            preserve the original newline count.

    Args:
        raw_input (str): The raw Fortran 77 source code.

    Returns:
        str: Normalized code with pseudo-tokens and preserved line-mapping.

    Raises:
        PreprocessorFormatError: If a line exceeds 72 columns.
        PreprocessorContinuationError: If a continuation appears without a preceding statement.
        PreprocessorLabelError: If the label field contains non-numeric characters.

    TODO:
        - Strictly enforce fixed-format rules.
          Example: other invalid format violations: only 3 chars in a non-comment line, etc.
        - Consider catching non-ASCII characters and raising warnings or errors.
    """
    lines = raw_input.splitlines()
    preprocessed_lines = []
    lineno = 0

    for line in lines:
        lineno += 1

        # Preserve empty lines for accurate line mapping
        if not line.strip():
            preprocessed_lines.append("")
            continue

        # Ensure line has at least 6 characters for fixed-format slicing
        if len(line) < 6:
            line = line.ljust(6)

        col1 = line[0]
        label_field = line[:5]
        cont_field = line[5]
        stmt_field = line[6:72].rstrip()  # Trim trailing whitespace from statement

        # 1. Handle Comment Lines
        if col1 in ['C', 'c', '*']:
            preprocessed_lines.append('!' + line[1:])
            continue

        # 2. Strict Column Validation
        if len(line) > 72:
            raise PreprocessorFormatError(f"Line exceeds 72 columns at line {lineno}")

        # 3. Handle Labels
        label = label_field.strip()
        if label:
            if not re.match(r'^\d{1,5}$', label):
                raise PreprocessorLabelError(f"Invalid label '{label}' at line {lineno}")
            preprocessed_lines.append(f"@LABEL({label})")

        # 4. Handle Continuation Logic
        # A continuation is any non-space character EXCEPT '0'
        is_continuation = cont_field.strip() and cont_field != '0'

        if is_continuation:
            if not preprocessed_lines:
                raise PreprocessorContinuationError(
                    f"First line cannot be a continuation at line {lineno}"
                )

            # Find the last non-comment, non-empty line to append to
            idx = len(preprocessed_lines) - 1
            while idx >= 0 and (not preprocessed_lines[idx] or preprocessed_lines[idx].startswith('!')):
                idx -= 1

            if idx < 0:
                raise PreprocessorContinuationError(
                    f"Continuation without preceding statement at line {lineno}"
                )

            # Glue this statement field to the end of the previous statement
            preprocessed_lines[idx] = preprocessed_lines[idx] + stmt_field
            # Add an empty string to maintain the total line count for the Lexer
            preprocessed_lines.append("")
        else:
            # Normal statement line
            preprocessed_lines.append(stmt_field)

    return "\n".join(preprocessed_lines)

###
# Free-format preprocessing
###

def _preprocess_free_format(raw_input: str) -> str:
    """
    Normalizes free-format (F90+) source into canonical logical lines.

    Architecture:
        Free-format uses the ampersand ('&') for continuation. This function
        mirrors the 'Lookback Gluing' logic of the fixed-format preprocessor:
        1. It identifies trailing ampersands.
        2. It searches backward to find the last valid statement line.
        3. It merges the current content into that line and leaves an
           empty string placeholder to preserve the original line numbering.

    Processing Steps:
        - Comment Handling: Ignores content after '!' for logic but preserves
          comment-only lines.
        - Label Extraction: Identifies 1-5 digit prefixes and wraps them in
          @LABEL(...) pseudo-tokens on their own lines.
        - Continuation Merging: If the previous non-comment line ended in '&',
          the current line's content is glued to it. It also handles the
          optional F90 'leading ampersand' on continued lines.
        - Line Mapping: Every time a line is 'glued', an empty string is
          appended to the output list to keep the Lexer's line count synced.

    Args:
        raw_input (str): The raw free-format Fortran source code.

    Returns:
        str: Preprocessed code where multi-line statements are joined.
    """
    lines = raw_input.splitlines()
    preprocessed_lines = []

    # Regex breakdown for matching a valid free-format label:
    # ^\s* : Matches optional leading whitespace.
    # (\d{1,5})  : Capture group 1: Matches exactly 1 to 5 digits.
    # (?=\s|!|$) : Positive lookahead: Ensures the digits are immediately followed
    #              by whitespace, an inline comment (!), or the end of the line.
    label_pattern = re.compile(r'^\s*(\d{1,5})(?=\s|!|$)')

    # State tracking: Did the previous logical line end with an ampersand?
    pending_continuation = False

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()

        # 1. Preserve empty lines for line-mapping
        if not stripped:
            preprocessed_lines.append("")
            continue

        # 2. Handle Comment-only lines
        if stripped.startswith('!'):
            preprocessed_lines.append(line)
            continue

        # 3. Logic Processing: Strip inline comments
        # We work with 'content' for gluing but keep the structure
        content_part = line.split('!')[0].rstrip()

        # Check if this line ends with a continuation marker
        ends_with_amp = content_part.endswith('&')

        # Clean content is the code minus the trailing ampersand
        clean_content = content_part[:-1] if ends_with_amp else content_part

        # 4. Leading Ampersand Rule (F90):
        # If continuing and line starts with '&', content starts after it.
        if pending_continuation:
            clean_content = clean_content.lstrip()
            if clean_content.startswith('&'):
                clean_content = clean_content[1:]

        # 5. Handle Labels (Only on the initial line of a statement)
        if not pending_continuation:
            match = label_pattern.match(clean_content)
            if match:
                label = match.group(1)
                preprocessed_lines.append(f"@LABEL({label})")
                clean_content = clean_content[match.end():]

        # 6. Gluing Logic
        if pending_continuation:
            # Find the last non-comment, non-empty line to append to
            idx = len(preprocessed_lines) - 1
            while idx >= 0 and (not preprocessed_lines[idx] or preprocessed_lines[idx].startswith('!')):
                idx -= 1

            if idx >= 0:
                # Glue content to the existing statement
                preprocessed_lines[idx] = preprocessed_lines[idx] + clean_content
                # Add placeholder to maintain lineno count
                preprocessed_lines.append("")
            else:
                # Fallback for orphaned continuations
                preprocessed_lines.append(clean_content)
        else:
            # Standard statement line
            preprocessed_lines.append(clean_content)

        # Update state for the next iteration
        pending_continuation = ends_with_amp

    return "\n".join(preprocessed_lines)

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
