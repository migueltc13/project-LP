import abstract_syntax_tree as ast
from error import get_token_column
from semantics.labels import (
    record_label_definition,
    record_label_reference
)


def p_statements(p):
    """
    statements : statement statements
               | empty
    """
    if len(p) == 3:
        p[0] = [p[1]] + p[2]
    else:
        p[0] = []


def p_statement(p):
    """
    statement : LABEL nonlabel_statement
              | nonlabel_statement
    """
    if len(p) == 3:
        label = p[1]

        record_label_definition(
            p.parser,
            label,
            lineno=p.lineno(1),
            col_start=get_token_column(p.slice[1]),
        )

        p[0] = ast.Label(p[1], p[2])
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
    if p.slice[1].type == "CONTINUE":
        p[0] = ast.Continue()
    else:
        p[0] = p[1]


def p_declaration(p):
    """
    declaration : type declarator_list
    """
    # AST node: create a node with the type and list of declarators
    p[0] = ast.Declare(p[1], p[2])


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
        p[0] = ast.VarDeclarator(p[1])
    else:
        p[0] = ast.ArrayDeclarator(p[1], p[3])


def p_assignment(p):
    """
    assignment : variable '=' expression
    """
    p[0] = ast.Assign(p[1], p[3])


def p_goto_statement(p):
    """
    goto_statement : GOTO INTEGER_NUMBER
    """
    # INFO We use the INTEGER_NUMBER token here since lexer will identify
    #      the label as INTEGER_NUMBER and not LABEL.

    label = p[2]

    record_label_reference(
        p.parser,
        label,
        lineno=p.lineno(2),
        col_start=get_token_column(p.slice[2])
    )

    p[0] = ast.Goto(label)


def p_stop_statement(p):
    """
    stop_statement : STOP
    """
    # AST node: just create a node for the STOP statement
    p[0] = ast.Stop()


def p_return_statement(p):
    """
    return_statement : RETURN
    """
    # AST node: just create a node for the RETURN statement
    p[0] = ast.Return()


def p_call_statement(p):
    """
    call_statement : CALL IDENTIFIER '(' expression_list ')'
                   | CALL IDENTIFIER
    """
    # AST node: if it's a function call with arguments, create a node with the
    # function name and arguments;
    # Otherwise, create a node with the function name and an empty argument list
    if len(p) == 6:
        p[0] = ast.CallStatement(p[2], p[4])
    else:
        p[0] = ast.CallStatement(p[2], [])


def p_variable(p):
    """
    variable : IDENTIFIER
             | IDENTIFIER '(' expression_list ')'
    """
    # AST node: if it's an array reference, create a node with the name and indices;
    # Otherwise, just create a node for the variable
    if len(p) == 2:
        p[0] = ast.Var(p[1])
    else:
        p[0] = ast.ArrayRef(p[1], p[3])
