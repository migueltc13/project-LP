#!/usr/bin/env python3

import ply.yacc as yacc
from pathlib import Path

from lexer import lexer, tokens, clear_lexer_state
from parser_rules.expressions import *
from parser_rules.conditionals import *
from parser_rules.io import *
from parser_rules.statements import *
from parser_rules.common import *
import abstract_syntax_tree as ast
from error import record_syntax_error, get_token_column

start = 'file'


def p_file(p):
    """
    file : program_units
         | empty
    """
    filename = getattr(p.parser, "source_filename", "<unknown>")
    p[0] = ast.File(filename, [] if p[1] is None else p[1])


###
# Program units
###

def p_program_units(p):
    """
    program_units : program_units program_unit
                  | program_unit
    """
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]


def p_program_unit(p):
    """
    program_unit : main_program
                 | subroutine
                 | function
    """
    p[0] = p[1]


def p_main_program(p):
    """
    main_program : PROGRAM IDENTIFIER statements END
    """
    # Record the main program unit location for error reporting
    # when more than one main program is defined
    p.parser.program_locations.append({
        "name": p[2],
        "lineno": p.lineno(1),
        "col_start": get_token_column(p.slice[1],
                                      getattr(p.lexer, "lexdata", None)),
        "length": len(p[1]),
    })

    p[0] = ast.Program(p[2], p[3], ast.location_from_parser_token(p, 2))


def p_subroutine(p):
    """
    subroutine : SUBROUTINE IDENTIFIER '(' arguments ')' enter_subroutine statements exit_subroutine END
    """
    p[0] = ast.Subroutine(p[2], p[4], p[7], ast.location_from_parser_token(p, 2))


def p_function(p):
    """
    function : type FUNCTION IDENTIFIER '(' arguments ')' enter_function statements exit_function END
    """
    p[0] = ast.Function(p[1], p[3], p[5], p[8],
                        ast.location_from_parser_token(p, 3))


###
# Basic Fortran 77 data types
###

def p_type(p):
    """
    type : INTEGER
         | REAL
         | DOUBLE
         | LOGICAL
         | CHARACTER
    """
    p[0] = p[1]


###
# Arguments for functions and subroutines declarations
###

def p_arguments(p):
    """
    arguments : arguments_rest
              | empty
    """
    p[0] = p[1] if p[1] is not None else []

def p_arguments_rest(p):
    """
    arguments_rest : arguments_rest ',' argument
                   | argument
    """
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]


def p_argument(p):
    """
    argument : IDENTIFIER
    """
    p[0] = p[1]


###
# State tracking: Subroutine, Function, Do-Loop
# Used to print error when RETURN or CONTINUE statements are outside of context
###

def p_enter_subroutine(p):
    """
    enter_subroutine :
    """
    p.parser.context_stack.append("subroutine")


def p_exit_subroutine(p):
    """
    exit_subroutine :
    """
    p.parser.context_stack.pop()


def p_enter_function(p):
    """
    enter_function :
    """
    p.parser.context_stack.append("function")


def p_exit_function(p):
    """
    exit_function :
    """
    p.parser.context_stack.pop()


###
# Error handling
###

def p_error(p):
    record_syntax_error(parser, p)


###
# Parser setup
###

_GENERATED_DIR = Path(__file__).resolve().parent / "generated"
_GENERATED_DIR.mkdir(exist_ok=True)

parser = yacc.yacc(
    outputdir=str(_GENERATED_DIR),
    debugfile="parser.out",
    tabmodule="generated.parsetab",
)

# Auxiliary parser variables

# List of source lines for error reporting
parser.source_lines = []

# Source filename for error reporting
parser.source_filename = None

# Whether any parser (syntax/semantic) errors were encountered during parsing
parser.has_error = False

# List of diagnostics collected during lexing and parsing
parser.diagnostics = []

# Context stack used for semantic checks in RETURN statements
# Tracks nested contexts - functions and subroutines
parser.context_stack = []

# DO loop references
parser.do_references = []

# CONTINUE statement locations
parser.continue_locations = []

# List of main program unit
parser.program_locations = []

# Labels
parser.defined_labels = set()
parser.redefined_labels = set()
parser.referenced_labels = set()

parser.label_definition_locations = {}
parser.label_reference_locations = {}

# NOTE location schema:
# {
#     "lineno":    lineno,
#     "col_start": col_start,
#     "length":    length
# }


# Auxiliary function to clean parser state

def clear_parser_state(parser):
    """
    Clear parser state before parsing a new file.
    """
    parser.source_lines.clear()

    parser.source_filename = None

    parser.has_error = False

    parser.diagnostics.clear()

    parser.context_stack.clear()

    parser.do_references.clear()

    parser.continue_locations.clear()

    parser.program_locations.clear()

    parser.defined_labels.clear()
    parser.redefined_labels.clear()
    parser.referenced_labels.clear()

    parser.label_definition_locations.clear()
    parser.label_reference_locations.clear()


###
# CLI
###

def main():
    """
    Main function to run the Fortran 77 parser and semantic checks.
    """

    import argparse
    import sys

    from common import read_input, detect_source_format, visualize_ast
    from preprocessor import preprocess
    from semantics import semantic_checks
    from abstract_syntax_tree import (
        pretty_print,
        DEFAULT_VIS_OUTPUT_PATH
    )
    from error import flush_diagnostics

    global lexer, parser

    # CLI argument parsing
    parser_args = argparse.ArgumentParser(
        description="Parse Fortran 77 source code, run semantic checks, and "
                    "print the resulting AST.",
        add_help=False,
    )

    parser_args.add_argument(
        "input_file",
        nargs="?",
        help="Fortran source file. If omitted, read from stdin.",
    )

    parser_args.add_argument(
        "--format",
        choices=["fixed", "free"],
        default=None,
        help="The source format. If omitted, inferred from file extension; "
             "stdin defaults to fixed."
    )

    parser_args.add_argument(
        "--no-preprocess",
        action="store_true",
        default=False,
        help="Skip preprocessing stage.",
    )

    parser_args.add_argument(
        "--viz", "--visualize",
        dest="visualize",
        nargs="?",
        const=DEFAULT_VIS_OUTPUT_PATH,
        metavar="OUTPUT",
        help="Generate a Graphviz image of the AST."
    )

    parser_args.add_argument(
        "--no-open",
        action="store_true",
        default=False,
        help="Do not open the generated AST visualization file. "
             "Only valid with --viz/--visualize."
    )

    parser_args.add_argument(
        "-h", "--help",
        help="Show this help message and exit.",
        action="help"
    )

    args = parser_args.parse_args()

    if args.no_open and not args.visualize:
        parser_args.error("--no-open can only be used with --viz/--visualize")

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

    # Set up lexer and parser state
    clear_lexer_state(lexer)
    clear_parser_state(parser)

    source_lines = source_data.splitlines()

    lexer.source_lines = source_lines
    lexer.source_filename = source_filename

    parser.source_lines = source_lines
    parser.source_filename = source_filename

    # Parse the input data
    result = parser.parse(source_data, lexer=lexer, debug=False)

    # Propagate lexer errors to parser, since the lexer doesn't exit on error
    parser.diagnostics.extend(lexer.diagnostics)
    if lexer.has_error:
        parser.has_error = True

    if result is None:
        flush_diagnostics(parser)
        print(
            f"\n{len(parser.diagnostics)} error(s)/warning(s) encountered.",
            file=sys.stderr
        )
        print("[panic] parser could't produce an AST", file=sys.stderr)
        sys.exit(1)

    # Semantic checks
    result, _ = semantic_checks(parser, ast=result)

    # Exit with non-zero status if any errors were encountered
    flush_diagnostics(parser)

    if parser.has_error:
        print(
            f"\n{len(parser.diagnostics)} error(s)/warning(s) encountered.",
            file=sys.stderr
        )
        sys.exit(1)

    # Pretty print the resulting AST
    print()
    pretty_print(result)

    # Visualize AST
    if args.visualize:
        visualize_ast(
            result,
            output_path=args.visualize,
            open_result=not args.no_open
        )


if __name__ == "__main__":
    main()
