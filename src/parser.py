#!/usr/bin/env python3

import ply.yacc as yacc
from lexer import lexer, tokens
from parser_rules.conditionals import *

# TODO Add implicit/explicit typing rules

start = 'program_unit'

def p_program_unit(p):
    """
    program_unit : PROGRAM IDENTIFIER statements END program_unit
                 | SUBROUTINE IDENTIFIER '(' arguments ')' statements END program_unit
                 | type FUNCTION IDENTIFIER '(' arguments ')' statements END program_unit
                 |
    """

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

###
# Arguments for functions and subroutines declarations
###

# TODO check if "type IDENTIFIER" is supported in Fortran 77
def p_arguments(p):
    """
    arguments : argument arguments_rest
    """

def p_arguments_rest(p):
    """
    arguments_rest : ',' argument arguments_rest
                   |
    """

def p_argument(p):
    """
    argument : IDENTIFIER
    """

###
# Expressions
###

def p_expression(p):
    """
    expression : NUMBER
    """

###
# Statements
###

def p_statements(p):
    """
    statements : statement statements
               |
    """

# NOTE Statements (in its own file) should have a separation for
# normal statements, function statements (subroutine too), and do statements

# NOTE These statements are general, meaning they can appear anywhere within a program unit.

def p_statement(p):
    """
    statement : if_statement
              | CONTINUE
              | LABEL statement
    """

###
# Loops
###

# TODO

###
# Parser
###

def p_error(p):
    print(f"Syntax error at '{p.value}' (line {p.lineno})")


# TODO rename output files
parser = yacc.yacc()


if __name__ == '__main__':
    import sys
    data = sys.stdin.read()
    result = parser.parse(data, lexer=lexer, debug=False)
    print(result)
