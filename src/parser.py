#!/usr/bin/env python3

import ply.yacc as yacc
from lexer import lexer, tokens
from preprocessor import preprocess
from parser_rules.expressions import *
from parser_rules.conditionals import *
from parser_rules.loops import *
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
        p[0] = ('program', p[2], p[3])
    elif len(p) == 8:
        p[0] = ('subroutine', p[2], p[4], p[6])
    elif len(p) == 10:
        p[0] = ('function', p[1], p[3], p[5], p[7])
    elif len(p) == 2:
        p[0] = ('block', p[1])
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
# Parser
###

def p_error(p):
    if p is None:
        print("Syntax error at EOF")
    else:
        print(f"Syntax error at '{p.value}' (line {p.lineno})")


# TODO rename output files
parser = yacc.yacc()


if __name__ == '__main__':
    import argparse
    import sys

    parser_args = argparse.ArgumentParser(
        description="Run syntax analysis on Fortran source code."
    )
    parser_args.add_argument("--format", choices=["fixed", "free"], default="fixed",
                             help="The source format (default: fixed)")
    parser_args.add_argument("--no-preprocess", action="store_true", default=False,
                             help="Skip preprocessing and parse the raw input directly")
    args = parser_args.parse_args()

    data = sys.stdin.read()

    if not args.no_preprocess:
        try:
            data = preprocess(data, format=args.format)
        except Exception as exc:
            print(f"Preprocessing error: {exc}")
            sys.exit(1)

    result = parser.parse(data, lexer=lexer, debug=False)
    print(result)
