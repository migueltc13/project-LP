import abstract_syntax_tree as ast

# Conditional grammar used by the parser.

# This module handles the structured IF form supported by the lexer:
# IF ... THEN ... [ELSE ...] ENDIF.

# TODO: Add support for ELSEIF

def p_if_statement(p):
    """
    if_statement : IF expression THEN statements if_statement_rest ENDIF
    """
    # AST node: condition, then-branch, and optional else-branch.
    p[0] = ast.If(p[2], p[4], p[5])


def p_if_statement_rest(p):
    """
    if_statement_rest : ELSE statements
                      | empty
    """
    # The ELSE branch is optional, so the empty production maps to None.
    if len(p) == 3:
        p[0] = p[2]
    else:
        p[0] = None
