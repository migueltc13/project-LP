import abstract_syntax_tree as ast

def p_empty(p):
    """empty :"""
    p[0] = None


def p_expression_list(p):
    """
    expression_list : expression_list ',' expression
                    | expression
    """
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]


# Optional argument list for function calls
def p_argument_list_opt(p):
    """
    argument_list_opt : argument_list
                      | empty
    """
    p[0] = [] if p[1] is None else p[1]


# Argument list is compose of one or more expressions separated by commas
def p_argument_list(p):
    """
    argument_list : expression
                  | argument_list ',' expression
    """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]
