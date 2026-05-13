#!/usr/bin/env python3

import ply.yacc as yacc
from pathlib import Path

import abstract_syntax_tree as ast
from lexer import lexer, tokens
from error import print_error
from parser_rules.expressions import *
from parser_rules.conditionals import *
from parser_rules.loops import *
from parser_rules.io import *
from parser_rules.statements import *

# TODO Add implicit/explicit typing rules

start = 'program_unit'


def p_program_unit(p):
    """
    program_unit : PROGRAM IDENTIFIER statements END program_unit
                 | SUBROUTINE IDENTIFIER '(' arguments ')' statements END program_unit
                 | type FUNCTION IDENTIFIER '(' arguments ')' statements END program_unit
                 | statements
    """
    # AST node -- program: create a node with the program name and body;
    #          -- subroutine: create a node with the subroutine name, arguments, and body;
    #          -- function: create a node with the function name, return type, arguments, and body;
    #          -- statements: create a block node for preprocessed statement-only fixtures;
    #          -- empty files are handled by the statements branch
    if len(p) == 6:
        p[0] = ast.Program(p[2], p[3])

    elif len(p) == 8:
        p[0] = ast.Subroutine(p[2], p[4], p[6])

    elif len(p) == 10:
        p[0] = ast.Function(p[1], p[3], p[5], p[7])

    elif len(p) == 2:
        p[0] = ast.Block(p[1])

    else:
        p[0] = None


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
    parser.has_error = True

    if p is None:
        if parser.source_lines:
            lineno = len(parser.source_lines)
            line_content = parser.source_lines[-1]
            col_start = len(line_content) + 1
        else:
            lineno = 1
            line_content = ""
            col_start = 1

        print_error(
            error="unexpected end of file",
            line=line_content,
            lineno=lineno,
            col_start=col_start,
            length=1,
            filename=parser.source_filename,
            hint="perhaps you forgot the END statement"
        )

        return

    try:
        line_content = parser.source_lines[p.lineno - 1]
    except IndexError:
        line_content = ""

    line_start = p.lexer.lexdata.rfind("\n", 0, p.lexpos) + 1
    column = p.lexpos - line_start + 1

    print_error(
        error=f"syntax error at token {p.value!r}",
        line=line_content,
        lineno=p.lineno,
        col_start=column,
        length=max(1, len(str(p.value))),
        filename=parser.source_filename,
    )


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
    Clear parser state for labels and errors before parsing a new file.
    """
    parser.source_lines.clear()

    parser.source_filename = None

    parser.has_error = False

    parser.defined_labels.clear()
    parser.redefined_labels.clear()
    parser.referenced_labels.clear()

    parser.label_definition_locations.clear()
    parser.label_reference_locations.clear()


###
# CLI
###

if __name__ == '__main__':
    import argparse
    import sys
    from preprocessor import preprocess
    from semantics.labels import check_labels
    from abstract_syntax_tree import (
        pretty_print,
        visualize,
        open_file,
        DEFAULT_VISUALIZE_OUTPUT_PATH
    )

    # CLI argument parsing
    parser_args = argparse.ArgumentParser(
        description="Parse Fortran 77 source code and print the resulting AST."
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
    data = sys.stdin.read()

    # Pre-process the input data
    if not args.no_preprocess:
        try:
            data = preprocess(data, format=args.format)
        except Exception as exc:
            print(f"Preprocessing error: {exc}")
            sys.exit(1)

    # Set up the parser state and parse the input data
    clear_parser_state(parser)

    parser.source_lines = data.splitlines()

    # TODO actually support input file with -i or similar
    #      otherwise read from stdin
    parser.source_filename = "<stdin>"

    result = parser.parse(data, lexer=lexer, debug=False)

    if result is None:
        sys.exit(1)

    # Semantic checks
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
            open_file(args.visualize)
        except Exception as exc:
            print(f"AST Visualization error: {exc}")
