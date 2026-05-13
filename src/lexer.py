#!/usr/bin/env python3

import ply.lex as lex
from error import (
    print_error,
    print_numeric_range_error,
    get_source_line,
    get_token_column
)

###
# Reserved words
###

# NOTE Fortran is case insensitive. To match reserved words,
# identifiers are converted to upper case in t_IDENTIFIER function.

reserved = {
    # Program structure
    'PROGRAM':    'PROGRAM',
    'END':        'END',

    # I/O statements
    'PRINT':      'PRINT',
    'READ':       'READ',
    'WRITE':      'WRITE',

    # Type declarations (Basic Fortran 77 data types)
    'INTEGER':    'INTEGER',
    'REAL':       'REAL',
    'DOUBLE':     'DOUBLE',
    'LOGICAL':    'LOGICAL',
    'CHARACTER':  'CHARACTER',

    # Control flow
    'IF':         'IF',
    'THEN':       'THEN',
    'ELSE':       'ELSE',
    'ENDIF':      'ENDIF',

    # Iteration and jumps
    'DO':         'DO',
    'CONTINUE':   'CONTINUE',
    'GOTO':       'GOTO',
    'STOP':       'STOP',

    # Procedures
    'CALL':       'CALL',
    'SUBROUTINE': 'SUBROUTINE',
    'FUNCTION':   'FUNCTION',
    'RETURN':     'RETURN',
}

###
# Tokens
###

tokens = [
    # Identifiers and literals
    'IDENTIFIER',      # variable names, procedure names, etc.
    'DOUBLE_NUMBER',   # double precision literals (e.g. 1.0D+10)
    'REAL_NUMBER',     # real literals (e.g. 1.0, .5E-3)
    'INTEGER_NUMBER',  # integer literals (e.g. 42)
    'STRING',          # string literals
    'LABEL',           # labels from preprocessor, e.g. @LABEL(123)

    # Mathematical operators
    # NOTE instead of defining mathematical operators as literals (+ - * /),
    # using tokens allow simpler to attach semantic meaning or precedence later
    'PLUS',
    'MINUS',
    'DIVIDE',
    'POWER',
    'ASTERISK',  # Asterisk is used in various contexts

    # Dot relational operators
    'EQ',
    'NE',
    'LT',
    'LE',
    'GT',
    'GE',

    # Logical dot operators and constants
    'AND',
    'OR',
    'NOT',
    'TRUE',
    'FALSE',
] + list(reserved.values())

###
# Literals
###

literals = ['(', ')', ',', ':', '=']

###
# Mathematical operators
###

t_PLUS     = r'\+'
t_MINUS    = r'-'
t_DIVIDE   = r'/'
t_POWER    = r'\*\*'
t_ASTERISK = r'\*'

###
# Dot operators
###

# Relational operators

t_EQ = r'\.EQ\.'
t_NE = r'\.NE\.'
t_LT = r'\.LT\.'
t_LE = r'\.LE\.'
t_GT = r'\.GT\.'
t_GE = r'\.GE\.'

# Logical operators

t_AND   = r'\.AND\.'
t_OR    = r'\.OR\.'
t_NOT   = r'\.NOT\.'

# Logical constants

t_TRUE  = r'\.TRUE\.'
t_FALSE = r'\.FALSE\.'


###
# String
###

# Matches both single (') and double (") quoted strings, properly handling
# escaped characters. Breakdown of the Regex:
# (
#   \"               : Start with a double quote
#   ([^\\\n]|(\\.))*?: Match either a non-backslash/non-newline char,
#                      OR an escaped char (\\.), zero or more times (non-greedy)
#   \"               : End with a double quote
# )
# |                  : OR
# (
#   \'               : Start with a single quote
#   ([^\\\n]|(\\.))*?: Same logic as above, but for single-quoted strings
#   \'               : End with a single quote
# )
def t_STRING(t):
    r'(\"([^\\\n]|(\\.))*?\")|(\'([^\\\n]|(\\.))*?\')'
    t.value = bytes(t.value[1:-1], "utf-8").decode("unicode_escape")
    return t


###
# Number
###

# Numeric literal limits
# TODO import this values from semantics/number_ranges.py

INTEGER_MIN = -2_147_483_648
INTEGER_MAX = 2_147_483_647
INTEGER_MAX_CHECK = 2_147_483_648

# These assume common IEEE-like sizes:
# REAL    -> 32-bit single precision
# DOUBLE  -> 64-bit double precision
# TODO adjust for EWVM

REAL_MAX = 3.4028235e38
DOUBLE_MAX = 1.7976931348623157e308


def t_DOUBLE_NUMBER(t):
    r'(\d+(\.\d*)?|\.\d+)[dD][+-]?\d+'

    literal = t.value

    try:
        value = float(literal.replace("D", "E").replace("d", "e"))
    except OverflowError:
        value = float("inf")

    # Check for out of range value (semantic error)
    if value == float("inf") or abs(value) > DOUBLE_MAX:
        print_numeric_range_error(
            t,
            literal=literal,
            type_name="double precision",
            hint=(
                "double precision literals must be representable in the "
                "target DOUBLE PRECISION range"
            ),
        )

    t.value = value
    return t


def t_REAL_NUMBER(t):
    r'(\d+\.\d*|\.\d+)([eE][+-]?\d+)?|\d+[eE][+-]?\d+'

    literal = t.value

    try:
        value = float(literal)
    except OverflowError:
        value = float("inf")

    # Check for out of range value (semantic error)
    if value == float("inf") or abs(value) > REAL_MAX:
        print_numeric_range_error(
            t,
            literal=literal,
            type_name="real",
            hint=(
                "real literals must be representable in the "
                "target REAL range"
            ),
        )

    t.value = value
    return t


def t_INTEGER_NUMBER(t):
    r'\d+'

    literal = t.value
    value = int(literal)

    # Check for out of range value (semantic error)
    if value > INTEGER_MAX_CHECK:  # NOTE the upper limit assumes a MINUS before
        print_numeric_range_error(
            t,
            literal=literal,
            type_name="integer",
            hint=(
                f"integer literals must be between "
                f"{INTEGER_MIN} and {INTEGER_MAX}"
            ),
        )

    t.value = value
    return t


###
# Identifier
###

def t_IDENTIFIER(t):
    r'[A-Za-z][A-Za-z0-9_]*'

    # Fortran is case insensitive
    t.value = t.value.upper()

    # Reserved word detection
    t.type = reserved.get(t.value, 'IDENTIFIER')

    return t


###
# LABEL token (generated by preprocessor)
###

def t_LABEL(t):
    r'@LABEL\(\d+\)'
    t.value = int(t.value[7:-1])
    return t


###
# Ignore spaces
###

t_ignore = ' \t&'


###
# Newlines
###

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


###
# Comments
###

# NOTE Comments are currently being ignored by the lexer, but they could be
# returned as COMMENT tokens if needed for documentation or other purposes.
# For now, we just skip them.

# Fixed-format comment lines: C, c, or * in column 1
def t_comment_fixed(t):
    r'^[Cc\*].*'
    pass  # Ignore fixed-format comment lines

    # t.type = 'COMMENT'
    # t.value = t.value[1:]  # Exclude the comment character
    # return t


# Inline comments starting with !
def t_comment_inline(t):
    r'!.*'
    pass  # Ignore inline comments

    # t.type = 'COMMENT'
    # t.value = t.value[1:]  # Exclude the '!' character
    # return t


###
# Error handling
###

def t_error(t):
    """
    Report one or more consecutive illegal characters using compiler-style
    diagnostics.
    """

    import re

    lexer = t.lexer

    lexer.has_error = True

    # NOTE '@' is not an usual char in Fortran source code,
    #      but it's introduced by preprocessor for labels.
    match = re.match(r"[^A-Za-z0-9\s+\-*/=(),.:_'\"&<>@]+", t.value)

    bad = t.value[0] if match is None else match.group(0)

    length = len(bad)

    if length == 1:
        error = f"illegal character {bad!r}"
        hint = (
            "remove this character or "
            "replace it with valid Fortran 77 syntax"
        )
    else:
        error = f"illegal character sequence {bad!r}"
        hint = (
            "remove these characters or "
            "replace them with valid Fortran 77 syntax"
        )

    print_error(
        error=error,
        line=get_source_line(lexer, t.lineno),
        lineno=t.lineno,
        col_start=get_token_column(t),
        length=length,
        filename=getattr(lexer, "source_filename", None),
        hint=hint
    )

    lexer.skip(length)


###
# Lexer setup
###

lexer = lex.lex()

# Auxiliary lexer variables

# List of source lines for error reporting
lexer.source_lines = []

# Source filename for error reporting
lexer.source_filename = None

# Whether the lexer has encountered an error
lexer.has_error = False


# Auxiliary function to clean lexer state

def clear_lexer_state(lexer):
    """
    Clear lexer state before parsing a new file.
    """
    lexer.lineno = 1
    lexer.source_lines.clear()
    lexer.source_filename = None
    lexer.has_error = False


###
# Main function for testing
###

def main():
    """
    Main function mainly for lexer testing.
    """

    import argparse
    import sys

    from common import read_input, detect_source_format
    from preprocessor import preprocess

    global lexer

    # CLI argument parsing
    parser_args = argparse.ArgumentParser(
        description="Run lexical analysis on Fortran source code."
    )

    parser_args.add_argument(
        "input_file",
        nargs="?",
        help="Fortran source file to lex. If omitted, read from stdin.",
    )

    parser_args.add_argument(
        "--format",
        choices=["fixed", "free"],
        help="The source format. If omitted, inferred from file extension; "
             "stdin defaults to fixed."
    )

    parser_args.add_argument(
        "--no-preprocess",
        action="store_true",
        default=False,
        help="Skip preprocessing and lex the raw input directly"
    )

    parser_args.add_argument(
        "--test",
        action="store_true",
        default=False,
        help="Output tokens in a test-friendly format (no cols are printed)"
    )

    args = parser_args.parse_args()

    # Read input data
    try:
        source_filename, source_data = read_input(args.input_file)
    except Exception as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        sys.exit(1)

    # Detect source format based on file extension
    source_format = detect_source_format(args.input_file, args.format)

    # Pre-process the input data
    if not args.no_preprocess:
        try:
            source_data = preprocess(source_data, format=source_format)
        except Exception as e:
            print(f"Preprocessing error: {e}", file=sys.stderr)
            sys.exit(1)

    # Setup lexer state before lexing
    clear_lexer_state(lexer)

    lexer.source_lines = source_data.splitlines()
    lexer.source_filename = source_filename

    # Parse the input data
    lexer.input(source_data)

    # Print lexed tokens
    if not args.test:
        for tok in lexer:
            print(tok)
    else:
        for tok in lexer:
            print(f"LexToken({tok.type}, {repr(tok.value)}, {tok.lineno})")

    # Exit with non-zero status if any errors were encountered
    if lexer.has_error:
        sys.exit(1)


if __name__ == "__main__":
    main()
