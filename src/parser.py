#!/usr/bin/env python3

import ply.yacc as yacc
from pathlib import Path

import abstract_syntax_tree as ast
from lexer import lexer, tokens, clear_lexer_state
from error import print_syntax_error, get_lexer_token_column
from parser_rules.expressions import *
from parser_rules.conditionals import *
from parser_rules.loops import *
from parser_rules.io import *
from parser_rules.statements import *

# TODO Add implicit/explicit typing rules

start = 'file'


def p_file(p):
    """
    file : program_units
    """
    filename = getattr(p.parser, "source_filename", "<unknown>")
    p[0] = ast.File(filename, p[1])


def p_file_empty(p):
    """
    file : empty
    """
    filename = getattr(p.parser, "source_filename", "<unknown>")
    p[0] = ast.File(filename, [])


###
# Program units
###

def p_program_units(p):
    """
    program_units : program_unit program_units
                  | program_unit
    """
    if len(p) == 3:
        p[0] = [p[1]] + p[2]
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
        "col_start": get_lexer_token_column(p.slice[1]),
        "length": len(p[1]),
    })

    p[0] = ast.Program(p[2], p[3])


def p_subroutine(p):
    """
    subroutine : SUBROUTINE IDENTIFIER '(' arguments ')' statements END
    """
    p[0] = ast.Subroutine(p[2], p[4], p[6])


def p_function(p):
    """
    function : type FUNCTION IDENTIFIER '(' arguments ')' statements END
    """
    p[0] = ast.Function(p[1], p[3], p[5], p[7])


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
    arguments : argument arguments_rest
    """
    # AST node: build the argument list with any continuation pieces.
    p[0] = [p[1]] + p[2]


def p_arguments_rest(p):
    """
    arguments_rest : ',' argument arguments_rest
                   |
    """
    # AST node: if there are more arguments, create a list of them;
    # Otherwise, an empty list
    if len(p) == 4:
        p[0] = [p[2]] + p[3]
    else:
        p[0] = []


def p_argument(p):
    """
    argument : IDENTIFIER
    """
    # AST node: just pass the argument name up the tree
    p[0] = p[1]


###
# Empty production (ε)
###

def p_empty(p):
    """
    empty :
    """
    p[0] = None


###
# Error handling
###

def p_error(p):
    """
    Report syntax errors using compiler-style diagnostics.
    """

    print_syntax_error(parser, p)


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
    from common import read_input, open_file
    from preprocessor import preprocess
    from semantics.labels import check_labels
    from semantics.program import check_program
    from abstract_syntax_tree import (
        pretty_print,
        visualize,
        DEFAULT_VISUALIZE_OUTPUT_PATH
    )

    global lexer, parser

    # CLI argument parsing
    parser_args = argparse.ArgumentParser(
        description="Parse Fortran 77 source code and print the resulting AST."
    )

    parser_args.add_argument(
        "input_file",
        nargs="?",
        help="Fortran source file to lex. If omitted, read from stdin.",
    )

    parser_args.add_argument(
        "--format",
        choices=["fixed", "free"],
        default="fixed",
        help="The source format (default: fixed)"
    )

    parser_args.add_argument(
        "--no-preprocess",
        action="store_true",
        default=False,
        help="Skip preprocessing and parse the raw input directly",
    )

    parser_args.add_argument(
        "--visualize", "--vis",
        nargs="?",
        const=DEFAULT_VISUALIZE_OUTPUT_PATH,
        metavar="OUTPUT",
        help=(
            "Generate a Graphviz image of the AST "
            f"(default output: {DEFAULT_VISUALIZE_OUTPUT_PATH})"
        ),
    )

    args = parser_args.parse_args()

    # Read input data
    try:
        source_filename, source_data = read_input(args.input_file)
    except Exception as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        sys.exit(1)

    # Pre-process the input data
    if not args.no_preprocess:
        try:
            source_data = preprocess(source_data, format=args.format)
        except Exception as exc:
            print(f"Preprocessing error: {exc}", file=sys.stderr)
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

    # Propagate lexer errors to parser error state,
    # since the lexer doesn't exit on error
    if lexer.has_error:
        parser.has_error = True

    if result is None:
        sys.exit(1)

    # Semantic checks
    check_program(parser)
    check_labels(parser)

    if parser.has_error:
        sys.exit(1)

    # Pretty print the resulting AST
    print()
    pretty_print(result)

    # Visualize AST
    if args.visualize:
        try:
            visualize_file = visualize(result, output_path=args.visualize)
            print(f"\nAST visualization generated at: {visualize_file}")
            open_file(visualize_file)
        except Exception as exc:
            print(f"AST Visualization error: {exc}")

    # Exit with non-zero status if any errors were encountered
    if parser.has_error:
        sys.exit(1)


if __name__ == "__main__":
    main()
