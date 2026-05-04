# Conditionals

# TODO: Add ELSEIF support

def p_if_statement(p):
    """
    if_statement : IF expression THEN statements if_statement_rest ENDIF
    """
    # AST node: condition, then-branch, and optional else-branch.
    p[0] = ('if', p[2], p[4], p[5])


def p_if_statement_rest(p):
    """
    if_statement_rest : ELSE statements
                      | empty
    """
    # AST node: if there's an else branch, pass the statements up the tree;
    if len(p) == 3:
        p[0] = p[2]
    else:
        p[0] = None


def p_empty(p):
    """
    empty :
    """
    p[0] = None
