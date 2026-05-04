# Statements

def p_statements(p):
    """
    statements : statement statements
               | empty
    """
    # AST node: if there are statements, create a list of them;
    # Otherwise, an empty list
    if len(p) == 3:
        p[0] = [p[1]] + p[2]
    else:
        p[0] = []

def p_statement(p):
    """
    statement : LABEL nonlabel_statement
              | nonlabel_statement
    """
    # AST node: if there's a label, create a node with the label and statement;
    # Otherwise, just pass the statement up the tree
    if len(p) == 3:
        p[0] = ('label', p[1], p[2])
    else:
        p[0] = p[1]


def p_nonlabel_statement(p):
    """
    nonlabel_statement : declaration
                       | assignment
                       | print_stmt
                       | read_stmt
                       | write_stmt
                       | goto_statement
                       | stop_statement
                       | return_statement
                       | call_statement
                       | if_statement
                       | do_loop
                       | CONTINUE
    """
    # AST node: just pass the statement up the tree
    p[0] = p[1]


def p_declaration(p):
    """
    declaration : type declarator_list
    """
    # AST node: create a node with the type and list of declarators
    p[0] = ('declare', p[1], p[2])


def p_declarator_list(p):
    """
    declarator_list : declarator declarator_list_tail
    """
    # AST node: build the declaration list with any continuation pieces.
    p[0] = [p[1]] + p[2]


# The preprocessor leaves line continuations as '&', so accept them in
# the same list structure as normal comma-separated declarators.
def p_declarator_list_tail(p):
    """
    declarator_list_tail : ',' declarator declarator_list_tail
                         | '&' declarator declarator_list_tail
                         | empty
    """
    # AST node: if there are more declarators, create a list of them;
    # Otherwise, an empty list
    if len(p) == 4:
        p[0] = [p[2]] + p[3]
    else:
        p[0] = []


def p_declarator(p):
    """
    declarator : IDENTIFIER
               | IDENTIFIER '(' expression_list ')'
    """
    # AST node: if it's an array declaration, create a node with the name and dimensions;
    # Otherwise, just create a node for the variable declaration
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = ('array', p[1], p[3])


def p_assignment(p):
    """
    assignment : variable '=' expression
    """
    # AST node: create a node with the variable and expression
    p[0] = ('assign', p[1], p[3])


def p_print_stmt(p):
    """
    print_stmt : PRINT ASTERISK ',' expression_list
               | PRINT expression_list
    """
    # AST node: if there's a format specifier, create a node with the expressions;
    # Otherwise, create a node with the expressions and a default format
    if len(p) == 5:
        p[0] = ('print', p[4])
    else:
        p[0] = ('print', p[2])


def p_read_stmt(p):
    """
    read_stmt : READ ASTERISK ',' variable_list
              | READ variable_list
    """
    # AST node: if there's a format specifier, create a node with the variables;
    # Otherwise, create a node with the variables and a default format
    if len(p) == 5:
        p[0] = ('read', p[4])
    else:
        p[0] = ('read', p[2])


def p_write_stmt(p):
    """
    write_stmt : WRITE ASTERISK ',' expression_list
               | WRITE expression_list
    """
    # AST node: if there's a format specifier, create a node with the expressions;
    # Otherwise, create a node with the expressions and a default format
    if len(p) == 5:
        p[0] = ('write', p[4])
    else:
        p[0] = ('write', p[2])


def p_goto_statement(p):
    """
    goto_statement : GOTO NUMBER
    """
    # AST node: create a node with the target label
    p[0] = ('goto', p[2])


def p_stop_statement(p):
    """
    stop_statement : STOP
    """
    # AST node: just create a node for the STOP statement
    p[0] = ('stop',)


def p_return_statement(p):
    """
    return_statement : RETURN
    """
    # AST node: just create a node for the RETURN statement
    p[0] = ('return',)


def p_call_statement(p):
    """
    call_statement : CALL IDENTIFIER '(' expression_list ')'
                   | CALL IDENTIFIER
    """
    # AST node: if it's a function call with arguments, create a node with the
    # function name and arguments;
    # Otherwise, create a node with the function name and an empty argument list
    if len(p) == 6:
        p[0] = ('call', p[2], p[4])
    else:
        p[0] = ('call', p[2], [])


def p_variable_list(p):
    """
    variable_list : variable variable_list_tail
    """
    # AST node: build the variable list with any continuation pieces.
    p[0] = [p[1]] + p[2]


# The preprocessor leaves line continuations as '&', so accept them in
# the same list structure as normal comma-separated variables.
def p_variable_list_tail(p):
    """
    variable_list_tail : ',' variable variable_list_tail
                       | '&' variable variable_list_tail
                       | empty
    """
   # AST node: if there are more variables, create a list of them;
   # Otherwise, an empty list
    if len(p) == 4:
        p[0] = [p[2]] + p[3]
    else:
        p[0] = []


def p_expression_list(p):
    """
    expression_list : expression expression_list_tail
    """
    # AST node: build the expression list with any continuation pieces.
    p[0] = [p[1]] + p[2]


# The preprocessor leaves line continuations as '&', so accept them in
# the same list structure as normal comma-separated expressions.
def p_expression_list_tail(p):
    """
    expression_list_tail : ',' expression expression_list_tail
                         | '&' expression expression_list_tail
                         | empty
    """
   # AST node: if there are more expressions, create a list of them;
    # Otherwise, an empty list
    if len(p) == 4:
        p[0] = [p[2]] + p[3]
    else:
        p[0] = []


def p_variable(p):
    """
    variable : IDENTIFIER
             | IDENTIFIER '(' expression_list ')'
    """
    # AST node: if it's an array reference, create a node with the name and indices;
    # Otherwise, just create a node for the variable
    if len(p) == 2:
        p[0] = ('var', p[1])
    else:
        p[0] = ('array_ref', p[1], p[3])