import abstract_syntax_tree as ast
from error import get_token_column, print_parser_token_error
from semantics.labels import (
    record_label_definition,
    record_label_reference,
    PREPROCESSED_LABEL_PREFIX_LEN
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
    statement : label_statement
              | nonlabel_statement
    """
    p[0] = p[1]


def p_label_statement(p):
    "label_statement : LABEL nonlabel_statement"
    label = p[1]

    record_label_definition(
        p.parser,
        label,
        lineno=p.lineno(1),
        col_start=get_token_column(p.slice[1]),
    )

    if isinstance(p[2], ast.Continue):
        p.parser.continue_locations.append({
            "label": label,
            "lineno": p.lineno(1),
            "col_start": get_token_column(p.slice[1]) + PREPROCESSED_LABEL_PREFIX_LEN,
            "length": len(str(label)),
        })

    p[0] = ast.Label(p[1], p[2])


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
                       | do_statement
                       | continue_statement
    """
    p[0] = p[1]


def p_declaration(p):
    "declaration : type declarator_list"
    p[0] = ast.Declare(p[1], p[2])


def p_declarator_list(p):
    "declarator_list : declarator declarator_list_tail"
    p[0] = [p[1]] + p[2]


# The preprocessor leaves line continuations as '&', so accept them in
# the same list structure as normal comma-separated declarators.
def p_declarator_list_tail(p):
    """
    declarator_list_tail : ',' declarator declarator_list_tail
                         | '&' declarator declarator_list_tail
                         | empty
    """
    if len(p) == 4:
        p[0] = [p[2]] + p[3]
    else:
        p[0] = []


def p_declarator(p):
    """
    declarator : IDENTIFIER
               | IDENTIFIER '(' expression_list ')'
    """
    location = ast.location_from_token(p.slice[1])

    if len(p) == 2:
        p[0] = ast.VarDeclarator(p[1], location)
    else:
        p[0] = ast.ArrayDeclarator(p[1], p[3], location)


def p_assignment(p):
    "assignment : variable '=' expression"
    p[0] = ast.Assign(p[1], p[3])


def p_variable(p):
    """
    variable : IDENTIFIER
             | IDENTIFIER '(' expression_list ')'
    """
    location = ast.location_from_token(p.slice[1])

    if len(p) == 2:
        p[0] = ast.Var(p[1], location)
    else:
        p[0] = ast.ArrayRef(p[1], p[3], location)


def p_goto_statement(p):
    "goto_statement : GOTO INTEGER_NUMBER"
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
    "stop_statement : STOP"
    p[0] = ast.Stop()


def p_return_statement(p):
    "return_statement : RETURN"
    if not any(ctx in p.parser.context_stack
               for ctx in {"function", "subroutine"}):

        print_parser_token_error(
            p.parser,
            p.slice[1],
            message="RETURN statement outside FUNCTION or SUBROUTINE"
        )

    p[0] = ast.Return()


def p_call_statement(p):
    """
    call_statement : CALL IDENTIFIER '(' expression_list ')'
                   | CALL IDENTIFIER
    """
    location = ast.location_from_token(p.slice[2])

    if len(p) == 6:
        p[0] = ast.CallStatement(p[2], p[4], location)
    else:
        p[0] = ast.CallStatement(p[2], [], location)


def p_do_statement(p):
    "do_statement : DO INTEGER_NUMBER IDENTIFIER '=' expression ',' expression"
    end_label = p[2]

    record_label_reference(
        p.parser,
        end_label,
        lineno=p.lineno(2),
        col_start=get_token_column(p.slice[2]),
    )

    p.parser.do_references.append({
        "end_label": end_label,
        "lineno": p.lineno(2),
        "col_start": get_token_column(p.slice[2]),
        "length": len(str(end_label)),
    })

    p[0] = ast.Do(
        end_label=end_label,
        variable=p[3],
        start=p[5],
        end=p[7],
    )


def p_continue_statement(p):
    "continue_statement : CONTINUE"
    p[0] = ast.Continue()
