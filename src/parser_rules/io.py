import abstract_syntax_tree as ast


# Input/output grammar used by the parser.

# This module owns the PRINT, READ, and WRITE productions plus the
# comma/continuation-separated list helpers they rely on.

def p_print_stmt(p):
    """
    print_stmt : PRINT ASTERISK ',' expression_list
               | PRINT expression_list
    """
    if len(p) == 5:
        p[0] = ast.Print(p[4])
    else:
        p[0] = ast.Print(p[2])


def p_read_stmt(p):
    """
    read_stmt : READ ASTERISK ',' variable_list
              | READ variable_list
    """
    if len(p) == 5:
        p[0] = ast.Read(p[4])
    else:
        p[0] = ast.Read(p[2])


def p_write_stmt(p):
    """
    write_stmt : WRITE ASTERISK ',' expression_list
               | WRITE expression_list
    """
    if len(p) == 5:
        p[0] = ast.Write(p[4])
    else:
        p[0] = ast.Write(p[2])


def p_variable_list(p):
    """
    variable_list : variable variable_list_tail
    """
    p[0] = [p[1]] + p[2]


def p_variable_list_tail(p):
    """
    variable_list_tail : ',' variable variable_list_tail
                       | empty
    """
    if len(p) == 4:
        p[0] = [p[2]] + p[3]
    else:
        p[0] = []


def p_expression_list(p):
    """
    expression_list : expression expression_list_tail
    """
    p[0] = [p[1]] + p[2]


def p_expression_list_tail(p):
    """
    expression_list_tail : ',' expression expression_list_tail
                         | empty
    """
    if len(p) == 4:
        p[0] = [p[2]] + p[3]
    else:
        p[0] = []
