import abstract_syntax_tree as ast


# This module handles the structured IF form supported by the lexer:
# IF ... THEN ... [ELSE ...] ENDIF.

# TODO: Add support for ELSEIF

def p_if_statement(p):
    """
    if_statement : IF expression THEN statements if_statement_rest ENDIF
    """
    p[0] = ast.If(p[2], p[4], p[5])


def p_if_statement_rest(p):
    """
    if_statement_rest : ELSE statements
                      | empty
    """
    if len(p) == 3:
        p[0] = p[2]
    else:
        p[0] = None
